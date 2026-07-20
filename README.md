# Inventory Labels Generator

Production-ready Python tool that generates printable asset inventory labels as a multi-page PDF, plus a CSV for inventory import.

Each label is drawn at **true physical size** (default **36 mm × 17 mm**) and **centered on its own A4 page**. The rest of the page stays blank so a print shop can verify dimensions before production.

## Features

- Inventory IDs with configurable prefix, digit padding, start number, and count
- Barcode symbologies: **Code 128** and **QR Code** (payload is exactly the inventory ID)
- True millimeter geometry via ReportLab (`mm` units)
- Company logo (PNG / JPEG / GIF / **SVG**), top-centered, aspect ratio preserved, max 25% of label height
- Automatic font sizing and barcode scaling within configurable margins
- Optional human-readable ID below the barcode
- CSV export (`ID` column) for inventory systems
- Typed, modular package with validation and logging

## Requirements

- Python **3.12+**
- Dependencies listed in `requirements.txt` (actively maintained libraries)

## Installation

```bash
cd labels_generator
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Quick start

```bash
python main.py
```

Default run (uses `assets/logo.png`):

| Setting | Default |
|---------|---------|
| Count | 10 |
| Prefix | `IT` |
| Digits | 4 |
| Start | 1 |
| Barcode | Code128 |
| Label size | 36 × 17 mm |
| Page | A4 |
| Margins | 1 mm |
| Logo | `assets/logo_TL_2026.png` (auto-trimmed) |
| Output | `output/labels.pdf`, `output/inventory.csv` |

## Usage

```bash
python main.py \
  --logo assets/logo.png \
  --count 5000 \
  --prefix IT \
  --digits 4 \
  --start 1 \
  --barcode code128 \
  --label-width-mm 36 \
  --label-height-mm 17 \
  --page-size A4 \
  --margin-mm 1 \
  --output-dir output
```

### QR codes

```bash
python main.py --logo assets/logo.png --count 100 --prefix IT --digits 4 --barcode qr
```

### SVG logo + text under barcode

```bash
python main.py \
  --logo assets/logo.svg \
  --count 20 \
  --prefix ASSET \
  --digits 5 \
  --barcode code128 \
  --show-text-below-barcode
```

### CLI reference

| Argument | Description |
|----------|-------------|
| `--logo` | Path to company logo (PNG, JPEG, GIF, SVG) |
| `--output-dir` | Output directory |
| `--count` | Number of labels |
| `--prefix` | ID prefix (e.g. `IT`) |
| `--digits` | Minimum zero-padded width (e.g. `4` → `IT-0001`) |
| `--start` | Starting sequence number |
| `--barcode` | `code128` or `qr` (alias: `qrcode`) |
| `--label-width-mm` | Label width in mm |
| `--label-height-mm` | Label height in mm |
| `--page-size` | `A4`, `A5`, or `LETTER` |
| `--margin-mm` | Inner margin on every side |
| `--show-text-below-barcode` | Draw ID again below the barcode |
| `--pdf-name` | PDF filename (default `labels.pdf`) |
| `--csv-name` | CSV filename (default `inventory.csv`) |
| `-v` / `--verbose` | Debug logging |

```bash
python main.py --help
```

## Generated IDs

With `prefix=IT`, `digits=4`, `start=1`, `count=5000`:

```text
IT-0001
IT-0002
...
IT-5000
```

If the number needs more than `digits` characters, it continues without truncation:

```text
IT-9999
IT-10000
IT-10001
```

## Label layout

```text
+----------------------+
|     [Company Logo]   |
|      [Barcode/QR]    |
|        IT-0001       |
+----------------------+
```

- Logo: top centered, aspect preserved (never stretched). Empty padding is
  auto-trimmed. Sized modestly (barcode-first) and never wider than the barcode
- Barcode/QR: middle band, priority element — gets remaining height after logo/ID
- Inventory number: bottom centered, compact but print-readable (~5–6.5 pt)
- Everything stays inside the label box

## Output

```text
output/
  labels.pdf      # one label per page, true physical size, centered
  inventory.csv   # header: ID
```

Example CSV:

```csv
ID
IT-0001
IT-0002
IT-0003
```

## Project structure

```text
main.py                 # thin launcher (python main.py)
requirements.txt
assets/logo.png         # sample raster logo
assets/logo.svg         # sample SVG logo
generator/
  __init__.py
  main.py               # CLI (argparse)
  config.py             # defaults + argument mapping
  models.py             # dataclasses / enums
  validation.py         # input validation
  ids.py                # ID formatting
  barcode.py            # Code128 + QR rendering
  layout.py             # mm geometry + auto sizing
  pdf.py                # ReportLab PDF writer
  export.py             # CSV export
  service.py            # orchestration
```

## Configuration in code

```python
from pathlib import Path
from generator.models import BarcodeType, LabelConfig, PAGE_SIZES
from generator.service import run_generation

config = LabelConfig(
    logo_path=Path("assets/logo.png").resolve(),
    output_dir=Path("output").resolve(),
    count=5000,
    prefix="IT",
    digits=4,
    start=1,
    barcode_type=BarcodeType.CODE128,
    label_width_mm=36.0,
    label_height_mm=17.0,
    page_size=PAGE_SIZES["A4"],
    margin_mm=1.0,
)
result = run_generation(config)
print(result.pdf_path, result.csv_path)
```

## Validation

The tool rejects invalid inputs with clear messages, including:

- Missing or corrupt logo
- Unsupported logo format
- `count <= 0`
- Invalid dimensions / margins
- Invalid prefix
- Unsupported barcode type
- Label larger than the selected page

## Notes for print shops

- PDF page size defaults to A4 (210 × 297 mm).
- The label footprint is outlined lightly and centered; surrounding area is blank.
- Measure the outlined box on a test print to confirm scale before a production run.
- Code 128 includes the ISO quiet zone in the barcode image; QR codes use a 4-module border.

## Dependency notes

SVG logos use `svglib` 1.5.x (ReportLab-only rendering). Newer `svglib` 1.6+ releases require system Cairo via `pycairo`, which this project intentionally avoids so `pip install -r requirements.txt` works on a stock Python environment.

## License

Use and adapt freely for your inventory workflows.
