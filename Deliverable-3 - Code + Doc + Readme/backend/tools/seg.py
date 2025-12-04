"""
Segmentation Tool using MobileSAM and BiRefNet
Real implementation for precise object segmentation
"""

import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Any, Union, List, Optional
import torch

# Model paths
MODEL_PATH = Path(__file__).parent.parent / "models" / "mobile_sam.pt"
BIREFNET_MODEL_PATH = Path(__file__).parent.parent / "models" / "BiRefNet-general-epoch_244.pth"

# Global model instances
_sam_model = None
_predictor = None
_birefnet_model = None

import gc

def get_sam_model():
    """Lazy load the MobileSAM model"""
    global _sam_model, _predictor

    if _sam_model is None:
        try:
            # Try to use MobileSAM from ultralytics
            from ultralytics import SAM

            if MODEL_PATH.exists():
                _sam_model = SAM(str(MODEL_PATH))
            else:
                # Download mobile_sam
                _sam_model = SAM("mobile_sam.pt")

            # Move to CUDA if available
            if torch.cuda.is_available():
                _sam_model.to("cuda")
            else:
                pass

        except ImportError:
            # Fallback: use GrabCut
            _sam_model = "grabcut_fallback"

    return _sam_model


def unload_models():
    """Unload segmentation models to free GPU memory"""
    global _sam_model, _predictor, _birefnet_model
    
    unloaded = False
    
    if _sam_model is not None:
        del _sam_model
        _sam_model = None
        unloaded = True
        
    if _predictor is not None:
        del _predictor
        _predictor = None
        
    if _birefnet_model is not None:
        del _birefnet_model
        _birefnet_model = None
        unloaded = True
        
    if unloaded:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def segment_object(
    image: Union[np.ndarray, str],
    bbox: Optional[List[int]] = None,
    points: Optional[List[List[int]]] = None,
    point_labels: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Segment an object in an image using MobileSAM or fallback methods.

    Args:
        image: Input image as numpy array (BGR) or path to image file
        bbox: Bounding box [x   1, y1, x2, y2] to segment within
        points: List of [x, y] points to prompt segmentation
        point_labels: Labels for points (1 = foreground, 0 = background)

    Returns:
        Dictionary containing:
            - mask: Binary segmentation mask
            - masked_image: Image with mask applied
            - contours: Contour points of the mask
            - area: Area of segmented region in pixels
    """
    # Load image if path provided
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")

    model = get_sam_model()

    if model == "grabcut_fallback":
        return _segment_grabcut(image, bbox)

    # Use SAM model
    try:
        if bbox is not None:
            # Use bounding box prompt
            results = model(image, bboxes=[bbox], verbose=False)
        elif points is not None:
            # Use point prompts
            results = model(image, points=points, labels=point_labels, verbose=False)
        else:
            # Auto-segment (use center point)
            h, w = image.shape[:2]
            center_point = [[w // 2, h // 2]]
            results = model(image, points=center_point, labels=[1], verbose=False)

        # Extract mask from results
        if results and len(results) > 0:
            mask = results[0].masks.data[0].cpu().numpy()
            mask = (mask * 255).astype(np.uint8)
        else:
            # Empty mask if no results
            mask = np.zeros(image.shape[:2], dtype=np.uint8)

    except Exception as e:
        return _segment_grabcut(image, bbox)

    return _process_mask(image, mask)

def _segment_grabcut(image: np.ndarray, bbox: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Fallback segmentation using OpenCV GrabCut.
    """
    if bbox is None:
        # Use center region as default
        h, w = image.shape[:2]
        margin = 50
        bbox = [margin, margin, w - margin, h - margin]

    # Initialize mask
    mask = np.zeros(image.shape[:2], np.uint8)

    # Create rect for GrabCut
    rect = (bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])

    # Initialize models
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    # Run GrabCut
    try:
        cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    except cv2.error as e:
        # Return empty mask
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        return _process_mask(image, mask)

    # Extract foreground mask
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
    mask_output = (mask2 * 255).astype(np.uint8)

    return _process_mask(image, mask_output)

def _process_mask(image: np.ndarray, mask: np.ndarray) -> Dict[str, Any]:
    """
    Process the mask and return results.
    CORRECTED: Preserves anti-aliasing (soft edges) in the RGBA output.
    """
    # 1. Ensure mask is uint8 (0-255)
    # This is our "Soft Mask" that contains transparency info (0..128..255)
    soft_mask = mask.astype(np.uint8)

    # 2. Create Binary Mask (strictly for Contours and Stats)
    # We ONLY use this for math, not for visuals!
    _, binary_mask = cv2.threshold(soft_mask, 127, 255, cv2.THRESH_BINARY)

    # 3. Create masked image (Preview)
    # Using binary here is okay for a quick preview, 
    # but for high-quality composition, you rely on rgba_image.
    masked_image = cv2.bitwise_and(image, image, mask=binary_mask)

    # 4. Find contours (Requires Binary Mask)
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 5. Calculate area (Based on binary coverage)
    area = int(np.sum(binary_mask > 0))

    # 6. Create RGBA image (THE FIX)
    if image.shape[2] == 3:
        rgba_image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    else:
        rgba_image = image.copy()
    
    # CRITICAL CHANGE: Use 'soft_mask', NOT 'binary_mask'
    # This applies the smooth 0-255 alpha values to the image.
    rgba_image[:, :, 3] = soft_mask

    # 7. Get contour points (Flatten for JSON/Export if needed)
    contour_points = []
    for contour in contours:
        # Squeeze removes single-dimensional entries from the shape of an array
        points = contour.squeeze() 
        if points.ndim == 2: # Ensure we have x,y pairs
             contour_points.extend(points.tolist())

    return {
        "mask": soft_mask,          # Return the HIGH QUALITY soft mask
        "binary_mask": binary_mask, # Return binary if needed for logic
        "masked_image": masked_image,
        "rgba_image": rgba_image,   # This now has smooth edges!
        "contours": contour_points,
        "area": area,
        "coverage": round(area / (image.shape[0] * image.shape[1]) * 100, 2)
    }


def extract_subject(
    image: Union[np.ndarray, str],
    mask: np.ndarray
) -> np.ndarray:
    """
    Extract subject with transparency based on mask.

    Returns:
        RGBA image with transparent background
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    # Convert to RGBA
    if image.shape[2] == 3:
        rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    else:
        rgba = image.copy()

    # Apply mask as alpha channel
    rgba[:, :, 3] = mask

    return rgba

def segment_single_bbox(
    image: Union[np.ndarray, str],
    bbox: List[int],
    label: str = "object"
) -> Dict[str, Any]:
    """
    Segment a single object from its bounding box.

    Args:
        image: Input image (BGR)
        bbox: Bounding box [x1, y1, x2, y2]
        label: Object label for metadata

    Returns:
        Dictionary with mask, masked_image, coverage, bbox, label
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    # Segment using the bbox
    result = segment_object(image, bbox=bbox)

    # Add label and bbox to result
    result["label"] = label
    result["bbox"] = bbox

    return result


def segment_multiple_objects(
    image: Union[np.ndarray, str],
    bboxes: List[List[int]],
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Segment multiple objects from their bounding boxes.

    Args:
        image: Input image (BGR)
        bboxes: List of bounding boxes [[x1, y1, x2, y2], ...]
        labels: Optional list of labels for each bbox

    Returns:
        Dictionary with:
            - combined_mask: Single mask with all objects (uint8, 0-255)
            - individual_masks: List of separate masks for each object
            - masked_image: Image with all objects segmented
            - labels: Labels for each segmented object
            - coverage: Total coverage percentage
            - count: Number of objects segmented
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    if labels is None:
        labels = [f"object_{i}" for i in range(len(bboxes))]

    # Initialize combined mask
    combined_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    individual_masks = []
    individual_results = []

    # Segment each object
    for i, (bbox, label) in enumerate(zip(bboxes, labels)):
        try:
            result = segment_single_bbox(image, bbox, label)
            mask = result["mask"]

            # Add to combined mask
            combined_mask = cv2.bitwise_or(combined_mask, mask)

            individual_masks.append(mask)
            individual_results.append(result)

        except Exception as e:
            # Add empty mask
            individual_masks.append(np.zeros(image.shape[:2], dtype=np.uint8))

    # Create masked image with combined mask
    masked_image = cv2.bitwise_and(image, image, mask=combined_mask)

    # Calculate total coverage
    total_area = int(np.sum(combined_mask > 0))
    coverage = round(total_area / (image.shape[0] * image.shape[1]) * 100, 2)

    # Create RGBA image
    rgba_image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    rgba_image[:, :, 3] = combined_mask

    return {
        "combined_mask": combined_mask,
        "individual_masks": individual_masks,
        "individual_results": individual_results,
        "masked_image": masked_image,
        "rgba_image": rgba_image,
        "labels": labels,
        "coverage": coverage,
        "count": len(bboxes),
        "total_area": total_area
    }


def segment_with_detection(
    image: Union[np.ndarray, str],
    label: str = "person",
    bbox_index: int = 0
) -> Dict[str, Any]:
    """
    Detect and segment an object by label.
    Combines detection and segmentation in one call.

    Args:
        image: Input image
        label: Object class label to segment
        bbox_index: Which detection to use if multiple objects of same class (0-indexed)

    Returns:
        Segmentation result with detection info
    """
    from .detect import detect_objects

    if isinstance(image, str):
        image = cv2.imread(image)

    # Detect objects
    detection_result = detect_objects(image)

    # Find all objects with matching label
    matching_detections = []
    for det in detection_result['detections']:
        if det['label'].lower() == label.lower():
            matching_detections.append(det)

    if not matching_detections:
        return {
            "error": f"No {label} detected in image",
            "mask": np.zeros(image.shape[:2], dtype=np.uint8),
            "masked_image": image,
            "coverage": 0,
            "area": 0
        }

    # Handle bbox_index
    if bbox_index >= len(matching_detections):
        bbox_index = 0  # Default to first if index out of range

    target_detection = matching_detections[bbox_index]

    # Segment using the bounding box
    result = segment_single_bbox(image, target_detection['bbox'], label)

    # Add detection info
    result["detection"] = target_detection
    result["detections_found"] = len(matching_detections)

    return result


def get_birefnet_model():
    """Lazy load the BiRefNet model"""
    global _birefnet_model

    if _birefnet_model is None:
        try:
            from transformers import AutoModelForImageSegmentation
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"

            # Try to load from local path first
            if BIREFNET_MODEL_PATH.exists():
                _birefnet_model = {
                    'model': AutoModelForImageSegmentation.from_pretrained(
                        str(BIREFNET_MODEL_PATH.parent),
                        trust_remote_code=True,
                        torch_dtype=torch.float16 if device == "cuda" else torch.float32
                    ).to(device),
                    'device': device
                }
            else:
                # Download from HuggingFace
                _birefnet_model = {
                    'model': AutoModelForImageSegmentation.from_pretrained(
                        'ZhengPeng7/BiRefNet',
                        trust_remote_code=True,
                        torch_dtype=torch.float16 if device == "cuda" else torch.float32
                    ).to(device),
                    'device': device
                }

            _birefnet_model['model'].eval()

        except Exception as e:
            _birefnet_model = None

    return _birefnet_model


def segment_foreground(
    image: Union[np.ndarray, str],
    return_rgba: bool = True
) -> Dict[str, Any]:
    """
    Segment the main foreground subject using BiRefNet.
    UPDATED: Returns a SOFT mask (anti-aliased) instead of hard binary to fix jagged edges.
    """
    # Load image if path provided
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")

    # Get BiRefNet model
    model_data = get_birefnet_model()

    if model_data is None:
        return segment_object(image, bbox=None)

    try:
        from torchvision import transforms
        from PIL import Image as PILImage
        import torch

        model = model_data['model']
        device = model_data['device']

        # Convert BGR to RGB for model
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = PILImage.fromarray(image_rgb)

        # Prepare input
        transform_image = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        input_tensor = transform_image(pil_image).unsqueeze(0).to(device)
        
        if model.dtype == torch.float16:
            input_tensor = input_tensor.half()

        # Run inference
        with torch.no_grad():
            output = model(input_tensor)[-1].sigmoid()

        # Post-process mask
        pred_mask = output[0, 0].float().cpu().numpy()
        
        # Cleanup
        del input_tensor
        del output
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        
        # 1. Resize back to original size using LINEAR or CUBIC interpolation
        # (Linear is smoother for upscaling masks than Nearest Neighbor)
        pred_mask = cv2.resize(pred_mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_LINEAR)

        # 2. DO NOT THRESHOLD (Removed: > 0.5)
        # Instead, scale the float values (0.0 to 1.0) directly to integers (0 to 255)
        # This keeps the gray pixels at the edges (Anti-aliasing)
        mask = (pred_mask * 255).astype(np.uint8)

        return _process_mask(image, mask)

    except Exception as e:
        return segment_object(image, bbox=None)

def smooth_mask_edges(mask: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Smooth the edges of a segmentation mask.

    Args:
        mask: Binary mask (uint8, 0-255)
        kernel_size: Size of smoothing kernel

    Returns:
        Smoothed mask (uint8, 0-255)
    """
    # Apply Gaussian blur
    if kernel_size % 2 == 0:
        kernel_size += 1

    blurred = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)

    # Re-threshold to maintain binary nature but with smoother edges
    _, smoothed = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)

    return smoothed


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = segment_foreground(sys.argv[1])

        # Save outputs
        cv2.imwrite("segmented_mask.png", result['mask'])
        cv2.imwrite("segmented_output.png", result['masked_image'])
        if 'rgba_image' in result:
            cv2.imwrite("segmented_rgba.png", result['rgba_image'])

