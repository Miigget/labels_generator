"""CLI configuration parsing and defaults."""

from __future__ import annotations

import argparse
from pathlib import Path

from generator.models import PAGE_SIZES, BarcodeType, LabelConfig, PageSize


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="labels-generator",
        description=(
            "Generate printable inventory labels as a multi-page PDF "
            "(one true-size label centered on each page) plus an inventory CSV."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--logo",
        type=Path,
        default=Path("assets/logo_TL_2026.png"),
        help="Path to the company logo (PNG, JPEG, GIF, or SVG).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for labels.pdf and inventory.csv.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of labels to generate.",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="IT",
        help="Prefix used in inventory IDs (e.g. IT -> IT-0001).",
    )
    parser.add_argument(
        "--digits",
        type=int,
        default=4,
        help="Minimum zero-padded digit width for the numeric part.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Starting sequence number (inclusive).",
    )
    parser.add_argument(
        "--barcode",
        type=str,
        default=BarcodeType.CODE128.value,
        help="Barcode symbology: code128 or qr (alias: qrcode).",
    )
    parser.add_argument(
        "--label-width-mm",
        type=float,
        default=36.0,
        help="Label width in millimeters.",
    )
    parser.add_argument(
        "--label-height-mm",
        type=float,
        default=17.0,
        help="Label height in millimeters.",
    )
    parser.add_argument(
        "--page-size",
        type=str,
        default="A4",
        choices=sorted(PAGE_SIZES.keys()),
        help="Page size for the PDF. Each label is centered on its own page.",
    )
    parser.add_argument(
        "--margin-mm",
        type=float,
        default=1.0,
        help="Inner margin on every side of the label, in millimeters.",
    )
    parser.add_argument(
        "--show-text-below-barcode",
        action="store_true",
        help="Draw a second human-readable copy of the ID below the barcode.",
    )
    parser.add_argument(
        "--pdf-name",
        type=str,
        default="labels.pdf",
        help="Output PDF filename inside the output directory.",
    )
    parser.add_argument(
        "--csv-name",
        type=str,
        default="inventory.csv",
        help="Output CSV filename inside the output directory.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> LabelConfig:
    """Build a ``LabelConfig`` from parsed CLI arguments.

    Args:
        args: Namespace produced by ``build_arg_parser().parse_args()``.

    Returns:
        Validated configuration object (validation runs separately).
    """
    page = PAGE_SIZES[args.page_size.upper()]
    return LabelConfig(
        logo_path=args.logo.expanduser().resolve(),
        output_dir=args.output_dir.expanduser().resolve(),
        count=args.count,
        prefix=args.prefix,
        digits=args.digits,
        start=args.start,
        barcode_type=BarcodeType.from_string(args.barcode),
        label_width_mm=args.label_width_mm,
        label_height_mm=args.label_height_mm,
        page_size=PageSize(page.name, page.width_mm, page.height_mm),
        margin_mm=args.margin_mm,
        show_text_below_barcode=args.show_text_below_barcode,
        pdf_filename=args.pdf_name,
        csv_filename=args.csv_name,
    )
