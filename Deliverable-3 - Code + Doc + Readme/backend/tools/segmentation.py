import torch
import torch.nn as nn
from torch.nn import init
import functools
from torchvision import models
import os
import numpy as np
import cv2

# --- Ported from SkyAR/networks.py ---

class Identity(nn.Module):
    def forward(self, x):
        return x

def get_norm_layer(norm_type='instance'):
    if norm_type == 'batch':
        norm_layer = functools.partial(nn.BatchNorm2d, affine=True, track_running_stats=True)
    elif norm_type == 'instance':
        norm_layer = functools.partial(nn.InstanceNorm2d, affine=False, track_running_stats=False)
    elif norm_type == 'none':
        norm_layer = lambda x: Identity()
    else:
        raise NotImplementedError('normalization layer [%s] is not found' % norm_type)
    return norm_layer

def init_weights(net, init_type='normal', init_gain=0.02):
    def init_func(m):
        classname = m.__class__.__name__
        if hasattr(m, 'weight') and (classname.find('Conv') != -1 or classname.find('Linear') != -1):
            if init_type == 'normal':
                init.normal_(m.weight.data, 0.0, init_gain)
            elif init_type == 'xavier':
                init.xavier_normal_(m.weight.data, gain=init_gain)
            elif init_type == 'kaiming':
                init.kaiming_normal_(m.weight.data, a=0, mode='fan_in')
            elif init_type == 'orthogonal':
                init.orthogonal_(m.weight.data, gain=init_gain)
            else:
                raise NotImplementedError('initialization method [%s] is not implemented' % init_type)
            if hasattr(m, 'bias') and m.bias is not None:
                init.constant_(m.bias.data, 0.0)
        elif classname.find('BatchNorm2d') != -1:
            init.normal_(m.weight.data, 1.0, init_gain)
            init.constant_(m.bias.data, 0.0)

    net.apply(init_func)

def init_net(net, init_type='normal', init_gain=0.02, gpu_ids=[]):
    if len(gpu_ids) > 0:
        assert(torch.cuda.is_available())
        net.to(gpu_ids[0])
        net = torch.nn.DataParallel(net, gpu_ids)
    init_weights(net, init_type, init_gain=init_gain)
    return net

class AddCoords(nn.Module):
    def __init__(self, with_r=False):
        super().__init__()
        self.with_r = with_r

    def forward(self, input_tensor):
        batch_size, _, y_dim, x_dim = input_tensor.size()

        yy_channel = torch.arange(y_dim).repeat(1, x_dim, 1).transpose(1, 2).type_as(input_tensor)
        yy_channel = yy_channel.float() / y_dim
        yy_channel = yy_channel.repeat(batch_size, 1, 1, 1)

        ret = torch.cat([input_tensor, yy_channel], dim=1)
        return ret

class CoordConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, **kwargs):
        super().__init__()
        in_size = in_channels + 1
        self.conv = nn.Conv2d(in_size, out_channels, **kwargs)

    def forward(self, x):
        ret = AddCoords()(x)
        ret = self.conv(ret)
        return ret

class ResNet50FCN(torch.nn.Module):
    def __init__(self, coordconv=False):
        super(ResNet50FCN, self).__init__()
        # Use weights=ResNet50_Weights.IMAGENET1K_V1 instead of pretrained=True for newer torch versions
        try:
            from torchvision.models import ResNet50_Weights
            self.resnet = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
        except ImportError:
            self.resnet = models.resnet50(pretrained=True)
            
        self.relu = nn.ReLU()
        self.upsample = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.coordconv = coordconv

        if coordconv:
            self.conv_in = CoordConv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
            self.conv_fpn1 = CoordConv2d(2048, 1024, kernel_size=3, padding=1)
            self.conv_fpn2 = CoordConv2d(1024, 512, kernel_size=3, padding=1)
            self.conv_fpn3 = CoordConv2d(512, 256, kernel_size=3, padding=1)
            self.conv_fpn4 = CoordConv2d(256, 64, kernel_size=3, padding=1)
            self.conv_pred_1 = CoordConv2d(64, 64, kernel_size=3, padding=1)
            self.conv_pred_2 = CoordConv2d(64, 1, kernel_size=3, padding=1)
        else:
            self.conv_fpn1 = nn.Conv2d(2048, 1024, kernel_size=3, padding=1)
            self.conv_fpn2 = nn.Conv2d(1024, 512, kernel_size=3, padding=1)
            self.conv_fpn3 = nn.Conv2d(512, 256, kernel_size=3, padding=1)
            self.conv_fpn4 = nn.Conv2d(256, 64, kernel_size=3, padding=1)
            self.conv_pred_1 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
            self.conv_pred_2 = nn.Conv2d(64, 1, kernel_size=3, padding=1)

        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        if self.coordconv:
            x = self.conv_in(x)
        else:
            x = self.resnet.conv1(x)
        x = self.resnet.bn1(x)
        x = self.resnet.relu(x)
        x = self.resnet.maxpool(x)

        x_4 = self.resnet.layer1(x) # 1/4
        x_8 = self.resnet.layer2(x_4) # 1/8
        x_16 = self.resnet.layer3(x_8) # 1/16
        x_32 = self.resnet.layer4(x_16) # 1/32

        # FPN with size matching
        x = self.upsample(self.relu(self.conv_fpn1(x_32)))
        
        # Ensure sizes match before addition
        if x.size()[2:] != x_16.size()[2:]:
            x = nn.functional.interpolate(x, size=x_16.size()[2:], mode='bilinear', align_corners=True)
        x = self.upsample(self.relu(self.conv_fpn2(x + x_16)))
        
        if x.size()[2:] != x_8.size()[2:]:
            x = nn.functional.interpolate(x, size=x_8.size()[2:], mode='bilinear', align_corners=True)
        x = self.upsample(self.relu(self.conv_fpn3(x + x_8)))
        
        if x.size()[2:] != x_4.size()[2:]:
            x = nn.functional.interpolate(x, size=x_4.size()[2:], mode='bilinear', align_corners=True)
        x = self.upsample(self.relu(self.conv_fpn4(x + x_4)))

        x = self.upsample(self.relu(self.conv_pred_1(x)))
        x = self.sigmoid(self.conv_pred_2(x))

        return x

def define_G(netG='coord_resnet50', gpu_ids=[]):
    net = None
    if netG == 'resnet50':
        net = ResNet50FCN()
    elif netG == 'coord_resnet50':
        net = ResNet50FCN(coordconv=True)
    else:
        raise NotImplementedError('Generator model name [%s] is not recognized' % netG)
    return init_net(net, 'normal', 0.02, gpu_ids)


# --- Wrapper Class ---

class SkySegmenter:
    def __init__(self, ckpt_path, device='cpu'):
        self.device = torch.device(device)
        self.net_G = define_G(netG='coord_resnet50').to(self.device)
        self.load_model(ckpt_path)

    def load_model(self, ckpt_path):
        if not os.path.exists(ckpt_path):
            raise FileNotFoundError(f"Checkpoint not found at {ckpt_path}")
        
        try:
            checkpoint = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        except TypeError:
            checkpoint = torch.load(ckpt_path, map_location=self.device)

        if 'model_G_state_dict' in checkpoint:
            self.net_G.load_state_dict(checkpoint['model_G_state_dict'])
        else:
            self.net_G.load_state_dict(checkpoint) # Fallback if structure is different
        
        self.net_G.eval()

    def predict(self, img_tensor):
        """
        Args:
            img_tensor: Preprocessed image tensor (1, 3, H, W)
        Returns:
            mask: Numpy array (H, W, 1)
        """
        with torch.no_grad():
            _, _, h, w = img_tensor.shape
            
            # ResNet typically works well with sizes divisible by 32
            pad_h = (32 - h % 32) % 32
            pad_w = (32 - w % 32) % 32
            
            if pad_h > 0 or pad_w > 0:
                # Pad the input tensor
                img_tensor_padded = torch.nn.functional.pad(
                    img_tensor, 
                    (0, pad_w, 0, pad_h), 
                    mode='reflect'
                )
                pred = self.net_G(img_tensor_padded.to(self.device))
                # Remove padding from prediction
                pred = pred[:, :, :h, :w]
            else:
                pred = self.net_G(img_tensor.to(self.device))
            
            if pred.shape[2:] != (h, w):
                pred = torch.nn.functional.interpolate(
                    pred, 
                    size=(h, w), 
                    mode='bilinear', 
                    align_corners=True
                )
            
            pred = pred[0, :].permute([1, 2, 0]) # (H, W, 1)
            pred = torch.cat([pred, pred, pred], dim=-1) # (H, W, 3)
            
            pred = pred.detach().cpu().numpy()
            pred = np.clip(pred, 0.0, 1.0)
            
        return pred