import random

import numpy as np


def apply_ken_burns(clip, target_w, target_h, zoom_range=(1.0, 1.15)):
    """Apply a slow zoom/pan (Ken Burns) effect to a clip."""
    start_zoom = random.uniform(*zoom_range)
    end_zoom = random.uniform(*zoom_range)

    # Random pan direction
    pan_x = random.uniform(-0.02, 0.02)
    pan_y = random.uniform(-0.02, 0.02)

    duration = clip.duration

    def effect(get_frame, t):
        frame = get_frame(t)
        h, w = frame.shape[:2]
        progress = t / duration if duration > 0 else 0

        zoom = start_zoom + (end_zoom - start_zoom) * progress
        cx = w / 2 + pan_x * w * progress
        cy = h / 2 + pan_y * h * progress

        crop_w = int(target_w / zoom)
        crop_h = int(target_h / zoom)

        x1 = int(max(0, min(cx - crop_w // 2, w - crop_w)))
        y1 = int(max(0, min(cy - crop_h // 2, h - crop_h)))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        cropped = frame[y1:y2, x1:x2]

        # Resize back to target
        from PIL import Image
        img = Image.fromarray(cropped)
        img = img.resize((target_w, target_h), Image.LANCZOS)
        return np.array(img)

    return clip.transform(effect)
