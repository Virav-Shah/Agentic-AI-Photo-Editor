import cv2
import numpy as np
from cv2.ximgproc import guidedFilter

def skymask_refinement(G_pred, img):
    """
    Refines the coarse sky mask using Guided Filter.
    Args:
        G_pred: Coarse mask (H, W, 3) or (H, W, 1), values 0-1.
        img: Source image (H, W, 3), values 0-1.
    Returns:
        refined_skymask: (H, W, 3)
    """
    r, eps = 20, 0.01
    # guidedFilter expects float32
    if G_pred.ndim == 3:
        mask_guide = G_pred[:, :, 0]
    else:
        mask_guide = G_pred
        
    # Using the Red channel of the image as guidance (SkyAR uses index 2 which is R in RGB or B in BGR? 
    # SkyAR loads with cv2.imread (BGR) then converts to RGB.
    # In SkyAR: refined_skymask = guidedFilter(img[:,:,2], G_pred[:,:,0], r, eps)
    # If img is RGB, index 2 is Blue. If img is BGR, index 2 is Red.
    # SkyAR: img_HD = cv2.cvtColor(img_HD, cv2.COLOR_BGR2RGB) -> RGB.
    # So index 2 is Blue.    
    refined_skymask = guidedFilter(img[:, :, 2], mask_guide, r, eps)
    
    # Apply edge-preserving smoothing with bilateral filter to remove white borders
    # while maintaining sharp transitions
    refined_skymask_u8 = (refined_skymask * 255).astype(np.uint8)
    
    # Bilateral filter: smooths while preserving edges
    refined_skymask_u8 = cv2.bilateralFilter(refined_skymask_u8, 9, 75, 75)
    
    # Apply morphological closing to remove small white artifacts
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    refined_skymask_u8 = cv2.morphologyEx(refined_skymask_u8, cv2.MORPH_CLOSE, kernel)
    
    # Convert back to float
    refined_skymask = refined_skymask_u8.astype(np.float32) / 255.0
    
    # Slight Gaussian blur for final smoothing
    refined_skymask = cv2.GaussianBlur(refined_skymask, (3, 3), 0)
    
    refined_skymask = np.stack(
        [refined_skymask, refined_skymask, refined_skymask], axis=-1)

    return np.clip(refined_skymask, a_min=0, a_max=1)

def relighting(img, skybg, skymask, relighting_factor=0.8, recoloring_factor=0.5, auto_light_matching=False):
    """
    Adjusts the foreground lighting to match the new sky.
    """
    # color matching, reference: skybox_img
    # Downsample for speed and robustness
    step = int(max(img.shape[0], img.shape[1]) / 20)
    if step < 1: step = 1
    
    skybg_thumb = skybg[::step, ::step, :]
    img_thumb = img[::step, ::step, :]
    skymask_thumb = skymask[::step, ::step, :]
    
    skybg_mean = np.mean(skybg_thumb, axis=(0, 1), keepdims=True)
    
    # Calculate foreground mean (weighted by 1-skymask)
    mask_sum = (1 - skymask_thumb).sum(axis=(0, 1), keepdims=True)
    img_mean = np.sum(img_thumb * (1 - skymask_thumb), axis=(0, 1), keepdims=True) / (mask_sum + 1e-9)
    
    diff = skybg_mean - img_mean
    img_colortune = img + recoloring_factor * diff

    if auto_light_matching:
        return np.clip(img_colortune, 0, 1)
    else:
        # keep foreground ambient_light and manually adjust lighting
        res = relighting_factor * (img_colortune + (img.mean() - img_colortune.mean()))
        return np.clip(res, 0, 1)

def halo(syneth, skybg, skymask, halo_radius_ratio=0.2):
    """
    Adds a halo effect (bloom) around the sky boundary.
    """
    h, w, c = syneth.shape
    kernel_size = int(w * halo_radius_ratio)
    if kernel_size % 2 == 0:
        kernel_size += 1
        
    # reflection
    halo_effect = 0.5 * cv2.blur(
        skybg * skymask, (kernel_size, kernel_size))
        
    # screen blend 1 - (1-a)(1-b)
    syneth_with_halo = 1 - (1 - syneth) * (1 - halo_effect)
    
    return np.clip(syneth_with_halo, 0, 1)

def color_transfer_reinhard(source, target):
    """
    Transfers the color distribution from the target image to the source image
    using the Reinhard method in LAB color space.
    Args:
        source: Source image (H, W, 3), float32 [0, 1] (RGB)
        target: Target image (H, W, 3), float32 [0, 1] (RGB)
    Returns:
        res: Color transferred source image (H, W, 3), float32 [0, 1]
    """
    # Convert to LAB
    src_lab = cv2.cvtColor((source * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    tgt_lab = cv2.cvtColor((target * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    
    # Calculate statistics
    src_mean, src_std = cv2.meanStdDev(src_lab)
    tgt_mean, tgt_std = cv2.meanStdDev(tgt_lab)
    
    src_mean = src_mean.reshape(1, 1, 3)
    src_std = src_std.reshape(1, 1, 3)
    tgt_mean = tgt_mean.reshape(1, 1, 3)
    tgt_std = tgt_std.reshape(1, 1, 3)
    
    # Avoid division by zero
    src_std = np.maximum(src_std, 1e-6)
    
    # Transfer
    res_lab = (src_lab - src_mean) * (tgt_std / src_std) + tgt_mean
    
    # Clip and convert back
    res_lab = np.clip(res_lab, 0, 255).astype(np.uint8)
    res_rgb = cv2.cvtColor(res_lab, cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0
    
    return res_rgb

def apply_fog(img, depth, sky_color, strength=0.5):
    """
    Applies atmospheric fog based on depth.
    Args:
        img: Image (H, W, 3)
        depth: Depth map (H, W), 1=close, 0=far
        sky_color: Average sky color (3,)
        strength: Fog intensity (0-1)
    """
    
    fog_factor = (1.0 - depth) * strength
    fog_factor = np.clip(fog_factor, 0, 1)
    fog_factor = fog_factor[:, :, np.newaxis] # (H, W, 1)
    
    res = img * (1 - fog_factor) + sky_color * fog_factor
    return np.clip(res, 0, 1)

def detect_sunlight(img, mask):
    """
    Detects bright, warm (sunlit) areas in the foreground.
    Args:
        img: RGB image (H, W, 3), float32 [0, 1]
        mask: Sky mask (H, W, 3), float32 [0, 1] (1=sky, 0=foreground)
    Returns:
        sunlight_mask: (H, W, 1), float32 [0, 1]
    """
    # Safety check
    if img is None or mask is None:
        return np.zeros((1, 1, 1), dtype=np.float32)

    # Convert to LAB
    img_uint8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    img_lab = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2LAB).astype(np.float32)
    L, A, B = cv2.split(img_lab)
    
    # Thresholds for "Bright" and "Warm" (Yellow/Orange)
    # Increased thresholds to avoid misclassifying white/neutral bright objects
    # L: Lightness (0-255) -> Stricter: > 210
    # B: Blue-Yellow (128 neutral) -> Stricter: > 150 (More yellow)
    
    l_mask = cv2.threshold(L, 210, 1.0, cv2.THRESH_BINARY)[1]
    b_mask = cv2.threshold(B, 150, 1.0, cv2.THRESH_BINARY)[1]
    
    # Combine
    sun_mask = l_mask * b_mask
    
    # Exclude sky area (Handle mask shape (H,W) or (H,W,1) or (H,W,3))
    if mask.ndim == 3:
        sky_val = mask[:, :, 0]
    else:
        sky_val = mask
        
    foreground_mask = 1.0 - sky_val
    sun_mask = sun_mask * foreground_mask
    
    # Morphological opening to remove noise (small specks)
    kernel = np.ones((5,5), np.uint8)
    sun_mask = cv2.morphologyEx(sun_mask, cv2.MORPH_OPEN, kernel)
    
    # Soften the mask
    sun_mask = cv2.GaussianBlur(sun_mask, (21, 21), 0)
    
    # Normalize
    if sun_mask.max() > 0:
        sun_mask = sun_mask / sun_mask.max()
        
    return sun_mask[:, :, np.newaxis]

def adaptive_reinhard_transfer(source, target, night_factor=0.0):
    """
    Region-Adaptive Color Transfer.
    Splits LAB channels:
    - L: Gamma correction / Scaling (Preserves contrast)
    - A/B: Reinhard Transfer (Matches color atmosphere)
    """
    source_lab = cv2.cvtColor((source * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    target_lab = cv2.cvtColor((target * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    
    l_s, a_s, b_s = cv2.split(source_lab)
    l_t, a_t, b_t = cv2.split(target_lab)
    
    # 1. Color Transfer (A & B Channels) - Standard Reinhard
    # Match Mean and Std
    def transfer_channel(src, tgt):
        m_s, s_s = cv2.meanStdDev(src)
        m_t, s_t = cv2.meanStdDev(tgt)
        s_s = np.maximum(s_s, 1e-6)
        return (src - m_s) * (s_t / s_s) + m_t

    a_new = transfer_channel(a_s, a_t)
    b_new = transfer_channel(b_s, b_t)
    
    # 2. Luminance Mapping (L Channel) - Adaptive
    # If Night Mode, apply specific formula: L_night = L_day^1.5 * 0.7
    if night_factor > 0.5:
        # Normalize L to 0-1 for gamma
        l_norm = l_s / 255.0
        # Gamma 1.5 (Darkens midtones)
        l_new_norm = np.power(l_norm, 1.5)
        # Scale 0.7 (Lowers white point)
        l_new_norm = l_new_norm * 0.7
        l_new = l_new_norm * 255.0
        
        # Blend with original L based on night_factor to transition smoothly
        pass
    else:
        # Standard Reinhard often works okay for Day-to-Day.
        l_new = transfer_channel(l_s, l_t)
        
    # Smooth transition for L if needed, but for now:
    if night_factor > 0:
        # Interpolate between "Reinhard L" (Day logic) and "Gamma L" (Night logic)
        l_reinhard = transfer_channel(l_s, l_t)
        
        l_norm = l_s / 255.0
        l_gamma = (np.power(l_norm, 1.5) * 0.7) * 255.0
        
        # night_factor 0 -> 1
        l_final = l_reinhard * (1 - night_factor) + l_gamma * night_factor
    else:
        l_final = l_new

    # 3. Blue Shift (Shift Yellows toward Blue)
    # B_night = B_day - delta
    if night_factor > 0:
        # Shift B channel towards negative (Blue)
        # Delta depends on night_factor
        delta = 10 * night_factor
        b_new = b_new - delta

    # Merge
    merged_lab = cv2.merge([l_final, a_new, b_new])
    merged_lab = np.clip(merged_lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(merged_lab, cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0

def apply_moonlight_specularity(img, sunlight_mask, night_factor):
    """
    Transforms sunlit areas to moonlight specularity (Silver/Blue Glint).
    """
    if night_factor <= 0:
        return img
        
    # Convert to LAB
    img_lab = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    L, A, B = cv2.split(img_lab)
    
    # 1. Desaturate (Reduce A and B magnitude)
    # Moonlight is less colorful than Sunlight
    saturation_scale = 1.0 - (0.8 * night_factor) # Reduce sat by up to 80%
    A_new = (A - 128) * saturation_scale + 128
    B_new = (B - 128) * saturation_scale + 128
    
    # 2. Blue Shift (Cooling)
    # Shift B towards Blue (negative)
    B_new = B_new - (15 * night_factor)
    
    # 3. Boost Luminance (Specularity)
    L_new = L * (1.0 + 0.1 * night_factor)
    
    img_spec_lab = cv2.merge([L_new, A_new, B_new])
    img_spec_lab = np.clip(img_spec_lab, 0, 255).astype(np.uint8)
    img_spec = cv2.cvtColor(img_spec_lab, cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0
    
    # Apply only to sunlit areas
    final_mask = sunlight_mask * night_factor
    
    res = img * (1 - final_mask) + img_spec * final_mask
    return np.clip(res, 0, 1)

def apply_virtual_point_light(img, depth_map, mask, night_factor):
    """
    Adds a "Virtual Lamp" effect to the foreground subject.
    """
    if night_factor < 0.5:
        return img
        
    h, w = img.shape[:2]
    
    # Create a radial gradient center (assume subject is center-ish or use depth)
    center_x, center_y = w // 2, h // 2
    
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
    
    # Radius
    radius = min(h, w) * 0.6
    
    # Gradient (1 at center, 0 at edge)
    gradient = 1 - np.clip(dist_from_center / radius, 0, 1)
    gradient = np.power(gradient, 2) # Falloff
    
    # Warm Orange Light
    light_color = np.array([1.0, 0.6, 0.3]) # #FFAA55 roughly
    
    # Apply only to Foreground (1 - SkyMask)
    foreground_mask = 1.0 - mask[:, :, 0]
    
    # Combine
    light_effect = gradient[:, :, np.newaxis] * light_color.reshape(1, 1, 3)
    
    # Intensity
    intensity = 0.4 * night_factor
    
    # Screen Blend: 1 - (1-A)(1-B)
    # A = img, B = light * intensity * mask
    B = light_effect * intensity * foreground_mask[:, :, np.newaxis]
    
    res = 1 - (1 - img) * (1 - B)
    return np.clip(res, 0, 1)

def refine_edges_dark_channel(img, mask):
    """
    Refines sky mask edges using Dark Channel Prior.
    """
    # Just return the mask as-is
    if mask.ndim == 2:
        return mask[:, :, np.newaxis]
    elif mask.shape[2] == 1:
        return mask
    else:
        return mask[:, :, 0:1]

def apply_fog_exponential(img, depth, sky_color, density=2.0):
    """
    Exponential Fog: Fog = 1 - exp(-depth * density)
    """

    
    # Invert depth to get "Distance Factor" (0=Close, 1=Far)
    distance = 1.0 - depth
    
    # Fog Factor
    fog_factor = 1.0 - np.exp(-distance * density)
    
    # Reshape
    fog_factor = fog_factor[:, :, np.newaxis]
    
    # Mix
    res = img * (1 - fog_factor) + sky_color * fog_factor
    return np.clip(res, 0, 1)


def resize_cover(img, target_size):
    """
    Resizes image to cover target_size (w, h) while maintaining aspect ratio.
    Crops excess.
    """
    th, tw = target_size[:2]
    h, w = img.shape[:2]
    
    scale_w = tw / w
    scale_h = th / h
    
    # Use the larger scale to ensure coverage
    scale = max(scale_w, scale_h)
    
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Center Crop
    x_start = (new_w - tw) // 2
    y_start = (new_h - th) // 2
    
    cropped = resized[y_start:y_start+th, x_start:x_start+tw]
    return cropped

def compute_normals_from_depth(depth_map):
    """
    Estimates surface normals from a depth map using Sobel gradients.
    Args:
        depth_map: (H, W) numpy array, normalized 0-1 (1=close, 0=far)
    Returns:
        normals: (H, W, 3) numpy array, values -1 to 1
    """
    # Gradients
    dzdx = cv2.Sobel(depth_map, cv2.CV_32F, 1, 0, ksize=3)
    dzdy = cv2.Sobel(depth_map, cv2.CV_32F, 0, 1, ksize=3)
    
    # Construct normal vector (-dzdx, -dzdy, 1)
    # We assume a reasonable scale factor.
    z_component = np.ones_like(depth_map) * 0.5 # Tune this for flatness
    
    normals = np.stack([-dzdx, -dzdy, z_component], axis=-1)
    
    # Normalize
    norm = np.linalg.norm(normals, axis=2, keepdims=True)
    normals = normals / (norm + 1e-6)
    
    return normals

def apply_dynamic_shading(img, normals, time_val):
    """
    Applies shading based on a moving sun position.
    Args:
        img: (H, W, 3) RGB image
        normals: (H, W, 3) Surface Normals
        time_val: 0-100 slider value
    """
    # 1. Calculate Sun Vector
    # 0 (Day) -> Left (-1, 0, 0.5)
    # 33 (Noon) -> Top (0, -1, 1)
    # 66 (Evening) -> Right (1, 0, 0.2)
    # 100 (Night) -> No sun shading (or Moon?)
    
    if time_val > 90:
        return img # Night, no strong directional shading
        
    # Interpolate Sun Vector
    if time_val <= 33:
        # Day -> Noon
        t = time_val / 33.0
        sun_start = np.array([-1.0, 0.2, 0.5]) # Left-ish
        sun_end = np.array([0.0, -1.0, 1.0])   # Top
        sun_vec = sun_start * (1-t) + sun_end * t
    elif time_val <= 66:
        # Noon -> Evening
        t = (time_val - 33) / 33.0
        sun_start = np.array([0.0, -1.0, 1.0]) # Top
        sun_end = np.array([1.0, 0.2, 0.2])    # Right-ish
        sun_vec = sun_start * (1-t) + sun_end * t
    else:
        # Evening -> Night
        t = (time_val - 66) / 24.0 # up to 90
        sun_start = np.array([1.0, 0.2, 0.2])
        sun_end = np.array([1.0, 0.5, -0.5]) # Below horizon
        sun_vec = sun_start * (1-t) + sun_end * t
        
    # Normalize Sun Vector
    sun_vec = sun_vec / np.linalg.norm(sun_vec)
    
    # 2. Calculate Shading (Lambertian: N dot L)
    # normals: (H, W, 3), sun_vec: (3,)
    shading = np.sum(normals * sun_vec, axis=2)
    shading = np.clip(shading, 0, 1)
    
    # 3. Apply Shading
    # Mix shading with ambient light.
    ambient = 0.6
    shading_map = shading * (1 - ambient) + ambient
    
    # Expand to 3 channels
    shading_map = shading_map[:, :, np.newaxis]
    
    # Apply to image
    res = img * shading_map
    return np.clip(res, 0, 1)

def blend(img, skybg, mask, relighting_factor=0.8, recoloring_factor=0.5, halo_effect=True, 
          use_reinhard=False, depth_map=None, fog_strength=0.0, night_factor=0.0, time_val=0):
    """
    Combines source image and sky background.
    """
    # Resize skybg to match img using Cover mode (Zoom & Crop)
    # Target size is (H, W) from img.shape
    if skybg.shape[:2] != img.shape[:2]:
        skybg = resize_cover(skybg, img.shape)
        
    # 0. Refine Edges (Dark Channel)
    mask = refine_edges_dark_channel(img, mask)
    # Re-expand to 3 channels
    mask = np.repeat(mask, 3, axis=2)

    # 1. Sunlight -> Moonlight Specularity
    if night_factor > 0:
        sunlight_mask = detect_sunlight(img, mask)
        img = apply_moonlight_specularity(img, sunlight_mask, night_factor)
        
    # 2. Relighting (Adaptive)
    if use_reinhard:
        img_relit_full = adaptive_reinhard_transfer(img, skybg, night_factor)
        img_relit = img * (1 - relighting_factor) + img_relit_full * relighting_factor
    else:
        img_relit = relighting(img, skybg, mask, relighting_factor, recoloring_factor)

    # 3. Virtual Point Light (Lamp)
    if night_factor > 0:
        img_relit = apply_virtual_point_light(img_relit, depth_map, mask, night_factor)

    # 4. Apply Fog (Exponential)
    if depth_map is not None and fog_strength > 0:
        sky_avg_color = np.mean(skybg, axis=(0, 1))
        img_relit = apply_fog_exponential(img_relit, depth_map, sky_avg_color, density=fog_strength*3)

    # 5. Blending
    syneth = img_relit * (1 - mask) + skybg * mask
    
    if halo_effect:
        syneth = halo(syneth, skybg, mask)
        
    return np.clip(syneth, 0, 1)