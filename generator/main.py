"""CLI entry point for the inventory label generator."""

from __future__ import annotations

import logging
import sys

from generator.config import build_arg_parser, config_from_args
from generator.service import run_generation
from generator.validation import ConfigError


def configure_logging(verbose: bool) -> None:
    """Configure root logging for CLI use."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Keep dependency loggers quieter even in verbose mode.
    logging.getLogger("PIL").setLevel(logging.INFO)
    logging.getLogger("svglib").setLevel(logging.INFO)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and run label generation.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 1 on user/config errors, 2 on unexpected).
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        config = config_from_args(args)
    except ValueError as exc:
        logging.error("%s", exc)
        return 1

    try:
        result = run_generation(config)
    except ConfigError as exc:
        logging.error("%s", exc)
        return 1
    except Exception:
        logging.exception("Label generation failed.")
        return 2

    print(f"Generated {result.label_count} labels.")
    print(f"PDF: {result.pdf_path}")
    print(f"CSV: {result.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
