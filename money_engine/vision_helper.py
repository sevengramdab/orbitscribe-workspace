"""
vision_helper.py
================
Helpers for analyzing screenshots to guide automation.
- Color region detection
- Template matching stub (for future cv2 integration)
- OCR stub (for future pytesseract integration)
- UI element heuristics
"""
from __future__ import annotations

import os
import io
import base64
from typing import Optional, Tuple, List
from pathlib import Path

try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:
    _HAS_NUMPY = False

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False


class VisionHelper:
    """Lightweight vision analysis without heavy ML dependencies."""

    @staticmethod
    def load_image(path_or_b64: str) -> Optional[Image.Image]:
        if not _HAS_PIL:
            return None
        try:
            if os.path.exists(path_or_b64):
                return Image.open(path_or_b64)
            # Try base64
            data = base64.b64decode(path_or_b64)
            return Image.open(io.BytesIO(data))
        except Exception:
            return None

    @staticmethod
    def average_brightness(img) -> float:
        if not _HAS_PIL or not _HAS_NUMPY:
            return 128.0
        try:
            arr = np.array(img.convert("L"))
            return float(np.mean(arr))
        except Exception:
            return 128.0

    @staticmethod
    def detect_white_region(img, threshold: int = 250) -> float:
        """Return percentage of image that is near-white (loading indicator)."""
        if not _HAS_PIL or not _HAS_NUMPY:
            return 0.0
        try:
            arr = np.array(img.convert("L"))
            white_pixels = np.sum(arr > threshold)
            return float(white_pixels / arr.size)
        except Exception:
            return 0.0

    @staticmethod
    def find_color_patch(img, target_rgb: Tuple[int, int, int], tolerance: int = 20) -> Optional[Tuple[int, int]]:
        """Find center of largest region matching target color. Returns (x, y) or None."""
        if not _HAS_PIL or not _HAS_NUMPY:
            return None
        try:
            arr = np.array(img)
            if len(arr.shape) != 3:
                return None
            diff = np.abs(arr[:, :, :3].astype(np.int16) - np.array(target_rgb, dtype=np.int16))
            mask = np.all(diff <= tolerance, axis=2)
            if not np.any(mask):
                return None
            ys, xs = np.where(mask)
            return int(np.median(xs)), int(np.median(ys))
        except Exception:
            return None

    @staticmethod
    def is_page_blank(img) -> bool:
        """Heuristic: page is blank/loading if >95% white."""
        return VisionHelper.detect_white_region(img) > 0.95

    @staticmethod
    def has_dark_modal(img) -> bool:
        """Heuristic: detect dark overlay modal by average brightness dip in center."""
        if not _HAS_PIL or not _HAS_NUMPY:
            return False
        try:
            arr = np.array(img)
            h, w = arr.shape[:2]
            center = arr[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]
            gray = np.mean(center[:, :, :3]) if len(center.shape) == 3 else np.mean(center)
            return gray < 80
        except Exception:
            return False

    @staticmethod
    def describe_screenshot(path_or_b64: str) -> dict:
        """Generate a simple text description of a screenshot."""
        img = VisionHelper.load_image(path_or_b64)
        if img is None:
            return {"success": False, "error": "Could not load image"}

        w, h = img.size
        bright = VisionHelper.average_brightness(img)
        white_pct = VisionHelper.detect_white_region(img) * 100
        blank = VisionHelper.is_page_blank(img)
        modal = VisionHelper.has_dark_modal(img)

        description = (
            f"Screenshot {w}x{h}. "
            f"Avg brightness: {bright:.1f}. "
            f"White pixels: {white_pct:.1f}%. "
            f"Blank/loading: {blank}. "
            f"Dark modal overlay: {modal}."
        )

        return {
            "success": True,
            "width": w,
            "height": h,
            "brightness": bright,
            "white_percent": white_pct,
            "is_blank": blank,
            "has_modal": modal,
            "description": description,
        }
