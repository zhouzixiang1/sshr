#!/usr/bin/env python3
"""Export the frozen XA-202609 Boolean-function benchmark manifest and CSV."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.competition_benchmarks import suite_manifest


DEFAULT_JSON = ROOT / "submission_competition" / "benchmark_suite_v1.json"
DEFAULT_CSV = ROOT / "submission_competition" / "benchmark_suite_v1.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()
    manifest = suite_manifest()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = manifest["cases"]
    fieldnames = [
        "case_id",
        "family",
        "n_inputs",
        "truth_table_hex",
        "function_key",
        "anf_terms",
        "onset_size",
        "generator",
        "generator_params",
        "source",
    ]
    with args.csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "generator_params": json.dumps(
                        row["generator_params"], ensure_ascii=False, sort_keys=True
                    ),
                }
            )
    print(f"suite_id={manifest['suite_id']} cases={manifest['case_count']}")
    print(args.json)
    print(args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
