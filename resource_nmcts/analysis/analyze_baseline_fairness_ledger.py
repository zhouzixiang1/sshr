#!/usr/bin/env python3
"""Build a baseline fairness ledger for reviewer-facing comparisons.

The existing comparison scorecards answer what the method beats and where it
does not.  This ledger answers a different reviewer question: whether each
comparison is being made under a clearly stated input, verifier, resource, and
claim-scope contract.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANON_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"

COMPARABILITY = RESULTS / "summary_baseline_comparability_audit.csv"
EVIDENCE = RESULTS / "summary_comparison_evidence_matrix.csv"
COUNTERPOINT = RESULTS / "summary_counterpoint_claim_boundary.csv"
SEARCH_CONTROL = RESULTS / "summary_search_control_baseline_audit.csv"

SUMMARY = RESULTS / "summary_baseline_fairness_ledger.csv"
ANALYSIS = RESULTS / "analysis_baseline_fairness_ledger.md"
MANIFEST = RESULTS / "manifest_baseline_fairness_ledger.json"
TABLE = TABLES / "baseline_fairness_ledger.tex"


@dataclass(frozen=True)
class LedgerSpec:
    family: str
    role: str
    evidence_blocks: tuple[str, ...]
    comparability_key: str
    input_contract: str
    verifier_contract: str
    resource_contract: str
    fairness_contract: str
    supported_claim: str
    boundary: str
    required_artifacts: tuple[Path, ...]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def row_by(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    for row in rows:
        if row.get(key) == value:
            return row
    return {}


def truthy(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered in {"1", "true", "yes", "y", "pass", "passed"} or (
        "verified" in lowered and "not verified" not in lowered
    )


def falsey(value: str) -> bool:
    return value.strip().lower() in {"", "0", "false", "no", "n", "none"}


def inspect_raw(path: Path) -> tuple[int, int, int, int]:
    """Return total, usable, rows_with_verifier_flags, verified rows."""
    if not path.exists():
        return (0, 0, 0, 0)
    rows = read_rows(path)
    verifier_columns = (
        "correct",
        "abc_blif_correct",
        "source_blif_correct",
        "verilog_correct",
        "permutation_checked",
        "truth_verified",
        "anf_verified",
        "circuit_anf_verified",
    )
    total = len(rows)
    usable = 0
    flagged = 0
    verified = 0
    for row in rows:
        skipped = row.get("skipped", "")
        error = row.get("error", "")
        if falsey(skipped) and falsey(error):
            usable += 1
        present = [column for column in verifier_columns if row.get(column, "") != ""]
        if present:
            flagged += 1
            if all(truthy(row.get(column, "")) for column in present):
                verified += 1
    return (total, usable, flagged, verified)


def source_paths(blocks: tuple[str, ...], evidence_rows: list[dict[str, str]]) -> list[Path]:
    paths: list[Path] = []
    for block in blocks:
        row = row_by(evidence_rows, "evidence_block", block)
        sources = row.get("sources", "")
        for source in sources.split(";"):
            source = source.strip()
            if source.startswith("results/"):
                paths.append(THIS_DIR / source)
    return sorted(set(paths))


def raw_integrity(paths: list[Path]) -> tuple[str, bool]:
    totals = [inspect_raw(path) for path in paths if path.name.startswith("raw_")]
    missing = [path for path in paths if not path.exists()]
    total_rows = sum(item[0] for item in totals)
    usable_rows = sum(item[1] for item in totals)
    flagged_rows = sum(item[2] for item in totals)
    verified_rows = sum(item[3] for item in totals)
    ok = not missing and (total_rows == 0 or flagged_rows == 0 or verified_rows == flagged_rows)
    text = (
        f"source_files={len(paths)}; missing={len(missing)}; "
        f"raw_rows={total_rows}; usable_rows={usable_rows}; "
        f"verified_flags={verified_rows}/{flagged_rows}"
    )
    return text, ok


def evidence_text(blocks: tuple[str, ...], evidence_rows: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for block in blocks:
        row = row_by(evidence_rows, "evidence_block", block)
        if row:
            parts.append(f"{block}: {row.get('verified_rows', 'missing')}")
        else:
            parts.append(f"{block}: missing")
    return "; ".join(parts)


def comparability_text(key: str, rows: list[dict[str, str]]) -> tuple[str, str, str]:
    row = row_by(rows, "baseline_family", key)
    if not row:
        return ("missing", "missing", "missing")
    return (
        row.get("task_alignment", "missing"),
        row.get("fairness_control", "missing"),
        row.get("residual_risk", "missing"),
    )


def specs() -> list[LedgerSpec]:
    return [
        LedgerSpec(
            family="Same-task Boolean-oracle baselines",
            role="primary benchmark",
            evidence_blocks=("Internal logical baselines", "Exported SSHR/ABC/BDD extension"),
            comparability_key="Direct algebraic and ESOP baselines",
            input_contract="Matched truth-table Boolean functions in the bit-flip oracle form.",
            verifier_contract="Complete truth-table correctness on small functions plus paired-name filtering.",
            resource_contract="Common logical T, CNOT, depth, gate, peak-ancilla, and weighted-score model.",
            fairness_contract="Use this row for headline T-count and weighted-score claims only.",
            supported_claim="Lower T-count and weighted score on matched logical bit-flip oracle rows.",
            boundary="No universal CNOT, depth, line-count, mapped-depth, or global-optimality claim.",
            required_artifacts=(RESULTS / "raw_traditional_resource.csv", RESULTS / "raw_external_traditional_resource_n6.csv"),
        ),
        LedgerSpec(
            family="SSHR geometric counterpoint",
            role="CNOT-oriented small-function baseline",
            evidence_blocks=("Internal logical baselines", "Exported SSHR/ABC/BDD extension"),
            comparability_key="SSHR-H and SSHR-I",
            input_contract="The same n<=6 Boolean functions are compared against SSHR-H and SSHR-I rows where available.",
            verifier_contract="SSHR rows are consumed only after row-level correctness and timeout accounting.",
            resource_contract="Score/T comparisons are reported separately from SSHR's CNOT-centered objective.",
            fairness_contract="Treat SSHR as a strong CNOT counterpoint, not as the proposed method's parent algorithm.",
            supported_claim="The proposed search has lower T-count and weighted score while SSHR remains CNOT-competitive.",
            boundary="Do not claim CNOT dominance over SSHR or full reproduction of every SSHR random experiment.",
            required_artifacts=(
                RESULTS / "raw_external_traditional_resource_n6.csv",
                RESULTS / "manifest_sshr_reproduction_scope_audit.json",
                RESULTS / "manifest_sshr_table8_candidate_counts.json",
            ),
        ),
        LedgerSpec(
            family="External logic-network probes",
            role="toolchain stress test",
            evidence_blocks=(
                "ROS-style LUT proxy",
                "mockturtle KLUT-to-XAG probe",
                "Caterpillar XAG API probe",
                "CirKit AIG/MC probe",
            ),
            comparability_key="ROS-style LUT and XAG/AIG/API probes",
            input_contract="Exported truth tables or ANF/XAG/AIG/LUT encodings of the same benchmark functions.",
            verifier_contract="Tool outputs are checked through truth-table, BLIF, Verilog, or API readback where available.",
            resource_contract="Logical-network resource estimates are scored with the same coefficients but not routed.",
            fairness_contract="Use as an external logical stress test against mature network optimizers.",
            supported_claim="The T/score advantage is not only an artifact of self-written algebraic baselines.",
            boundary="Not a full ROS SAT garbage-management, reversible-emission, or hardware-mapped comparison.",
            required_artifacts=(
                RESULTS / "raw_ros_lut_proxy_best.csv",
                RESULTS / "raw_mockturtle_xag_probe.csv",
                RESULTS / "raw_caterpillar_xag_api_best.csv",
                RESULTS / "raw_cirkit_aig_probe.csv",
            ),
        ),
        LedgerSpec(
            family="Published tiny-function optima",
            role="optimum-library boundary",
            evidence_blocks=("Published STG optimum-library counterpoint",),
            comparability_key="Published STG optimum-library counterpoint",
            input_contract="Public n=4/5 STG spectral representatives are matched by truth-table hex.",
            verifier_contract="Rows are checked as a published-counterpoint slice, not as a reproduced optimizer.",
            resource_contract="T-count, T-depth, and qubit-count optima are kept separate from the paper score.",
            fairness_contract="Use as a non-win boundary against precomputed tiny-function optima.",
            supported_claim="The method improves local direct baselines on this slice but does not beat STG optima.",
            boundary="No claim of beating published STG T-count, T-depth, or qubit optima.",
            required_artifacts=(RESULTS / "raw_stg_published_benchmark.csv", RESULTS / "summary_stg_published_benchmark.csv"),
        ),
        LedgerSpec(
            family="RevKit exact-oracle probe",
            role="exact reversible counterpoint",
            evidence_blocks=("Legacy RevKit CLI exact oracle",),
            comparability_key="Legacy RevKit CLI exact-oracle portfolio",
            input_contract="Each function is embedded as the exact permutation (x,y)->(x,y xor f(x)).",
            verifier_contract="RevKit portfolio rows are checked through the exact-oracle permutation route.",
            resource_contract="T/score are compared while line-count and derived CNOT/depth remain visible.",
            fairness_contract="Use as a genuine reversible-synthesis probe, not a hardware-mapped compiler run.",
            supported_claim="A reversible-synthesis portfolio does not remove the T-count/score advantage.",
            boundary="Do not claim lower auxiliary-line count, routed depth, or final mapped Clifford+T dominance.",
            required_artifacts=(RESULTS / "raw_revkit_cli_multiflow_traditional.csv",),
        ),
        LedgerSpec(
            family="Phase/Rz transfer branch",
            role="logical phase proxy",
            evidence_blocks=("RevKit phase/Rz branch", "Learned phase pruning"),
            comparability_key="Phase/Rz baselines and learned shortlist",
            input_contract="The same Boolean functions are evaluated as phase-oracle or affine-FPRM instances.",
            verifier_contract="Phase rows are verified up to global phase and shortlist rows against exact scoring.",
            resource_contract="Rz/phase proxy costs are reported separately from the bit-flip oracle claim.",
            fairness_contract="Use only as transfer evidence for the search framing.",
            supported_claim="Affine search and learned shortlist pruning help a related verified phase/Rz proxy.",
            boundary="Not a final approximate-rotation or Clifford+T sequence-synthesis result.",
            required_artifacts=(RESULTS / "raw_phase_parity_affine.csv", RESULTS / "raw_phase_affine_policy_rank_diverse.csv"),
        ),
        LedgerSpec(
            family="AI/search-control ablations",
            role="causal-control evidence",
            evidence_blocks=(),
            comparability_key="AI/search-control ablations",
            input_contract="Ablations reuse the same benchmark names, budgets, or candidate pools when applicable.",
            verifier_contract="Learned controls are accepted only through guarded rows, random controls, or disjoint held-out checks with explicit uncertainty gates.",
            resource_contract="Report quality and planning-time effects separately.",
            fairness_contract="Use to attribute bounded gains to search control, ranking, and gating.",
            supported_claim="MCTS and Pareto selection add bounded quality gains; fitted-Q control reduces optional Pareto effort at explicit score regret.",
            boundary="Do not claim deep reinforcement learning alone causes the full resource reduction or dominates always-on Pareto score.",
            required_artifacts=(
                RESULTS / "analysis_search_control_baseline_audit.md",
                RESULTS / "analysis_bitflip_random_prior_control.md",
                RESULTS / "analysis_frontier_random_depth_control.md",
                RESULTS / "analysis_mcts_budget_policy.md",
                RESULTS / "manifest_mcts_budget_policy.json",
                SEARCH_CONTROL,
            ),
        ),
        LedgerSpec(
            family="Large-scale correctness envelope",
            role="scalability verification",
            evidence_blocks=("High-dimensional frontier search", "Complete truth-table bridges"),
            comparability_key="High-dimensional symbolic and bridge checks",
            input_contract="Generated large-n term-set functions and bridge functions exercise the same emitted oracle semantics.",
            verifier_contract="Symbolic ANF/circuit verification covers scale rows; n=21--30 bridges add full truth-table checks.",
            resource_contract="Logical resources are reported without hardware routing or noise models.",
            fairness_contract="Use to support logical-layer scaling, not optimality.",
            supported_claim="The emitter and verifier remain effective beyond the n<=6 truth-table benchmark slice.",
            boundary="Not exhaustive high-dimensional truth-table benchmarking or global optimality evidence.",
            required_artifacts=(
                RESULTS / "raw_screen_scale_depth_frontier_terms.csv",
                RESULTS / "raw_screen_scale_ultra_scale64_terms.csv",
                RESULTS / "raw_truth_bridge_n30_terms.csv",
            ),
        ),
        LedgerSpec(
            family="Trade-off and sensitivity rows",
            role="non-dominance boundary",
            evidence_blocks=(),
            comparability_key="Trade-off and resource-sensitivity audits",
            input_contract="Matched-function resource vectors are audited independently of weighted score.",
            verifier_contract="Dominance and sensitivity rows are derived from verified raw comparison tables.",
            resource_contract="Four-resource dominance excludes weighted score; sensitivity sweeps vary score coefficients.",
            fairness_contract="Use to prevent one weighted-score metric from becoming a universal leaderboard.",
            supported_claim="The method occupies a strong T/score point with explicit CNOT/depth/ancilla trade-offs.",
            boundary="No complete Pareto dominance or hardware-level dominance claim.",
            required_artifacts=(
                RESULTS / "analysis_multimetric_pareto_tradeoff.md",
                RESULTS / "manifest_resource_weight_sensitivity_audit.json",
                COUNTERPOINT,
            ),
        ),
    ]


def evaluate(spec: LedgerSpec, evidence_rows: list[dict[str, str]], comparability_rows: list[dict[str, str]]) -> dict[str, str]:
    alignment, comparability_control, residual = comparability_text(spec.comparability_key, comparability_rows)
    paths = source_paths(spec.evidence_blocks, evidence_rows)
    all_paths = sorted(set(paths + list(spec.required_artifacts)))
    integrity, raw_ok = raw_integrity(all_paths)
    missing = [path for path in all_paths if not path.exists()]
    coverage = evidence_text(spec.evidence_blocks, evidence_rows) if spec.evidence_blocks else "derived audit rows only"
    comparability_ok = all(
        value.strip() and value.strip().lower() != "missing"
        for value in (alignment, comparability_control, residual)
    )
    status = "pass" if not missing and raw_ok and comparability_ok else "needs revision"
    return {
        "family": spec.family,
        "role": spec.role,
        "status": status,
        "comparability_key": spec.comparability_key,
        "input_contract": spec.input_contract,
        "verifier_contract": spec.verifier_contract,
        "resource_contract": spec.resource_contract,
        "fairness_contract": spec.fairness_contract,
        "coverage": coverage,
        "raw_integrity": integrity,
        "task_alignment": alignment,
        "comparability_control": comparability_control,
        "residual_risk": residual,
        "supported_claim": spec.supported_claim,
        "boundary": spec.boundary,
        "missing_artifacts": "; ".join(str(path.relative_to(THIS_DIR)) for path in missing) if missing else "none",
        "next_action": (
            "Keep this row tied to its verifier/resource/claim-scope contract."
            if status == "pass"
            else "Restore missing raw/derived artifacts or the matching comparability row before relying on this baseline family."
        ),
    }


def latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = {
        "Resource-NMCTS": r"\method{}",
        "Pareto-Resource-NMCTS": r"Pareto-\method{}",
        "ANF": r"\anf{}",
        "FPRM": r"\fprm{}",
        "MCTS": r"\mcts{}",
        "Rz": r"\rz{}",
        "n<=6": r"$n\leq6$",
        "n=21--30": r"$n=21$--$30$",
        "(x,y)->(x,y xor f(x))": r"$(x,y)\mapsto(x,y\oplus f(x))$",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "family",
        "role",
        "status",
        "comparability_key",
        "input_contract",
        "verifier_contract",
        "resource_contract",
        "fairness_contract",
        "coverage",
        "raw_integrity",
        "task_alignment",
        "comparability_control",
        "residual_risk",
        "supported_claim",
        "boundary",
        "missing_artifacts",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Baseline Fairness Ledger",
        "",
        "This ledger records the input, verifier, resource, and claim-scope contract for each comparison family.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| family | role | coverage | raw integrity | supported claim | boundary | status |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {family} | {role} | {coverage} | {raw_integrity} | {supported_claim} | {boundary} | {status} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.21\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.18\linewidth}}",
        r"\toprule",
        r"Family & Input/verifier contract & Evidence coverage & Supported use & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} {} & {} & {} & {} \\\\".format(
                latex_cell(row["family"]),
                latex_cell(row["input_contract"]),
                latex_cell(row["verifier_contract"]),
                latex_cell(row["coverage"]),
                latex_cell(row["supported_claim"]),
                latex_cell(row["boundary"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    manuscript_text = "\n".join(read_text(path) for path in (AUTHOR_PAPER, ANON_PAPER, ACM_PAPER))
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": status_counts,
        "needs_revision_count": status_counts.get("needs revision", 0),
        "families": [row["family"] for row in rows],
        "roles": sorted({row["role"] for row in rows}),
        "table": "paper_latex/tables/baseline_fairness_ledger.tex",
        "table_anchor_present": "tab:baseline-fairness-ledger" in manuscript_text,
        "raw_integrity_rows": [row["raw_integrity"] for row in rows],
        "comparability_key_by_family": {spec.family: spec.comparability_key for spec in specs()},
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    evidence_rows = read_rows(EVIDENCE)
    comparability_rows = read_rows(COMPARABILITY)
    rows = [evaluate(spec, evidence_rows, comparability_rows) for spec in specs()]
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {SUMMARY.relative_to(THIS_DIR)}")
    print(f"wrote {ANALYSIS.relative_to(THIS_DIR)}")
    print(f"wrote {MANIFEST.relative_to(THIS_DIR)}")
    print(f"wrote {TABLE.relative_to(THIS_DIR)}")


if __name__ == "__main__":
    main()
