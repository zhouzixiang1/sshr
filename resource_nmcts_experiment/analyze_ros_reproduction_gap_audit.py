#!/usr/bin/env python3
"""Audit the boundary between ROS-style proxy evidence and full ROS reproduction.

The paper compares against a deliberately marked ROS-style LUT proxy and several
external toolchain probes.  This audit makes the boundary machine-checkable:
which ROS-facing elements are covered, which are only partial proxies, and
which full ROS components remain outside the current logical-layer package.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
REFERENCES = THIS_DIR / "paper_latex" / "references.bib"
README = THIS_DIR / "README.md"
DELIVERABLE = THIS_DIR / "DELIVERABLE_zh.md"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"

ROS_PROXY_ANALYSIS = RESULTS / "analysis_ros_lut_proxy.md"
ROS_PROXY_SUMMARY = RESULTS / "summary_ros_lut_proxy.csv"
ROS_PROXY_MANIFEST = RESULTS / "manifest_ros_lut_proxy.json"
ROS_PROXY_SWEEP = RESULTS / "raw_ros_lut_proxy_sweep.csv"
ROS_PROXY_BEST = RESULTS / "raw_ros_lut_proxy_best.csv"
ROS_LINE_ANALYSIS = RESULTS / "analysis_ros_lut_line_sensitivity.md"
ROS_LINE_SUMMARY = RESULTS / "summary_ros_lut_line_sensitivity.csv"
ROS_LINE_MANIFEST = RESULTS / "manifest_ros_lut_line_sensitivity.json"
ROS_LINE_RAW = RESULTS / "raw_ros_lut_line_sensitivity.csv"
STG_ANALYSIS = RESULTS / "analysis_stg_published_benchmark.md"
STG_SUMMARY = RESULTS / "summary_stg_published_benchmark.csv"
STG_MANIFEST = RESULTS / "manifest_stg_published_benchmark.json"
STG_RAW = RESULTS / "raw_stg_published_benchmark.csv"
TOOLCHAIN_ANALYSIS = RESULTS / "analysis_toolchain_readiness.md"
COMPARISON_EVIDENCE = RESULTS / "analysis_comparison_evidence_matrix.md"
COMPARISON_PROTOCOL = RESULTS / "analysis_comparison_protocol_audit.md"
COMPARISON_PROTOCOL_MANIFEST = RESULTS / "manifest_comparison_protocol_audit.json"
CLAIM_MATRIX = RESULTS / "summary_baseline_claim_matrix.csv"
CLAIM_SCOPE_MANIFEST = RESULTS / "manifest_claim_scope_lint.json"
REPRODUCIBILITY = RESULTS / "analysis_reproducibility_audit.md"


@dataclass(frozen=True)
class CsvExpectation:
    path: Path
    expected_rows: int
    require_all_correct: bool = False


@dataclass(frozen=True)
class JsonExpectation:
    path: Path
    key: str
    expected: object


@dataclass(frozen=True)
class RosSpec:
    item: str
    coverage_status: str
    official_requirement: str
    current_coverage: str
    files: tuple[Path, ...]
    tokens: tuple[str, ...]
    csv_expectations: tuple[CsvExpectation, ...]
    json_expectations: tuple[JsonExpectation, ...]
    supported_claim: str
    excluded_claim: str
    next_reproduction_step: str


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def token_hits(files: tuple[Path, ...], tokens: tuple[str, ...]) -> tuple[int, list[str]]:
    combined = "\n".join(read_text(path) for path in files)
    missing = [token for token in tokens if token not in combined]
    return len(tokens) - len(missing), missing


def check_csv(expectation: CsvExpectation) -> tuple[bool, str]:
    if not expectation.path.exists():
        return False, f"{rel(expectation.path)} missing"
    with expectation.path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row_ok = len(rows) == expectation.expected_rows
    correct_ok = True
    incorrect = 0
    if expectation.require_all_correct:
        for row in rows:
            value = row.get("correct", "")
            if str(value).lower() not in {"true", "1", "yes"}:
                incorrect += 1
        correct_ok = incorrect == 0
    status = row_ok and correct_ok
    detail = f"{rel(expectation.path)} rows={len(rows)}/{expectation.expected_rows}"
    if expectation.require_all_correct:
        detail += f", incorrect={incorrect}"
    return status, detail


def check_json(expectation: JsonExpectation) -> tuple[bool, str]:
    manifest = read_json(expectation.path)
    if not manifest:
        return False, f"{rel(expectation.path)} missing_or_invalid"
    actual = manifest.get(expectation.key)
    return actual == expectation.expected, f"{rel(expectation.path)}::{expectation.key}={actual}"


def specs() -> list[RosSpec]:
    return [
        RosSpec(
            item="ROS literature and task anchor",
            coverage_status="covered",
            official_requirement="The paper must cite ROS and identify its resource-constrained LUT-oracle role before using a ROS-style baseline.",
            current_coverage="The manuscript and bibliography cite ROS and frame the current study as logical-layer Boolean-oracle synthesis.",
            files=(PAPER, REFERENCES, RESULTS / "analysis_citation_support_audit.md"),
            tokens=("meuli2020ros", "Resource-constrained Oracle Synthesis", "resource-constrained LUT mapping", "logical-layer"),
            csv_expectations=(),
            json_expectations=(),
            supported_claim="ROS is a relevant resource-constrained oracle-synthesis comparator family.",
            excluded_claim="This citation anchor alone does not reproduce the ROS implementation.",
            next_reproduction_step="No immediate action; keep the literature anchor when venue formatting changes.",
        ),
        RosSpec(
            item="Verified LUT K-sweep proxy",
            coverage_status="partial",
            official_requirement="ROS uses LUT-network decomposition as part of an oracle-synthesis flow.",
            current_coverage="The project runs an ABC if -K sweep for K=3,4,5, verifies each mapped BLIF truth table, and selects the best K per function.",
            files=(ROS_PROXY_ANALYSIS, ROS_PROXY_SUMMARY, ROS_PROXY_MANIFEST, ROS_PROXY_SWEEP, ROS_PROXY_BEST, COMPARISON_EVIDENCE),
            tokens=("Sweep rows: 927; usable: 927", "Best-K rows: 309", "It is not the official ROS", "927/927 K-sweep rows"),
            csv_expectations=(
                CsvExpectation(ROS_PROXY_SWEEP, 927, True),
                CsvExpectation(ROS_PROXY_BEST, 309, True),
            ),
            json_expectations=(
                JsonExpectation(ROS_PROXY_MANIFEST, "sweep_rows", 927),
                JsonExpectation(ROS_PROXY_MANIFEST, "best_rows", 309),
            ),
            supported_claim="The paper can report a verified ROS-style LUT proxy and best-K pressure test.",
            excluded_claim="The proxy is not the official ROS mapper or reversible implementation flow.",
            next_reproduction_step="Replace or supplement ABC if -K with an official ROS-compatible mapper if one becomes available.",
        ),
        RosSpec(
            item="Line and garbage-pressure sensitivity",
            coverage_status="partial",
            official_requirement="ROS explicitly targets qubit/garbage pressure through resource-aware choices.",
            current_coverage="The line-sensitivity audit reselects the verified LUT sweep under min-ancilla and line-weighted objectives.",
            files=(ROS_LINE_ANALYSIS, ROS_LINE_SUMMARY, ROS_LINE_MANIFEST, ROS_LINE_RAW, PAPER),
            tokens=("not the official ROS SAT garbage-management algorithm", "Selected rows: 1236", "minimum-ancilla selector", "peak ancilla by 32.47"),
            csv_expectations=(CsvExpectation(ROS_LINE_RAW, 1236, True),),
            json_expectations=(JsonExpectation(ROS_LINE_MANIFEST, "selected_rows", 1236),),
            supported_claim="The score advantage is robust to line-aware LUT proxy selectors.",
            excluded_claim="This is not SAT garbage management and cannot be called a full ROS reproduction.",
            next_reproduction_step="Implement or obtain the ROS SAT garbage-management stage before making any official-ROS claim.",
        ),
        RosSpec(
            item="Published STG optimum-library counterpoint",
            coverage_status="covered",
            official_requirement="The related STG benchmark reports precomputed 4- and 5-input spectral-representative circuit optima, not a full ROS execution path.",
            current_coverage="The project synthesizes the same 54 public truth-table representatives and reports both the negative STG-optimum boundary and the same-slice direct-baseline gains.",
            files=(STG_ANALYSIS, STG_SUMMARY, STG_MANIFEST, STG_RAW, PAPER, COMPARISON_EVIDENCE),
            tokens=("Published STG optima remain much stronger", "raw synthesis rows: 270", "Pareto vs STG T-count optimum", "tab:stg-published"),
            csv_expectations=(CsvExpectation(STG_RAW, 270, True),),
            json_expectations=(
                JsonExpectation(STG_MANIFEST, "raw_rows", 270),
                JsonExpectation(STG_MANIFEST, "needs_revision_count", 0),
            ),
            supported_claim="The paper includes a published small-function optimum-library counterpoint and does not hide that STG wins on tiny precomputed representatives.",
            excluded_claim="This is not a reproduced ROS SAT garbage-management flow and does not replace scalable logical-layer comparisons.",
            next_reproduction_step="Keep this counterpoint separate from ROS-style LUT and RevKit rows; add full ROS only if executable artifacts or a faithful SAT-garbage implementation are available.",
        ),
        RosSpec(
            item="Official ROS SAT garbage management",
            coverage_status="not reproduced",
            official_requirement="Full ROS includes SAT-based garbage management after LUT mapping.",
            current_coverage="The manuscript, README, and line-sensitivity audit explicitly mark SAT garbage management as not reproduced.",
            files=(PAPER, README, ROS_LINE_ANALYSIS, DELIVERABLE),
            tokens=("than a full ROS reproduction with SAT garbage management", "The full official ROS flow remains future work", "still do not implement ROS SAT garbage management", "官方 ROS 仍未完整复现"),
            csv_expectations=(),
            json_expectations=(),
            supported_claim="The package is transparent about the missing official ROS component.",
            excluded_claim="No result may be described as beating or reproducing full ROS with SAT garbage management.",
            next_reproduction_step="Track down executable ROS artifacts or reimplement the SAT garbage-management formulation as a separate baseline.",
        ),
        RosSpec(
            item="Reversible emission and exact-oracle counterpoint",
            coverage_status="partial",
            official_requirement="A full oracle-synthesis comparison should include a reversible-oracle emission path, not only logic-network estimates.",
            current_coverage="Legacy RevKit CLI probes synthesize exact oracle permutations and serve as a separate reversible-synthesis counterpoint.",
            files=(COMPARISON_EVIDENCE, TOOLCHAIN_ANALYSIS, README),
            tokens=("Legacy RevKit CLI exact oracle", "Exact reversible oracle permutation", "RevKit/CirKit legacy CLI is locally available", "run_revkit_cli_probe.py"),
            csv_expectations=(),
            json_expectations=(),
            supported_claim="The paper has a genuine exact reversible-oracle toolchain probe in addition to LUT/XAG/AIG proxies.",
            excluded_claim="The RevKit CLI probe is not the ROS hierarchical LUT plus SAT garbage-management flow.",
            next_reproduction_step="Add a ROS-compatible reversible emission stage if the official flow or enough algorithmic detail is reimplemented.",
        ),
        RosSpec(
            item="External toolchain availability boundary",
            coverage_status="covered",
            official_requirement="External comparisons should record which tools are locally runnable and which remain only proxy-level.",
            current_coverage="Toolchain readiness records ABC, mockturtle, CirKit, RevKit API, and legacy RevKit/CirKit availability and separates them from full ROS.",
            files=(TOOLCHAIN_ANALYSIS, REPRODUCIBILITY, README),
            tokens=("mockturtle source and the project KLUT-to-XAG adapter are available", "CirKit 3 shell is locally available", "RevKit/CirKit legacy CLI is locally available", "This is still not the full official ROS flow"),
            csv_expectations=(),
            json_expectations=(),
            supported_claim="The external-probe environment is reproducible and provenance-recorded.",
            excluded_claim="Tool availability is not the same as official ROS reproduction.",
            next_reproduction_step="Rerun the readiness audit after adding any official ROS source, binary, or independent reimplementation.",
        ),
        RosSpec(
            item="Claim wording and comparison protocol",
            coverage_status="covered",
            official_requirement="The manuscript must prevent proxy rows from being interpreted as full external compiler wins.",
            current_coverage="Claim matrix, comparison protocol, claim-scope lint, and manuscript limitations state the ROS boundary.",
            files=(CLAIM_MATRIX, COMPARISON_PROTOCOL, PAPER, SUBMISSION_PACKAGE / "README.md"),
            tokens=("Does not reproduce full ROS SAT garbage management", "They are not a full ROS SAT garbage-management flow", "The ROS-style LUT result is a proxy rather", "A full ROS SAT garbage-management reproduction."),
            csv_expectations=(),
            json_expectations=(
                JsonExpectation(COMPARISON_PROTOCOL_MANIFEST, "needs_revision_count", 0),
                JsonExpectation(CLAIM_SCOPE_MANIFEST, "unresolved_count", 0),
            ),
            supported_claim="The paper can use ROS-style evidence without overclaiming full ROS reproduction.",
            excluded_claim="The current evidence cannot support a full-ROS or hardware-mapped dominance statement.",
            next_reproduction_step="Keep this row green after any abstract, cover-letter, or results wording change.",
        ),
        RosSpec(
            item="Reviewer-facing support visibility",
            coverage_status="covered",
            official_requirement="Reviewers should be able to find the ROS proxy commands and the excluded full-ROS claim quickly.",
            current_coverage="The submission package exposes the ROS-style proxy command and states that full ROS SAT garbage management is not included.",
            files=(SUBMISSION_PACKAGE / "artifact_reproduction_guide.md", SUBMISSION_PACKAGE / "reviewer_concern_brief.md", SUBMISSION_PACKAGE / "README.md"),
            tokens=("ROS-style LUT proxy: `run_ros_lut_proxy.py`", "Direct ANF, ESOP, BDD/ABC, SSHR, ROS-style LUT", "A full ROS SAT garbage-management reproduction."),
            csv_expectations=(),
            json_expectations=(),
            supported_claim="The upload package makes the ROS boundary visible without requiring the reviewer to infer it from code.",
            excluded_claim="Support-package visibility does not add a new official ROS experiment.",
            next_reproduction_step="Add this audit report to reviewer-facing docs if venue page limits allow supplementary navigation.",
        ),
    ]


def evaluate(spec: RosSpec) -> dict[str, str]:
    missing_files = [rel(path) for path in spec.files if not path.exists()]
    hits, missing_tokens = token_hits(spec.files, spec.tokens)
    csv_results = [check_csv(expectation) for expectation in spec.csv_expectations]
    json_results = [check_json(expectation) for expectation in spec.json_expectations]
    csv_ok = all(ok for ok, _ in csv_results)
    json_ok = all(ok for ok, _ in json_results)
    status = "pass" if not missing_files and hits == len(spec.tokens) and csv_ok and json_ok else "needs revision"
    evidence_parts = [
        f"files_missing={missing_files or 'none'}",
        f"tokens={hits}/{len(spec.tokens)}",
        f"missing_tokens={missing_tokens or 'none'}",
    ]
    if csv_results:
        evidence_parts.append("csv=" + "; ".join(detail for _, detail in csv_results))
    if json_results:
        evidence_parts.append("json=" + "; ".join(detail for _, detail in json_results))
    return {
        "item": spec.item,
        "audit_status": status,
        "coverage_status": spec.coverage_status,
        "official_requirement": spec.official_requirement,
        "current_coverage": spec.current_coverage,
        "evidence": "; ".join(evidence_parts),
        "supported_claim": spec.supported_claim,
        "excluded_claim": spec.excluded_claim,
        "next_reproduction_step": spec.next_reproduction_step,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "item",
        "audit_status",
        "coverage_status",
        "official_requirement",
        "current_coverage",
        "evidence",
        "supported_claim",
        "excluded_claim",
        "next_reproduction_step",
    ]
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


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts: dict[str, int] = {}
    coverage_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["audit_status"]] = status_counts.get(row["audit_status"], 0) + 1
        coverage_counts[row["coverage_status"]] = coverage_counts.get(row["coverage_status"], 0) + 1
    lines = [
        "# ROS Reproduction Gap Audit",
        "",
        "This audit separates verified ROS-style proxy evidence from full official ROS reproduction.",
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
            "## Boundary matrix",
            "",
            "| item | audit status | coverage | current coverage | supported claim | excluded claim |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {item} | {audit_status} | {coverage_status} | {current_coverage} | {supported_claim} | {excluded_claim} |".format(
                **safe
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.12\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.28\linewidth}}",
        r"\toprule",
        r"ROS-facing element & Coverage & Current evidence & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["item"]),
                    tex_escape(row["coverage_status"]),
                    tex_escape(row["current_coverage"]),
                    tex_escape(row["excluded_claim"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = {
        status: sum(1 for row in rows if row["audit_status"] == status)
        for status in sorted({row["audit_status"] for row in rows})
    }
    coverage_counts = {
        status: sum(1 for row in rows if row["coverage_status"] == status)
        for status in sorted({row["coverage_status"] for row in rows})
    }
    failures = status_counts.get("needs revision", 0)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": status_counts,
        "coverage_counts": coverage_counts,
        "needs_revision_count": failures,
        "official_ros_fully_reproduced": False,
        "full_ros_boundary_is_explicit": failures == 0 and coverage_counts.get("not reproduced", 0) >= 1,
        "outputs": {
            "summary": "results/summary_ros_reproduction_gap_audit.csv",
            "analysis": "results/analysis_ros_reproduction_gap_audit.md",
            "manifest": "results/manifest_ros_reproduction_gap_audit.json",
            "table": "paper_latex/tables/ros_reproduction_gap_audit.tex",
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [evaluate(spec) for spec in specs()]
    write_csv(RESULTS / "summary_ros_reproduction_gap_audit.csv", rows)
    write_markdown(RESULTS / "analysis_ros_reproduction_gap_audit.md", rows)
    write_latex(TABLES / "ros_reproduction_gap_audit.tex", rows)
    write_manifest(RESULTS / "manifest_ros_reproduction_gap_audit.json", rows)
    failures = sum(1 for row in rows if row["audit_status"] == "needs revision")
    print(f"wrote {len(rows)} ROS reproduction gap audit rows")
    if failures:
        print(f"warning: {failures} ROS reproduction gap row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
