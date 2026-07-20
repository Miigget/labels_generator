"""CSV export for inventory systems."""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterable
from pathlib import Path

from generator.models import InventoryId

logger = logging.getLogger(__name__)


def write_inventory_csv(path: Path, inventory_ids: Iterable[InventoryId]) -> int:
    """Write inventory IDs to a CSV file with a single ``ID`` column.

    Args:
        path: Destination CSV path. Parent directories are created as needed.
        inventory_ids: IDs to export.

    Returns:
        Number of data rows written (excluding the header).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ID"])
        for item in inventory_ids:
            writer.writerow([item.value])
            count += 1
    logger.info("Wrote %d inventory IDs to %s", count, path)
    return count
