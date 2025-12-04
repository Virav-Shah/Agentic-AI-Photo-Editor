import os
import streamlit.components.v1 as components
import base64
from io import BytesIO

# Create a _RELEASE constant. We'll set this to False while developing.
_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "tiefling_viewer",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend")
    _component_func = components.declare_component("tiefling_viewer", path=build_dir)

def _to_base64(img_or_str):
    if img_or_str is None:
        return None
    if isinstance(img_or_str, str):
        if img_or_str.startswith("data:image"):
            return img_or_str
        return img_or_str
    
    buffered = BytesIO()
    img_or_str.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def tiefling_viewer_v2(image, depth_map, background=None, background_depth_map=None, mask=None, 
                       focus=0.5, sensitivity=0.5, radius=0, crop=0, 
                       foreground_sensitivity=0.05, background_sensitivity=1.0, 
                       grounded_mode=True, key=None):
    """
    Create a new instance of "tiefling_viewer".
    
    Args:
        foreground_sensitivity: Parallax sensitivity multiplier for foreground layer (0.0-1.0)
        background_sensitivity: Parallax sensitivity multiplier for background layer (0.0-2.0)
        grounded_mode: If True, subject bottom moves with background (natural for shadows)
    """
    
    image_b64 = _to_base64(image)
    depth_map_b64 = _to_base64(depth_map)
    background_b64 = _to_base64(background)
    background_depth_map_b64 = _to_base64(background_depth_map)
    mask_b64 = _to_base64(mask)

    component_value = _component_func(
        image=image_b64,
        depth_map=depth_map_b64,
        background=background_b64,
        background_depth_map=background_depth_map_b64,
        mask=mask_b64,
        focus=focus,
        sensitivity=sensitivity,
        radius=radius,
        crop=crop,
        foreground_sensitivity=foreground_sensitivity,
        background_sensitivity=background_sensitivity,
        grounded_mode=grounded_mode,
        key=key,
        default=0,
        height=1000
    )
    return component_value
