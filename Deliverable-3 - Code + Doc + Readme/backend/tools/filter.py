"""
Filter Tool using Pillow/OpenCV
Real implementation for various image filters and adjustments
"""

import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter
from typing import Dict, Any, Union, Optional

def apply_filter(
    image: Union[np.ndarray, str, Image.Image],
    filter_type: str,
    intensity: float = 1.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Apply various filters and adjustments to an image.

    Args:
        image: Input image (numpy array, path, or PIL Image)
        filter_type: Type of filter to apply
        intensity: Filter intensity (0.0 to 2.0, 1.0 = normal)
        **kwargs: Additional filter-specific parameters

    Supported filters:
        - blur: Gaussian blur (kernel_size in kwargs)
        - sharpen: Sharpen image
        - grayscale: Convert to grayscale
        - sepia: Sepia tone effect
        - brightness: Adjust brightness
        - contrast: Adjust contrast
        - saturation: Adjust color saturation
        - warm: Warm color temperature
        - cool: Cool color temperature
        - vintage: Vintage photo effect
        - vignette: Add vignette effect
        - hdr: HDR-like effect
        - denoise: Reduce noise
        - edge_detect: Edge detection
        - emboss: Emboss effect
        - invert: Invert colors

    Returns:
        Dictionary with filtered_image and metadata
    """
    # Convert to numpy array (BGR)
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")
    elif isinstance(image, Image.Image):
        image = np.array(image)
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    original = image.copy()

    # Apply filter based on type
    filter_type = filter_type.lower()

    if filter_type == "blur":
        kernel_size = kwargs.get("kernel_size", 5)
        kernel_size = int(kernel_size * intensity)
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel_size = max(1, kernel_size)
        filtered = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

    elif filter_type == "sharpen":
        kernel = np.array([[-1, -1, -1],
                          [-1, 9 * intensity, -1],
                          [-1, -1, -1]])
        filtered = cv2.filter2D(image, -1, kernel)

    elif filter_type == "grayscale":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        filtered = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    elif filter_type == "sepia":
        kernel = np.array([[0.272, 0.534, 0.131],
                          [0.349, 0.686, 0.168],
                          [0.393, 0.769, 0.189]])
        filtered = cv2.transform(image, kernel)
        filtered = np.clip(filtered, 0, 255).astype(np.uint8)
        # Blend with original based on intensity
        filtered = cv2.addWeighted(original, 1 - intensity, filtered, intensity, 0)

    elif filter_type == "brightness":
        # intensity: 0 = black, 1 = normal, 2 = bright
        factor = intensity
        filtered = cv2.convertScaleAbs(image, alpha=factor, beta=0)

    elif filter_type == "contrast":
        # intensity: 0 = gray, 1 = normal, 2 = high contrast
        factor = intensity
        mean = np.mean(image)
        filtered = cv2.convertScaleAbs(image, alpha=factor, beta=(1 - factor) * mean)

    elif filter_type == "saturation":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = hsv[:, :, 1] * intensity
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        filtered = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    elif filter_type == "warm":
        # Add warmth by increasing red, decreasing blue
        filtered = image.copy().astype(np.float32)
        filtered[:, :, 2] = np.clip(filtered[:, :, 2] * (1 + 0.2 * intensity), 0, 255)  # Red
        filtered[:, :, 0] = np.clip(filtered[:, :, 0] * (1 - 0.1 * intensity), 0, 255)  # Blue
        filtered = filtered.astype(np.uint8)

    elif filter_type == "cool":
        # Add coolness by increasing blue, decreasing red
        filtered = image.copy().astype(np.float32)
        filtered[:, :, 0] = np.clip(filtered[:, :, 0] * (1 + 0.2 * intensity), 0, 255)  # Blue
        filtered[:, :, 2] = np.clip(filtered[:, :, 2] * (1 - 0.1 * intensity), 0, 255)  # Red
        filtered = filtered.astype(np.uint8)

    elif filter_type == "vintage":
        # Combine sepia, reduced saturation, and vignette
        # Sepia
        kernel = np.array([[0.272, 0.534, 0.131],
                          [0.349, 0.686, 0.168],
                          [0.393, 0.769, 0.189]])
        sepia = cv2.transform(image, kernel)
        sepia = np.clip(sepia, 0, 255).astype(np.uint8)

        # Reduce saturation
        hsv = cv2.cvtColor(sepia, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.7
        vintage = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Add vignette
        filtered = _add_vignette(vintage, 0.5 * intensity)

    elif filter_type == "vignette":
        filtered = _add_vignette(image, intensity)

    elif filter_type == "hdr":
        # HDR-like effect using CLAHE
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0 * intensity, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        filtered = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    elif filter_type == "denoise":
        strength = int(10 * intensity)
        filtered = cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)

    elif filter_type == "edge_detect":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        filtered = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    elif filter_type == "emboss":
        kernel = np.array([[-2, -1, 0],
                          [-1, 1, 1],
                          [0, 1, 2]])
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        embossed = cv2.filter2D(gray, -1, kernel)
        filtered = cv2.cvtColor(embossed, cv2.COLOR_GRAY2BGR)

    elif filter_type == "invert":
        filtered = cv2.bitwise_not(image)

    else:
        filtered = image
        return {
            "filtered_image": filtered,
            "filter_type": filter_type,
            "error": f"Unknown filter type: {filter_type}"
        }

    return {
        "filtered_image": filtered,
        "filter_type": filter_type,
        "intensity": intensity,
        "original_size": [image.shape[1], image.shape[0]]
    }

def _add_vignette(image: np.ndarray, intensity: float) -> np.ndarray:
    """Add vignette effect to image."""
    rows, cols = image.shape[:2]

    # Create gradient
    X = cv2.getGaussianKernel(cols, cols * 0.5)
    Y = cv2.getGaussianKernel(rows, rows * 0.5)
    mask = Y * X.T
    mask = mask / mask.max()

    # Apply to each channel
    result = image.copy().astype(np.float32)
    for i in range(3):
        result[:, :, i] = result[:, :, i] * (1 - intensity + intensity * mask)

    return np.clip(result, 0, 255).astype(np.uint8)

def apply_multiple_filters(
    image: Union[np.ndarray, str],
    filters: list
) -> Dict[str, Any]:
    """
    Apply multiple filters in sequence.

    Args:
        image: Input image
        filters: List of filter dicts with 'type' and optional 'intensity'

    Returns:
        Dictionary with filtered_image and applied filters
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    current = image.copy()
    applied = []

    for f in filters:
        filter_type = f.get('type', f.get('filter_type', 'blur'))
        intensity = f.get('intensity', 1.0)
        kwargs = {k: v for k, v in f.items() if k not in ['type', 'filter_type', 'intensity']}

        result = apply_filter(current, filter_type, intensity, **kwargs)
        current = result['filtered_image']
        applied.append({
            'type': filter_type,
            'intensity': intensity
        })

    return {
        "filtered_image": current,
        "applied_filters": applied,
        "original_size": [image.shape[1], image.shape[0]]
    }

def get_available_filters() -> list:
    """Return list of available filter types."""
    return [
        "blur", "sharpen", "grayscale", "sepia", "brightness",
        "contrast", "saturation", "warm", "cool", "vintage",
        "vignette", "hdr", "denoise", "edge_detect", "emboss", "invert"
    ]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Test with sepia filter
        result = apply_filter(sys.argv[1], "vintage", intensity=0.8)
        cv2.imwrite("filtered_output.jpg", result['filtered_image'])
