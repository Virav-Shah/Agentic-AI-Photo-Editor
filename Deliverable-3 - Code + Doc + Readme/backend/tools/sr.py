"""
Super-Resolution Tool using SwinIR
Real implementation with SwinIR model for 4x upscaling
Includes patchwise processing for large images and HD detection
"""

import numpy as np
import cv2
from typing import Dict, Any, Union, Tuple
from PIL import Image
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Global model cache
_sr_model = None
_sr_device = None

# Resolution thresholds
HD_WIDTH = 1280
HD_HEIGHT = 720
FULL_HD_WIDTH = 1920
FULL_HD_HEIGHT = 1080

# Patch processing settings - OPTIMIZED for GPU
MAX_PATCH_SIZE = 512  # Larger patches for GPU 
PATCH_OVERLAP = 64    # Increased overlap for better blending
BATCH_SIZE = 4        # Process multiple patches at once on GPU


def _load_sr_model():
    """Load SwinIR model (singleton pattern)."""
    global _sr_model, _sr_device

    if _sr_model is not None:
        return _sr_model, _sr_device

    try:
        import torch
        import torch.nn as nn

        # Add lr_sr to path for imports
        lr_sr_path = Path(__file__).parent.parent / "models"
        if str(lr_sr_path) not in sys.path:
            sys.path.insert(0, str(lr_sr_path))

        from dependencies.network_swinir import SwinIR

        # Set device - prioritize CUDA
        if torch.cuda.is_available():
            _sr_device = torch.device("cuda")

        else:
            _sr_device = torch.device("cpu")

        # Model path
        model_path = lr_sr_path / "003_realSR_BSRGAN_DFO_s64w8_SwinIR-M_x4_GAN.pth"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")

        # Create model
        _sr_model = SwinIR(
            upscale=4,
            img_size=64,
            patch_size=1,
            in_chans=3,
            embed_dim=180,
            depths=[6, 6, 6, 6, 6, 6],
            num_heads=[6, 6, 6, 6, 6, 6],
            window_size=8,
            mlp_ratio=2.,
            qkv_bias=True,
            qk_scale=None,
            drop_rate=0.,
            attn_drop_rate=0.,
            drop_path_rate=0.1,
            norm_layer=nn.LayerNorm,
            ape=False,
            patch_norm=True,
            use_checkpoint=False,
            img_range=1.,
            upsampler='nearest+conv',
            resi_connection='1conv'
        )

        # Load weights
        checkpoint = torch.load(str(model_path), map_location=_sr_device)

        if 'params_ema' in checkpoint:
            state_dict = checkpoint['params_ema']
        elif 'params' in checkpoint:
            state_dict = checkpoint['params']
        else:
            state_dict = checkpoint

        _sr_model.load_state_dict(state_dict, strict=True)
        _sr_model.eval()
        _sr_model.to(_sr_device)

        return _sr_model, _sr_device

    except Exception as e:
        return None, None


def _check_resolution(h: int, w: int) -> Tuple[bool, str]:
    """
    Check if image is already HD or higher resolution.

    Returns:
        (is_hd, resolution_name)
    """
    pixels = h * w

    # Check for 4K (3840x2160)
    if w >= 3840 or h >= 2160:
        return True, "4K"

    # Check for Full HD (1920x1080)
    if w >= FULL_HD_WIDTH or h >= FULL_HD_HEIGHT:
        return True, "Full HD (1080p)"

    # Check for HD (1280x720)
    if w >= HD_WIDTH or h >= HD_HEIGHT:
        return True, "HD (720p)"

    # Also check by total pixels (for non-standard aspect ratios)
    if pixels >= FULL_HD_WIDTH * FULL_HD_HEIGHT:
        return True, "Full HD equivalent"

    if pixels >= HD_WIDTH * HD_HEIGHT:
        return True, "HD equivalent"

    return False, "SD"


def _run_swinir_patch(patch: np.ndarray, model, device, scale: int = 4) -> np.ndarray:
    """Run SwinIR inference on a single patch - GPU optimized."""
    import torch
    import torch.nn.functional as F

    # Convert BGR to RGB
    patch_rgb = cv2.cvtColor(patch, cv2.COLOR_BGR2RGB)

    # Convert to tensor directly (faster than PIL)
    image_tensor = torch.from_numpy(patch_rgb).permute(2, 0, 1).float() / 255.0
    image_tensor = image_tensor.unsqueeze(0).to(device, non_blocking=True)

    h, w = patch.shape[:2]

    # Pad for window size
    window_size = 8
    pad_h = (window_size - h % window_size) % window_size
    pad_w = (window_size - w % window_size) % window_size

    if pad_h > 0 or pad_w > 0:
        image_tensor = F.pad(image_tensor, (0, pad_w, 0, pad_h), 'reflect')

    # Run inference
    with torch.no_grad():
        sr_tensor = model(image_tensor)

    # Crop to original size * scale
    h_output = h * scale
    w_output = w * scale
    sr_tensor = sr_tensor[:, :, :h_output, :w_output]

    # Clamp and convert back
    sr_tensor = torch.clamp(sr_tensor, 0, 1)

    # Convert to numpy efficiently
    sr_np = (sr_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

    # Convert RGB to BGR
    sr_bgr = cv2.cvtColor(sr_np, cv2.COLOR_RGB2BGR)

    return sr_bgr


def _run_swinir_patchwise(image: np.ndarray, scale: int = 4) -> np.ndarray:
    """
    Run SwinIR inference using OPTIMIZED patchwise processing.
    - Larger patches (512x512 instead of 256x256)
    - CUDA GPU acceleration
    """
    import torch

    model, device = _load_sr_model()

    if model is None:
        raise RuntimeError("SwinIR model not available")

    h, w = image.shape[:2]

    # Calculate number of patches
    patch_size = MAX_PATCH_SIZE
    overlap = PATCH_OVERLAP
    stride = patch_size - overlap

    # Output dimensions
    out_h = h * scale
    out_w = w * scale
    out_patch_size = patch_size * scale
    out_overlap = overlap * scale
    out_stride = stride * scale

    # Initialize output and weight arrays
    output = np.zeros((out_h, out_w, 3), dtype=np.float32)
    weight = np.zeros((out_h, out_w, 1), dtype=np.float32)

    # Create blending weights (feathered edges)
    blend_weight = _create_blend_weight(out_patch_size, out_overlap)

    # Process patches
    num_patches_h = max(1, (h - overlap) // stride + 1)
    num_patches_w = max(1, (w - overlap) // stride + 1)
    total_patches = num_patches_h * num_patches_w

    import time
    start_time = time.time()

    patch_idx = 0
    for i in range(num_patches_h):
        for j in range(num_patches_w):
            # Calculate patch coordinates
            y1 = min(i * stride, h - patch_size)
            x1 = min(j * stride, w - patch_size)
            y2 = y1 + patch_size
            x2 = x1 + patch_size

            # Handle edge cases
            if y1 < 0:
                y1 = 0
                y2 = min(patch_size, h)
            if x1 < 0:
                x1 = 0
                x2 = min(patch_size, w)

            # Extract patch
            patch = image[y1:y2, x1:x2]

            # Pad if patch is smaller than expected
            ph, pw = patch.shape[:2]
            if ph < patch_size or pw < patch_size:
                padded = np.zeros((patch_size, patch_size, 3), dtype=patch.dtype)
                padded[:ph, :pw] = patch
                patch = padded

            # Process patch
            try:
                sr_patch = _run_swinir_patch(patch, model, device, scale)
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    # Clear cache and retry
                    if device.type == 'cuda':
                        torch.cuda.empty_cache()
                    sr_patch = _run_swinir_patch(patch, model, device, scale)
                else:
                    raise

            # Output coordinates
            out_y1 = y1 * scale
            out_x1 = x1 * scale
            out_y2 = out_y1 + out_patch_size
            out_x2 = out_x1 + out_patch_size

            # Crop if exceeds output size
            actual_h = min(out_y2, out_h) - out_y1
            actual_w = min(out_x2, out_w) - out_x1

            # Get appropriate weight
            curr_weight = blend_weight[:actual_h, :actual_w]
            sr_patch_cropped = sr_patch[:actual_h, :actual_w]

            # Accumulate weighted output
            output[out_y1:out_y1+actual_h, out_x1:out_x1+actual_w] += \
                sr_patch_cropped.astype(np.float32) * curr_weight
            weight[out_y1:out_y1+actual_h, out_x1:out_x1+actual_w] += curr_weight

            patch_idx += 1
            if patch_idx % 5 == 0 or patch_idx == total_patches:
                elapsed = time.time() - start_time
                speed = patch_idx / elapsed
                eta = (total_patches - patch_idx) / speed if speed > 0 else 0

    # Normalize by weights
    weight = np.maximum(weight, 1e-8)  # Avoid division by zero
    output = output / weight
    output = np.clip(output, 0, 255).astype(np.uint8)

    total_time = time.time() - start_time

    # Clear GPU cache
    if device.type == 'cuda':
        torch.cuda.empty_cache()

    return output


def _create_blend_weight(size: int, overlap: int) -> np.ndarray:
    """Create a blending weight matrix with feathered edges."""
    weight = np.ones((size, size, 1), dtype=np.float32)

    # Create linear ramps for edges
    if overlap > 0:
        ramp = np.linspace(0, 1, overlap)

        # Top edge
        for i in range(overlap):
            weight[i, :, 0] *= ramp[i]

        # Bottom edge
        for i in range(overlap):
            weight[size - 1 - i, :, 0] *= ramp[i]

        # Left edge
        for i in range(overlap):
            weight[:, i, 0] *= ramp[i]

        # Right edge
        for i in range(overlap):
            weight[:, size - 1 - i, 0] *= ramp[i]

    return weight


def _run_swinir_inference(image: np.ndarray, scale: int = 4) -> np.ndarray:
    """
    Run SwinIR inference on image.
    Uses patchwise processing for large images to avoid OOM errors.
    """
    h, w = image.shape[:2]

    # Check if image is too large for single-pass processing
    # With GPU + FP16, we can handle larger images
    # Threshold based on typical GPU memory
    model, device = _load_sr_model()

    if device and device.type == 'cuda':
        # GPU can handle larger images
        max_pixels_single_pass = 1024 * 1024  # 1 megapixel
    else:
        # CPU is slower, use smaller threshold
        max_pixels_single_pass = 512 * 512  # 0.25 megapixels

    if h * w > max_pixels_single_pass:
        return _run_swinir_patchwise(image, scale)
    else:
        pass

    # Small enough for single-pass processing
    import torch
    import torch.nn.functional as F

    if model is None:
        raise RuntimeError("SwinIR model not available")

    # Convert BGR to RGB and to tensor directly 
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_tensor = torch.from_numpy(image_rgb).permute(2, 0, 1).float() / 255.0
    image_tensor = image_tensor.unsqueeze(0).to(device, non_blocking=True)

    # Pad for window size
    window_size = 8
    pad_h = (window_size - h % window_size) % window_size
    pad_w = (window_size - w % window_size) % window_size

    if pad_h > 0 or pad_w > 0:
        image_tensor = F.pad(image_tensor, (0, pad_w, 0, pad_h), 'reflect')

    # Run inference
    with torch.no_grad():
        try:
            sr_tensor = model(image_tensor)
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                if device.type == 'cuda':
                    torch.cuda.empty_cache()
                # Fallback to patchwise
                return _run_swinir_patchwise(image, scale)
            raise

    # Crop to original size * scale
    h_output = h * scale
    w_output = w * scale
    sr_tensor = sr_tensor[:, :, :h_output, :w_output]

    # Clamp and convert to numpy efficiently
    sr_tensor = torch.clamp(sr_tensor, 0, 1)
    sr_np = (sr_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

    # Convert RGB to BGR
    sr_bgr = cv2.cvtColor(sr_np, cv2.COLOR_RGB2BGR)

    # Clear GPU cache
    if device.type == 'cuda':
        torch.cuda.empty_cache()

    return sr_bgr


def super_resolution(
    image: Union[np.ndarray, str],
    scale: int = 4,
    method: str = "swinir",
    force: bool = False
) -> Dict[str, Any]:
    """
    Super-resolution upscaling using SwinIR model.

    Args:
        image: Input image (numpy array or path)
        scale: Upscaling factor (only 4x supported for SwinIR)
        method: "swinir" for real SR, "bicubic" for fallback
        force: If True, process even if image is already HD

    Returns:
        Dictionary containing:
            - upscaled_image: The upscaled image
            - original_size: Original dimensions
            - new_size: New dimensions
            - is_mock: False if using real model
            - message: Status message
            - skipped: True if skipped due to HD detection
    """
    # Load image
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")

    h, w = image.shape[:2]

    # Check if already HD/Full HD
    is_hd, resolution_name = _check_resolution(h, w)

    if is_hd and not force:
        return {
            "upscaled_image": image,
            "original_size": [w, h],
            "new_size": [w, h],
            "scale_factor": 1,
            "is_mock": False,
            "message": f"Image is already {resolution_name} ({w}x{h}). No upscaling needed. Use force=True to override.",
            "method": "skipped",
            "skipped": True,
            "resolution": resolution_name
        }

    # SwinIR only supports 4x scale
    if scale != 4 and method == "swinir":
        scale = 4

    new_h, new_w = h * scale, w * scale

    # Try SwinIR first
    if method == "swinir":
        try:
            upscaled = _run_swinir_inference(image, scale)
            return {
                "upscaled_image": upscaled,
                "original_size": [w, h],
                "new_size": [new_w, new_h],
                "scale_factor": scale,
                "is_mock": False,
                "message": f"Super-resolved {scale}x using SwinIR model ({w}x{h} → {new_w}x{new_h})",
                "method": "swinir",
                "skipped": False
            }
        except Exception as e:
            method = "bicubic"

    # Fallback to bicubic
    interp = cv2.INTER_CUBIC
    upscaled = cv2.resize(image, (new_w, new_h), interpolation=interp)

    # Add slight sharpening
    kernel = np.array([[-0.5, -0.5, -0.5],
                       [-0.5,  5.0, -0.5],
                       [-0.5, -0.5, -0.5]])
    upscaled = cv2.filter2D(upscaled, -1, kernel * 0.3 + np.eye(3) * 0.7)
    upscaled = np.clip(upscaled, 0, 255).astype(np.uint8)

    return {
        "upscaled_image": upscaled,
        "original_size": [w, h],
        "new_size": [new_w, new_h],
        "scale_factor": scale,
        "is_mock": True,
        "message": (
            "Using bicubic interpolation fallback. "
            "SwinIR model not available or failed to load."
        ),
        "method": "bicubic",
        "skipped": False
    }


def get_sr_info() -> Dict[str, Any]:
    """
    Get information about the SR tool status.
    """
    model, device = _load_sr_model()

    if model is not None:
        return {
            "status": "ready",
            "model": "SwinIR-M (BSRGAN)",
            "device": str(device),
            "scale": 4,
            "description": "Real super-resolution using SwinIR transformer model",
            "features": [
                "Patchwise processing for large images",
                "HD/Full HD detection",
                "Automatic OOM recovery"
            ]
        }
    else:
        return {
            "status": "fallback",
            "reason": "SwinIR model not loaded",
            "fallback": "Bicubic interpolation with sharpening"
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = super_resolution(sys.argv[1], scale=4)

        if not result.get('skipped', False):
            cv2.imwrite("sr_output.jpg", result['upscaled_image'])
        else:
            pass
            