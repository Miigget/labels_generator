"""Logo loading helpers: padding trim without stretching."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

# Max channel distance from the detected background color to treat as padding.
_BG_TOLERANCE = 18
# Extra pixels kept around the detected content (avoids clipping anti-alias).
_TRIM_PADDING_PX = 4


def load_raster_logo(path: Path, *, trim_padding: bool = True) -> Image.Image:
    """Load a raster logo as RGBA, optionally trimming empty padding.

    Trimming removes uniform border padding (black, white, or transparent)
    detected from the image corners. Aspect ratio of the real artwork is
    preserved — pixels are only cropped, never stretched or resampled here.

    Args:
        path: Path to a raster image file.
        trim_padding: When True, crop away empty borders.

    Returns:
        RGBA ``PIL.Image`` ready for PDF embedding.
    """
    with Image.open(path) as image:
        logo = image.convert("RGBA")

    original_size = logo.size
    if trim_padding:
        logo = trim_logo_padding(logo)
        if logo.size != original_size:
            logger.info(
                "Trimmed logo padding %s: %sx%s -> %sx%s",
                path.name,
                original_size[0],
                original_size[1],
                logo.size[0],
                logo.size[1],
            )
    return logo


def trim_logo_padding(image: Image.Image) -> Image.Image:
    """Crop uniform padding around logo content.

    Background color is inferred from the four corners. Pixels close to that
    color (or fully transparent) are treated as padding. If no content is
    found, the original image is returned unchanged.
    """
    rgba = image.convert("RGBA")
    width, height = rgba.size
    if width == 0 or height == 0:
        return rgba

    pixels = rgba.load()
    bg = _detect_background(pixels, width, height)

    min_x, min_y = width, height
    max_x, max_y = -1, -1

    for y in range(height):
        for x in range(width):
            if _is_padding(pixels[x, y], bg):
                continue
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y

    if max_x < 0:
        return rgba

    min_x = max(0, min_x - _TRIM_PADDING_PX)
    min_y = max(0, min_y - _TRIM_PADDING_PX)
    max_x = min(width - 1, max_x + _TRIM_PADDING_PX)
    max_y = min(height - 1, max_y + _TRIM_PADDING_PX)

    if min_x == 0 and min_y == 0 and max_x == width - 1 and max_y == height - 1:
        return rgba

    return rgba.crop((min_x, min_y, max_x + 1, max_y + 1))


def _detect_background(
    pixels: object,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    """Average the four corner pixels as the padding/background color."""
    corners = (
        pixels[0, 0],  # type: ignore[index]
        pixels[width - 1, 0],  # type: ignore[index]
        pixels[0, height - 1],  # type: ignore[index]
        pixels[width - 1, height - 1],  # type: ignore[index]
    )
    r = sum(c[0] for c in corners) // 4
    g = sum(c[1] for c in corners) // 4
    b = sum(c[2] for c in corners) // 4
    a = sum(c[3] for c in corners) // 4
    return (r, g, b, a)


def _is_padding(
    pixel: tuple[int, int, int, int],
    background: tuple[int, int, int, int],
) -> bool:
    """Return True when a pixel is transparent or matches the background."""
    r, g, b, a = pixel
    if a < 10:
        return True
    br, bg, bb, ba = background
    # Mostly-transparent background: treat low-alpha as padding.
    if ba < 10 and a < 40:
        return True
    return (
        abs(r - br) <= _BG_TOLERANCE
        and abs(g - bg) <= _BG_TOLERANCE
        and abs(b - bb) <= _BG_TOLERANCE
    )
