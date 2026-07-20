"""Inventory ID generation."""

from __future__ import annotations

from collections.abc import Iterator

from generator.models import InventoryId, LabelConfig


def format_inventory_id(prefix: str, number: int, digits: int) -> str:
    """Format an inventory ID without truncating oversized numbers.

    Args:
        prefix: ID prefix (e.g. ``IT``).
        number: Sequence number.
        digits: Minimum zero-padded width. Values that need more digits
            are rendered in full (e.g. digits=4, number=10000 -> ``IT-10000``).

    Returns:
        Formatted ID such as ``IT-0001``.
    """
    numeric = f"{number:0{digits}d}"
    return f"{prefix}-{numeric}"


def iter_inventory_ids(config: LabelConfig) -> Iterator[InventoryId]:
    """Yield inventory IDs for a generation run.

    Args:
        config: Label configuration controlling prefix, digits, start, and count.

    Yields:
        ``InventoryId`` instances from ``start`` through ``start + count - 1``.
    """
    prefix = config.prefix.strip()
    end = config.start + config.count
    for sequence in range(config.start, end):
        yield InventoryId(
            value=format_inventory_id(prefix, sequence, config.digits),
            sequence=sequence,
        )
