"""
Resize Tool using Pillow/OpenCV
Real implementation for image resizing operations
"""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, Union, Optional, Tuple

def resize_image(
    image: Union[np.ndarray, str, Image.Image],
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale: Optional[float] = None,
    maintain_aspect: bool = True,
    interpolation: str = "lanczos"
) -> Dict[str, Any]:
    """
    Resize an image with various options.

    Args:
        image: Input image (numpy array, path, or PIL Image)
        width: Target width in pixels
        height: Target height in pixels
        scale: Scale factor (e.g., 0.5 for half size, 2.0 for double)
        maintain_aspect: Whether to maintain aspect ratio
        interpolation: Interpolation method ("nearest", "linear", "cubic", "lanczos")

    Returns:
        Dictionary containing:
            - resized_image: The resized image
            - original_size: Original dimensions [width, height]
            - new_size: New dimensions [width, height]
            - scale_factor: Actual scale factors [x, y]
    """
    # Convert to numpy array
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")
    elif isinstance(image, Image.Image):
        image = np.array(image)
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    h, w = image.shape[:2]
    original_size = [w, h]

    # Determine interpolation method
    interp_map = {
        "nearest": cv2.INTER_NEAREST,
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
        "lanczos": cv2.INTER_LANCZOS4,
        "area": cv2.INTER_AREA  # Best for downscaling
    }
    interp = interp_map.get(interpolation.lower(), cv2.INTER_LANCZOS4)

    # Calculate new dimensions
    if scale is not None:
        new_w = int(w * scale)
        new_h = int(h * scale)
    elif width is not None and height is not None:
        if maintain_aspect:
            # Fit within the specified dimensions
            aspect = w / h
            target_aspect = width / height

            if aspect > target_aspect:
                # Image is wider
                new_w = width
                new_h = int(width / aspect)
            else:
                # Image is taller
                new_h = height
                new_w = int(height * aspect)
        else:
            new_w = width
            new_h = height
    elif width is not None:
        new_w = width
        new_h = int(h * (width / w)) if maintain_aspect else h
    elif height is not None:
        new_h = height
        new_w = int(w * (height / h)) if maintain_aspect else w
    else:
        # No resize parameters
        return {
            "resized_image": image,
            "original_size": original_size,
            "new_size": original_size,
            "scale_factor": [1.0, 1.0],
            "message": "No resize parameters provided"
        }

    # Ensure minimum size
    new_w = max(1, new_w)
    new_h = max(1, new_h)

    # Use INTER_AREA for downscaling for better quality
    if new_w < w or new_h < h:
        interp = cv2.INTER_AREA

    # Perform resize
    resized = cv2.resize(image, (new_w, new_h), interpolation=interp)

    return {
        "resized_image": resized,
        "original_size": original_size,
        "new_size": [new_w, new_h],
        "scale_factor": [round(new_w / w, 4), round(new_h / h, 4)]
    }

def resize_to_fit(
    image: Union[np.ndarray, str],
    max_width: int,
    max_height: int
) -> Dict[str, Any]:
    """
    Resize image to fit within maximum dimensions while maintaining aspect ratio.
    Only downscales if necessary.
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    h, w = image.shape[:2]

    # Check if resize is needed
    if w <= max_width and h <= max_height:
        return {
            "resized_image": image,
            "original_size": [w, h],
            "new_size": [w, h],
            "scale_factor": [1.0, 1.0],
            "message": "Image already fits within constraints"
        }

    # Calculate scale to fit
    scale = min(max_width / w, max_height / h)

    return resize_image(image, scale=scale)

def resize_for_web(
    image: Union[np.ndarray, str],
    preset: str = "large"
) -> Dict[str, Any]:
    """
    Resize image for web use with common presets.

    Args:
        image: Input image
        preset: "thumbnail" (150px), "small" (320px), "medium" (640px),
                "large" (1280px), "hd" (1920px), "4k" (3840px)

    Returns:
        Resized image dictionary
    """
    presets = {
        "thumbnail": 150,
        "small": 320,
        "medium": 640,
        "large": 1280,
        "hd": 1920,
        "4k": 3840
    }

    max_dim = presets.get(preset.lower(), 1280)

    if isinstance(image, str):
        image = cv2.imread(image)

    h, w = image.shape[:2]

    # Determine which dimension to constrain
    if w >= h:
        return resize_image(image, width=max_dim, maintain_aspect=True)
    else:
        return resize_image(image, height=max_dim, maintain_aspect=True)

def resize_canvas(
    image: Union[np.ndarray, str],
    width: int,
    height: int,
    position: str = "center",
    background: Tuple[int, int, int] = (255, 255, 255)
) -> Dict[str, Any]:
    """
    Resize canvas (add padding) without scaling the image.

    Args:
        image: Input image
        width: New canvas width
        height: New canvas height
        position: Position of image on canvas ("center", "top-left", "top-right", etc.)
        background: Background color (B, G, R)

    Returns:
        Dictionary with resized canvas image
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    h, w = image.shape[:2]

    # Create new canvas
    if len(image.shape) == 3:
        canvas = np.full((height, width, image.shape[2]), background, dtype=np.uint8)
    else:
        canvas = np.full((height, width), background[0], dtype=np.uint8)

    # Calculate position
    positions = {
        "center": ((width - w) // 2, (height - h) // 2),
        "top-left": (0, 0),
        "top-right": (width - w, 0),
        "bottom-left": (0, height - h),
        "bottom-right": (width - w, height - h),
        "top-center": ((width - w) // 2, 0),
        "bottom-center": ((width - w) // 2, height - h),
        "left-center": (0, (height - h) // 2),
        "right-center": (width - w, (height - h) // 2)
    }

    x, y = positions.get(position.lower(), positions["center"])

    # Ensure we don't go out of bounds
    x = max(0, min(x, width - w))
    y = max(0, min(y, height - h))

    # Place image on canvas
    canvas[y:y+h, x:x+w] = image

    return {
        "resized_image": canvas,
        "original_size": [w, h],
        "new_size": [width, height],
        "position": position,
        "offset": [x, y]
    }

def batch_resize(
    images: list,
    **kwargs
) -> list:
    """
    Resize multiple images with the same parameters.

    Args:
        images: List of images (paths or arrays)
        **kwargs: Parameters for resize_image

    Returns:
        List of resize result dictionaries
    """
    results = []
    for img in images:
        result = resize_image(img, **kwargs)
        results.append(result)
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Test resize
        result = resize_for_web(sys.argv[1], "medium")
        cv2.imwrite("resized_output.jpg", result['resized_image'])
