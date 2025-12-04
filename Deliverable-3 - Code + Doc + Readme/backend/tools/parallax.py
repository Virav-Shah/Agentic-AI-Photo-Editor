"""
Parallax Tool - 3D Depth-based Effect with BiRefNet
Integrated workflow for creating iPhone-like parallax/3D photo effects
Exports JSON for Unity/Flutter integration
"""
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Any, Union, List, Optional, Tuple
import json
import base64
from PIL import Image
from io import BytesIO
from .depth import estimate_depth

def _fast_blur(depth_map: np.ndarray, scale: float = 0.1, kernel_size: int = 11) -> np.ndarray:
    """
    Fast blur using downsampling. 10-20x faster than direct Gaussian blur.
    
    Args:
        depth_map: Input depth map
        scale: Downsampling factor (0.1 = 10x smaller)
        kernel_size: Blur kernel size on downsampled image
    
    Returns:
        Heavily blurred depth map
    """
    # Downsample
    small = cv2.resize(depth_map, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    # Blur on small image
    blur_small = cv2.blur(small, (kernel_size, kernel_size))
    # Upsample back
    blurred = cv2.resize(blur_small, (depth_map.shape[1], depth_map.shape[0]), interpolation=cv2.INTER_LINEAR)
    return blurred

def create_parallax(
    image: Union[np.ndarray, str],
    mask: Optional[np.ndarray] = None,
    depth_scale: float = 20.0,
    num_frames: int = 30,
    motion_type: str = "circular",
    output_format: str = "frames",
    label: Optional[str] = None,
    export_json: bool = False,
    min_coverage_percent: float = 4.0,  # Skip if subject < 4% of image
    min_subject_depth: float = 100.0    # Skip if subject too far (0-255 scale)
) -> Dict[str, Any]:
    """
    Full Parallax Workflow with "Hidden Volume" logic to prevent artifacts.
    """
    
    # 1. LOAD IMAGE
    if isinstance(image, str):
        image = cv2.imread(image)
        if image is None: 
            raise ValueError(f"Could not load image")
    
    # Store original image dimensions
    original_image = image.copy()
    original_h, original_w = original_image.shape[:2]
    
    # 2. SEGMENTATION (BiRefNet) - on ORIGINAL image for quality
    if mask is None:
        mask_original = _segment_with_birefnet(original_image)
        if np.sum(mask_original) == 0:
            return {"has_layers": False, "subject_layer": original_image}
    else:
        mask_original = mask
    
    # Ensure mask is uint8/binary [0, 255]
    if mask_original.dtype != np.uint8:
        mask_original = (mask_original * 255).astype(np.uint8)
    
    # Downsample image for depth estimation (faster)
    h, w = original_h, original_w
    max_dim = 960
    scale_factor = 1.0
    
    if max(h, w) > max_dim:
        scale_factor = max_dim / max(h, w)
        # Use INTER_AREA for downsampling (better for preventing aliasing)
        image_downsampled = cv2.resize(original_image, (int(w * scale_factor), int(h * scale_factor)), interpolation=cv2.INTER_AREA)
        # Downsample mask too for depth processing
        mask_downsampled = cv2.resize(mask_original, (int(w * scale_factor), int(h * scale_factor)), interpolation=cv2.INTER_LINEAR)
        h_down, w_down = image_downsampled.shape[:2]
    else:
        image_downsampled = original_image
        mask_downsampled = mask_original
        h_down, w_down = h, w
    
    # 3. GENERATE FULL DEPTH MAP (Geometry Source) - on downsampled image for speed
    depth_result = estimate_depth(image_downsampled)
    full_depth_map = depth_result['depth_map']

    # --- SKIP LOGIC: Check if subject is too small or too far ---
    # Perform these checks ON DOWNSAMPLED DATA to save compute
    
    # Check 1: Coverage
    coverage = (mask_downsampled > 0).sum() / mask_downsampled.size * 100
    
    # Check 2: Subject depth (is it too far?)
    subject_depth_values = full_depth_map[mask_downsampled > 0]
    avg_subject_depth = np.mean(subject_depth_values) if len(subject_depth_values) > 0 else 0


    if coverage < min_coverage_percent or avg_subject_depth < min_subject_depth:
        # Fallback: Apply heavy blur to full depth map
        blurred_full_depth = _fast_blur(full_depth_map)
        
        # Upscale depth to original resolution
        blurred_full_depth_original = cv2.resize(
            blurred_full_depth, (original_w, original_h), interpolation=cv2.INTER_LINEAR
        )
        return {
            "has_layers": False, 
            "subject_layer": original_image,
            "full_depth": blurred_full_depth_original
        }
    # --- STEP 4: VISUAL LAYER (SOFT EDGES) ---
    # Fixes "Jagged Hands". Soft alpha mask for TEXTURE.
    
    # Use fixed 5px blur (matches parallax_app proven approach)
    # This provides subtle anti-aliasing without over-blurring
    blur_k = 5
    
    # Apply Gaussian blur to soften mask edges
    soft_mask_original = cv2.GaussianBlur(mask_original, (blur_k, blur_k), 0)
    
    # Create RGBA Subject Layer
    subject_layer = np.zeros((original_h, original_w, 4), dtype=np.uint8)
    subject_layer[:, :, :3] = original_image
    subject_layer[:, :, 3] = soft_mask_original

    # --- STEP 5: DEPTH MASK (DILATED/HARD) ---
    # Fixes "Edge Stretching". Wider mask for GEOMETRY.
    
    # Dynamic Dilation Kernel: 0.5% of downsampled width for geometry expansion
    dilate_k_val = max(3, int(w_down * 0.005))
    kernel_dilate = np.ones((dilate_k_val, dilate_k_val), np.uint8)
    
    dilated_mask_downsampled = cv2.dilate(mask_downsampled, kernel_dilate, iterations=1)

    # --- STEP 6: BACKGROUND GENERATION ---
    # Inpaint on ORIGINAL image for quality. 
    # We need a heavy dilation for inpainting to remove the "halo" of the subject.
    
    # Dynamic Inpaint Kernel: 1.0% of original width
    inpaint_k_val = max(5, int(original_w * 0.01))
    kernel_inpaint = np.ones((inpaint_k_val, inpaint_k_val), np.uint8)
    
    # We create a HARD binary mask for inpainting logic (threshold to remove soft edges)
    _, mask_original_hard = cv2.threshold(mask_original, 127, 255, cv2.THRESH_BINARY)
    mask_for_inpainting = cv2.dilate(mask_original_hard, kernel_inpaint, iterations=2)
    
    background_layer = _create_background(original_image, mask_for_inpainting)
    
    # --- STEP 7: BACKGROUND DEPTH ---
    # Compute on downsampled background for speed
    background_downsampled = cv2.resize(background_layer, (w_down, h_down), interpolation=cv2.INTER_AREA)
    bg_depth_result = estimate_depth(background_downsampled)
    background_depth = bg_depth_result['depth_map']
    
    # Heavy blur for background depth
    background_depth = _fast_blur(background_depth)
    
    # Upscale to original resolution
    background_depth_original = cv2.resize(background_depth, (original_w, original_h), interpolation=cv2.INTER_LINEAR)
    
    # --- STEP 8: FOREGROUND DEPTH (ANCHORED & VOLUMETRIC) ---
    # Fixes "Floating Feet" and "Cardboard Effect".
    foreground_depth = _process_foreground_depth_grounded(
        full_depth_map, 
        background_depth, 
        dilated_mask_downsampled  # Uses downsampled dilated mask
    )
    
    # Upscale foreground depth to original resolution
    # CUBIC is often better for depth maps to preserve smooth curvature
    foreground_depth_original = cv2.resize(foreground_depth, (original_w, original_h), interpolation=cv2.INTER_CUBIC)

    # Final Result Construction
    return {
        "subject_layer": subject_layer,       # RGBA with Soft Edges
        "background_layer": background_layer, # Inpainted Background
        "foreground_depth": foreground_depth_original, 
        "background_depth": background_depth_original, 
        "mask": soft_mask_original,           
        "depth_scale": depth_scale,
        "has_layers": True
    }

def _process_foreground_depth_grounded(depth_map: np.ndarray, background_depth: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Robust Grounding & Volume Logic.
    1. Finds strict bottom contact point (Feet).
    2. Snaps Feet Depth to Background Ground Depth.
    3. Preserves internal volume (curves).
    4. Prevents 'Shifted Back' errors using Max clamping.
    """
    # Work in float32
    depth = depth_map.astype(np.float32)
    bg_depth = background_depth.astype(np.float32)
    
    # Ensure binary mask for logic calculations
    if len(mask.shape) > 2: mask = mask[:,:,0]
    _, mask_binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    
    # 1. FIND CONTACT POINT
    y_indices, x_indices = np.where(mask_binary > 0)
    if len(y_indices) == 0: return depth_map

    max_y = np.max(y_indices)
    
    # Look at absolute bottom 2 pixels (Strict Feet Detection)
    bottom_edge_mask = (mask_binary > 0) & (np.indices(mask_binary.shape)[0] >= max_y - 2)
    
    # Fallback if mask is too small
    if not np.any(bottom_edge_mask): bottom_edge_mask = mask_binary > 0

    # 2. GET ANCHOR VALUES
    # Subject Feet Depth
    subject_feet_depth = np.median(depth[bottom_edge_mask])
    
    # Background Ground Depth (at same location)
    ground_depth = np.median(bg_depth[bottom_edge_mask])
    
    # Safety: Don't let ground be "too bright" (too close) if estimation failed
    ground_depth = min(ground_depth, 250.0)


    # 3. FLATTEN DEPTH (User Request)
    # Instead of preserving volume, we flatten the entire subject to the ground depth.
    # This treats the subject as a flat "cardboard cutout" placed at the correct depth.
    adjusted_depth = np.full_like(depth, ground_depth + 1)
    
    # 4. (Skipped) APPLY SHIFT TO PRESERVE VOLUME
    # adjusted_depth = depth + shift
    
    # 5. (Skipped) PREVENT "SHIFTED BACK" / "SINKING"
    # adjusted_depth = np.maximum(adjusted_depth, ground_depth + 1)
    
    # 6. MASK AND RETURN
    final_depth = np.zeros_like(depth)
    final_depth[mask_binary > 0] = adjusted_depth[mask_binary > 0]
    
    # Ensure edge dilation in the depth map itself to match the mask
    # This ensures the "Hard" depth mask is filled with valid data
    final_depth = cv2.dilate(final_depth, np.ones((3,3), np.uint8), iterations=1)
    
    return np.clip(final_depth, 0, 255).astype(np.uint8)

def _segment_with_birefnet(image: np.ndarray) -> np.ndarray:
    """
    Segment main subject using BiRefNet for high-quality segmentation.

    Args:
        image: Input image (BGR format)

    Returns:
        Binary mask (uint8, 0-255) of the detected subject
    """
    try:
        from .seg import segment_foreground

        # Use BiRefNet segmentation
        result = segment_foreground(image)
        mask = result['mask']

        # Check if segmentation was successful
        if np.sum(mask) > 0:
            coverage = (mask > 0).sum() / mask.size * 100
            return mask
        else:
            return np.zeros(image.shape[:2], dtype=np.uint8)

    except Exception as e:
        pass


    """
    Last resort segmentation using GrabCut.

    Args:
        image: Input image (BGR format)

    Returns:
        Binary mask (uint8, 0-255)
    """
    h, w = image.shape[:2]

    # Use center region as probable foreground
    margin = min(h, w) // 8
    rect = (margin, margin, w - 2 * margin, h - 2 * margin)

    # Initialize GrabCut
    mask = np.zeros(image.shape[:2], np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        mask = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        return (mask * 255).astype(np.uint8)
    except:
        # If GrabCut fails, return center region
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        mask[margin:h-margin, margin:w-margin] = 255
        return mask


def _process_foreground_depth(depth_map: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Create a flat depth map for the foreground, anchored to the ground.
    This ensures the feet stick to the ground position.

    Args:
        depth_map: Original depth map (grayscale)
        mask: Binary mask of foreground subject

    Returns:
        Processed depth map for foreground (flat, anchored)
    """
    depth = depth_map.copy()

    # Ensure mask is binary
    if len(mask.shape) > 2:
        mask = mask[:,:,0]
    _, mask_binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # Find the bottom-most pixels of the subject
    y_indices, x_indices = np.where(mask_binary > 0)

    if len(y_indices) == 0:
        return depth

    max_y = np.max(y_indices)

    # Sample depth from the ground just below the feet
    h, w = depth.shape
    sample_y_start = min(max_y + 1, h - 1)
    sample_y_end = min(max_y + 20, h)

    # Get x-range of the bottom of the subject
    bottom_pixels_mask = (mask_binary > 0) & (np.indices(mask_binary.shape)[0] >= (max_y - 5))
    bottom_x_indices = np.where(bottom_pixels_mask)[1]

    if len(bottom_x_indices) > 0:
        min_x = np.min(bottom_x_indices)
        max_x = np.max(bottom_x_indices)

        # Extract ground region
        ground_region = depth[sample_y_start:sample_y_end, min_x:max_x]

        if ground_region.size > 0:
            anchor_depth = np.median(ground_region)
        else:
            anchor_depth = np.median(depth[bottom_pixels_mask])
    else:
        anchor_depth = np.median(depth[mask_binary > 0])

    # Create a flat depth map for foreground
    flat_depth = depth.copy()
    flat_depth[mask_binary > 0] = int(anchor_depth)

    return flat_depth

def _create_background(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Create background by inpainting the masked region using MI-GAN.

    Args:
        image: Input image (BGR)
        mask: Binary mask of region to inpaint

    Returns:
        Inpainted background (BGR)
    """
    from .inpaint import inpaint_region

    # Use MI-GAN inpainting
    try:
        result = inpaint_region(image, mask, fallback_opencv=True)
        background = result['inpainted_image']
    except Exception as e:
        # Fallback to OpenCV inpainting
        kernel = np.ones((5, 5), np.uint8)
        dilated_mask = cv2.dilate(mask, kernel, iterations=2)
        background = cv2.inpaint(image, dilated_mask, 7, cv2.INPAINT_TELEA)

    return background


def _generate_parallax_frames(
    subject: np.ndarray,
    background: np.ndarray,
    depth_scale: float,
    num_frames: int,
    motion_type: str
) -> List[np.ndarray]:
    """
    Generate list of parallax animation frames.

    Args:
        subject: Subject layer (RGBA)
        background: Background layer (BGR)
        depth_scale: Depth effect strength
        num_frames: Number of frames to generate
        motion_type: Type of motion ("circular", "horizontal", "vertical")

    Returns:
        List of rendered frames (BGR)
    """
    frames = []
    h, w = background.shape[:2]

    for i in range(num_frames):
        t = i / num_frames * 2 * np.pi

        if motion_type == "circular":
            dx = np.sin(t) * depth_scale
            dy = np.cos(t) * depth_scale * 0.5
        elif motion_type == "horizontal":
            dx = np.sin(t) * depth_scale
            dy = 0
        elif motion_type == "vertical":
            dx = 0
            dy = np.sin(t) * depth_scale
        else:  # mouse or default
            dx = np.sin(t) * depth_scale
            dy = np.cos(t) * depth_scale * 0.3

        # Move background (less movement for farther objects)
        bg_dx = dx * 0.3
        bg_dy = dy * 0.3

        # Move subject (more movement for closer objects)
        subj_dx = -dx * 0.7
        subj_dy = -dy * 0.7

        # Create frame by compositing
        frame = _composite_layers(
            subject, background,
            (subj_dx, subj_dy), (bg_dx, bg_dy)
        )
        frames.append(frame)

    return frames


def _composite_layers(
    subject: np.ndarray,
    background: np.ndarray,
    subject_offset: Tuple[float, float],
    bg_offset: Tuple[float, float]
) -> np.ndarray:
    """
    Composite subject and background with offsets.

    Args:
        subject: Subject layer (RGBA)
        background: Background layer (BGR)
        subject_offset: (dx, dy) offset for subject
        bg_offset: (dx, dy) offset for background

    Returns:
        Composited frame (BGR)
    """
    h, w = background.shape[:2]

    # Create translation matrices
    bg_matrix = np.float32([[1, 0, bg_offset[0]], [0, 1, bg_offset[1]]])
    subj_matrix = np.float32([[1, 0, subject_offset[0]], [0, 1, subject_offset[1]]])

    # Translate background
    bg_shifted = cv2.warpAffine(
        background, bg_matrix, (w, h),
        borderMode=cv2.BORDER_REPLICATE
    )

    # Translate subject
    subj_shifted = cv2.warpAffine(
        subject, subj_matrix, (w, h),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0)
    )

    # Composite: place subject over background
    if bg_shifted.shape[2] == 3:
        result = cv2.cvtColor(bg_shifted, cv2.COLOR_BGR2BGRA)
    else:
        result = bg_shifted.copy()

    # Alpha blending
    alpha = subj_shifted[:, :, 3:4] / 255.0
    for c in range(3):
        result[:, :, c] = (
            subj_shifted[:, :, c] * alpha[:, :, 0] +
            result[:, :, c] * (1 - alpha[:, :, 0])
        ).astype(np.uint8)

    # Convert back to BGR
    result = cv2.cvtColor(result, cv2.COLOR_BGRA2BGR)

    return result


def _generate_interactive_html(
    subject: np.ndarray,
    background: np.ndarray,
    foreground_depth: np.ndarray,
    background_depth: np.ndarray,
    depth_scale: float
) -> str:
    """
    Generate interactive HTML with mouse/gyro parallax effect.
    Uses the tiefling viewer approach with depth-based displacement.

    Args:
        subject: Subject layer (RGBA)
        background: Background layer (BGR)
        foreground_depth: Depth map for foreground
        background_depth: Depth map for background
        depth_scale: Depth effect strength

    Returns:
        HTML string with embedded viewer
    """
    # Encode images to base64
    _, subject_buffer = cv2.imencode('.png', subject)
    subject_b64 = base64.b64encode(subject_buffer).decode('utf-8')

    _, bg_buffer = cv2.imencode('.jpg', background)
    bg_b64 = base64.b64encode(bg_buffer).decode('utf-8')

    # Encode depth maps
    _, fg_depth_buffer = cv2.imencode('.png', foreground_depth)
    fg_depth_b64 = base64.b64encode(fg_depth_buffer).decode('utf-8')

    _, bg_depth_buffer = cv2.imencode('.png', background_depth)
    bg_depth_b64 = base64.b64encode(bg_depth_buffer).decode('utf-8')

    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Parallax Photo Effect</title>
    <style>
        body {{
            margin: 0;
            overflow: hidden;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        .parallax-container {{
            position: relative;
            width: {background.shape[1]}px;
            height: {background.shape[0]}px;
            overflow: hidden;
            perspective: 1000px;
        }}
        .layer {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            transition: transform 0.1s ease-out;
        }}
        .background {{
            z-index: 1;
        }}
        .subject {{
            z-index: 2;
        }}
        img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .info {{
            position: fixed;
            top: 10px;
            left: 10px;
            color: white;
            background: rgba(0,0,0,0.7);
            padding: 10px;
            border-radius: 5px;
            font-family: Arial, sans-serif;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="info">
        Move your mouse to see the 3D parallax effect<br>
        <small>Generated with BiRefNet + MI-GAN</small>
    </div>
    <div class="parallax-container" id="container">
        <div class="layer background" id="bgLayer">
            <img src="data:image/jpeg;base64,{bg_b64}" alt="Background">
        </div>
        <div class="layer subject" id="subjLayer">
            <img src="data:image/png;base64,{subject_b64}" alt="Subject">
        </div>
    </div>

    <script>
        const container = document.getElementById('container');
        const bgLayer = document.getElementById('bgLayer');
        const subjLayer = document.getElementById('subjLayer');
        const depthScale = {depth_scale};

        // Mouse movement
        container.addEventListener('mousemove', (e) => {{
            const rect = container.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;

            const bgX = x * depthScale * 0.3;
            const bgY = y * depthScale * 0.3;
            const subjX = -x * depthScale * 0.7;
            const subjY = -y * depthScale * 0.7;

            bgLayer.style.transform = `translate(${{bgX}}px, ${{bgY}}px)`;
            subjLayer.style.transform = `translate(${{subjX}}px, ${{subjY}}px)`;
        }});

        // Reset on mouse leave
        container.addEventListener('mouseleave', () => {{
            bgLayer.style.transform = 'translate(0, 0)';
            subjLayer.style.transform = 'translate(0, 0)';
        }});

        // Gyroscope support for mobile
        if (window.DeviceOrientationEvent) {{
            window.addEventListener('deviceorientation', (e) => {{
                const x = e.gamma / 45;
                const y = e.beta / 45;

                const bgX = x * depthScale * 0.3;
                const bgY = y * depthScale * 0.3;
                const subjX = -x * depthScale * 0.7;
                const subjY = -y * depthScale * 0.7;

                bgLayer.style.transform = `translate(${{bgX}}px, ${{bgY}}px)`;
                subjLayer.style.transform = `translate(${{subjX}}px, ${{subjY}}px)`;
            }});
        }}
    </script>
</body>
</html>'''

    return html


# Backward compatibility exports
def save_parallax_html(
    image: Union[np.ndarray, str],
    output_path: str,
    label: str = "person",
    mask: Optional[np.ndarray] = None,
    depth_scale: float = 20.0
) -> str:
    """
    Create and save interactive parallax HTML file.

    Args:
        image: Input image
        output_path: Path to save HTML file
        label: (Deprecated) Class label
        mask: Optional pre-computed mask
        depth_scale: Depth effect strength

    Returns:
        Path to saved HTML file
    """
    result = create_parallax(
        image, mask=mask, depth_scale=depth_scale,
        output_format="html"
    )

    with open(output_path, 'w') as f:
        f.write(result['html'])

    return output_path


def create_depth_map(image: Union[np.ndarray, str]) -> np.ndarray:
    """
    Create a depth map using Depth-Anything-V2.

    Args:
        image: Input image

    Returns:
        Depth map (grayscale, 0-255)
    """
    if isinstance(image, str):
        image = cv2.imread(image)

    from .depth import estimate_depth
    result = estimate_depth(image)
    return result['depth_map']


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = create_parallax(sys.argv[1], output_format="html", export_json=True)

        # Save HTML
        html_path = "parallax_output.html"
        with open(html_path, 'w') as f:
            f.write(result['html'])

        # Save JSON
        if 'json_string' in result:
            json_path = "parallax_config.json"
            with open(json_path, 'w') as f:
                f.write(result['json_string'])
