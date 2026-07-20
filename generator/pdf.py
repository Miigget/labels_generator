"""PDF generation with true physical label dimensions."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from generator.barcode import render_barcode_image
from generator.ids import iter_inventory_ids
from generator.layout import compute_layout, probe_logo_aspect
from generator.logo import load_raster_logo
from generator.models import BarcodeType, InventoryId, LabelConfig, LabelLayout

logger = logging.getLogger(__name__)

_BOLD_FONT = "Helvetica-Bold"
_REGULAR_FONT = "Helvetica"


def generate_labels_pdf(config: LabelConfig) -> Path:
    """Generate a multi-page PDF with one true-size label centered per page.

    Args:
        config: Validated label configuration.

    Returns:
        Path to the written PDF file.
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.pdf_path

    page_w = config.page_size.width_mm * mm
    page_h = config.page_size.height_mm * mm
    label_w = config.label_width_mm * mm
    label_h = config.label_height_mm * mm

    # Center the physical label on the page.
    origin_x = (page_w - label_w) / 2.0
    origin_y = (page_h - label_h) / 2.0

    logo_aspect = probe_logo_aspect(config.logo_path)
    logo_cache = _LogoCache(config.logo_path)

    pdf = canvas.Canvas(str(output_path), pagesize=(page_w, page_h))
    total = config.count
    log_every = max(1, total // 20)

    for index, inventory_id in enumerate(iter_inventory_ids(config), start=1):
        layout = compute_layout(
            config,
            inventory_id.value,
            logo_aspect=logo_aspect,
        )
        _draw_label_page(
            pdf,
            config=config,
            inventory_id=inventory_id,
            layout=layout,
            origin_x=origin_x,
            origin_y=origin_y,
            logo_cache=logo_cache,
        )
        pdf.showPage()

        if index == 1 or index == total or index % log_every == 0:
            logger.info(
                "Rendered page %d / %d (%s)",
                index,
                total,
                inventory_id.value,
            )

    pdf.save()
    logger.info("Wrote PDF: %s (%d pages)", output_path, total)
    return output_path


def _draw_label_page(
    pdf: canvas.Canvas,
    *,
    config: LabelConfig,
    inventory_id: InventoryId,
    layout: LabelLayout,
    origin_x: float,
    origin_y: float,
    logo_cache: _LogoCache,
) -> None:
    """Draw a single centered label onto the current PDF page."""
    pdf.saveState()
    pdf.translate(origin_x, origin_y)

    # Outline so print shops can verify the physical label footprint.
    pdf.setStrokeColorRGB(0.75, 0.75, 0.75)
    pdf.setLineWidth(0.2)
    pdf.rect(
        0,
        0,
        layout.label_width_mm * mm,
        layout.label_height_mm * mm,
        stroke=1,
        fill=0,
    )

    logo_cache.draw(
        pdf,
        x=layout.logo_x_mm * mm,
        y=layout.logo_y_mm * mm,
        width=layout.logo_width_mm * mm,
        height=layout.logo_height_mm * mm,
    )

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(_BOLD_FONT, layout.id_font_size_pt)
    baseline = layout.id_y_mm * mm + (layout.id_font_size_pt * 0.15)
    pdf.drawCentredString(layout.id_x_mm * mm, baseline, inventory_id.value)

    # ~12 px/mm (~300 DPI) for sharp print output.
    px_per_mm = 12.0
    barcode_img = render_barcode_image(
        inventory_id.value,
        config.barcode_type,
        target_width_px=max(8, int(layout.barcode_width_mm * px_per_mm)),
        target_height_px=max(8, int(layout.barcode_height_mm * px_per_mm)),
        include_text=False,
    )
    buffer = BytesIO()
    barcode_img.save(buffer, format="PNG")
    buffer.seek(0)
    # Code128: fill the allocated box so every label gets the same bar area.
    # (Bar height is independent of module width; uniform box = consistent look.)
    # QR: keep square aspect ratio.
    preserve_aspect = config.barcode_type is BarcodeType.QR
    pdf.drawImage(
        ImageReader(buffer),
        layout.barcode_x_mm * mm,
        layout.barcode_y_mm * mm,
        width=layout.barcode_width_mm * mm,
        height=layout.barcode_height_mm * mm,
        mask="auto",
        preserveAspectRatio=preserve_aspect,
        anchor="c",
    )

    if (
        config.show_text_below_barcode
        and layout.human_text_y_mm is not None
        and layout.human_text_font_size_pt is not None
    ):
        pdf.setFont(_REGULAR_FONT, layout.human_text_font_size_pt)
        pdf.drawCentredString(
            layout.id_x_mm * mm,
            layout.human_text_y_mm * mm,
            inventory_id.value,
        )

    pdf.restoreState()


class _LogoCache:
    """Load a logo once and reuse it across pages."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._suffix = path.suffix.lower()
        self._raster: ImageReader | None = None
        self._svg_drawing = None

        if self._suffix == ".svg":
            from svglib.svglib import svg2rlg

            drawing = svg2rlg(str(path))
            if drawing is None:
                raise ValueError(f"Failed to parse SVG logo: {path}")
            self._svg_drawing = drawing
            self._svg_width = float(drawing.width or 1.0)
            self._svg_height = float(drawing.height or 1.0)
        else:
            # Trim empty padding so artwork can fill the logo slot without stretching.
            converted = load_raster_logo(path, trim_padding=True)
            buffer = BytesIO()
            converted.save(buffer, format="PNG")
            buffer.seek(0)
            self._raster = ImageReader(buffer)

    def draw(
        self,
        pdf: canvas.Canvas,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw the logo into the given rectangle (PDF points)."""
        if self._svg_drawing is not None:
            from reportlab.graphics import renderPDF

            scale = min(width / self._svg_width, height / self._svg_height)
            dx = x + (width - self._svg_width * scale) / 2.0
            dy = y + (height - self._svg_height * scale) / 2.0
            pdf.saveState()
            pdf.translate(dx, dy)
            pdf.scale(scale, scale)
            renderPDF.draw(self._svg_drawing, pdf, 0, 0)
            pdf.restoreState()
            return

        assert self._raster is not None
        pdf.drawImage(
            self._raster,
            x,
            y,
            width=width,
            height=height,
            mask="auto",
            preserveAspectRatio=True,
            anchor="c",
        )
