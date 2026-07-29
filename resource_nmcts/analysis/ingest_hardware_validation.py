#!/usr/bin/env python3
"""Validate and append one hardware-validation JSONL file to DuckDB."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hardware_validation_ingest import (  # noqa: E402
    DEFAULT_EXPERIMENT_SLUG,
    DEFAULT_EXPERIMENT_TITLE,
    HardwareValidationIngestError,
    ingest_jsonl,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--experiment-slug", default=DEFAULT_EXPERIMENT_SLUG)
    parser.add_argument("--experiment-title", default=DEFAULT_EXPERIMENT_TITLE)
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="fail instead of returning success when the exact source hash already exists",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = ingest_jsonl(
            args.input_jsonl,
            args.db,
            experiment_slug=args.experiment_slug,
            experiment_title=args.experiment_title,
            resume=not args.no_resume,
        )
    except (HardwareValidationIngestError, FileNotFoundError, OSError) as exc:
        print(f"ingestion failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
