#!/usr/bin/env python3
"""Derive immutable success-only JSONL files from interrupted runner outputs.

No row is repaired or rewritten semantically.  Every input row first passes the
hardware-validation hash/schema contract; rows are then selected only when
``status == 'ok'``.  The manifest records source/output hashes and all excluded
error identities so interrupted, memory-failed runs remain auditable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hardware_validation_ingest import load_jsonl  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derive_success_file(source: Path, output: Path) -> dict[str, Any]:
    rows, source_sha256 = load_jsonl(source)
    selected = [row for row in rows if row["status"] == "ok"]
    excluded = [row for row in rows if row["status"] != "ok"]
    if not selected:
        raise ValueError(f"{source} contains no successful rows")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        for row in selected:
            stream.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
            )
    # Re-load the derived stream through the same contract before publishing
    # its hash in the manifest.
    verified_rows, output_sha256 = load_jsonl(output)
    if len(verified_rows) != len(selected):
        raise AssertionError("derived JSONL row-count mismatch")
    return {
        "source": source.resolve().as_posix(),
        "source_sha256": source_sha256,
        "source_rows": len(rows),
        "source_status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "output": output.resolve().as_posix(),
        "output_sha256": output_sha256,
        "output_rows": len(selected),
        "selection_predicate": "status == 'ok' after full fixed-schema/hash validation",
        "excluded_rows": [
            {
                "record_key": row["record_key"],
                "function_id": row["function_id"],
                "requested_method": row["requested_method"],
                "synthesis_seed": row["synthesis_seed"],
                "target_id": row["target_id"],
                "transpile_seed": row["transpile_seed"],
                "status": row["status"],
                "stage": row["stage"],
                "error_code": row["error_code"],
                "error_message": row["error_message"],
            }
            for row in excluded
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.manifest.exists():
        raise FileExistsError(args.manifest)
    records = []
    for source in args.input:
        source = source.resolve()
        output = args.output_dir.resolve() / f"{source.stem}_ok.jsonl"
        records.append(derive_success_file(source, output))
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "recover validated facts from interrupted memory-pressure runs",
        "mutation_policy": "no source file changed; excluded rows remain only in raw source",
        "files": records,
        "totals": {
            "source_rows": sum(row["source_rows"] for row in records),
            "selected_rows": sum(row["output_rows"] for row in records),
            "excluded_rows": sum(len(row["excluded_rows"]) for row in records),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest["totals"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
