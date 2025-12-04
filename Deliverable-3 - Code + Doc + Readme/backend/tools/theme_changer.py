"""
Theme Changer Tool - Weather-Aware Day/Night Transformation
Integrates weather detection with advanced sky replacement pipeline
"""

import os
import numpy as np
import cv2
import tensorflow as tf
from pathlib import Path
from typing import Dict, Any, Union, Optional

# Import your sky replacement modules
from tools.segmentation import SkySegmenter
from tools.depth import DepthEstimator
import tools.blending as sr_blending
from tools.utils import preprocess_image

class WeatherDetector:
    """Detects weather conditions from images using ResNet152V2."""

    def __init__(self, model_path='models/resnet.h5'):
        self.classes = [
            'dew', 'fog_smog', 'frost', 'glaze', 'hail',
            'lightning', 'rain', 'rainbow', 'rime', 'sandstorm', 'snow'
        ]
        self.model = None

        # Try multiple possible paths
        possible_paths = [
            model_path,
            'models/resnet.h5',
            os.path.join(os.path.dirname(__file__), '../models/resnet.h5')
        ]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    self.model = self._build_model(len(self.classes))
                    self.model.build((None, 256, 256, 3))
                    self.model.load_weights(path)
                    break
                except Exception as e:
                    pass

        if self.model is None:
            pass

    def _build_model(self, n_classes):
        from tensorflow.keras.applications import ResNet152V2
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout

        base_model = ResNet152V2(include_top=False, input_shape=(256, 256, 3))
        base_model.trainable = False
        model = Sequential([
            base_model,
            GlobalAveragePooling2D(),
            Dense(256, activation='relu'),
            Dropout(0.4),
            Dense(128, activation='relu'),
            Dropout(0.2),
            Dense(n_classes, activation="softmax")
        ])
        return model

    def detect(self, image):
        """Detect weather class from image."""
        if self.model is None:
            return "default"

        try:
            # Preprocess
            img = cv2.resize(image, (256, 256))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype(np.float32) / 255.0
            img = np.expand_dims(img, axis=0)

            # Predict
            preds = self.model.predict(img, verbose=0)
            class_idx = np.argmax(preds)
            confidence = preds[0][class_idx]

            detected_class = self.classes[class_idx]

            return detected_class
        except Exception as e:
            return "default"


class WeatherSkyProcessor:
    """Processes weather-aware sky replacement using your new pipeline."""

    def __init__(self):
        self.skysegmenter = None
        self.depth_estimator = None

    def load_skysegmenter(self, ckpt_path=None):
        """Load PyTorch SkySegmenter with best_ckpt.pt."""
        if self.skysegmenter is None:
            try:
                # Check for checkpoint in various locations
                checkpoint_candidates = [
                    ckpt_path,
                    'best_ckpt.pt',
                    'checkpoints_G_coord_resnet50/best_ckpt.pt',
                    'models/best_ckpt.pt',
                    'checkpoints/best_ckpt.pt',
                    os.path.join(os.path.dirname(__file__), 'best_ckpt.pt'),
                    os.path.join(os.path.dirname(__file__), '../best_ckpt.pt'),
                    os.path.join(os.path.dirname(__file__), '../checkpoints_G_coord_resnet50/best_ckpt.pt'),
                    os.path.join(os.path.dirname(__file__), '../models/best_ckpt.pt'),
                ]

                # Filter out None values and find existing checkpoint
                candidates = [c for c in checkpoint_candidates if c is not None]
                ckpt_path_found = None
                
                for candidate in candidates:
                    if candidate and os.path.exists(candidate):
                        ckpt_path_found = candidate
                        break

                if ckpt_path_found is None:
                    raise FileNotFoundError("No SkySegmenter checkpoint (best_ckpt.pt) found")

                self.skysegmenter = SkySegmenter(ckpt_path_found, device='cpu')
                return True

            except Exception as e:
                self.skysegmenter = None
                return False
        return True

    def load_depth_estimator(self):
        """Load depth estimator for fog effects."""
        if self.depth_estimator is None:
            try:
                self.depth_estimator = DepthEstimator(device='cpu')
                self.depth_estimator.load_model()
                return True
            except Exception as e:
                self.depth_estimator = None
                return False
        return True

    def segment_sky(self, image):
        """Segment sky using SkySegmenter with proper preprocessing."""
        if not self.load_skysegmenter():
            raise RuntimeError("SkySegmenter not available")

        try:
            import torch
            
            # Convert to RGB and normalize
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Resize to a standard size that works well with the model (e.g., 384x384)
            # This ensures consistent behavior regardless of input size
            original_h, original_w = img_rgb.shape[:2]
            process_size = (384, 384)
            
            # Preprocess the image
            img_processed = preprocess_image(img_rgb, process_size[0], process_size[1])
            
            # Convert to tensor
            img_tensor = torch.tensor(img_processed).permute(2, 0, 1).unsqueeze(0)
            
            # Get prediction
            pred = self.skysegmenter.predict(img_tensor)
            
            # Resize back to original dimensions
            if pred.shape[:2] != (original_h, original_w):
                pred_resized = cv2.resize(pred, (original_w, original_h))
            else:
                pred_resized = pred
                
            # Handle different mask formats and take first channel
            if pred_resized.ndim == 3:
                mask = pred_resized[:, :, 0]  # Take first channel
            else:
                mask = pred_resized
                
            return mask.astype(np.float32)
            
        except Exception as e:
            # Fallback: create a simple sky mask based on color
            return self._create_fallback_sky_mask(image)

    def _create_fallback_sky_mask(self, image):
        """Create a simple sky mask based on color as fallback."""
        
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Blue sky range
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # White/gray sky range (cloudy)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        # Combine masks
        mask = cv2.bitwise_or(mask_blue, mask_white)
        
        # Focus on upper portion of image
        mask[int(h*0.6):, :] = 0
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Convert to float and smooth
        mask_float = mask.astype(np.float32) / 255.0
        mask_float = cv2.GaussianBlur(mask_float, (21, 21), 0)
        
        return mask_float

    def get_weather_sky_texture(self, weather_class, time_val):
        """
        Load and interpolate weather-specific sky textures.
        Returns interpolated sky texture based on time value.
        """
        # Try multiple possible base paths
        possible_bases = [
            'assets/day_night',
            os.path.join(os.path.dirname(__file__), '../assets/day_night')
        ]

        base_path = None
        for base in possible_bases:
            test_path = os.path.join(base, weather_class)
            if os.path.exists(test_path):
                base_path = test_path
                break

        # Fallback to default if weather-specific not found
        if base_path is None:
            for base in possible_bases:
                test_path = os.path.join(base, 'default')
                if os.path.exists(test_path):
                    base_path = test_path
                    break

        sky_assets = []
        if base_path and os.path.exists(base_path):
            files = sorted([f for f in os.listdir(base_path) if f.endswith(('.png', '.jpg', '.jpeg'))])
            for f in files:
                img = cv2.imread(os.path.join(base_path, f))
                if img is not None:
                    # Convert BGR to RGB for consistency
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    sky_assets.append(img_rgb)

        if not sky_assets:
            # Create a default blue sky
            default_sky = np.zeros((512, 512, 3), dtype=np.uint8)
            default_sky[:, :] = [135, 206, 235]  # Sky blue
            sky_assets = [default_sky]

        # Interpolate between sky textures based on time_val (0-100)
        n_assets = len(sky_assets)
        if n_assets == 1:
            return sky_assets[0].astype(np.float32) / 255.0

        # Map time_val to asset indices
        float_idx = (time_val / 100.0) * (n_assets - 1)
        idx1 = int(np.floor(float_idx))
        idx2 = min(int(np.ceil(float_idx)), n_assets - 1)
        alpha = float_idx - idx1

        # Blend between two adjacent sky textures
        img1 = sky_assets[idx1]
        img2 = sky_assets[idx2]
        
        # Resize to match if needed
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
        blended = cv2.addWeighted(img1, 1.0 - alpha, img2, alpha, 0)
        return blended.astype(np.float32) / 255.0


# Global instances (lazy loaded)
_weather_detector = None
_sky_processor = None


def get_weather_detector():
    """Get or create weather detector instance."""
    global _weather_detector
    if _weather_detector is None:
        _weather_detector = WeatherDetector()
    return _weather_detector


def get_sky_processor():
    """Get or create sky processor instance."""
    global _sky_processor
    if _sky_processor is None:
        _sky_processor = WeatherSkyProcessor()
    return _sky_processor


def change_theme(
    image: Union[np.ndarray, str],
    time_of_day: int = 50,
    weather_class: Optional[str] = None,
    use_reinhard: bool = False,
    relighting_factor: float = 0.7,
    halo_effect: bool = False,
    use_depth: bool = False,
    fog_strength: float = 0.2
) -> Dict[str, Any]:
    """
    Change image theme using weather detection and advanced sky replacement.
    """
    if(time_of_day>80):
        halo_effect = True
        fog_strength=0.6
        use_reinhard = True
        relighting_factor = 0.6
    
    # Load image
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")

    # Step 1: Detect weather (or use override)
    if weather_class is None:
        detector = get_weather_detector()
        weather_class = detector.detect(image)
    else:
        pass

    # Step 2: Get weather-specific sky texture
    processor = get_sky_processor()
    sky_texture = processor.get_weather_sky_texture(weather_class, time_of_day)

    # Step 3: Segment sky
    sky_mask = processor.segment_sky(image)

    # Step 4: Prepare images for blending pipeline
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img_float = img_rgb.astype(np.float32) / 255.0
    
    # Prepare mask as 3-channel float
    if sky_mask.ndim == 2:
        mask_3ch = np.stack([sky_mask] * 3, axis=-1)
    else:
        mask_3ch = sky_mask

    # Step 5: Depth estimation (if enabled)
    depth_map = None
    if use_depth and processor.load_depth_estimator():
        try:
            depth_map = processor.depth_estimator.predict(img_rgb)
        except Exception as e:
            pass
    # Step 6: Calculate night factor for special effects
    night_factor = max(0.0, min(1.0, (time_of_day - 66) / 34.0)) if time_of_day > 66 else 0.0

    # Step 7: Apply advanced blending
    result = sr_blending.blend(
        img_float,
        sky_texture,
        mask_3ch,
        relighting_factor=relighting_factor,
        recoloring_factor=0.5,
        halo_effect=halo_effect,
        use_reinhard=use_reinhard,
        depth_map=depth_map,
        fog_strength=fog_strength if use_depth else 0.0,
        night_factor=night_factor,
        time_val=time_of_day,
    )

    # Convert back to BGR for output
    result_bgr = cv2.cvtColor((np.clip(result, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)

    assets_count = 5 
    
    return {
        "transformed_image": result_bgr,
        "detected_weather": weather_class,
        "sky_mask": (sky_mask * 255).astype(np.uint8),
        "time_of_day": time_of_day,
        "night_factor": night_factor,
        "used_depth": depth_map is not None,
        "assets_count": assets_count,  
        "original_size": image.shape[:2]
    }

def get_available_weather_classes():
    """Return list of available weather classes."""
    return [
        'default', 'dew', 'fog_smog', 'frost', 'glaze', 'hail',
        'lightning', 'rain', 'rainbow', 'rime', 'sandstorm', 'snow'
    ]