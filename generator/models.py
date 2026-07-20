"""Domain models for inventory label generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class BarcodeType(str, Enum):
    """Supported barcode symbologies."""

    CODE128 = "code128"
    QR = "qr"

    @classmethod
    def from_string(cls, value: str) -> BarcodeType:
        """Parse a user-provided barcode type string.

        Args:
            value: Case-insensitive barcode type name.

        Returns:
            Matching ``BarcodeType``.

        Raises:
            ValueError: If the value is not a supported type.
        """
        normalized = value.strip().lower().replace("-", "").replace("_", "")
        aliases = {
            "code128": cls.CODE128,
            "qr": cls.QR,
            "qrcode": cls.QR,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            supported = ", ".join(sorted({m.value for m in cls}))
            raise ValueError(
                f"Unsupported barcode type '{value}'. "
                f"Supported types: {supported} (aliases: qrcode)."
            ) from exc


@dataclass(frozen=True, slots=True)
class PageSize:
    """Physical page dimensions in millimeters."""

    name: str
    width_mm: float
    height_mm: float


# Common ISO / North-American page sizes (width x height in mm).
PAGE_SIZES: dict[str, PageSize] = {
    "A4": PageSize("A4", 210.0, 297.0),
    "A5": PageSize("A5", 148.0, 210.0),
    "LETTER": PageSize("LETTER", 215.9, 279.4),
}


@dataclass(slots=True)
class LabelConfig:
    """Configuration for a label generation run.

    All linear dimensions are expressed in millimeters so PDF output
    maps 1:1 to real-world print size.
    """

    logo_path: Path
    output_dir: Path = Path("output")
    count: int = 10
    prefix: str = "IT"
    digits: int = 4
    start: int = 1
    barcode_type: BarcodeType = BarcodeType.CODE128
    label_width_mm: float = 36.0
    label_height_mm: float = 17.0
    page_size: PageSize = field(default_factory=lambda: PAGE_SIZES["A4"])
    margin_mm: float = 1.0
    show_text_below_barcode: bool = False
    pdf_filename: str = "labels.pdf"
    csv_filename: str = "inventory.csv"

    @property
    def pdf_path(self) -> Path:
        """Absolute path of the generated PDF file."""
        return self.output_dir / self.pdf_filename

    @property
    def csv_path(self) -> Path:
        """Absolute path of the generated inventory CSV file."""
        return self.output_dir / self.csv_filename


@dataclass(frozen=True, slots=True)
class InventoryId:
    """A single inventory identifier."""

    value: str
    sequence: int

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class LabelLayout:
    """Computed geometry for one label, in millimeters relative to the label origin.

    Coordinates use a bottom-left origin to match ReportLab's canvas.
    """

    label_width_mm: float
    label_height_mm: float
    content_left_mm: float
    content_bottom_mm: float
    content_width_mm: float
    content_height_mm: float
    logo_x_mm: float
    logo_y_mm: float
    logo_width_mm: float
    logo_height_mm: float
    id_x_mm: float
    id_y_mm: float
    id_font_size_pt: float
    barcode_x_mm: float
    barcode_y_mm: float
    barcode_width_mm: float
    barcode_height_mm: float
    human_text_y_mm: float | None
    human_text_font_size_pt: float | None
