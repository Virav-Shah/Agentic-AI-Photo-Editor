"""
Depth Estimation Tool using Depth-Anything-V2
"""

import torch
from transformers import pipeline
from PIL import Image
import numpy as np
import cv2
from typing import Dict, Any, Union
from pathlib import Path

# Global depth estimator (lazy loaded)
_depth_estimator = None

import gc

def get_depth_estimator():
    """Lazy load the Depth-Anything-V2 model"""
    global _depth_estimator

    if _depth_estimator is None:
        device = 0 if torch.cuda.is_available() else -1
        model_id = "depth-anything/Depth-Anything-V2-Small-hf"

        try:
            _depth_estimator = pipeline(
                task="depth-estimation",
                model=model_id,
                device=device
            )
        except Exception as e:
            _depth_estimator = pipeline(task="depth-estimation", device=device)

    return _depth_estimator


def unload_model():
    """Unload the depth estimation model to free GPU memory"""
    global _depth_estimator
    if _depth_estimator is not None:
        del _depth_estimator
        _depth_estimator = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def estimate_depth(image: Union[np.ndarray, str, Image.Image]) -> Dict[str, Any]:
    """
    Estimate depth map for an image using Depth-Anything-V2.

    Args:
        image: Input image (numpy array BGR, file path, or PIL Image)

    Returns:
        Dictionary containing:
            - depth_map: Depth map as numpy array (H, W) uint8 0-255
            - depth_pil: Depth map as PIL Image (grayscale)
            - normalized_depth: Normalized depth (H, W) float 0-1
            - message: Status message
    """
    # Load image if path provided
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")

    # Convert to PIL Image if numpy array
    if isinstance(image, np.ndarray):
        # Convert BGR to RGB for PIL
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        pil_image = Image.fromarray(image_rgb)
    else:
        pil_image = image

    # Get depth estimator
    pipe = get_depth_estimator()

    # Estimate depth
    result = pipe(pil_image)
    depth_pil = result["depth"]

    # Convert to numpy array
    depth_array = np.array(depth_pil)

    # Normalize to 0-255 uint8
    depth_min = depth_array.min()
    depth_max = depth_array.max()

    if depth_max - depth_min > 1e-6:
        depth_normalized = (depth_array - depth_min) / (depth_max - depth_min)
    else:
        depth_normalized = np.zeros_like(depth_array, dtype=np.float32)

    depth_uint8 = (depth_normalized * 255).astype(np.uint8)

    return {
        "depth_map": depth_uint8,
        "depth_pil": depth_pil,
        "normalized_depth": depth_normalized,
        "message": "Depth estimation completed using Depth-Anything-V2"
    }


def predict_depth(image: Union[np.ndarray, str]) -> np.ndarray:
    """
    Backward compatibility function for old MiDaS API.

    Args:
        image: Input image (numpy array or path)

    Returns:
        Normalized depth map (H, W) float 0-1
    """
    result = estimate_depth(image)
    return result['normalized_depth']


class DepthEstimator:
    """
    Backward compatibility class for old MiDaS API.
    Now uses Depth-Anything-V2 internally.
    """

    def __init__(self, model_type="depth-anything", device="cpu"):
        """
        Args:
            model_type: Ignored (kept for backward compatibility)
            device: "cpu" or "cuda"
        """
        self.device = device
        self.model_type = "Depth-Anything-V2"
        self._estimator = None

    def load_model(self):
        """Load the depth estimation model"""
        if self._estimator is None:
            self._estimator = get_depth_estimator()

    def predict(self, img: np.ndarray) -> np.ndarray:
        """
        Predict depth map (backward compatible with MiDaS API).

        Args:
            img: RGB numpy array (H, W, 3), values 0-255 (uint8)

        Returns:
            depth_map: Normalized depth map (H, W), values 0-1 (float)
        """
        if self._estimator is None:
            self.load_model()

        result = estimate_depth(img)
        return result['normalized_depth']

    def estimate_depth(self, image: Union[np.ndarray, Image.Image]) -> Image.Image:
        """
        Estimate depth map (backward compatible with parallax_app API).

        Args:
            image: PIL Image or numpy array

        Returns:
            Depth map as PIL Image (grayscale)
        """
        if self._estimator is None:
            self.load_model()

        result = estimate_depth(image)
        return result['depth_pil']


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = estimate_depth(sys.argv[1])

        # Save depth map
        output_path = "depth_output.png"
        cv2.imwrite(output_path, result['depth_map'])

    else:
        pass