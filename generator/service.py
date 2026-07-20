"""High-level orchestration for a label generation run."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from generator.export import write_inventory_csv
from generator.ids import iter_inventory_ids
from generator.models import LabelConfig
from generator.pdf import generate_labels_pdf
from generator.validation import validate_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Paths produced by a successful generation run."""

    pdf_path: Path
    csv_path: Path
    label_count: int


def run_generation(config: LabelConfig) -> GenerationResult:
    """Validate configuration, then write PDF and CSV outputs.

    Args:
        config: Label generation settings.

    Returns:
        ``GenerationResult`` with output paths and count.

    Raises:
        ConfigError: If configuration is invalid.
        OSError: If files cannot be written.
    """
    validate_config(config)
    logger.info(
        "Generating %d labels (%s, %s, %s digits, start=%d) -> %s",
        config.count,
        config.prefix,
        config.barcode_type.value,
        config.digits,
        config.start,
        config.output_dir,
    )

    # Materialize IDs once so PDF and CSV stay identical.
    inventory_ids = list(iter_inventory_ids(config))
    pdf_path = generate_labels_pdf(config)
    csv_path = config.csv_path
    write_inventory_csv(csv_path, inventory_ids)

    return GenerationResult(
        pdf_path=pdf_path,
        csv_path=csv_path,
        label_count=len(inventory_ids),
    )
