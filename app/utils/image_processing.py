# app/utils/image_processing.py
from __future__ import annotations

import io
import os
from typing import Tuple
from PIL import Image

# Allowed MIME types (comma-separated in env). Default: jpeg/png/webp.
_ALLOWED = os.getenv("AVATAR_ALLOWED_MIME", "image/jpeg,image/png,image/webp")
ALLOWED_MIME = {m.strip().lower() for m in _ALLOWED.split(",") if m.strip()}

def _mime_for_format(fmt: str) -> str:
    fmt = (fmt or "").upper()
    if fmt == "PNG":
        return "image/png"
    if fmt == "WEBP":
        return "image/webp"
    # default
    return "image/jpeg"

def _ext_for_mime(mime: str) -> str:
    m = (mime or "").lower()
    if m == "image/png":
        return "png"
    if m == "image/webp":
        return "webp"
    return "jpg"

def ext_from_mime(mime: str) -> str:
    """
    Public helper used by routes: map MIME type -> file extension.
    """
    return _ext_for_mime(mime)

def resize_image_max_side(
    data: bytes,
    max_side: int = 512,
    output_format: str = "JPEG",
    output_quality: int = 85,
) -> Tuple[bytes, str]:
    """
    Core resizer: keeps aspect ratio so the longest side == max_side.
    Returns (bytes, mime_type).
    """
    if max_side is None or max_side <= 0:
        # passthrough; try to detect original mime
        try:
            with Image.open(io.BytesIO(data)) as im:
                im.load()
                return data, _mime_for_format(im.format)
        except Exception:
            return data, "application/octet-stream"

    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side))
        out = io.BytesIO()
        fmt = (output_format or "JPEG").upper()
        im.save(out, format=fmt, quality=output_quality, optimize=True)
        return out.getvalue(), _mime_for_format(fmt)

# Compatibility wrapper expected by your route
def resize_image_if_needed(data: bytes, max_side: int) -> Tuple[bytes, str]:
    """
    Backwards-compatible name used by user_routes.
    """
    return resize_image_max_side(data=data, max_side=max_side)
