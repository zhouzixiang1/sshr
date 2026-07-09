#!/usr/bin/env python3
"""Audit benchmark-suite composition and representativeness boundaries.

This audit answers a reviewer question that is different from "which baseline
won": what slices are actually in the benchmark package, how many rows are
verified, which abstraction each slice uses, and what representativeness
boundary remains.  It is deliberately descriptive; it does not create new
scientific claims beyond the existing raw CSVs and manifests.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

SUMMARY = RESULTS / "summary_benchmark_suite_audit.csv"
ANALYSIS = RESULTS / "analysis_benchmark_suite_audit.md"
MANIFEST = RESULTS / "manifest_benchmark_suite_audit.json"
TABLE = TABLES / "benchmark_suite_audit.tex"


@dataclass(frozen=True)
class SuiteSpec:
    suite: str
    role: str
    patterns: tuple[str, ...]
    verification_route: str
    usable_claim: str
    boundary: str


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def collect(patterns: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in RESULTS.glob(pattern) if path.is_file())
    return sorted(set(files), key=rel)


def truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def row_verified(row: dict[str, str]) -> bool:
    if "status" in row and row["status"]:
        return row["status"] == "pass"
    checks = [
        field
        for field in (
            "anf_verified",
            "truth_verified",
            "circuit_anf_verified",
            "permutation_checked",
            "verified_up_to_global_phase",
            "smoke_pass",
        )
        if field in row
    ]
    if checks:
        return all(truthy(row.get(field)) for field in checks) and not truthy(row.get("skipped"))
    if "correct" in row and row["correct"]:
        return truthy(row["correct"]) and not truthy(row.get("skipped"))
    return False


def instance_key(row: dict[str, str]) -> str:
    dataset = row.get("dataset") or row.get("profile") or row.get("source_file") or ""
    name = row.get("name") or row.get("source_name") or row.get("target_id") or row.get("index") or ""
    n_value = row.get("n") or row.get("source_n") or ""
    return "|".join([dataset, name, n_value])


def n_values(rows: list[dict[str, str]]) -> list[int]:
    values: set[int] = set()
    for row in rows:
        for field in ("n", "source_n"):
            value = row.get(field, "")
            if re.fullmatch(r"\d+", value.strip()):
                values.add(int(value))
    return sorted(values)


def n_scope(values: list[int]) -> str:
    if not values:
        return "not applicable"
    if len(values) == 1:
        return f"n={values[0]}"
    return f"n={values[0]}--{values[-1]}"


def method_count(rows: list[dict[str, str]]) -> int:
    return len({row.get("method", "") for row in rows if row.get("method", "")})


def suite_specs() -> list[SuiteSpec]:
    return [
        SuiteSpec(
            suite="Matched small Boolean oracles",
            role="primary same-task benchmark",
            patterns=(
                "raw_traditional_resource.csv",
                "raw_external_traditional_resource_n4.csv",
                "raw_external_traditional_resource_n5.csv",
                "raw_external_traditional_resource_n6.csv",
            ),
            verification_route="complete truth table for n<=6 rows; timeout/skipped rows remain explicit",
            usable_claim="Paired T-count and weighted-score comparisons on the main bit-flip oracle task.",
            boundary="Small functions are enumerable and fair for method comparison, but they are not a large-n optimality claim.",
        ),
        SuiteSpec(
            suite="Published tiny-function optimum counterpoint",
            role="optimum-library boundary",
            patterns=("raw_stg_published_benchmark.csv",),
            verification_route="public n=4/5 truth tables with complete correctness checks",
            usable_claim="A negative control showing where published STG optima remain stronger.",
            boundary="Used as a small-function boundary, not as evidence that the proposed search beats precomputed optima.",
        ),
        SuiteSpec(
            suite="External logic-network probes",
            role="toolchain stress test",
            patterns=(
                "raw_ros_lut_proxy_best.csv",
                "raw_mockturtle_xag_probe.csv",
                "raw_mockturtle_xag_highdim_probe.csv",
                "raw_caterpillar_xag_api_best.csv",
                "raw_cirkit_aig_probe.csv",
                "raw_cirkit_aig_highdim_probe.csv",
            ),
            verification_route="export/readback, ABC BLIF/Verilog, XAG/AIG/API checks where available",
            usable_claim="Mature Boolean-network and LUT/XAG/AIG toolchains do not erase the T/score story.",
            boundary="These are logical probes, not full ROS SAT garbage management, reversible emission, routing, or hardware mapping.",
        ),
        SuiteSpec(
            suite="RevKit reversible and phase probes",
            role="reversible/phase counterpoint",
            patterns=(
                "raw_revkit_cli_multiflow_traditional.csv",
                "raw_revkit_oracle_synth_traditional.csv",
                "raw_phase_parity_anf.csv",
                "raw_phase_parity_fprm.csv",
                "raw_phase_parity_affine.csv",
                "raw_phase_parity_affine_wide128.csv",
                "raw_phase_affine_policy_rank_diverse.csv",
                "raw_phase_rotation_sequence_smoke_audit.csv",
            ),
            verification_route="exact reversible permutation checks, phase verification up to global phase, and coarse rotation-sequence smoke checks",
            usable_claim="A reversible-synthesis portfolio and a phase/Rz branch are tested as bounded counterpoints.",
            boundary="Rz rows are proxy-level phase evidence and do not constitute final approximate Clifford+T rotation synthesis.",
        ),
        SuiteSpec(
            suite="Large symbolic term-set scaling",
            role="scalability and stress test",
            patterns=(
                "raw_screen_scale_terms.csv",
                "raw_screen_scale_extended_terms.csv",
                "raw_screen_scale_ultra_scale64_terms.csv",
                "raw_screen_scale_depth_frontier_policy*_terms.csv",
                "raw_screen_scale_schedule_depth_frontier_policy*_terms.csv",
            ),
            verification_route="symbolic ANF and emitted-circuit ANF checks",
            usable_claim="The bounded logical search and emitter scale to generated n=20--64 term-set instances.",
            boundary="Symbolic large-n rows are not exhaustive truth-table enumeration and do not prove global optimality.",
        ),
        SuiteSpec(
            suite="Complete truth-table bridge slices",
            role="large-n semantic bridge",
            patterns=("raw_truth_bridge*_terms.csv", "raw_schedule_truth_bridge*_terms.csv"),
            verification_route="complete truth-table construction plus plan and emitted-circuit checks",
            usable_claim="Bridge slices connect symbolic high-dimensional plans to full semantic checking up to n=30 generated functions.",
            boundary="The bridge is intentionally narrow because full truth tables grow exponentially.",
        ),
        SuiteSpec(
            suite="Learned-control and stochastic controls",
            role="causal attribution and stability control",
            patterns=(
                "raw_bitflip_random_prior_control.csv",
                "raw_bitflip_neural_budget_sweep.csv",
                "raw_sparse_depth4_gate_generalization.csv",
                "raw_phase_affine_policy.csv",
                "raw_phase_affine_policy_rank_diverse.csv",
            ),
            verification_route="same-budget random controls, held-out splits, independent seeds, and semantic checks",
            usable_claim="Neural ranking, frontier policies, and guards are separated from the algebraic representation effect.",
            boundary="These rows support bounded control gains; they do not imply that deep learning alone causes the main resource reduction.",
        ),
    ]


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in suite_specs():
        files = collect(spec.patterns)
        data_rows: list[dict[str, str]] = []
        for path in files:
            for row in read_csv(path):
                row["_source_file"] = rel(path)
                data_rows.append(row)
        raw_rows = len(data_rows)
        verified_rows = sum(1 for row in data_rows if row_verified(row))
        instances = {instance_key(row) for row in data_rows if instance_key(row).strip("|")}
        n_list = n_values(data_rows)
        missing_patterns = [pattern for pattern in spec.patterns if not collect((pattern,))]
        status = "pass"
        if not files or missing_patterns:
            status = "needs revision"
        elif raw_rows == 0:
            status = "needs revision"
        elif verified_rows == 0:
            status = "needs revision"

        rows.append(
            {
                "suite": spec.suite,
                "role": spec.role,
                "n_scope": n_scope(n_list),
                "instances": str(len(instances)),
                "raw_rows": str(raw_rows),
                "verified_rows": str(verified_rows),
                "methods": str(method_count(data_rows)),
                "source_files": "; ".join(rel(path) for path in files),
                "verification_route": spec.verification_route,
                "usable_claim": spec.usable_claim,
                "boundary": spec.boundary,
                "status": status,
                "next_action": (
                    "Restore the missing/raw evidence files and rerun this audit."
                    if status != "pass"
                    else "Keep this row aligned with benchmark generators, raw CSVs, and manuscript scope wording."
                ),
            }
        )
    return rows


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("<=", r"$\leq$")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = {
        "Resource-NMCTS": r"\method{}",
        "ANF": r"\anf{}",
        "Rz": r"\rz{}",
        "MCTS": r"\mcts{}",
        "n=3--6": r"$n=3$--$6$",
        "n=4--5": r"$n=4$--$5$",
        "n=20--64": r"$n=20$--$64$",
        "n=21--30": r"$n=21$--$30$",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    escaped = re.sub(r"n=(\d+)--(\d+)", r"$n=\1$--$\2$", escaped)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "suite",
        "role",
        "n_scope",
        "instances",
        "raw_rows",
        "verified_rows",
        "methods",
        "source_files",
        "verification_route",
        "usable_claim",
        "boundary",
        "status",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    total_raw = sum(int(row["raw_rows"]) for row in rows)
    total_verified = sum(int(row["verified_rows"]) for row in rows)
    lines = [
        "# Benchmark Suite Audit",
        "",
        "This audit records what benchmark slices are represented in the paper package, how each slice is verified, and which representativeness boundary remains.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Aggregate coverage",
            "",
            f"- raw rows across suite families: {total_raw}",
            f"- verified rows across suite families: {total_verified}",
            "",
            "| suite | role | n scope | instances | raw rows | verified rows | methods | verification route | boundary | status |",
            "|---|---|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {suite} | {role} | {n_scope} | {instances} | {raw_rows} | {verified_rows} | {methods} | {verification_route} | {boundary} | {status} |".format(
                **row
            )
        )
    lines.extend(["", "## Source files", ""])
    for row in rows:
        lines.append(f"- **{row['suite']}**: `{row['source_files']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}p{0.08\linewidth}>{\raggedleft\arraybackslash}p{0.07\linewidth}>{\raggedleft\arraybackslash}p{0.08\linewidth}>{\raggedleft\arraybackslash}p{0.08\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.18\linewidth}}",
        r"\toprule",
        r"Suite & Role & Scope & Items & Rows & Checked & Verification route & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["suite"]),
                latex_cell(row["role"]),
                latex_cell(row["n_scope"]),
                row["instances"],
                row["raw_rows"],
                row["verified_rows"],
                latex_cell(row["verification_route"]),
                latex_cell(row["boundary"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    author_text = read_text(AUTHOR_TEX)
    anon_text = read_text(ANON_TEX)
    acm_text = read_text(ACM_TEX)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "raw_rows": sum(int(row["raw_rows"]) for row in rows),
        "verified_rows": sum(int(row["verified_rows"]) for row in rows),
        "suite_names": [row["suite"] for row in rows],
        "n_scopes": sorted({row["n_scope"] for row in rows}),
        "table": "paper_latex/tables/benchmark_suite_audit.tex",
        "table_anchor_present": "tab:benchmark-suite-audit" in author_text,
        "anonymous_table_anchor_present": "tab:benchmark-suite-audit" in anon_text,
        "acm_table_anchor_present": "tab:benchmark-suite-audit" in acm_text,
        "source_files": sorted({source for row in rows for source in row["source_files"].split("; ") if source}),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {rel(SUMMARY)}")
    print(f"wrote {rel(ANALYSIS)}")
    print(f"wrote {rel(MANIFEST)}")
    print(f"wrote {rel(TABLE)}")


if __name__ == "__main__":
    main()
