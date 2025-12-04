"""
MI-GAN ONNX Inpainting Tool
AI-powered inpainting using MI-GAN ONNX model
"""

import numpy as np
import cv2
import onnxruntime as ort
from typing import Dict, Any, Union, Optional
from pathlib import Path

# Path to ONNX model
MODEL_PATH = Path(__file__).parent.parent / "models/migan_pipeline_v2.onnx"
MODEL_RESOLUTION = 256  # kept for backward compatibility

# Global session (lazy loaded)
_onnx_session = None


# -----------------------------------------------------------
#  Mask Fix  — expand + feather (SAM masks need soft edges)
# -----------------------------------------------------------
def expand_and_feather(mask, expand_px=15, feather_px=21):
    """Expands and feathers SAM masks so MI-GAN behaves correctly."""
    kernel = np.ones((expand_px, expand_px), np.uint8)

    # Expand region
    dilated = cv2.dilate(mask, kernel, iterations=1)

    # Feather edges
    blurred = cv2.GaussianBlur(dilated, (feather_px | 1, feather_px | 1), 0)

    # Re-binarize
    return np.where(blurred > 127, 255, 0).astype(np.uint8)


# -----------------------------------------------------------
#  Load ONNX model
# -----------------------------------------------------------
import gc

def get_onnx_session():
    global _onnx_session
    if _onnx_session is None:

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"MI-GAN ONNX model not found at {MODEL_PATH}."
            )

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        _onnx_session = ort.InferenceSession(
            str(MODEL_PATH), providers=providers
        )

    return _onnx_session


def unload_model():
    """Unload the inpainting model to free GPU memory"""
    global _onnx_session
    if _onnx_session is not None:
        del _onnx_session
        _onnx_session = None
        gc.collect()
        # ONNX Runtime handles its own memory, but gc helps


# -----------------------------------------------------------
#  Main Inpaint Function 
# -----------------------------------------------------------
def inpaint_region(
    image: Union[np.ndarray, str],
    mask: Union[np.ndarray, str],
    prompt: Optional[str] = None,
    fallback_opencv: bool = True
) -> Dict[str, Any]:
    """
    Inpaint masked region using MI-GAN ONNX model.
    Compatible with the original tool schema.
    """

    # ---------------------------
    # Load image
    # ---------------------------
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None:
            raise ValueError(f"Could not load image from {image}")

    # ---------------------------
    # Load mask
    # ---------------------------
    if isinstance(mask, str):
        mask = cv2.imread(mask, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise ValueError(f"Could not load mask from {mask}")

    # ensure 0/255
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # -------------------------------------------------------
    # MI-GAN requires SOFT masks, expand + feather
    # -------------------------------------------------------
    mask = expand_and_feather(mask, expand_px=15, feather_px=21)

    # -------------------------------------------------------
    # MI-GAN expects 255 = known, 0 = to inpaint → invert
    # -------------------------------------------------------
    mask = 255 - mask

    # -------------------------------------------------------
    # Convert to tensors — **NO resizing**
    # -------------------------------------------------------
    image_tensor = image.transpose(2, 0, 1)[None].astype(np.uint8)
    mask_tensor = mask[None, None].astype(np.uint8)

    try:
        session = get_onnx_session()

        inputs = session.get_inputs()
        outputs = session.get_outputs()

        input_feed = {
            inputs[0].name: image_tensor,
            inputs[1].name: mask_tensor
        }

        # Run model
        output = session.run([outputs[0].name], input_feed)[0]

        # Back to HWC
        inpainted = output[0].transpose(1, 2, 0).astype(np.uint8)

        return {
            "inpainted_image": inpainted,
            "mask_used": mask,            # same key as old version
            "original_size": [image.shape[1], image.shape[0]],
            "is_stub": False,
            "model_used": "MI-GAN",
            "message": "Successfully inpainted using MI-GAN ONNX model"
        }

    except Exception as e:
        if not fallback_opencv:
            raise

        # --------------------------------------
        # Fallback: OpenCV
        # --------------------------------------
        print(f"MI-GAN failed: {e} → Using OpenCV fallback")

        inpainted = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)

        return {
            "inpainted_image": inpainted,
            "mask_used": mask,
            "original_size": [image.shape[1], image.shape[0]],
            "is_stub": True,
            "model_used": "OpenCV (fallback)",
            "message": f"MI-GAN failed ({str(e)}), used OpenCV fallback",
            "error": str(e)
        }


# -----------------------------------------------------------
#  Remove Object (unchanged API)
# -----------------------------------------------------------
def remove_object(
    image: Union[np.ndarray, str],
    bbox: list,
    prompt: Optional[str] = None
) -> Dict[str, Any]:

    if isinstance(image, str):
        image = cv2.imread(image)

    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    x1, y1, x2, y2 = [int(i) for i in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    mask[y1:y2, x1:x2] = 255

    return inpaint_region(image, mask, prompt)


# -----------------------------------------------------------
# Tool info
# -----------------------------------------------------------
def get_inpaint_info() -> Dict[str, Any]:
    model_available = MODEL_PATH.exists()

    return {
        "status": "ready" if model_available else "model_missing",
        "model": "MI-GAN ONNX",
        "model_path": str(MODEL_PATH),
        "model_exists": model_available,
        "model_resolution": MODEL_RESOLUTION,
        "capabilities": {
            "remove_objects": True,
            "inpaint_large_regions": True,
            "content_aware": True,
            "prompt_support": False
        },
        "providers_available": ort.get_available_providers(),
        "recommended_provider":
            "CUDAExecutionProvider"
            if "CUDAExecutionProvider" in ort.get_available_providers()
            else "CPUExecutionProvider"
    }


# -----------------------------------------------------------
# CLI
# -----------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 2:
        print("Running MI-GAN inpainting...")
        result = inpaint_region(sys.argv[1], sys.argv[2])

        output_path = "inpaint_output.jpg"
        cv2.imwrite(output_path, result["inpainted_image"])
        print(f"Saved to {output_path}")

    else:
        print("Usage: python inpaint.py <image_path> <mask_path>")
        import json
        print(json.dumps(get_inpaint_info(), indent=2))
