#!/usr/bin/env python3
"""Consolidate verified runner facts into one paired-analysis experiment.

Runner outputs are intentionally immutable and may come from several recovery
runs.  This utility validates each source independently, selects one successful
fact per frozen semantic cell, writes a content-addressed consolidation
manifest, and ingests the selected rows under one experiment identity.  The
original ``run_id`` on every row is preserved; no result metric is rewritten.

Failures are never discarded from their raw sources, but they are not inserted
into the quality-analysis experiment because a failed first attempt would mask
a later successful retry in the append-only canonical view.  Coverage and
failure-rate reporting must therefore use the raw recovery manifests alongside
this success-only experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.experiment_db import ExperimentDB, canonical_json  # noqa: E402
from src.hardware_validation_ingest import ingest_rows, load_jsonl  # noqa: E402


DEFAULT_METHODS = (
    "direct_anf",
    "greedy_factor",
    "mcts_factor",
    "sshr_h",
    "sshr_beam",
    "resource_nmcts",
)
DEFAULT_SEEDS = (7, 17, 29)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


def _parse_int_csv(value: str) -> tuple[int, ...]:
    return tuple(int(item) for item in _parse_csv(value))


def _mapping_semantics(row: dict[str, Any]) -> dict[str, Any]:
    config = row["compile_config"]
    return {
        "target_id": row["target_id"],
        "target_hash": row["target_hash"],
        "seed_transpiler": int(row["transpile_seed"]),
        "optimization_level": int(config["optimization_level"]),
        "layout_method": config.get("layout_method"),
        "routing_method": config.get("routing_method"),
        "hls_ancilla_budget": int(config.get("hls_ancilla_budget", 0)),
        "mcx_methods": list(config.get("mcx_methods", [])),
    }


def _cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(row["function_truth_hash"]),
        str(row["requested_method"]),
        int(row["synthesis_seed"]),
        canonical_json(_mapping_semantics(row)),
        str(row["synthesis_config_hash"]),
        row["model_hash"],
    )


def _metric_signature(row: dict[str, Any]) -> str:
    fields = (
        "logic_T",
        "logic_CNOT",
        "logic_depth",
        "logic_gates",
        "logic_peak_ancilla",
        "mapped_gates",
        "mapped_depth",
        "native_twoq_count",
        "native_twoq_depth",
        "unsupported_instructions",
        "coupling_violations",
        "mapped_mismatches",
    )
    return canonical_json({field: row[field] for field in fields})


def _load_primary_cases(audit_path: Path) -> tuple[str, ...]:
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    values = payload["recommended_primary20"]["case_ids"]
    return tuple(str(value) for value in values)


def _choose_latest(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return max(rows, key=lambda row: (str(row["run_ts"]), str(row["record_key"])))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument(
        "--coverage-audit",
        type=Path,
        default=PROJECT_ROOT / "submission_competition" / "formal_coverage_audit.json",
    )
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--target-id", default="cx_full_12")
    parser.add_argument("--transpile-seed", type=int, default=3)
    parser.add_argument("--optimization-level", type=int, default=1)
    parser.add_argument("--layout-method", default="sabre")
    parser.add_argument("--routing-method", default="sabre")
    parser.add_argument("--hls-ancilla-budget", type=int, default=0)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--experiment-slug", required=True)
    parser.add_argument("--experiment-title", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.manifest.exists():
        raise FileExistsError(args.manifest)

    primary_cases = set(_load_primary_cases(args.coverage_audit.resolve()))
    methods = set(_parse_csv(args.methods))
    seeds = set(_parse_int_csv(args.seeds))
    sources: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    exclusion_counts: Counter[str] = Counter()

    for input_path in args.input:
        source = input_path.resolve()
        rows, source_sha256 = load_jsonl(source)
        sources.append(
            {
                "path": source.as_posix(),
                "sha256": source_sha256,
                "rows": len(rows),
                "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
            }
        )
        for row in rows:
            reason = None
            if row["status"] != "ok":
                reason = "not_ok"
            elif row["function_id"] not in primary_cases:
                reason = "outside_primary_cases"
            elif row["requested_method"] not in methods:
                reason = "outside_methods"
            elif int(row["synthesis_seed"]) not in seeds:
                reason = "outside_synthesis_seeds"
            elif row["target_id"] != args.target_id:
                reason = "wrong_target"
            elif int(row["transpile_seed"]) != args.transpile_seed:
                reason = "wrong_transpile_seed"
            else:
                config = row["compile_config"]
                if int(config["optimization_level"]) != args.optimization_level:
                    reason = "wrong_optimization_level"
                elif config.get("layout_method") != args.layout_method:
                    reason = "wrong_layout_method"
                elif config.get("routing_method") != args.routing_method:
                    reason = "wrong_routing_method"
                elif int(config.get("hls_ancilla_budget", 0)) != args.hls_ancilla_budget:
                    reason = "wrong_hls_ancilla_budget"
            if reason is None:
                eligible.append(row)
            else:
                exclusion_counts[reason] += 1

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        grouped[_cell_key(row)].append(row)

    selected = [_choose_latest(group) for group in grouped.values()]
    selected.sort(
        key=lambda row: (
            str(row["family"]),
            str(row["function_id"]),
            int(row["synthesis_seed"]),
            str(row["requested_method"]),
        )
    )

    divergent_duplicates = []
    for group in grouped.values():
        signatures = {_metric_signature(row) for row in group}
        if len(signatures) > 1:
            divergent_duplicates.append(
                {
                    "function_id": group[0]["function_id"],
                    "method": group[0]["requested_method"],
                    "synthesis_seed": group[0]["synthesis_seed"],
                    "record_keys": sorted(str(row["record_key"]) for row in group),
                    "metric_signature_count": len(signatures),
                }
            )

    intended = len(primary_cases) * len(methods) * len(seeds)
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "single-experiment verified paired analysis for primary20 core3",
        "selection_contract": {
            "status": "ok",
            "case_ids": sorted(primary_cases),
            "methods": sorted(methods),
            "synthesis_seeds": sorted(seeds),
            "target_id": args.target_id,
            "transpile_seed": args.transpile_seed,
            "optimization_level": args.optimization_level,
            "layout_method": args.layout_method,
            "routing_method": args.routing_method,
            "hls_ancilla_budget": args.hls_ancilla_budget,
            "deduplication": "latest run_ts then record_key within identical semantic cell",
            "verification_runtime_fields": "ignored for cell identity; retained in source row",
        },
        "failure_policy": (
            "quality experiment contains verified successes only; raw sources and recovery "
            "manifests remain authoritative for failure/coverage reporting"
        ),
        "sources": sources,
        "counts": {
            "source_rows": sum(item["rows"] for item in sources),
            "eligible_rows_before_deduplication": len(eligible),
            "selected_verified_cells": len(selected),
            "intended_cells": intended,
            "missing_cells": intended - len(selected),
            "duplicate_rows_removed": len(eligible) - len(selected),
            "divergent_duplicate_cells": len(divergent_duplicates),
            "exclusions": dict(sorted(exclusion_counts.items())),
        },
        "divergent_duplicates": divergent_duplicates,
        "selected": [
            {
                "record_key": row["record_key"],
                "source_run_id": row["run_id"],
                "function_id": row["function_id"],
                "requested_method": row["requested_method"],
                "synthesis_seed": row["synthesis_seed"],
                "target_id": row["target_id"],
                "transpile_seed": row["transpile_seed"],
            }
            for row in selected
        ],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_sha256 = _sha256(args.manifest)

    summary: dict[str, Any] = {
        "manifest": args.manifest.resolve().as_posix(),
        "manifest_sha256": manifest_sha256,
        **manifest["counts"],
    }
    if not args.dry_run:
        with ExperimentDB(args.db.resolve()) as db:
            ingested = ingest_rows(
                db,
                selected,
                source_sha256=manifest_sha256,
                source_path=args.manifest,
                source_byte_size=args.manifest.stat().st_size,
                experiment_slug=args.experiment_slug,
                experiment_title=args.experiment_title,
            )
        summary["ingest"] = ingested.to_dict()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
