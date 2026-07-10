#!/usr/bin/env python3
"""Audit the SSHR reproduction scope used by the submission.

The manuscript uses SSHR as an important CNOT-oriented counterpoint, but the
claim must stay narrower than a full re-execution of every table from Zheng et
al.  This audit makes that boundary explicit and machine-checkable from the
paper-facing payload: which SSHR rows are generated and verified, which paper
reference data or source anchors are present when the full repository is
available, and which stronger reproduction claims remain outside the current
logical-layer package.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
SSHR_DIR = REPO_ROOT / "sshr"
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
ANONYMOUS_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex"
ACM_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_acm_tqc.tex"
REFERENCES = THIS_DIR / "paper_latex" / "references.bib"
DELIVERABLE = THIS_DIR / "DELIVERABLE_zh.md"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"

RAW_TRADITIONAL = RESULTS / "raw_traditional_resource.csv"
MANIFEST_TRADITIONAL = RESULTS / "manifest_traditional_resource.json"
RAW_EXTERNAL_N4 = RESULTS / "raw_external_traditional_resource_n4.csv"
RAW_EXTERNAL_N6 = RESULTS / "raw_external_traditional_resource_n6.csv"
MANIFEST_EXTERNAL_N4 = RESULTS / "manifest_external_traditional_resource_n4.json"
MANIFEST_EXTERNAL_N6 = RESULTS / "manifest_external_traditional_resource_n6.json"
SUMMARY_EXACT_FPRM = RESULTS / "summary_exact_fprm_dp.csv"
EXACT_FPRM_ANALYSIS = RESULTS / "analysis_exact_fprm_dp.md"
SUMMARY_EXACT_XAG = RESULTS / "summary_exact_xag_mc.csv"
RESOURCE_WEIGHT_ANALYSIS = RESULTS / "analysis_resource_weight_sensitivity_audit.md"
RESOURCE_WEIGHT_MANIFEST = RESULTS / "manifest_resource_weight_sensitivity_audit.json"
MULTIMETRIC_ANALYSIS = RESULTS / "analysis_multimetric_pareto_tradeoff.md"
COMPARISON_ANSWER = RESULTS / "analysis_comparison_answer_scorecard.md"
COMPARISON_TARGET = RESULTS / "analysis_comparison_target_validity_audit.md"
THREATS_VALIDITY = RESULTS / "analysis_threats_to_validity_audit.md"
CLAIM_SCOPE = RESULTS / "manifest_claim_scope_lint.json"

SSHR_README = SSHR_DIR / "README.md"
SSHR_RUN_TABLES = SSHR_DIR / "experiments" / "run_tables.py"
SSHR_PAPER_DATA = SSHR_DIR / "paper_data.py"
SSHR_H_IMPL = SSHR_DIR / "sshr_h.py"
SSHR_I_IMPL = SSHR_DIR / "sshr_i.py"
SSHR_ENUM = SSHR_DIR / "parallelotope_enum.py"
TABLE8_RAW = RESULTS / "raw_sshr_table8_candidate_counts.csv"
TABLE8_SUMMARY = RESULTS / "summary_sshr_table8_candidate_counts.csv"
TABLE8_ANALYSIS = RESULTS / "analysis_sshr_table8_candidate_counts.md"
TABLE8_MANIFEST = RESULTS / "manifest_sshr_table8_candidate_counts.json"
TABLE8_LATEX = TABLES / "sshr_table8_candidate_counts.tex"

TABLE_VIII_COUNTS = {3: 49, 4: 257, 5: 1539, 6: 10299, 7: 75905, 8: 609441}


@dataclass(frozen=True)
class CsvCheck:
    path: Path
    method: str | None = None
    expected_rows: int | None = None
    require_correct: bool = False


@dataclass(frozen=True)
class JsonCheck:
    path: Path
    key: str
    expected: object


@dataclass(frozen=True)
class AuditSpec:
    item: str
    coverage: str
    current_evidence: str
    files: tuple[Path, ...]
    tokens: tuple[str, ...]
    csv_checks: tuple[CsvCheck, ...]
    json_checks: tuple[JsonCheck, ...]
    supported_claim: str
    excluded_claim: str


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(THIS_DIR))
    except ValueError:
        try:
            return str(path.relative_to(REPO_ROOT))
        except ValueError:
            return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def token_hits(files: tuple[Path, ...], tokens: tuple[str, ...]) -> tuple[int, list[str]]:
    combined = "\n".join(read_text(path) for path in files)
    missing = [token for token in tokens if token not in combined]
    return len(tokens) - len(missing), missing


def check_csv(check: CsvCheck) -> tuple[bool, str]:
    rows = read_csv(check.path)
    if not rows:
        return False, f"{rel(check.path)} missing_or_empty"
    if check.method is not None:
        rows = [row for row in rows if row.get("method") == check.method]
    row_ok = check.expected_rows is None or len(rows) == check.expected_rows
    correct_ok = True
    incorrect = 0
    if check.require_correct:
        for row in rows:
            if str(row.get("correct", "")).lower() not in {"true", "1", "yes"}:
                incorrect += 1
        correct_ok = incorrect == 0
    detail = f"{rel(check.path)}"
    if check.method is not None:
        detail += f"::{check.method}"
    detail += f" rows={len(rows)}"
    if check.expected_rows is not None:
        detail += f"/{check.expected_rows}"
    if check.require_correct:
        detail += f", incorrect={incorrect}"
    return row_ok and correct_ok, detail


def check_json(check: JsonCheck) -> tuple[bool, str]:
    manifest = read_json(check.path)
    if not manifest:
        return False, f"{rel(check.path)} missing_or_invalid"
    actual = manifest.get(check.key)
    return actual == check.expected, f"{rel(check.path)}::{check.key}={actual}"


def source_tree_available() -> bool:
    return all(path.exists() for path in (SSHR_README, SSHR_RUN_TABLES, SSHR_PAPER_DATA, SSHR_H_IMPL, SSHR_I_IMPL))


def table_viii_source_check() -> tuple[bool, str]:
    if not source_tree_available():
        return True, "sshr_source_tree_not_packaged; payload uses recorded Table VIII counts and paper-facing baseline rows"
    text = "\n".join(read_text(path) for path in (SSHR_PAPER_DATA, SSHR_RUN_TABLES, SSHR_ENUM, SSHR_README))
    missing = [str(value) for value in TABLE_VIII_COUNTS.values() if str(value) not in text]
    tokens = ["TABLE_VIII_COUNTS", "run_table8", "enumerate_parallelotopes"]
    missing_tokens = [token for token in tokens if token not in text]
    ok = not missing and not missing_tokens
    return ok, f"source_tree_available=True; table_viii_counts={TABLE_VIII_COUNTS}; missing_counts={missing or 'none'}; missing_tokens={missing_tokens or 'none'}"


def table_viii_reproduction_check() -> tuple[bool, str]:
    manifest = read_json(TABLE8_MANIFEST)
    raw_rows = read_csv(TABLE8_RAW)
    summary_rows = read_csv(TABLE8_SUMMARY)
    analysis_exists = TABLE8_ANALYSIS.exists()
    table_exists = TABLE8_LATEX.exists()
    source_ok, source_detail = table_viii_source_check()
    all_match = bool(manifest.get("all_match", False)) if manifest else False
    rows = int(manifest.get("rows", -1)) if manifest else -1
    max_n = int(manifest.get("max_n", -1)) if manifest else -1
    max_count = int(manifest.get("max_sshr_count", -1)) if manifest else -1
    raw_match_count = sum(1 for row in raw_rows if str(row.get("matches_reference", "")).lower() == "true")
    ok = (
        source_ok
        and all_match
        and rows == 6
        and max_n == 8
        and max_count == TABLE_VIII_COUNTS[8]
        and len(raw_rows) == 6
        and raw_match_count == 6
        and len(summary_rows) == 1
        and analysis_exists
        and table_exists
    )
    detail = (
        f"{source_detail}; table8_raw_rows={len(raw_rows)}; raw_matches={raw_match_count}; "
        f"manifest_rows={rows}; all_match={all_match}; max_n={max_n}; max_count={max_count}; "
        f"summary_rows={len(summary_rows)}; analysis_exists={analysis_exists}; table_exists={table_exists}"
    )
    return ok, detail


def specs() -> list[AuditSpec]:
    return [
        AuditSpec(
            item="SSHR literature and method boundary",
            coverage="covered",
            current_evidence="The manuscript cites SSHR, states that the proposed method does not search parallelotope candidates, and uses SSHR as a CNOT-oriented small-function baseline.",
            files=(PAPER, ANONYMOUS_PAPER, ACM_PAPER, REFERENCES, COMPARISON_TARGET),
            tokens=("zheng2025sshr", "parallelotope", "CNOT-oriented", "not an SSHR", "small-function"),
            csv_checks=(),
            json_checks=(),
            supported_claim="SSHR is a relevant structured baseline for small Boolean-function oracle synthesis.",
            excluded_claim="The proposed method is not an SSHR variant and does not inherit SSHR's CNOT-only objective.",
        ),
        AuditSpec(
            item="SSHR Table VIII candidate-space reproduction",
            coverage="covered",
            current_evidence="The package reruns the local SSHR parallelotope enumerator on full n=3..8 hypercubes and matches all six Table VIII candidate-space counts, including n=8 -> 609441.",
            files=(TABLE8_RAW, TABLE8_SUMMARY, TABLE8_ANALYSIS, TABLE8_MANIFEST, TABLE8_LATEX, DELIVERABLE, PAPER),
            tokens=("SSHR", "parallelotope", "candidate-space", "609441"),
            csv_checks=(),
            json_checks=(),
            supported_claim="The paper can explain why SSHR's search space is a CNOT-oriented parallelotope counterpoint rather than the proposed ANF/FPRM action space.",
            excluded_claim="This count reproduction does not rerun SSHR-I Gurobi tables or every published SSHR random benchmark.",
        ),
        AuditSpec(
            item="SSHR-H same-task baseline rows",
            coverage="covered",
            current_evidence="The traditional bit-flip benchmark includes 177 correct SSHR-H rows and the manuscript keeps SSHR-H visible as the best mean-CNOT baseline in the traditional table.",
            files=(RAW_TRADITIONAL, MANIFEST_TRADITIONAL, PAPER, ANONYMOUS_PAPER, ACM_PAPER),
            tokens=("sshr_h", "SSHR-H", "lowest mean CNOT", "tab:traditional"),
            csv_checks=(CsvCheck(RAW_TRADITIONAL, "sshr_h", 177, True),),
            json_checks=(JsonCheck(MANIFEST_TRADITIONAL, "functions", 177),),
            supported_claim="Resource-NMCTS is compared with a same-function SSHR-H implementation on all traditional benchmark functions.",
            excluded_claim="The SSHR-H row is not evidence of CNOT-only dominance by the proposed method.",
        ),
        AuditSpec(
            item="SSHR-I CNOT/T extension rows",
            coverage="partial",
            current_evidence="The external n<=6 extension includes SSHR-I CNOT-objective and T-objective rows for the same 177 functions with correctness checks and explicit timeout metadata.",
            files=(RAW_EXTERNAL_N6, MANIFEST_EXTERNAL_N6, PAPER, ANONYMOUS_PAPER, ACM_PAPER),
            tokens=("external_sshr_i_cnot", "external_sshr_i_t", "SSHR-I", "timeout"),
            csv_checks=(
                CsvCheck(RAW_EXTERNAL_N6, "external_sshr_i_cnot", 177, True),
                CsvCheck(RAW_EXTERNAL_N6, "external_sshr_i_t", 177, True),
            ),
            json_checks=(
                JsonCheck(MANIFEST_EXTERNAL_N6, "functions", 177),
                JsonCheck(MANIFEST_EXTERNAL_N6, "max_ilp_n", 6),
                JsonCheck(MANIFEST_EXTERNAL_N6, "timeout", 10.0),
            ),
            supported_claim="The manuscript can use SSHR-I as a time-limited CNOT/T-oriented counterpoint on the matched traditional slice.",
            excluded_claim="The n<=6 extension is not an exact certificate for all SSHR-I random-paper settings.",
        ),
        AuditSpec(
            item="n<=4 exact/pilot SSHR-I cross-check",
            coverage="covered",
            current_evidence="The n<=4 external pilot records 72 functions and 216 SSHR-H/SSHR-I rows, and exact small-slice analyses include SSHR-I references as counterpoints.",
            files=(RAW_EXTERNAL_N4, MANIFEST_EXTERNAL_N4, SUMMARY_EXACT_FPRM, EXACT_FPRM_ANALYSIS, SUMMARY_EXACT_XAG, PAPER),
            tokens=("external_sshr_i_cnot", "external_sshr_i_t", "Exact FPRM-DP Analysis", "SSHR-I"),
            csv_checks=(
                CsvCheck(RAW_EXTERNAL_N4, "external_sshr_i_cnot", 72, True),
                CsvCheck(RAW_EXTERNAL_N4, "external_sshr_i_t", 72, True),
            ),
            json_checks=(
                JsonCheck(MANIFEST_EXTERNAL_N4, "functions", 72),
                JsonCheck(MANIFEST_EXTERNAL_N4, "rows", 216),
                JsonCheck(MANIFEST_EXTERNAL_N4, "max_ilp_n", 4),
            ),
            supported_claim="The small-function exact slice has a harder SSHR-I sanity check than the broad n<=6 timed extension.",
            excluded_claim="Even this slice is a counterpoint under the paper's logical resource projection, not a proof of global reversible optimality.",
        ),
        AuditSpec(
            item="SSHR tradeoff in resource-weight sensitivity",
            coverage="covered",
            current_evidence="The resource-weight audit explicitly keeps SSHR-H and SSHR-I CNOT-only losses visible while showing paper-score and T-score advantages.",
            files=(RESOURCE_WEIGHT_ANALYSIS, RESOURCE_WEIGHT_MANIFEST, MULTIMETRIC_ANALYSIS, PAPER),
            tokens=("Pareto vs SSHR-H", "Pareto vs SSHR-I CNOT", "CNOT-only", "43/128/6", "0/168/9"),
            csv_checks=(),
            json_checks=(JsonCheck(RESOURCE_WEIGHT_MANIFEST, "needs_revision_count", 0),),
            supported_claim="The proposed method improves T-count and weighted resource profiles against SSHR while preserving the CNOT-only counterexample.",
            excluded_claim="Weighted-score wins cannot be rewritten as all-metric or CNOT-only SSHR dominance.",
        ),
        AuditSpec(
            item="Comparison and claim-boundary integration",
            coverage="covered",
            current_evidence="Comparison answer, target-validity, threats-to-validity, and claim-scope gates all mark SSHR as a CNOT counterpoint rather than the whole comparison target.",
            files=(COMPARISON_ANSWER, COMPARISON_TARGET, THREATS_VALIDITY, PAPER),
            tokens=("SSHR", "CNOT counterpoint", "not treated as the whole story", "not that \\method{} dominates every metric"),
            csv_checks=(),
            json_checks=(JsonCheck(CLAIM_SCOPE, "unresolved_count", 0),),
            supported_claim="The manuscript's SSHR comparison is meaningful and bounded by explicit claim-scope checks.",
            excluded_claim="No paper-facing text may claim full SSHR replacement, universal optimality, or hardware-mapped dominance.",
        ),
        AuditSpec(
            item="Reviewer payload visibility",
            coverage="covered",
            current_evidence="The submission package exposes the comparison role, reviewer concern brief, and artifact guide so a reviewer can locate SSHR rows and their boundary quickly.",
            files=(
                SUBMISSION_PACKAGE / "artifact_reproduction_guide.md",
                SUBMISSION_PACKAGE / "reviewer_concern_brief.md",
                SUBMISSION_PACKAGE / "README.md",
                PAPER,
            ),
            tokens=("SSHR", "Direct ANF, ESOP, BDD/ABC, SSHR", "comparison", "logical-layer"),
            csv_checks=(),
            json_checks=(),
            supported_claim="The uploaded artifact makes the SSHR comparison and its limited role findable without reading implementation history.",
            excluded_claim="Support-package visibility does not add a new SSHR random-table rerun.",
        ),
    ]


def evaluate(spec: AuditSpec) -> dict[str, str]:
    missing_files = [rel(path) for path in spec.files if not path.exists()]
    hits, missing_tokens = token_hits(spec.files, spec.tokens)
    csv_results = [check_csv(check) for check in spec.csv_checks]
    json_results = [check_json(check) for check in spec.json_checks]
    table_viii_ok = True
    table_viii_detail = ""
    if spec.item == "SSHR Table VIII candidate-space reproduction":
        table_viii_ok, table_viii_detail = table_viii_reproduction_check()
    status = (
        "pass"
        if not missing_files
        and hits == len(spec.tokens)
        and all(ok for ok, _ in csv_results)
        and all(ok for ok, _ in json_results)
        and table_viii_ok
        else "needs revision"
    )
    evidence_parts = [
        f"files_missing={missing_files or 'none'}",
        f"tokens={hits}/{len(spec.tokens)}",
        f"missing_tokens={missing_tokens or 'none'}",
    ]
    if csv_results:
        evidence_parts.append("csv=" + "; ".join(detail for _, detail in csv_results))
    if json_results:
        evidence_parts.append("json=" + "; ".join(detail for _, detail in json_results))
    if table_viii_detail:
        evidence_parts.append(table_viii_detail)
    return {
        "item": spec.item,
        "audit_status": status,
        "coverage": spec.coverage,
        "current_evidence": spec.current_evidence,
        "evidence": "; ".join(evidence_parts),
        "supported_claim": spec.supported_claim,
        "excluded_claim": spec.excluded_claim,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "audit_status", "coverage", "current_evidence", "evidence", "supported_claim", "excluded_claim"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.25\linewidth}}",
        r"\toprule",
        r"SSHR-facing element & Scope & Current evidence & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["item"]),
                    tex_escape(row["coverage"]),
                    tex_escape(row["current_evidence"]),
                    tex_escape(row["excluded_claim"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = {status: sum(1 for row in rows if row["audit_status"] == status) for status in sorted({row["audit_status"] for row in rows})}
    coverage_counts = {status: sum(1 for row in rows if row["coverage"] == status) for status in sorted({row["coverage"] for row in rows})}
    lines = [
        "# SSHR Reproduction Scope Audit",
        "",
        "This audit records which SSHR-facing evidence is reproduced, source-anchored, or deliberately bounded in the current logical-layer submission package.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(status_counts):
        lines.append(f"- {status}: {status_counts[status]}")
    lines.extend(["", "## Coverage counts", ""])
    for status in sorted(coverage_counts):
        lines.append(f"- {status}: {coverage_counts[status]}")
    lines.extend(
        [
            "",
            "## Scope matrix",
            "",
            "| item | audit status | coverage | current evidence | supported claim | excluded claim |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {item} | {audit_status} | {coverage} | {current_evidence} | {supported_claim} | {excluded_claim} |".format(
                **safe
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = {status: sum(1 for row in rows if row["audit_status"] == status) for status in sorted({row["audit_status"] for row in rows})}
    coverage_counts = {status: sum(1 for row in rows if row["coverage"] == status) for status in sorted({row["coverage"] for row in rows})}
    failures = status_counts.get("needs revision", 0)
    table8_manifest = read_json(TABLE8_MANIFEST)
    paper_text = read_text(PAPER)
    anonymous_text = read_text(ANONYMOUS_PAPER)
    acm_text = read_text(ACM_PAPER)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": status_counts,
        "coverage_counts": coverage_counts,
        "needs_revision_count": failures,
        "source_tree_available": source_tree_available(),
        "table_viii_counts": TABLE_VIII_COUNTS,
        "table_viii_reproduction_rows": table8_manifest.get("rows", "missing") if table8_manifest else "missing",
        "table_viii_reproduction_all_match": table8_manifest.get("all_match", False) if table8_manifest else False,
        "table_viii_reproduction_max_n": table8_manifest.get("max_n", "missing") if table8_manifest else "missing",
        "table_viii_reproduction_max_count": table8_manifest.get("max_sshr_count", "missing") if table8_manifest else "missing",
        "table_viii_reproduction_runtime_policy": table8_manifest.get("runtime_policy", "missing") if table8_manifest else "missing",
        "table_viii_reproduction_table_present": TABLE8_LATEX.exists(),
        "table_anchor_present": "tab:sshr-reproduction-scope" in paper_text,
        "anonymous_table_anchor_present": "tab:sshr-reproduction-scope" in anonymous_text,
        "acm_table_anchor_present": "tab:sshr-reproduction-scope" in acm_text,
        "sshr_methods_checked": ["sshr_h", "external_sshr_h", "external_sshr_i_cnot", "external_sshr_i_t"],
        "outputs": {
            "summary": "results/summary_sshr_reproduction_scope_audit.csv",
            "analysis": "results/analysis_sshr_reproduction_scope_audit.md",
            "manifest": "results/manifest_sshr_reproduction_scope_audit.json",
            "table": "paper_latex/tables/sshr_reproduction_scope_audit.tex",
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [evaluate(spec) for spec in specs()]
    write_csv(RESULTS / "summary_sshr_reproduction_scope_audit.csv", rows)
    write_markdown(RESULTS / "analysis_sshr_reproduction_scope_audit.md", rows)
    write_latex(TABLES / "sshr_reproduction_scope_audit.tex", rows)
    write_manifest(RESULTS / "manifest_sshr_reproduction_scope_audit.json", rows)
    failures = sum(1 for row in rows if row["audit_status"] == "needs revision")
    print(f"wrote {len(rows)} SSHR reproduction scope audit rows")
    if failures:
        print(f"warning: {failures} SSHR reproduction scope row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
