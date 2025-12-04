import python_multipart
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
# env config
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


try:
    # Set both part and file size limits to 100MB
    python_multipart.multipart.MultipartParser.max_part_size = 100 * 1024 * 1024
    python_multipart.multipart.MultipartParser.max_file_size = 100 * 1024 * 1024
except ImportError:
    pass

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import base64
import numpy as np
import cv2
from PIL import Image
import io
import json
import os
import shutil
from deepgram import DeepgramClient
from typing import Optional

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    detect_objects, segment_object, crop_image, apply_filter,
    resize_image, create_parallax, super_resolution, inpaint_region,
    change_theme
)
from tools.seg import segment_with_detection, segment_multiple_objects, segment_single_bbox
from tools.filter import get_available_filters
from tools.theme_changer import get_available_weather_classes
from orchestrator import run_agent, undo_last_edit
from quick_agent_mode.quick_agent import QuickAgentGemma

app = FastAPI(title="Adobe Photo Editor API", version="1.0.0")

# CORS - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from starlette.requests import Request
from starlette.responses import PlainTextResponse

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    try:
        body = await request.body()
    except:
        pass
    return PlainTextResponse("Internal error", status_code=500)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def process_pil_image(img_pil: Image.Image) -> np.ndarray:
    """Process PIL image: resize if too large and convert to BGR"""
    # Auto-resize very large images to prevent memory issues
    # If image is >10MB (approx check via size) or dimensions >4000px, resize to max 2048px
    max_dimension = 2048
    if max(img_pil.size) > 4000:
        img_pil.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    
    img_array = np.array(img_pil)

    # Convert to BGR for OpenCV
    if len(img_array.shape) == 2:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    elif img_array.shape[2] == 4:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    return img_bgr

def decode_base64_image(base64_str: str) -> np.ndarray:
    """Decode base64 string to numpy array (BGR format for OpenCV)"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]

        img_data = base64.b64decode(base64_str)
        
        img_pil = Image.open(io.BytesIO(img_data))
        return process_pil_image(img_pil)
    except Exception as e:
        raise ValueError(f"Failed to decode image: {str(e)}")

def encode_image_to_base64(img: np.ndarray) -> str:
    """Encode numpy array (BGR) to base64 string"""
    try:
        # Convert BGR to RGB
        if len(img.shape) == 3 and img.shape[2] == 3:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif len(img.shape) == 3 and img.shape[2] == 4:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        else:
            img_rgb = img

        img_pil = Image.fromarray(img_rgb.astype('uint8'))
        buffer = io.BytesIO()
        # Use compress_level=0 for maximum quality (no compression)
        img_pil.save(buffer, format="PNG", compress_level=0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return img_base64
    except Exception as e:
        raise ValueError(f"Failed to encode image: {str(e)}")

def encode_mask_to_base64(mask: np.ndarray) -> str:
    """Encode mask to base64"""
    try:
        mask_pil = Image.fromarray(mask.astype('uint8'))
        buffer = io.BytesIO()
        mask_pil.save(buffer, format="PNG")
        mask_base64 = base64.b64encode(buffer.getvalue()).decode()
        return mask_base64
    except Exception as e:
        raise ValueError(f"Failed to encode mask: {str(e)}")

def clean_state_for_json(state):
    """Recursively clean state to make it JSON-serializable"""
    if state is None:
        return None

    if isinstance(state, np.ndarray):
        # Convert numpy array to base64
        return encode_image_to_base64(state)
    elif isinstance(state, dict):
        cleaned = {}
        for key, value in state.items():
            if key in ['current_image', 'original_image'] and isinstance(value, np.ndarray):
                # Convert image arrays to base64
                cleaned[key] = encode_image_to_base64(value)
            elif key == 'intermediate_images' and isinstance(value, list):
                # Convert list of image arrays
                cleaned[key] = [encode_image_to_base64(img) if isinstance(img, np.ndarray) else img for img in value]
            elif isinstance(value, (dict, list)):
                cleaned[key] = clean_state_for_json(value)
            elif isinstance(value, np.ndarray):
                # Convert any other numpy arrays
                cleaned[key] = encode_image_to_base64(value)
            elif isinstance(value, (str, int, float, bool, type(None))):
                cleaned[key] = value
            else:
                # Try to convert to string for other types
                try:
                    cleaned[key] = str(value)
                except:
                    cleaned[key] = None
        return cleaned
    elif isinstance(state, list):
        return [clean_state_for_json(item) for item in state]
    else:
        return state

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Adobe Photo Editor API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "manual_tools": [
                "/tools/crop", "/tools/filter", "/tools/resize",
                "/tools/detect", "/tools/segment", "/tools/inpaint",
                "/tools/super_resolution", "/tools/parallax", "/tools/theme_change"
            ],
            "ai_agent": ["/agent/run", "/agent/undo"],
            "quick_edit": ["/quick_edit/parse", "/quick_edit/execute"],
            "utilities": ["/filters", "/weather_classes", "/health"]
        }
    }

@app.get("/health")
def health_check():
    return {"status": "OK", "message": "Server is running"}

@app.post("/system/clear_cache")
async def clear_cache():
    """
    Clear GPU cache and unload models to free VRAM.
    Useful if multiple requests are causing OOM or slowdowns.
    """
    try:
        import gc
        import torch
        from tools.depth import unload_model as unload_depth
        from tools.seg import unload_models as unload_seg
        from tools.inpaint import unload_model as unload_inpaint
        
        
        # Unload all models
        unload_depth()
        unload_seg()
        unload_inpaint()
        
        # Force garbage collection
        gc.collect()
        
        # Clear CUDA cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            vram_free = torch.cuda.mem_get_info()[0] / 1024**3
            vram_total = torch.cuda.mem_get_info()[1] / 1024**3
            message = f"Cache cleared. Free VRAM: {vram_free:.2f}GB / {vram_total:.2f}GB"
        else:
            message = "Cache cleared (CPU mode)"
            
        return {"success": True, "message": message}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")

# ============================================================================
# MANUAL TOOLS ENDPOINTS
# ============================================================================

@app.post("/tools/crop")
async def crop_tool(
    image: str = Form(...),
    aspect_ratio: str = Form(None),
    bbox: str = Form(None)
):
    """
    Crop image by aspect ratio or bbox

    Parameters:
    - image: base64 encoded image
    - aspect_ratio: "1:1", "4:3", "16:9", "9:16" or None
    - bbox: JSON string "[x1, y1, x2, y2]" or None
    """
    try:
        img = decode_base64_image(image)
        bbox_list = json.loads(bbox) if bbox else None

        result = crop_image(
            img,
            bbox=bbox_list,
            aspect_ratio=aspect_ratio if aspect_ratio else None
        )

        return {
            "success": True,
            "cropped_image": encode_image_to_base64(result["cropped_image"]),
            "original_size": result.get("original_size"),
            "new_size": result.get("new_size")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop failed: {str(e)}")

@app.post("/tools/filter")
async def filter_tool(
    image: str = Form(...),
    filter_type: str = Form(...),
    intensity: float = Form(1.0)
):
    """
    Apply filter to image

    Parameters:
    - image: base64 encoded image
    - filter_type: "grayscale", "sepia", "vintage", etc.
    - intensity: 0.0 to 2.0
    """
    try:
        img = decode_base64_image(image)
        result = apply_filter(img, filter_type, intensity)

        return {
            "success": True,
            "filtered_image": encode_image_to_base64(result["filtered_image"]),
            "filter_type": filter_type,
            "intensity": intensity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filter failed: {str(e)}")

@app.post("/tools/resize")
async def resize_tool(
    image: str = Form(...),
    scale: float = Form(None),
    width: int = Form(None),
    height: int = Form(None),
    maintain_aspect: bool = Form(True)
):
    """
    Resize image

    Parameters:
    - image: base64 encoded image
    - scale: Scale factor (e.g., 0.5, 2.0)
    - width: Target width in pixels
    - height: Target height in pixels
    - maintain_aspect: Whether to maintain aspect ratio
    """
    try:
        img = decode_base64_image(image)
        result = resize_image(
            img,
            scale=scale,
            width=width,
            height=height,
            maintain_aspect=maintain_aspect
        )

        return {
            "success": True,
            "resized_image": encode_image_to_base64(result["resized_image"]),
            "original_size": result.get("original_size"),
            "new_size": result.get("new_size")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resize failed: {str(e)}")

@app.post("/tools/detect")
async def detect_tool(
    image: str = Form(...),
    conf_threshold: float = Form(0.5)
):
    """
    Detect objects in image using YOLO

    Parameters:
    - image: base64 encoded image
    - conf_threshold: Confidence threshold (0.0 to 1.0)

    Returns:
    - annotated_image: Image with bounding boxes
    - detections: List of detected objects with labels, confidence, bbox
    - count: Number of objects detected
    """
    try:
        img = decode_base64_image(image)
        result = detect_objects(img, conf_threshold=conf_threshold)

        return {
            "success": True,
            "annotated_image": encode_image_to_base64(result["annotated_image"]),
            "detections": result["detections"],
            "count": result["count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@app.post("/tools/segment")
async def segment_tool(
    image: str = Form(...),
    bboxes: str = Form(...),
    labels: str = Form(...),
    mode: str = Form("single")
):
    """
    Segment object(s) using MobileSAM

    Parameters:
    - image: base64 encoded image
    - bboxes: JSON array of bounding boxes [[x1,y1,x2,y2], ...]
    - labels: JSON array of labels ["person", "car", ...]
    - mode: "single" or "multi"

    Returns:
    - masked_image: Segmented image
    - mask: Binary mask (single mode) or combined_mask (multi mode)
    - coverage: Percentage of image covered by mask
    """
    try:
        img = decode_base64_image(image)
        bboxes_list = json.loads(bboxes)
        labels_list = json.loads(labels)

        if mode == "multi":
            result = segment_multiple_objects(img, bboxes_list, labels_list)
            return {
                "success": True,
                "masked_image": encode_image_to_base64(result["masked_image"]),
                "combined_mask": encode_mask_to_base64(result["combined_mask"]),
                "coverage": result["coverage"],
                "count": result["count"]
            }
        else:
            result = segment_single_bbox(img, bboxes_list[0], labels_list[0])
            return {
                "success": True,
                "masked_image": encode_image_to_base64(result["masked_image"]),
                "mask": encode_mask_to_base64(result["mask"]),
                "coverage": result["coverage"]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

@app.post("/tools/inpaint")
async def inpaint_tool(
    image: str = Form(...),
    mask: str = Form(...)
):
    """
    Inpaint region using MI-GAN

    Parameters:
    - image: base64 encoded image
    - mask: base64 encoded binary mask (white = remove, black = keep)

    Returns:
    - inpainted_image: Image with inpainted regions
    """
    try:
        img = decode_base64_image(image)
        mask_img = decode_base64_image(mask)

        # Convert mask to grayscale
        if len(mask_img.shape) == 3:
            mask_gray = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
        else:
            mask_gray = mask_img

        result = inpaint_region(img, mask_gray)

        return {
            "success": True,
            "inpainted_image": encode_image_to_base64(result["inpainted_image"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inpainting failed: {str(e)}")

@app.post("/tools/super_resolution")
async def sr_tool(
    image: str = Form(...),
    scale: int = Form(4)
):
    """
    Upscale image using SwinIR

    Parameters:
    - image: base64 encoded image
    - scale: Upscale factor (typically 4)

    Returns:
    - upscaled_image: High resolution image
    - message: Status message
    """
    try:
        img = decode_base64_image(image)
        result = super_resolution(img, scale=scale)

        return {
            "success": True,
            "upscaled_image": encode_image_to_base64(result["upscaled_image"]),
            "message": result.get("message", "Super resolution completed"),
            "scale": scale
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Super resolution failed: {str(e)}")

@app.post("/tools/parallax")
async def parallax_tool(
    image: UploadFile = File(...),
    mask: UploadFile = File(None),
    depth_scale: float = Form(20.0),
    output_format: str = Form("html")
):
    """
    Create 3D parallax effect
    
    Parameters:
    - image: Image file upload
    - mask: Optional mask file upload
    - depth_scale: Depth scale for 3D effect (5.0 to 50.0)
    - output_format: "html", "frames", or "json"
    """
    try:
        # Read image file
        contents = await image.read()
        img_pil = Image.open(io.BytesIO(contents))
        img = process_pil_image(img_pil)

        mask_img = None
        if mask:
            mask_contents = await mask.read()
            mask_pil = Image.open(io.BytesIO(mask_contents))
            # Convert to numpy/grayscale
            mask_np = np.array(mask_pil)
            if len(mask_np.shape) == 3:
                mask_img = cv2.cvtColor(mask_np, cv2.COLOR_RGB2GRAY)
            else:
                mask_img = mask_np
        
        # Parallax
        result = create_parallax(
            img,
            mask=mask_img,
            depth_scale=depth_scale,
            output_format=output_format,
            export_json=True
        )
        response = {
            "success": True,
        }
        if "subject_layer" in result:
            response["subject_layer"] = encode_image_to_base64(result["subject_layer"])
        if "background_layer" in result:
            response["background_layer"] = encode_image_to_base64(result["background_layer"])
        if "foreground_depth" in result:
            response["foreground_depth"] = encode_mask_to_base64(result["foreground_depth"])
        if "background_depth" in result:
            response["background_depth"] = encode_mask_to_base64(result["background_depth"])
        if "mask" in result:
            response["mask"] = encode_mask_to_base64(result["mask"])
        if "json_config" in result:
            response["json_config"] = result["json_config"]
        if "json_string" in result:
            response["json_string"] = result["json_string"]
        if "has_layers" in result:
            response["has_layers"] = result["has_layers"]
        if "full_depth" in result:
            response["full_depth"] = encode_mask_to_base64(result["full_depth"])
        
        response["depth_scale"] = depth_scale
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Parallax creation failed: {str(e)}")

@app.post("/tools/theme_change")
async def theme_change_tool(
    image: UploadFile = File(...),
    time_of_day: int = Form(50),
    auto_detect: bool = Form(True),
    weather_override: str = Form(None)
):
    """
    Change theme (day/night) with weather awareness

    Parameters:
    - image: Image file upload
    - time_of_day: 0-100 (0=Day, 50=Evening, 100=Night)
    - auto_detect: Auto-detect weather from image
    - weather_override: Manually specify weather class

    Returns:
    - transformed_image: Theme-changed image
    - detected_weather: Detected weather class
    - sky_mask: Sky segmentation mask
    - time_of_day: Applied time value
    """
    try:
        contents = await image.read()
        img_pil = Image.open(io.BytesIO(contents))
        img = process_pil_image(img_pil)
        
        result = change_theme(
            img,
            time_of_day=time_of_day,
            weather_class=weather_override
        )

        response = {
            "success": True,
            "transformed_image": encode_image_to_base64(result["transformed_image"]),
            "detected_weather": result.get("detected_weather", "unknown"),
            "time_of_day": time_of_day
        }

        if "sky_mask" in result and result["sky_mask"] is not None:
            response["sky_mask"] = encode_mask_to_base64(result["sky_mask"])

        if "assets_count" in result:
            response["assets_count"] = result["assets_count"]

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Theme change failed: {str(e)}")

# ============================================================================
# AI AGENT ENDPOINTS 
# ============================================================================
deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)

async def run_agent_internal(
    query: str,
    img,  # Already decoded image
    existing_state: dict = None
):
    """
    Internal function to run agent - called by both endpoints
    """
    try:
        # If existing_state has base64 images, decode them back to numpy arrays
        if existing_state:
            if 'current_image' in existing_state and isinstance(existing_state['current_image'], str):
                existing_state['current_image'] = decode_base64_image(existing_state['current_image'])
            if 'original_image' in existing_state and isinstance(existing_state['original_image'], str):
                existing_state['original_image'] = decode_base64_image(existing_state['original_image'])
            if 'intermediate_images' in existing_state and isinstance(existing_state['intermediate_images'], list):
                existing_state['intermediate_images'] = [
                    decode_base64_image(img_str) if isinstance(img_str, str) else img_str 
                    for img_str in existing_state['intermediate_images']
                ]
            if 'image_history' in existing_state and isinstance(existing_state['image_history'], list):
                existing_state['image_history'] = [
                    decode_base64_image(img_str) if isinstance(img_str, str) else img_str 
                    for img_str in existing_state['image_history']
                ]

        result = run_agent(
            query,
            img,
            existing_state=existing_state
        )

        response = {
            "success": True,
            "status": result["status"],
            "explain": result.get("explain", ""),
            "state": clean_state_for_json(result["state"])
        }

        if result.get("result_image") is not None:
            response["result_image"] = encode_image_to_base64(result["result_image"])

        if result.get("html_output"):
            response["html_output"] = result["html_output"]

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


import logging
import time
import json
import os
from fastapi import File, Form, UploadFile, HTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

@app.post("/agent/process-voice")
async def process_voice_agent(
    audio: UploadFile = File(...),
    image: str = Form(...),
    existing_state: Optional[str] = Form(None),
    mode: str = Form("thinking"),
):
    start_time = time.time()
    logger = logging.getLogger("process_voice_agent")

    logger.info("─────────────── PROCESS VOICE REQUEST ───────────────")

    # Incoming metadata
    logger.info(f"Image type: {type(image)}")
    logger.info(f"Image length: {len(image)} chars")
    logger.info(f"Image preview: {image[:50]!r}")
    logger.info(f"Mode: {mode}")
    logger.info(f"Existing state length: {len(existing_state) if existing_state else 0}")

    temp_filename = None

    try:
        # --------------------------------------------------
        # 1. READ AUDIO
        # --------------------------------------------------
        audio_data = await audio.read()
        logger.info(f"Audio received: {len(audio_data)} bytes")
        logger.info(f"Audio filename: {audio.filename}, content-type={audio.content_type}")

        # Magic bytes for format detection
        logger.info(f"Audio first 16 bytes: {audio_data[:16].hex()}")

        # --------------------------------------------------
        # 2. DETECT AUDIO FORMAT
        # --------------------------------------------------
        if len(audio_data) > 8 and audio_data[4:8] == b'ftyp':
            temp_filename = "temp_audio.m4a"
            logger.info("Detected audio format: M4A (ftyp)")
        elif audio_data[:4] == b'\x1a\x45\xdf\xa3':
            temp_filename = "temp_audio.webm"
            logger.info("Detected audio format: WebM (EBML header)")
        else:
            temp_filename = "temp_audio.webm"
            logger.warning(f"Unknown audio format, defaulting to WebM. Bytes: {audio_data[:8].hex()}")

        # --------------------------------------------------
        # 3. WRITE TEMP FILE
        # --------------------------------------------------
        with open(temp_filename, "wb") as f:
            f.write(audio_data)

        logger.info(f"Saved audio → {temp_filename}")

        # --------------------------------------------------
        # 4. PREPARE AUDIO FOR DEEPGRAM
        # --------------------------------------------------
        with open(temp_filename, "rb") as f:
            audio_bytes = f.read()

        logger.info(f"Loaded audio bytes for Deepgram: {len(audio_bytes)} bytes")

        # --------------------------------------------------
        # 5. SEND TO DEEPGRAM
        # --------------------------------------------------
        logger.info("Sending audio to Deepgram…")

        try:
            response = deepgram.listen.v1.media.transcribe_file(
                request=audio_bytes,
                model="nova-3"
            )
        except Exception as dg_error:
            logger.error("Deepgram request failed!")
            logger.error(f"Deepgram exception: {repr(dg_error)}")
            raise

        logger.info("Deepgram responded successfully")

        # Log Deepgram response structure
        try:
            alt = response.results.channels[0].alternatives
            logger.info(f"Deepgram alternatives count: {len(alt)}")
        except Exception:
            logger.warning("Deepgram response missing 'alternatives' array")

        transcript = (
            response.results.channels[0].alternatives[0].transcript
            if response.results.channels[0].alternatives
            else ""
        )

        logger.info(f"Transcript: {transcript!r}")

        if not transcript:
            logger.warning("No speech detected by Deepgram")
            return {"success": False, "status": "no_speech_detected"}

        # --------------------------------------------------
        # 6. DECODE IMAGE
        # --------------------------------------------------
        logger.info("Decoding base64 image…")
        img = decode_base64_image(image)
        logger.info("Image decoded successfully")

        # --------------------------------------------------
        # 7. ROUTE TO FAST VS THINKING
        # --------------------------------------------------
        if mode == "fast":
            logger.info("[FAST MODE] Executing Quick Edit")
            result = await execute_quick_edit_internal(transcript, img)
        else:
            logger.info("[THINKING MODE] Running Agent")
            state_dict = json.loads(existing_state) if existing_state else None

            logger.info(f"Existing state loaded: {bool(state_dict)}")

            result = await run_agent_internal(
                transcript,
                img,
                existing_state=state_dict
            )

        logger.info("Agent execution complete")
        return result

    except Exception as e:
        logger.error("ERROR in process_voice_agent:")
        logger.exception(e)  # logs full stack trace
        raise HTTPException(status_code=500, detail=f"Voice error: {str(e)}")

    finally:
        # --------------------------------------------------
        # 8. CLEANUP TEMP FILE
        # --------------------------------------------------
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)
            logger.info(f"Temp file deleted: {temp_filename}")

        logger.info(f"Total processing time: {time.time() - start_time:.2f}s")
        logger.info("──────────── END PROCESS VOICE REQUEST ────────────")

@app.post("/agent/run")
async def run_agent_endpoint(
    query: str = Form(...),
    image: str = Form(...),
    session_id: str = Form(None),
    existing_state: str = Form(None)
):
    """
    Run AI agents
    """
    try:
        img = decode_base64_image(image)
        state_dict = json.loads(existing_state) if existing_state else None
        
        # Call internal function
        result = await run_agent_internal(
            query,
            img,
            existing_state=state_dict
        )
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
@app.post("/agent/undo")
async def undo_agent(state: str = Form(...)):
    """
    Undo last agent action

    Parameters:
    - state: Current agent state as JSON string

    Returns:
    - state: Updated state after undo
    - current_image: Image after undo
    """
    try:
        state_dict = json.loads(state)
        new_state = undo_last_edit(state_dict)

        response = {
            "success": True,
            "state": clean_state_for_json(new_state)
        }

        if new_state.get("current_image") is not None:
            response["current_image"] = encode_image_to_base64(new_state["current_image"])

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Undo failed: {str(e)}")

# ============================================================================
# QUICK EDIT ENDPOINTS (GEMMA MODE)
# ============================================================================

# Initialize Quick Agent
quick_agent = QuickAgentGemma()

@app.post("/quick_edit/parse")
async def parse_quick_query(query: str = Form(...)):
    """
    Parse query using Gemma (Quick Mode)

    Parameters:
    - query: User query/command

    Returns:
    - tool: Detected tool name
    - params: Extracted parameters
    """
    try:
        intent = quick_agent.parse_query(query)
        return {
            "success": True,
            "tool": intent["tool"],
            "params": intent["params"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query parsing failed: {str(e)}")

async def execute_quick_edit_internal(query: str, img: np.ndarray):
    """
    Internal function to execute quick edit
    
    Parameters:
    - query: User query/command
    - img: Decoded numpy array image
    
    Returns:
    - result dict with success, tool, params, result_image, etc.
    """
    try:
        # Parse query
        intent = quick_agent.parse_query(query)
        tool_name = intent["tool"]
        params = intent["params"]

        result_image = None
        result_html = None

        # Execute corresponding tool
        if tool_name == "filter":
            res = apply_filter(img, params.get("type"), params.get("intensity", 1.0))
            result_image = res["filtered_image"]

        elif tool_name == "super_resolution":
            res = super_resolution(img, scale=params.get("scale", 4))
            result_image = res["upscaled_image"]

        elif tool_name == "parallax":
            # Use create_parallax
            res = create_parallax(
                img,
                depth_scale=params.get("depth_scale", 20),
                output_format="json",
                export_json=True
            )
            
            # Return all parallax data
            response = {
                "success": True,
                "tool": tool_name,
                "params": params,
                "explain": "Applied 3D parallax effect"
            }
            
            # Add layer data
            if "subject_layer" in res:
                response["subject_layer"] = encode_image_to_base64(res["subject_layer"])
            if "background_layer" in res:
                response["background_layer"] = encode_image_to_base64(res["background_layer"])
            if "foreground_depth" in res:
                response["foreground_depth"] = encode_mask_to_base64(res["foreground_depth"])
            if "background_depth" in res:
                response["background_depth"] = encode_mask_to_base64(res["background_depth"])
            if "mask" in res:
                response["mask"] = encode_mask_to_base64(res["mask"])
            if "json_string" in res:
                response["json_config"] = res["json_string"]
            if "has_layers" in res:
                response["has_layers"] = res["has_layers"]
            
            return response

        elif tool_name == "theme_changer":
            res = change_theme(
                img,
                time_of_day=params.get("time_of_day", 50)
            )
            result_image = res["transformed_image"]

        elif tool_name == "crop":
            res = crop_image(img, aspect_ratio=params.get("aspect_ratio"))
            result_image = res["cropped_image"]

        elif tool_name == "resize":
            res = resize_image(img, scale=params.get("scale", 1.0))
            result_image = res["resized_image"]

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        response = {
            "success": True,
            "tool": tool_name,
            "params": params,
            "explain": f"Applied {tool_name} with params: {params}"
        }

        if result_image is not None:
            response["result_image"] = encode_image_to_base64(result_image)
        if result_html is not None:
            response["html_output"] = result_html

        return response
    except RuntimeError as e:
        if "SkySegmenter not available" in str(e):
            return {
                "success": False,
                "error": "SkySegmenter model not available",
                "explain": "The relight feature requires the SkySegmenter model. Please use Thinking mode or the manual relight slider instead."
            }
        raise HTTPException(status_code=500, detail=f"Quick edit failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick edit failed: {str(e)}")

@app.post("/quick_edit/execute")
async def execute_quick_edit(
    query: str = Form(...),
    image: str = Form(...)
):
    """
    Execute quick edit using Gemma parsing
    """
    try:
        img = decode_base64_image(image)
        return await execute_quick_edit_internal(query, img)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick edit failed: {str(e)}")

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/filters")
def get_filters():
    """Get available filter types"""
    try:
        filters = get_available_filters()
        return {
            "success": True,
            "filters": filters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get filters: {str(e)}")

@app.get("/weather_classes")
def get_weather():
    """Get available weather classes for theme changer"""
    try:
        classes = get_available_weather_classes()
        return {
            "success": True,
            "classes": classes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weather classes: {str(e)}")

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("Adobe Photo Editor API Server")
    print("="*60)
    print("Starting server on http://0.0.0.0:8000")
    print("API Documentation: http://0.0.0.0:8000/docs")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")