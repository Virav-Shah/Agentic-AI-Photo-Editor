"""
Object Detection Tool using YOLO
Real implementation using ultralytics YOLOv8/v11
"""

import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from ultralytics import YOLO

# Model path
MODEL_PATH = Path(__file__).parent.parent / "models" / "yolo11n.pt"

# Global model instance (lazy loading)
_model = None

def get_model():
    """Lazy load the YOLO model"""
    global _model
    if _model is None:
        if MODEL_PATH.exists():
            _model = YOLO(str(MODEL_PATH))
        else:
            # Fall back to downloading yolov8n
            _model = YOLO("yolov8n.pt")
    return _model

def detect_objects(
    image: Union[np.ndarray, str],
    classes: Optional[List[int]] = None,
    conf_threshold: float = 0.5,
    iou_threshold: float = 0.45
) -> Dict[str, Any]:
    """
    Detect objects in an image using YOLO.

    Args:
        image: Input image as numpy array (BGR) or path to image file
        classes: List of class IDs to detect (None for all)
        conf_threshold: Confidence threshold for detections
        iou_threshold: IoU threshold for NMS

    Returns:
        Dictionary containing:
            - detections: List of detection dicts with bbox, label, confidence
            - image: Annotated image with bounding boxes
            - count: Number of detections
    """
    model = get_model()

    # Load image if path provided
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")

    # Run inference
    results = model(
        image,
        conf=conf_threshold,
        iou=iou_threshold,
        classes=classes,
        verbose=False
    )

    detections = []
    annotated_image = image.copy()

    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for i, box in enumerate(boxes):
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = model.names[class_id]

                detection = {
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "label": class_name,
                    "class_id": class_id,
                    "confidence": round(confidence, 3),
                    "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)],
                    "size": [int(x2 - x1), int(y2 - y1)]
                }
                detections.append(detection)

                # Draw on annotated image
                color = (0, 255, 0)  # Green
                cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
                label_text = f"{class_name}: {confidence:.2f}"
                cv2.putText(
                    annotated_image, label_text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
                )

    return {
        "detections": detections,
        "annotated_image": annotated_image,
        "count": len(detections),
        "image_size": [image.shape[1], image.shape[0]]  # width, height
    }

def detect_person(image: Union[np.ndarray, str], conf_threshold: float = 0.5) -> Dict[str, Any]:
    """
    Detect people in an image (convenience function).
    Class 0 in COCO is 'person'.
    """
    return detect_objects(image, classes=[0], conf_threshold=conf_threshold)

def detect_face(image: Union[np.ndarray, str]) -> Dict[str, Any]:
    """
    Detect faces using OpenCV's DNN face detector as fallback.
    """ 
    if isinstance(image, str):
        image = cv2.imread(image)

    # Use OpenCV's DNN face detector
    modelFile = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(modelFile)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    detections = []
    annotated_image = image.copy()

    for (x, y, w, h) in faces:
        detection = {
            "bbox": [int(x), int(y), int(x + w), int(y + h)],
            "label": "face",
            "confidence": 0.9,  # Cascade doesn't provide confidence
            "center": [int(x + w/2), int(y + h/2)],
            "size": [int(w), int(h)]
        }
        detections.append(detection)

        cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (255, 0, 0), 2)

    return {
        "detections": detections,
        "annotated_image": annotated_image,
        "count": len(detections),
        "image_size": [image.shape[1], image.shape[0]]
    }


if __name__ == "__main__":
    # Test the detector
    import sys
    if len(sys.argv) > 1:
        result = detect_objects(sys.argv[1])
        for det in result['detections']:
            pass
            # print(f"  - {det['label']}: {det['confidence']:.2f} at {det['bbox']}")
