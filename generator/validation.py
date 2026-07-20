"""Configuration and input validation."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from generator.models import LabelConfig

logger = logging.getLogger(__name__)

# Prefix: non-empty, no whitespace, printable ASCII without path separators.
_PREFIX_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
_SVG_EXTENSIONS = {".svg"}


class ConfigError(ValueError):
    """Raised when configuration or inputs are invalid."""


def validate_config(config: LabelConfig) -> None:
    """Validate a ``LabelConfig`` and raise ``ConfigError`` on failure.

    Args:
        config: Configuration to validate.

    Raises:
        ConfigError: If any field is invalid.
    """
    errors: list[str] = []

    if config.count <= 0:
        errors.append(
            f"count must be a positive integer (got {config.count}). "
            "Use --count with a value greater than 0."
        )

    if config.start < 0:
        errors.append(
            f"start must be >= 0 (got {config.start}). "
            "Negative sequence numbers are not allowed."
        )

    if config.digits < 1:
        errors.append(
            f"digits must be >= 1 (got {config.digits}). "
            "Example: --digits 4 produces IT-0001."
        )

    if not config.prefix or not config.prefix.strip():
        errors.append("prefix must not be empty. Example: --prefix IT")
    elif not _PREFIX_PATTERN.fullmatch(config.prefix.strip()):
        errors.append(
            f"invalid prefix '{config.prefix}'. "
            "Use letters, digits, and ._+- only; no spaces. Example: IT, ASSET, HQ-IT"
        )

    if config.label_width_mm <= 0:
        errors.append(
            f"label width must be > 0 mm (got {config.label_width_mm})."
        )
    if config.label_height_mm <= 0:
        errors.append(
            f"label height must be > 0 mm (got {config.label_height_mm})."
        )
    if config.margin_mm < 0:
        errors.append(f"margin must be >= 0 mm (got {config.margin_mm}).")

    content_w = config.label_width_mm - 2 * config.margin_mm
    content_h = config.label_height_mm - 2 * config.margin_mm
    if content_w <= 0 or content_h <= 0:
        errors.append(
            "margins leave no usable content area inside the label. "
            f"label={config.label_width_mm}x{config.label_height_mm} mm, "
            f"margin={config.margin_mm} mm."
        )

    if (
        config.label_width_mm > config.page_size.width_mm
        or config.label_height_mm > config.page_size.height_mm
    ):
        errors.append(
            f"label ({config.label_width_mm}x{config.label_height_mm} mm) "
            f"does not fit on page {config.page_size.name} "
            f"({config.page_size.width_mm}x{config.page_size.height_mm} mm)."
        )

    if not config.pdf_filename.lower().endswith(".pdf"):
        errors.append(
            f"pdf filename must end with .pdf (got '{config.pdf_filename}')."
        )
    if not config.csv_filename.lower().endswith(".csv"):
        errors.append(
            f"csv filename must end with .csv (got '{config.csv_filename}')."
        )

    logo_errors = _validate_logo(config.logo_path)
    errors.extend(logo_errors)

    if errors:
        joined = "\n  - ".join(errors)
        raise ConfigError(f"Invalid configuration:\n  - {joined}")


def _validate_logo(logo_path: Path) -> list[str]:
    """Return a list of validation error messages for the logo path."""
    if not logo_path.exists():
        return [
            f"logo file not found: {logo_path}. "
            "Provide a valid path with --logo."
        ]
    if not logo_path.is_file():
        return [f"logo path is not a file: {logo_path}"]

    suffix = logo_path.suffix.lower()
    if suffix in _SVG_EXTENSIONS:
        try:
            text = logo_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return [f"unable to read SVG logo '{logo_path}': {exc}"]
        if "<svg" not in text.lower():
            return [
                f"invalid SVG logo '{logo_path}': file does not contain an <svg> element."
            ]
        return []

    if suffix not in _RASTER_EXTENSIONS:
        return [
            f"unsupported logo format '{suffix or '(none)'}' for '{logo_path}'. "
            f"Supported: {', '.join(sorted(_RASTER_EXTENSIONS | _SVG_EXTENSIONS))}."
        ]

    try:
        with Image.open(logo_path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return [f"invalid or corrupt logo image '{logo_path}': {exc}"]

    # verify() can leave the image in a bad state; reopen for a size sanity check.
    try:
        with Image.open(logo_path) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return [f"unable to load logo image '{logo_path}': {exc}"]

    if width <= 0 or height <= 0:
        return [f"logo image has invalid dimensions: {width}x{height}"]

    logger.debug("Logo validated: %s (%dx%d)", logo_path, width, height)
    return []
