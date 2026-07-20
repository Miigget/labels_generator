"""Label geometry and automatic sizing."""

from __future__ import annotations

import logging
from pathlib import Path

from generator.models import BarcodeType, LabelConfig, LabelLayout

logger = logging.getLogger(__name__)

# Barcode-first: logo stays secondary. Padding trim makes the artwork readable
# at this height without needing a huge logo slot.
_LOGO_MAX_HEIGHT_FRACTION = 0.34
# Tight gap under the logo; slightly larger gap elsewhere.
_GAP_AFTER_LOGO_MM = 0.15
_GAP_MM = 0.35
# Compact human-readable ID: small but still legible after print (~5–6.5 pt).
_ID_TARGET_HEIGHT_MM = 1.9
_ID_MIN_FONT_PT = 5.0
_ID_MAX_FONT_PT = 6.5
# Points per millimeter (PostScript / PDF).
PT_PER_MM = 72.0 / 25.4


def compute_layout(
    config: LabelConfig,
    inventory_id: str,
    *,
    logo_aspect: float,
) -> LabelLayout:
    """Compute positions and sizes for all label elements.

    Stack: logo → barcode → inventory ID. The barcode receives the remaining
    height after a modest logo and compact ID. Logo width is never wider than
    the barcode band (aesthetic alignment) and never stretched.

    Args:
        config: Generation configuration.
        inventory_id: Text used for font-fit calculations.
        logo_aspect: Logo width / height ratio (> 0), ideally after trim.

    Returns:
        ``LabelLayout`` with millimeter coordinates relative to the label's
        bottom-left corner.
    """
    if logo_aspect <= 0:
        raise ValueError(f"logo_aspect must be > 0 (got {logo_aspect})")

    margin = config.margin_mm
    label_w = config.label_width_mm
    label_h = config.label_height_mm
    content_w = label_w - 2 * margin
    content_h = label_h - 2 * margin
    content_left = margin
    content_bottom = margin

    # --- Compact inventory ID at the bottom (reserve first) ---
    id_font_pt = _fit_font_size_pt(
        inventory_id,
        max_width_mm=content_w,
        max_height_mm=_ID_TARGET_HEIGHT_MM,
        bold=True,
        min_pt=_ID_MIN_FONT_PT,
        max_pt=_ID_MAX_FONT_PT,
    )
    id_block_h = id_font_pt / PT_PER_MM

    human_font_pt: float | None = None
    human_block_h = 0.0
    if config.show_text_below_barcode:
        human_font_pt = _fit_font_size_pt(
            inventory_id,
            max_width_mm=content_w,
            max_height_mm=min(1.6, content_h * 0.12),
            bold=False,
            min_pt=4.5,
            max_pt=5.5,
        )
        human_block_h = human_font_pt / PT_PER_MM + _GAP_MM

    # --- Barcode band width (logo must not exceed this) ---
    # Code128 uses the full content width. QR is square and sized after height.
    if config.barcode_type is BarcodeType.QR:
        # Provisional: QR side limited later by leftover height; width cap for
        # the logo uses full content width so the logo is not over-constrained
        # before we know the final QR side.
        barcode_width_cap = content_w
    else:
        barcode_width_cap = content_w

    # --- Logo: modest height, never wider than barcode, never stretched ---
    max_logo_h = min(label_h * _LOGO_MAX_HEIGHT_FRACTION, content_h * 0.38)
    max_logo_w = barcode_width_cap
    logo_h = max_logo_h
    logo_w = logo_h * logo_aspect
    if logo_w > max_logo_w:
        logo_w = max_logo_w
        logo_h = logo_w / logo_aspect

    # --- Barcode gets the remaining vertical space (priority) ---
    reserved = logo_h + _GAP_AFTER_LOGO_MM + _GAP_MM + id_block_h + human_block_h
    barcode_h = max(2.5, content_h - reserved)

    if config.barcode_type is BarcodeType.QR:
        barcode_side = min(content_w, barcode_h)
        barcode_w = barcode_side
        barcode_h = barcode_side
        # Re-clamp logo so it is not wider than the final QR side.
        if logo_w > barcode_w:
            logo_w = barcode_w
            logo_h = logo_w / logo_aspect
            reserved = (
                logo_h + _GAP_AFTER_LOGO_MM + _GAP_MM + id_block_h + human_block_h
            )
            barcode_h = max(2.5, content_h - reserved)
            barcode_side = min(content_w, barcode_h)
            barcode_w = barcode_side
            barcode_h = barcode_side
    else:
        barcode_w = content_w

    # Stack from the top of the content box downward (PDF y grows upward).
    top = content_bottom + content_h
    logo_y = top - logo_h
    logo_x = content_left + (content_w - logo_w) / 2.0

    cursor = logo_y - _GAP_AFTER_LOGO_MM
    barcode_y = cursor - barcode_h
    min_barcode_y = content_bottom + human_block_h + id_block_h + _GAP_MM
    if barcode_y < min_barcode_y:
        barcode_y = min_barcode_y
        barcode_h = max(2.0, cursor - barcode_y)
        if config.barcode_type is BarcodeType.QR:
            barcode_side = min(content_w, barcode_h)
            barcode_w = barcode_side
            barcode_h = barcode_side
            barcode_y = cursor - barcode_h
            if logo_w > barcode_w:
                logo_w = barcode_w
                logo_h = logo_w / logo_aspect
                logo_y = top - logo_h
                logo_x = content_left + (content_w - logo_w) / 2.0

    barcode_x = content_left + (content_w - barcode_w) / 2.0

    id_y = content_bottom + human_block_h
    id_x = content_left + content_w / 2.0

    human_text_y: float | None = None
    if config.show_text_below_barcode and human_font_pt is not None:
        human_text_y = content_bottom

    layout = LabelLayout(
        label_width_mm=label_w,
        label_height_mm=label_h,
        content_left_mm=content_left,
        content_bottom_mm=content_bottom,
        content_width_mm=content_w,
        content_height_mm=content_h,
        logo_x_mm=logo_x,
        logo_y_mm=logo_y,
        logo_width_mm=logo_w,
        logo_height_mm=logo_h,
        id_x_mm=id_x,
        id_y_mm=id_y,
        id_font_size_pt=id_font_pt,
        barcode_x_mm=barcode_x,
        barcode_y_mm=barcode_y,
        barcode_width_mm=barcode_w,
        barcode_height_mm=barcode_h,
        human_text_y_mm=human_text_y,
        human_text_font_size_pt=human_font_pt,
    )
    logger.debug("Layout for %s: %s", inventory_id, layout)
    return layout


def probe_logo_aspect(logo_path: Path) -> float:
    """Return width/height aspect ratio for a logo file.

    Raster logos are measured after padding trim so empty borders do not
    shrink the visible artwork. SVG logos without an intrinsic size fall
    back to 3:1 (typical wide wordmark).
    """
    suffix = logo_path.suffix.lower()
    if suffix == ".svg":
        aspect = _svg_aspect(logo_path)
        return aspect if aspect else 3.0

    from generator.logo import load_raster_logo

    logo = load_raster_logo(logo_path, trim_padding=True)
    width, height = logo.size
    if height <= 0:
        raise ValueError(f"Logo has invalid height: {logo_path}")
    return width / height


def _svg_aspect(logo_path: Path) -> float | None:
    """Best-effort aspect ratio from SVG width/height or viewBox attributes."""
    try:
        from svglib.svglib import svg2rlg
    except ImportError:
        return None

    drawing = svg2rlg(str(logo_path))
    if drawing is None:
        return None
    if drawing.height and drawing.height > 0:
        return float(drawing.width) / float(drawing.height)
    return None


def _fit_font_size_pt(
    text: str,
    *,
    max_width_mm: float,
    max_height_mm: float,
    bold: bool,
    min_pt: float = 4.0,
    max_pt: float = 18.0,
) -> float:
    """Choose a font size in points that fits within the given box.

    Uses Helvetica metrics approximated via average glyph width so layout
    can run without creating a canvas first.
    """
    if not text:
        return min(6.0, max_pt)

    # Average glyph width as a fraction of font size (Helvetica-ish).
    avg_glyph = 0.55 if bold else 0.50
    max_width_pt = max_width_mm * PT_PER_MM
    max_height_pt = max_height_mm * PT_PER_MM

    size_by_width = max_width_pt / (len(text) * avg_glyph)
    size_by_height = max_height_pt
    size = min(size_by_width, size_by_height)

    return max(min_pt, min(size, max_pt))
