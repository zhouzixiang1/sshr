#!/usr/bin/env python3
"""Build a verification-strength ladder for the experiment package.

The benchmark-suite audit answers "what data are in the package."  This audit
answers the reviewer-facing follow-up: which layers of evidence are strong
enough for headline resource claims, which layers only stress scalability, and
where the complete semantic checks stop.  It is derived from existing summary
CSVs and manifests rather than from hand-entered manuscript numbers.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

BENCHMARK_SUMMARY = RESULTS / "summary_benchmark_suite_audit.csv"
BENCHMARK_MANIFEST = RESULTS / "manifest_benchmark_suite_audit.json"
FUNCTION_DIVERSITY_MANIFEST = RESULTS / "manifest_benchmark_function_diversity_audit.json"
ULTRA_PROFILE_MANIFEST = RESULTS / "manifest_screen_scale_ultra_scale64_resource_profile.json"
RUNTIME_MANIFEST = RESULTS / "manifest_runtime_envelope_audit.json"
REPRO_SUMMARY = RESULTS / "summary_reproducibility_audit.csv"

SUMMARY = RESULTS / "summary_experimental_evidence_ladder.csv"
ANALYSIS = RESULTS / "analysis_experimental_evidence_ladder.md"
MANIFEST = RESULTS / "manifest_experimental_evidence_ladder.json"
TABLE = TABLES / "experimental_evidence_ladder.tex"


@dataclass(frozen=True)
class LadderSpec:
    level: str
    source_suite: str | None
    evidence_role: str
    verification_strength: str
    resource_dimensions: str
    claim_use: str
    boundary: str
    required_files: tuple[Path, ...]


LADDER = (
    LadderSpec(
        level="1. Exact same-task core",
        source_suite="Matched small Boolean oracles",
        evidence_role="Headline bit-flip oracle comparison",
        verification_strength="complete truth-table checks",
        resource_dimensions="T, CNOT, depth, peak ancilla, weighted score",
        claim_use="Primary paired T-count and weighted-score claim over same-function baselines.",
        boundary="Small n is fair and exact, but not a large-n optimality certificate.",
        required_files=(
            RESULTS / "analysis_paired_statistical_evidence.md",
            RESULTS / "analysis_resource_weight_sensitivity_audit.md",
        ),
    ),
    LadderSpec(
        level="2. Small optimum counterpoint",
        source_suite="Published tiny-function optimum counterpoint",
        evidence_role="Negative control against precomputed public optima",
        verification_strength="public truth tables with exact small-function checks",
        resource_dimensions="T, CNOT, depth, ancilla, score where comparable",
        claim_use="Shows that the paper does not hide stronger tiny-function optimum rows.",
        boundary="Counterpoint evidence only; it is not a headline victory over optimum libraries.",
        required_files=(RESULTS / "analysis_stg_published_benchmark.md",),
    ),
    LadderSpec(
        level="3. External toolchain stress",
        source_suite="External logic-network probes",
        evidence_role="Independent Boolean-network and LUT/XAG/AIG pressure",
        verification_strength="export/readback and logic-network checks",
        resource_dimensions="logical network resources plus emitted oracle estimates",
        claim_use="Checks that the resource story is not only against local hand-written baselines.",
        boundary="Proxy logical-tool evidence, not a full reversible or hardware-mapped reproduction.",
        required_files=(
            RESULTS / "analysis_ros_reproduction_gap_audit.md",
            RESULTS / "analysis_caterpillar_xag_api_probe.md",
        ),
    ),
    LadderSpec(
        level="4. Reversible and phase boundary",
        source_suite="RevKit reversible and phase probes",
        evidence_role="Exact reversible and phase/Rz transfer counterpoint",
        verification_strength="permutation checks, phase checks up to global phase, smoke sequence checks",
        resource_dimensions="line count, phase/Rz proxy score, coarse sequence cost",
        claim_use="Separates reversible/phase transfer evidence from the main bit-flip result.",
        boundary="Not a final approximate Clifford+T rotation-synthesis comparison.",
        required_files=(
            RESULTS / "analysis_phase_policy_budget_frontier.md",
            RESULTS / "analysis_rotation_synthesis_backend_audit.md",
        ),
    ),
    LadderSpec(
        level="5. Complete high-n semantic bridge",
        source_suite="Complete truth-table bridge slices",
        evidence_role="Large-n semantic bridge",
        verification_strength="complete truth-table construction and emitted-circuit checks",
        resource_dimensions="T, CNOT, depth, ancilla, T-depth proxy, lifetime",
        claim_use="Connects symbolic large-instance plans to exact semantic checks up to n=30 generated functions.",
        boundary="Deliberately narrow because full truth tables grow exponentially.",
        required_files=(
            RESULTS / "analysis_scaling_resource_audit.md",
            RESULTS / "analysis_schedule_proxy_audit.md",
        ),
    ),
    LadderSpec(
        level="6. Ultra-scale symbolic stress",
        source_suite="Large symbolic term-set scaling",
        evidence_role="Scalability and resource-profile stress test",
        verification_strength="symbolic ANF and emitted-circuit ANF checks",
        resource_dimensions="score, T, CNOT, depth, ancilla, T-depth proxy, runtime",
        claim_use="Shows the bounded search and emitter still run on generated n=20--64 logical instances.",
        boundary="Symbolic verification is not exhaustive high-dimensional truth-table enumeration.",
        required_files=(
            RESULTS / "analysis_screen_scale_ultra_scale64_stress.md",
            RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md",
        ),
    ),
    LadderSpec(
        level="7. AI/search-control attribution",
        source_suite="Learned-control and stochastic controls",
        evidence_role="Neural/MCTS causal and stability evidence",
        verification_strength="same-budget controls, held-out splits, independent seeds, semantic checks",
        resource_dimensions="score deltas, time/effort deltas, false-skip and bootstrap intervals",
        claim_use="Separates learned ranking, frontier policies, guards, and MCTS controls from representation effects.",
        boundary="Does not claim deep learning alone causes the full resource reduction.",
        required_files=(
            RESULTS / "analysis_search_control_baseline_audit.md",
            RESULTS / "analysis_learned_control_effect_uncertainty.md",
        ),
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def benchmark_rows_by_suite() -> dict[str, dict[str, str]]:
    return {row.get("suite", ""): row for row in read_csv(BENCHMARK_SUMMARY)}


def compute_note(level: str) -> str:
    ultra = read_json(ULTRA_PROFILE_MANIFEST)
    runtime = read_json(RUNTIME_MANIFEST)
    if level.startswith("6.") and ultra:
        n_values = ",".join(str(n) for n in ultra.get("n_values", []))
        return (
            f"ultra_profile_raw_rows={ultra.get('raw_rows', 'missing')}; "
            f"n_values={n_values}; plan_verified={ultra.get('plan_verified_rows', 'missing')}; "
            f"circuit_verified={ultra.get('circuit_verified_rows', 'missing')}"
        )
    if level.startswith("7.") and runtime:
        return f"runtime_envelope_rows={runtime.get('rows', 'missing')}; runtime_status={runtime.get('status_counts', {})}"
    return "none"


def build_rows() -> list[dict[str, str]]:
    suite_rows = benchmark_rows_by_suite()
    manuscript_blob = "\n".join((read_text(AUTHOR_TEX), read_text(ANON_TEX), read_text(ACM_TEX)))
    rows: list[dict[str, str]] = []
    for spec in LADDER:
        suite = suite_rows.get(spec.source_suite or "", {})
        missing_files = [rel(path) for path in spec.required_files if not path.exists()]
        status = "pass"
        if not suite:
            status = "needs revision"
        elif suite.get("status") != "pass":
            status = "needs revision"
        elif missing_files:
            status = "needs revision"
        rows.append(
            {
                "level": spec.level,
                "evidence_role": spec.evidence_role,
                "n_scope": suite.get("n_scope", "missing"),
                "instances": suite.get("instances", "0"),
                "raw_rows": suite.get("raw_rows", "0"),
                "verified_rows": suite.get("verified_rows", "0"),
                "verification_strength": spec.verification_strength,
                "resource_dimensions": spec.resource_dimensions,
                "claim_use": spec.claim_use,
                "boundary": spec.boundary,
                "source_suite": spec.source_suite or "none",
                "compute_note": compute_note(spec.level),
                "status": status,
                "missing_files": "; ".join(missing_files) if missing_files else "none",
            }
        )

    table_anchor = "\\input{tables/experimental_evidence_ladder}"
    integration_missing = [
        name
        for name, ok in (
            ("author", table_anchor in read_text(AUTHOR_TEX)),
            ("anonymous", table_anchor in read_text(ANON_TEX)),
            ("acm_tqc", table_anchor in read_text(ACM_TEX)),
        )
        if not ok
    ]
    rows.append(
        {
            "level": "8. Manuscript integration",
            "evidence_role": "Experimental-strength ladder is visible in all submission variants",
            "n_scope": "not applicable",
            "instances": "0",
            "raw_rows": "0",
            "verified_rows": "0",
            "verification_strength": "source anchor check",
            "resource_dimensions": "not applicable",
            "claim_use": "Places benchmark scale, semantic strength, and boundaries before result tables.",
            "boundary": "Integration evidence is not a new experiment.",
            "source_suite": "none",
            "compute_note": "none",
            "status": "pass" if not integration_missing else "needs revision",
            "missing_files": "; ".join(integration_missing) if integration_missing else "none",
        }
    )
    return rows


def latex_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = {
        "Resource-NMCTS": r"\method{}",
        "ANF": r"\anf{}",
        "MCTS": r"\mcts{}",
        "Rz": r"\rz{}",
        "T-depth": r"T-depth",
        "n=3--6": r"$n=3$--$6$",
        "n=3--18": r"$n=3$--$18$",
        "n=3--40": r"$n=3$--$40$",
        "n=4--5": r"$n=4$--$5$",
        "n=20--64": r"$n=20$--$64$",
        "n=21--30": r"$n=21$--$30$",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "level",
        "evidence_role",
        "n_scope",
        "instances",
        "raw_rows",
        "verified_rows",
        "verification_strength",
        "resource_dimensions",
        "claim_use",
        "boundary",
        "source_suite",
        "compute_note",
        "status",
        "missing_files",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    experiment_rows = [row for row in rows if not row["level"].startswith("8.")]
    total_raw = sum(int(row["raw_rows"]) for row in experiment_rows)
    total_verified = sum(int(row["verified_rows"]) for row in experiment_rows)
    lines = [
        "# Experimental Evidence Ladder",
        "",
        "This audit ranks the experiment package by verification strength and claim use.  It is derived from existing benchmark-suite summaries and manifests.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Aggregate ladder coverage",
            "",
            f"- experiment raw rows represented: {total_raw}",
            f"- experiment verified rows represented: {total_verified}",
            "",
            "| level | role | n scope | instances | raw rows | verified rows | verification strength | claim use | boundary | status |",
            "|---|---|---:|---:|---:|---:|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {level} | {evidence_role} | {n_scope} | {instances} | {raw_rows} | {verified_rows} | {verification_strength} | {claim_use} | {boundary} | {status} |".format(
                **row
            )
        )
    lines.extend(["", "## Source suites", ""])
    for row in rows:
        lines.append(f"- **{row['level']}**: {row['source_suite']}; compute note: `{row['compute_note']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.08\linewidth}>{\raggedleft\arraybackslash}p{0.07\linewidth}>{\raggedleft\arraybackslash}p{0.08\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Level & Evidence role & Scope & Items & Checked & Verification strength & Claim use / boundary \\",
        r"\midrule",
    ]
    for row in rows:
        claim_boundary = f"{row['claim_use']} Boundary: {row['boundary']}"
        lines.append(
            "{} & {} & {} & {} & {} & {} & {} \\\\".format(
                latex_cell(row["level"]),
                latex_cell(row["evidence_role"]),
                latex_cell(row["n_scope"]),
                row["instances"],
                row["verified_rows"],
                latex_cell(row["verification_strength"]),
                latex_cell(claim_boundary),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    experiment_rows = [row for row in rows if not row["level"].startswith("8.")]
    author = read_text(AUTHOR_TEX)
    anon = read_text(ANON_TEX)
    acm = read_text(ACM_TEX)
    benchmark_manifest = read_json(BENCHMARK_MANIFEST)
    function_manifest = read_json(FUNCTION_DIVERSITY_MANIFEST)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "experiment_levels": len(experiment_rows),
        "raw_rows": sum(int(row["raw_rows"]) for row in experiment_rows),
        "verified_rows": sum(int(row["verified_rows"]) for row in experiment_rows),
        "n_scopes": sorted({row["n_scope"] for row in experiment_rows}),
        "semantic_bridge_present": any(row["source_suite"] == "Complete truth-table bridge slices" for row in rows),
        "ultra_scale_present": any(row["source_suite"] == "Large symbolic term-set scaling" for row in rows),
        "benchmark_suite_manifest_rows": benchmark_manifest.get("rows", "missing"),
        "function_diversity_rows": function_manifest.get("rows", "missing"),
        "table": "paper_latex/tables/experimental_evidence_ladder.tex",
        "table_anchor_present": "tab:experimental-evidence-ladder" in author,
        "anonymous_table_anchor_present": "tab:experimental-evidence-ladder" in anon,
        "acm_table_anchor_present": "tab:experimental-evidence-ladder" in acm,
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
