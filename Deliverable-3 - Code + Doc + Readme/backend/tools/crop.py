"""
Crop Tool using Pillow/OpenCV
Real implementation for image cropping operations
"""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, Union, List, Optional, Tuple

def crop_image(
    image: Union[np.ndarray, str, Image.Image],
    bbox: Optional[Union[List[int], str]] = None,
    center: Optional[List[int]] = None,
    size: Optional[List[int]] = None,
    aspect_ratio: Optional[str] = None,
    crop_direction: Optional[str] = None,
    padding: int = 0
) -> Dict[str, Any]:
    """
    Crop an image based on various parameters.

    Args:
        image: Input image (numpy array, path, or PIL Image)
        bbox: Bounding box [x1, y1, x2, y2] to crop (as list or parseable string)
        center: Center point [x, y] for crop (use with size)
        size: Size [width, height] for crop (use with center)
        aspect_ratio: Desired aspect ratio ("16:9", "4:3", "1:1", etc.)
        crop_direction: Direction to crop from ('left', 'right', 'top', 'bottom', 'center')
        padding: Additional padding around crop region

    Returns:
        Dictionary containing:
            - cropped_image: The cropped image
            - original_size: Original image dimensions
            - crop_region: The actual crop region used
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

    # Determine crop region
    x1, y1, x2, y2 = None, None, None, None  # Initialize

    if bbox is not None:
        # Handle bbox - it might be a string from LLM that needs parsing
        if isinstance(bbox, str):
            # Try to parse bbox string (handle cases like "[10, 0, 500, 400]")
            try:
                # Clean up string first - remove any variable names or expressions
                import re
                # Keep only numbers, commas, brackets, minus signs
                cleaned = re.sub(r'[^0-9,\-\[\]]', '', bbox)
                import ast
                bbox = ast.literal_eval(cleaned)
            except:
                bbox = None

        if bbox is not None:
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                x1, y1, x2, y2 = bbox
            else:
                return {
                    "cropped_image": image,
                    "original_size": original_size,
                    "crop_region": [0, 0, w, h],
                    "message": f"Invalid bbox format: {bbox}. Expected [x1, y1, x2, y2]"
                }
    elif crop_direction is not None:
        # Crop from a specific direction (10% from that side)
        crop_amount = 0.1  # 10%

        if crop_direction == 'left':
            x1 = int(w * crop_amount)
            y1 = 0
            x2 = w
            y2 = h
        elif crop_direction == 'right':
            x1 = 0
            y1 = 0
            x2 = int(w * (1 - crop_amount))
            y2 = h
        elif crop_direction == 'top':
            x1 = 0
            y1 = int(h * crop_amount)
            x2 = w
            y2 = h
        elif crop_direction == 'bottom':
            x1 = 0
            y1 = 0
            x2 = w
            y2 = int(h * (1 - crop_amount))
        else:  # center or unknown
            # Crop 10% from all sides
            x1 = int(w * crop_amount)
            y1 = int(h * crop_amount)
            x2 = int(w * (1 - crop_amount))
            y2 = int(h * (1 - crop_amount))
    elif center is not None and size is not None:
        cx, cy = center
        crop_w, crop_h = size
        x1 = cx - crop_w // 2
        y1 = cy - crop_h // 2
        x2 = x1 + crop_w
        y2 = y1 + crop_h
    elif aspect_ratio is not None:
        # Calculate crop for desired aspect ratio
        ratio_w, ratio_h = map(int, aspect_ratio.split(':'))
        target_ratio = ratio_w / ratio_h
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Image is wider, crop width
            new_w = int(h * target_ratio)
            x1 = (w - new_w) // 2
            y1 = 0
            x2 = x1 + new_w
            y2 = h
        else:
            # Image is taller, crop height
            new_h = int(w / target_ratio)
            x1 = 0
            y1 = (h - new_h) // 2
            x2 = w
            y2 = y1 + new_h
    else:
        # No crop parameters, return original
        return {
            "cropped_image": image,
            "original_size": original_size,
            "crop_region": [0, 0, w, h],
            "message": "No crop parameters provided"
        }

    # Check if valid crop region was determined
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return {
            "cropped_image": image,
            "original_size": original_size,
            "crop_region": [0, 0, w, h],
            "message": "Invalid crop parameters, returned original"
        }

    # Apply padding
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)

    # Perform crop
    cropped = image[y1:y2, x1:x2]

    return {
        "cropped_image": cropped,
        "original_size": original_size,
        "crop_region": [int(x1), int(y1), int(x2), int(y2)],
        "cropped_size": [int(x2 - x1), int(y2 - y1)]
    }

def smart_crop(
    image: Union[np.ndarray, str],
    target_size: Tuple[int, int],
    focus: str = "center"
) -> Dict[str, Any]:
    """
    Smart crop that maintains focus on important content.

    Args:
        image: Input image
        target_size: (width, height) of output
        focus: "center", "face", "subject", or "auto"

    Returns:
        Cropped image dictionary
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    h, w = image.shape[:2]
    target_w, target_h = target_size

    # Calculate scale to fill target
    scale = max(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    # Resize to fill
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # Determine crop center based on focus
    if focus == "face":
        from .detect import detect_face
        faces = detect_face(resized)
        if faces['count'] > 0:
            # Use first face center
            face = faces['detections'][0]
            cx, cy = face['center']
        else:
            cx, cy = new_w // 2, new_h // 2
    elif focus == "subject":
        from .detect import detect_person
        persons = detect_person(resized)
        if persons['count'] > 0:
            # Use first person center
            person = persons['detections'][0]
            cx, cy = person['center']
        else:
            cx, cy = new_w // 2, new_h // 2
    else:  # center or auto
        cx, cy = new_w // 2, new_h // 2

    # Calculate crop region
    x1 = max(0, cx - target_w // 2)
    y1 = max(0, cy - target_h // 2)

    # Adjust if out of bounds
    if x1 + target_w > new_w:
        x1 = new_w - target_w
    if y1 + target_h > new_h:
        y1 = new_h - target_h

    x1 = max(0, x1)
    y1 = max(0, y1)

    cropped = resized[y1:y1+target_h, x1:x1+target_w]

    return {
        "cropped_image": cropped,
        "original_size": [w, h],
        "crop_region": [int(x1), int(y1), int(x1+target_w), int(y1+target_h)],
        "cropped_size": [target_w, target_h],
        "focus": focus
    }

def crop_to_content(
    image: Union[np.ndarray, str],
    threshold: int = 10,
    padding: int = 10
) -> Dict[str, Any]:
    """
    Crop image to content (remove empty borders).

    Args:
        image: Input image
        threshold: Threshold for considering a pixel as content
        padding: Padding to add around content

    Returns:
        Cropped image dictionary
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Find content
    coords = np.argwhere(gray > threshold)

    if len(coords) == 0:
        return {
            "cropped_image": image,
            "original_size": [image.shape[1], image.shape[0]],
            "crop_region": [0, 0, image.shape[1], image.shape[0]],
            "message": "No content found"
        }

    # Get bounding box
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)

    # Add padding
    h, w = image.shape[:2]
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(w, x1 + padding)
    y1 = min(h, y1 + padding)

    cropped = image[y0:y1, x0:x1]

    return {
        "cropped_image": cropped,
        "original_size": [w, h],
        "crop_region": [int(x0), int(y0), int(x1), int(y1)],
        "cropped_size": [int(x1 - x0), int(y1 - y0)]
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Test aspect ratio crop
        result = crop_image(sys.argv[1], aspect_ratio="16:9")
        cv2.imwrite("cropped_output.jpg", result['cropped_image'])
