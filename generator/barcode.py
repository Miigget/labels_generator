"""Barcode and QR code rendering."""

from __future__ import annotations

import logging
from enum import Enum
from io import BytesIO

import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image
from qrcode.constants import ERROR_CORRECT_M

from generator.models import BarcodeType

logger = logging.getLogger(__name__)


class QuietZone(int, Enum):
    """Quiet-zone constants required by barcode specifications."""

    # ISO/IEC 15417: Code 128 quiet zone >= 10× module width.
    CODE128_MODULES = 10
    # ISO/IEC 18004: QR quiet zone = 4 modules.
    QR_BORDER_MODULES = 4


def render_barcode_image(
    value: str,
    barcode_type: BarcodeType,
    *,
    target_width_px: int,
    target_height_px: int,
    include_text: bool = False,
) -> Image.Image:
    """Render a barcode/QR encoding exactly ``value``.

    Args:
        value: Exact payload to encode (the inventory ID).
        barcode_type: Symbology to use.
        target_width_px: Desired image width in pixels (best-effort).
        target_height_px: Desired image height in pixels (best-effort).
        include_text: When True and using Code128, draw human-readable text
            under the bars (QR codes never embed text in the symbol image).

    Returns:
        RGB ``PIL.Image`` of the symbol, including quiet zones.
    """
    if barcode_type is BarcodeType.CODE128:
        return _render_code128(
            value,
            target_width_px=target_width_px,
            target_height_px=target_height_px,
            include_text=include_text,
        )
    if barcode_type is BarcodeType.QR:
        return _render_qr(
            value,
            target_width_px=target_width_px,
            target_height_px=target_height_px,
        )
    raise ValueError(f"Unhandled barcode type: {barcode_type}")


def _render_code128(
    value: str,
    *,
    target_width_px: int,
    target_height_px: int,
    include_text: bool,
) -> Image.Image:
    """Render a Code 128 barcode as a PIL image."""
    # ImageWriter uses mm-ish module dimensions; we render large then scale.
    writer = ImageWriter()
    options = {
        "module_width": 0.25,
        "module_height": max(8.0, target_height_px / 12.0),
        "quiet_zone": float(QuietZone.CODE128_MODULES),
        "write_text": include_text,
        "font_size": 10 if include_text else 0,
        "text_distance": 3.0 if include_text else 1.0,
        "dpi": 300,
    }
    buffer = BytesIO()
    Code128(value, writer=writer).write(buffer, options=options)
    buffer.seek(0)
    image = Image.open(buffer).convert("RGB")
    return _fit_image(image, target_width_px, target_height_px)


def _render_qr(
    value: str,
    *,
    target_width_px: int,
    target_height_px: int,
) -> Image.Image:
    """Render a QR code as a PIL image with a 4-module quiet zone."""
    side = max(target_width_px, target_height_px, 64)
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=int(QuietZone.QR_BORDER_MODULES),
    )
    qr.add_data(value)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    # Keep square aspect; fit into the smaller target dimension.
    fit_side = max(8, min(side, target_width_px, target_height_px))
    return _fit_image(image, fit_side, fit_side, keep_square=True)


def _fit_image(
    image: Image.Image,
    max_width: int,
    max_height: int,
    *,
    keep_square: bool = False,
) -> Image.Image:
    """Scale an image to fit within max dimensions, preserving aspect ratio."""
    max_width = max(1, max_width)
    max_height = max(1, max_height)
    width, height = image.size
    if width <= 0 or height <= 0:
        return image

    if keep_square:
        scale = min(max_width / width, max_height / height)
    else:
        scale = min(max_width / width, max_height / height)

    new_size = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    if new_size == image.size:
        return image
    return image.resize(new_size, Image.Resampling.LANCZOS)
