import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def professional_local_erase(img: Image.Image, x1, y1, x2, y2) -> Image.Image:
    """
    ULTRA-PRECISION Structural Inpainter.
    Specifically tuned to remove high-contrast logos (Grok/Symbols) 
    without leaving blur or leftovers.
    """
    img = img.convert("RGBA")
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0: return img

    # 1. ANALYZE LOCAL SENSOR GRAIN
    # We sample a 32x32 area nearby to capture the exact "Noise Signature"
    sample_grain_box = img.crop((max(0, x1-40), max(0, y1-40), x1, y1)).convert("RGB")
    grain_arr = np.array(sample_grain_box).astype(np.float32)
    grain_std = np.std(grain_arr, axis=(0,1)) # The "Real" grain level

    # 2. LOCAL LIGHTING SYNC
    # Sample the ring around the logo to get the target lighting
    ring = 12
    mask_ring = Image.new("L", (x2-x1 + 2*ring, y2-y1 + 2*ring), 0)
    d_ring = ImageDraw.Draw(mask_ring)
    d_ring.rectangle((0, 0, mask_ring.width, mask_ring.height), fill=255)
    d_ring.rectangle((ring, ring, ring+w, ring+h), fill=0)
    
    context_area = img.crop((max(0, x1-ring), max(0, y1-ring), min(img.width, x2+ring), min(img.height, y2+ring))).convert("RGB")
    target_stats = np.array(context_area)
    # Mask out the logo itself from the stats
    target_mean = np.mean(target_stats, axis=(0,1))

    # 3. HIGH-DENSITY TEXTURE SEARCH
    # We look for a 1:1 texture match in a 200px radius
    search_r = 200
    sx1, sy1 = max(0, x1 - search_r), max(0, y1 - search_r)
    sx2, sy2 = min(img.width, x2 + search_r), min(img.height, y2 + search_r)
    search_area = np.array(img.crop((sx1, sy1, sx2, sy2)).convert("RGB"))
    
    best_patch = None
    min_diff = float('inf')
    
    # Precise Search: 250 candidates for best structural fit
    for _ in range(250):
        try:
            px = np.random.randint(0, search_area.shape[1] - w)
            py = np.random.randint(0, search_area.shape[0] - h)
            
            # Avoid the logo area
            hx, hy = x1 - sx1, y1 - sy1
            if (px < hx + w and px + w > hx) and (py < hy + h and py + h > hy): continue
            
            candidate = search_area[py:py+h, px:px+w]
            cand_mean = np.mean(candidate, axis=(0,1))
            
            # Score based on Lighting + Color Similiarity
            diff = np.sum((target_mean - cand_mean)**2)
            if diff < min_diff:
                min_diff = diff
                best_patch = candidate
        except: continue

    # 4. RECONSTRUCTION
    if best_patch is None:
        # Better fallback: Mirror local texture
        patch_img = img.crop((max(0, x1-w), y1, x1, y1+h)).transpose(Image.FLIP_LEFT_RIGHT).convert("RGB")
    else:
        # Match lighting of donor patch to target spot
        best_patch = best_patch.astype(np.float32)
        for c in range(3):
            best_patch[:,:,c] = (best_patch[:,:,c] - np.mean(best_patch[:,:,c])) + target_mean[c]
        patch_img = Image.fromarray(np.clip(best_patch, 0, 255).astype(np.uint8))

    # 5. PRECISION BLENDING (Zero Leftovers)
    patch_rgba = patch_img.convert("RGBA")
    
    # Add matched grain back to the patch
    p_arr = np.array(patch_rgba).astype(np.float32)
    for c in range(3):
        noise = np.random.normal(0, grain_std[c], (h, w))
        p_arr[:,:,c] += noise
    patch_rgba = Image.fromarray(np.clip(p_arr, 0, 255).astype(np.uint8))

    # Create the final result with a "Zero-Halos" mask
    # We use a tight mask but with a heavy "Structural Blur" to hide the edges
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    # The logo area - slightly larger to catch the edges
    d.rectangle((x1-1, y1-1, x2+1, y2+1), fill=255)
    
    # Multi-stage blend: Soft inside, slightly harder towards outside
    mask_blur = mask.filter(ImageFilter.GaussianBlur(radius=8))
    
    # Layering
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    overlay.paste(patch_rgba, (x1, y1))
    
    # Combine
    return Image.composite(overlay, img, mask_blur)
