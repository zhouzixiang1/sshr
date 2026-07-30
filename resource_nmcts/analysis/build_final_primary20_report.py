#!/usr/bin/env python3
"""Freeze the primary20 headline table and its content-addressed evidence manifest.

This script is deliberately read-only with respect to the DuckDB database and the
five detailed statistical reports.  It validates that all reports refer to the
same frozen experiment, database hash, analysis contract, candidate method and
seed contract before emitting a compact competition-facing summary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# Project root (resource_nmcts/), matching the figure script's ROOT so that the
# content-addressed manifest keys are relative paths shared by all consumers.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


BASELINES = {
    "resource_vs_direct_anf.json": ("direct_anf", "Direct-ANF"),
    "resource_vs_greedy_factor.json": ("greedy_factor", "Greedy-Factor"),
    "resource_vs_mcts_factor.json": ("mcts_factor", "MCTS-Factor"),
    "resource_vs_sshr_h.json": ("sshr_h", "SSHR-H"),
    "resource_vs_sshr_beam.json": ("sshr_beam", "SSHR-Beam"),
}

PRIMARY_METRICS = {
    ("logical", "t_count"): ("logic_T", "T count"),
    ("logical", "cnot_count"): ("logic_CNOT", "CNOT count"),
    ("mapping", "native_entangling_count"): (
        "native_twoq_count",
        "Native 2Q count",
    ),
    ("mapping", "mapped_depth"): ("mapped_depth", "Mapped depth"),
}

TEX_BASELINE_NAMES = {
    "direct_anf": "DirectAnf",
    "greedy_factor": "GreedyFactor",
    "mcts_factor": "MctsFactor",
    "sshr_h": "SshrH",
    "sshr_beam": "SshrBeam",
}

TEX_METRIC_NAMES = {
    "logic_T": "LogicT",
    "logic_CNOT": "LogicCnot",
    "native_twoq_count": "NativeTwoQ",
    "mapped_depth": "MappedDepth",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def require_equal(label: str, values: Iterable[Any]) -> Any:
    values = list(values)
    if not values:
        raise ValueError(f"no values supplied for {label}")
    first = values[0]
    if any(value != first for value in values[1:]):
        raise ValueError(f"inconsistent {label}: {values!r}")
    return first


def classify_claim(row: dict[str, Any]) -> tuple[str, bool]:
    """Apply the frozen conservative claim gate.

    Lower is better.  A result is called strictly significantly better only when
    the family-Holm decision rejects and *both* bootstrap interval encodings are
    strictly directional: median raw delta CI is below zero and median relative
    improvement CI is above zero.  Touching zero is not counted as strict.
    """

    delta = float(row["median_delta"])
    delta_hi = float(row["median_delta_ci_high"])
    relative = float(row["median_relative_improvement_pct"])
    relative_lo = float(row["median_relative_improvement_pct_ci_low"])
    holm = bool(row["holm_reject"])

    strict = holm and delta < 0.0 and delta_hi < 0.0 and relative > 0.0 and relative_lo > 0.0
    if strict:
        return "strict_significant_better", True
    if holm and delta < 0.0 and relative > 0.0:
        if delta_hi == 0.0 or relative_lo == 0.0:
            return "holm_supported_ci_touches_zero", False
        return "holm_supported_ci_crosses_zero", False
    if delta == 0.0:
        return "no_median_difference", False
    if delta > 0.0 or relative < 0.0:
        return "candidate_not_better", False
    return "not_statistically_supported", False


def build_summary(
    *,
    database: Path,
    stats_dir: Path,
    coverage_path: Path,
    consolidation_manifest_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, str]]]:
    database_hash = sha256_file(database)
    coverage = load_json(coverage_path)
    consolidation = load_json(consolidation_manifest_path)

    reports: list[tuple[Path, dict[str, Any], str, str]] = []
    input_records: dict[str, dict[str, str]] = {
        "database": {"path": str(database.as_posix()), "sha256": database_hash},
        "coverage_audit": {
            "path": str(coverage_path.as_posix()),
            "sha256": sha256_file(coverage_path),
        },
        "consolidation_manifest": {
            "path": str(consolidation_manifest_path.as_posix()),
            "sha256": sha256_file(consolidation_manifest_path),
        },
    }
    for filename, (expected_reference, display_name) in BASELINES.items():
        path = stats_dir / filename
        report = load_json(path)
        references = report.get("filters", {}).get("reference_methods", [])
        if references != [expected_reference]:
            raise ValueError(
                f"{path} reference mismatch: expected {[expected_reference]!r}, "
                f"found {references!r}"
            )
        if report.get("input", {}).get("database_unchanged") is not True:
            raise ValueError(f"statistics did not preserve database bytes: {path}")
        before = report.get("input", {}).get("database_sha256_before")
        after = report.get("input", {}).get("database_sha256_after")
        if before != database_hash or after != database_hash:
            raise ValueError(
                f"{path} database hash mismatch: report={before}/{after}, actual={database_hash}"
            )
        reports.append((path, report, expected_reference, display_name))
        input_records[f"statistics/{expected_reference}"] = {
            "path": str(path.as_posix()),
            "sha256": sha256_file(path),
        }

    experiment_slug = require_equal(
        "experiment slug",
        [r["filters"]["experiment_slugs"] for _, r, _, _ in reports],
    )
    suite = require_equal(
        "suite", [r["filters"]["suites"] for _, r, _, _ in reports]
    )
    candidate = require_equal(
        "candidate method",
        [r["filters"]["candidate_methods"] for _, r, _, _ in reports],
    )
    required_seeds = require_equal(
        "required seeds",
        [r["filters"]["required_seeds"] for _, r, _, _ in reports],
    )
    analysis_contract_sha256 = require_equal(
        "analysis contract hash",
        [r["statistics"]["analysis_contract_sha256"] for _, r, _, _ in reports],
    )
    bootstrap = require_equal(
        "bootstrap contract",
        [r["statistics"]["bootstrap"] for _, r, _, _ in reports],
    )

    rows: list[dict[str, Any]] = []
    for path, report, reference, display_name in reports:
        selected: dict[tuple[str, str], dict[str, Any]] = {}
        for row in report.get("summaries", []):
            key = (row.get("scope"), row.get("metric"))
            if key in PRIMARY_METRICS:
                if key in selected:
                    raise ValueError(f"duplicate primary summary {key!r} in {path}")
                selected[key] = row
        if set(selected) != set(PRIMARY_METRICS):
            missing = set(PRIMARY_METRICS) - set(selected)
            raise ValueError(f"missing primary summaries in {path}: {sorted(missing)!r}")

        for key, (competition_metric, metric_display) in PRIMARY_METRICS.items():
            row = selected[key]
            claim_class, strict = classify_claim(row)
            rows.append(
                {
                    "reference_method": reference,
                    "reference_display": display_name,
                    "candidate_method": row["candidate_method"],
                    "scope": row["scope"],
                    "metric": row["metric"],
                    "competition_metric": competition_metric,
                    "metric_display": metric_display,
                    "n_functions": int(row["n_pairs"]),
                    "n_seed_pairs": int(row["n_seed_pairs"]),
                    "required_seeds": list(required_seeds),
                    "win_count": int(row["win_count"]),
                    "tie_count": int(row["tie_count"]),
                    "loss_count": int(row["loss_count"]),
                    "median_delta": float(row["median_delta"]),
                    "median_delta_ci_low": float(row["median_delta_ci_low"]),
                    "median_delta_ci_high": float(row["median_delta_ci_high"]),
                    "median_relative_improvement_pct": float(
                        row["median_relative_improvement_pct"]
                    ),
                    "median_relative_improvement_pct_ci_low": float(
                        row["median_relative_improvement_pct_ci_low"]
                    ),
                    "median_relative_improvement_pct_ci_high": float(
                        row["median_relative_improvement_pct_ci_high"]
                    ),
                    "rank_biserial": float(row["rank_biserial"]),
                    "wilcoxon_p_raw": float(row["wilcoxon_p_raw"]),
                    "holm_family": row["holm_family"],
                    "holm_p_adjusted": float(row["holm_p_adjusted"]),
                    "holm_reject": bool(row["holm_reject"]),
                    "global_holm_p_adjusted": float(
                        row["global_holm_p_adjusted"]
                    ),
                    "global_holm_reject": bool(row["global_holm_reject"]),
                    "claim_class": claim_class,
                    "strict_significant_better": strict,
                }
            )

    core3 = coverage["recommended_primary20"]["core3"]
    counts = consolidation["counts"]
    for label, left, right in (
        ("intended cells", core3["intended_cells"], counts["intended_cells"]),
        (
            "verified cells",
            core3["union_verified_cells"],
            counts["selected_verified_cells"],
        ),
        ("missing cells", core3["missing_cells"], counts["missing_cells"]),
    ):
        if int(left) != int(right):
            raise ValueError(f"coverage/consolidation mismatch for {label}: {left} != {right}")

    missing = []
    for row in coverage["recommended_primary20"]["core3_recovery_groups"]:
        missing.append(
            {
                "case_id": row["case_id"],
                "family": row["family"],
                "requested_method": row["missing_methods"],
                "synthesis_seed": int(row["synthesis_seed"]),
                "target_name": row["target_name"],
                "transpile_seed": int(row["transpile_seed"]),
                "status": "synthesis_timeout_300s",
            }
        )
    if len(missing) != int(core3["missing_cells"]):
        raise ValueError(
            f"missing-cell detail count {len(missing)} does not equal denominator "
            f"{core3['missing_cells']}"
        )

    core_payload = {
        "schema_version": 1,
        "database_sha256": database_hash,
        "experiment_slug": experiment_slug,
        "suite": suite,
        "candidate_method": candidate,
        "required_seeds": required_seeds,
        "analysis_contract_sha256": analysis_contract_sha256,
        "bootstrap": bootstrap,
        "claim_gate": {
            "alpha": 0.05,
            "multiple_testing": "Holm within frozen logical-primary and mapping-primary families",
            "strict_rule": (
                "lower-is-better median delta < 0; family-Holm reject; median-delta "
                "95% bootstrap CI high < 0; median-relative-improvement 95% bootstrap "
                "CI low > 0; zero-touching intervals are not strict"
            ),
        },
        "coverage": {
            "planned_cells": int(core3["intended_cells"]),
            "verified_cells": int(core3["union_verified_cells"]),
            "missing_cells": int(core3["missing_cells"]),
            "coverage_fraction": float(core3["coverage_fraction"]),
            "missing": missing,
            "divergent_duplicate_cells": int(counts["divergent_duplicate_cells"]),
            "duplicate_rows_removed": int(counts["duplicate_rows_removed"]),
        },
        "headline_rows": rows,
        # Only role -> digest participates in the analysis ID.  Local paths are
        # recorded in the outer manifest but cannot perturb the content ID.
        "input_sha256": {
            role: record["sha256"]
            for role, record in sorted(input_records.items())
        },
    }
    analysis_digest = canonical_sha256(core_payload)
    core_payload["analysis_id"] = f"xa202609-primary20-{analysis_digest[:12]}"
    core_payload["analysis_payload_sha256"] = analysis_digest
    return core_payload, rows, input_records


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serializable = dict(row)
            serializable["required_seeds"] = json.dumps(
                serializable["required_seeds"], separators=(",", ":")
            )
            writer.writerow(serializable)


def _format_tex_number(value: float, digits: int = 1) -> str:
    return f"{float(value):.{digits}f}"


def write_tex_macros(path: Path, payload: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """Emit data-only TeX macros so prose and tables need not retype results."""

    coverage = payload["coverage"]
    lines = [
        "% AUTO-GENERATED by analysis/build_final_primary20_report.py; do not edit.",
        f"\\newcommand{{\\FinalAnalysisID}}{{{payload['analysis_id']}}}",
        f"\\newcommand{{\\FinalDatabaseSHA}}{{{payload['database_sha256']}}}",
        f"\\newcommand{{\\FinalAnalysisContractSHA}}{{{payload['analysis_contract_sha256']}}}",
        f"\\newcommand{{\\FinalPlannedCells}}{{{coverage['planned_cells']}}}",
        f"\\newcommand{{\\FinalVerifiedCells}}{{{coverage['verified_cells']}}}",
        f"\\newcommand{{\\FinalMissingCells}}{{{coverage['missing_cells']}}}",
        f"\\newcommand{{\\FinalCoveragePct}}{{{_format_tex_number(100.0 * coverage['coverage_fraction'])}}}",
    ]
    for row in rows:
        prefix = TEX_BASELINE_NAMES[row["reference_method"]] + TEX_METRIC_NAMES[
            row["competition_metric"]
        ]
        lines.extend(
            [
                f"\\newcommand{{\\{prefix}N}}{{{row['n_functions']}}}",
                f"\\newcommand{{\\{prefix}Pct}}{{{_format_tex_number(row['median_relative_improvement_pct'])}}}",
                f"\\newcommand{{\\{prefix}PctLow}}{{{_format_tex_number(row['median_relative_improvement_pct_ci_low'])}}}",
                f"\\newcommand{{\\{prefix}PctHigh}}{{{_format_tex_number(row['median_relative_improvement_pct_ci_high'])}}}",
                f"\\newcommand{{\\{prefix}HolmP}}{{{float(row['holm_p_adjusted']):.4g}}}",
                f"\\newcommand{{\\{prefix}WTL}}{{{row['win_count']}/{row['tie_count']}/{row['loss_count']}}}",
                f"\\newcommand{{\\{prefix}Strict}}{{{'yes' if row['strict_significant_better'] else 'no'}}}",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", type=Path, default=Path("results/competition_primary20_final.duckdb")
    )
    parser.add_argument("--stats-dir", type=Path, default=Path("results/final_stats"))
    parser.add_argument(
        "--coverage",
        type=Path,
        default=Path("submission_competition/formal_coverage_audit.json"),
    )
    parser.add_argument(
        "--consolidation-manifest",
        type=Path,
        default=Path(
            "submission_competition/formal_primary20_core3_final_manifest_v2.json"
        ),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("results/final_stats/primary20_headline.json"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("results/final_stats/primary20_headline.csv"),
    )
    parser.add_argument(
        "--output-manifest",
        type=Path,
        default=Path("submission_competition/final_analysis_manifest.json"),
    )
    parser.add_argument(
        "--output-tex",
        type=Path,
        default=Path("submission_competition/generated_final_numbers.tex"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, rows, input_records = build_summary(
        database=args.database,
        stats_dir=args.stats_dir,
        coverage_path=args.coverage,
        consolidation_manifest_path=args.consolidation_manifest,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(args.output_csv, rows)
    write_tex_macros(args.output_tex, payload, rows)

    manifest = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_id": payload["analysis_id"],
        "analysis_payload_sha256": payload["analysis_payload_sha256"],
        "database_sha256": payload["database_sha256"],
        "analysis_contract_sha256": payload["analysis_contract_sha256"],
        "inputs": input_records,
        "outputs": {
            str(args.output_json.resolve().relative_to(PROJECT_ROOT).as_posix()): sha256_file(args.output_json),
            str(args.output_csv.resolve().relative_to(PROJECT_ROOT).as_posix()): sha256_file(args.output_csv),
            str(args.output_tex.resolve().relative_to(PROJECT_ROOT).as_posix()): sha256_file(args.output_tex),
        },
        "coverage": payload["coverage"],
        "strict_significant_better_count": sum(
            bool(row["strict_significant_better"]) for row in rows
        ),
        "headline_row_count": len(rows),
        "database_access": "hash-only by this aggregator; detailed statistics were generated read-only",
    }
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "analysis_id": payload["analysis_id"],
                "database_sha256": payload["database_sha256"],
                "coverage": payload["coverage"],
                "headline_rows": len(rows),
                "strict_significant_better": manifest[
                    "strict_significant_better_count"
                ],
                "outputs": manifest["outputs"],
                "manifest": str(args.output_manifest),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
