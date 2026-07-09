#!/usr/bin/env python3
"""Audit editor- and reviewer-facing screening support.

This audit checks that the public submission support package answers the
questions that usually trigger desk rejection or early reviewer objections:
scope, novelty, comparison fairness, counterexamples, AI overclaiming,
large-scale verification, reproducibility, and remaining author/venue gates.
It does not judge acceptance probability and does not use private metadata.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
EDITOR_BRIEF = THIS_DIR / "submission_package" / "editor_screening_brief.md"
REVIEWER_BRIEF = THIS_DIR / "submission_package" / "reviewer_concern_brief.md"
TARGET_VENUE_BRIEF = THIS_DIR / "submission_package" / "target_venue_brief.md"
README = THIS_DIR / "submission_package" / "README.md"
CHECKLIST = THIS_DIR / "submission_package" / "submission_checklist.md"

COMPARISON_PROTOCOL = RESULTS / "manifest_comparison_protocol_audit.json"
COMPARISON_TARGET_VALIDITY = RESULTS / "manifest_comparison_target_validity_audit.json"
CLAIM_SCOPE = RESULTS / "manifest_claim_scope_lint.json"
CITATION_SUPPORT = RESULTS / "manifest_citation_support_audit.json"
COUNTERPOINT = RESULTS / "analysis_counterpoint_claim_boundary.md"
SEARCH_CONTROL = RESULTS / "manifest_search_control_baseline_audit.json"
LEARNED_CONTROL = RESULTS / "analysis_learned_control_audit.md"
SCALING = RESULTS / "analysis_scaling_resource_audit.md"
ULTRA_PROFILE = RESULTS / "analysis_screen_scale_ultra_scale64_resource_profile.md"
TRACEABILITY = RESULTS / "analysis_submission_traceability_audit.md"
ARCHIVE_MANIFEST = RESULTS / "analysis_submission_archive_manifest.md"
METADATA_CLOSURE = RESULTS / "manifest_submission_metadata_closure_path.json"
AUTHOR_PACKET = THIS_DIR / "submission_package" / "AUTHOR_INPUT_REQUIRED.md"


@dataclass(frozen=True)
class ScreeningSpec:
    item: str
    risk: str
    files: tuple[Path, ...]
    tokens: tuple[str, ...]
    manifest_path: Path | None
    manifest_key: str
    expected_value: int
    supported_decision: str
    boundary: str


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


def count_value(value: object, default: int = -1) -> int:
    if isinstance(value, list):
        return len(value)
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def token_hits(files: tuple[Path, ...], tokens: tuple[str, ...]) -> tuple[int, list[str]]:
    combined = "\n".join(read_text(path) for path in files)
    missing = [token for token in tokens if token not in combined]
    return len(tokens) - len(missing), missing


def manifest_ok(path: Path | None, key: str, expected: int) -> tuple[bool, str]:
    if path is None:
        return True, "not_applicable"
    manifest = read_json(path)
    if not manifest:
        return False, f"{rel(path)} missing_or_invalid"
    actual = count_value(manifest.get(key), -999999)
    return actual == expected, f"{rel(path)}::{key}={actual}"


def specs() -> list[ScreeningSpec]:
    return [
        ScreeningSpec(
            item="Logical-layer scope visible at first screening",
            risk="Editor may reject the manuscript as an overbroad hardware compiler claim.",
            files=(PAPER, EDITOR_BRIEF, TARGET_VENUE_BRIEF),
            tokens=("logical-layer", "not a hardware-mapped", "hardware mapping", "routing"),
            manifest_path=CLAIM_SCOPE,
            manifest_key="unresolved_count",
            expected_value=0,
            supported_decision="The manuscript can be sent to reviewers as a logical-layer oracle-synthesis paper.",
            boundary="Do not imply hardware routing, native-gate scheduling, noise modeling, or device execution.",
        ),
        ScreeningSpec(
            item="Novelty and comparison route visible",
            risk="Editor may see the work as only an SSHR variant or as a weak-baseline comparison.",
            files=(PAPER, EDITOR_BRIEF, REVIEWER_BRIEF),
            tokens=("does not use SSHR", "layered comparisons", "Baseline claim matrix", "Comparison evidence matrix"),
            manifest_path=COMPARISON_PROTOCOL,
            manifest_key="needs_revision_count",
            expected_value=0,
            supported_decision="The screening package explains why SSHR is a baseline and why comparisons are layered.",
            boundary="The claim is not universal superiority over every synthesis method.",
        ),
        ScreeningSpec(
            item="Comparison target roles visible",
            risk="Editor or reviewer may treat controls, probes, and counterpoints as if they were all primary benchmarks.",
            files=(PAPER, README, CHECKLIST),
            tokens=("Comparison target validity audit", "primary benchmark", "external stress test", "causal control"),
            manifest_path=COMPARISON_TARGET_VALIDITY,
            manifest_key="needs_revision_count",
            expected_value=0,
            supported_decision="The package makes comparison roles explicit before the results are read as a universal leaderboard.",
            boundary="Role labels clarify the current evidence; they do not broaden any comparison beyond the logical-layer claim.",
        ),
        ScreeningSpec(
            item="Counterpoint and negative-result visibility",
            risk="Reviewer may object that weighted-score wins hide CNOT, depth, or ancilla losses.",
            files=(PAPER, EDITOR_BRIEF, REVIEWER_BRIEF, COUNTERPOINT),
            tokens=("SSHR", "CirKit", "RevKit", "universal CNOT"),
            manifest_path=CLAIM_SCOPE,
            manifest_key="unresolved_count",
            expected_value=0,
            supported_decision="Unfavorable metric evidence is visible before review rather than hidden in raw tables.",
            boundary="Weighted-score wins must stay separated from raw resource dominance.",
        ),
        ScreeningSpec(
            item="AI and MCTS contribution bounded",
            risk="Reviewer may reject an overclaim that deep learning alone explains the gains.",
            files=(PAPER, REVIEWER_BRIEF, LEARNED_CONTROL),
            tokens=("bounded controls", "deep learning alone", "Search-control baseline audit", "learned-control"),
            manifest_path=SEARCH_CONTROL,
            manifest_key="needs_revision_count",
            expected_value=0,
            supported_decision="The manuscript can claim neural/MCTS search-control support without overclaiming deep RL.",
            boundary="The largest gains remain tied to algebraic action space and guarded/Pareto selection.",
        ),
        ScreeningSpec(
            item="Large-scale verification boundary visible",
            risk="Reviewer may object that the n=48--64 symbolic stress rows are not exhaustive truth-table checks.",
            files=(PAPER, REVIEWER_BRIEF, SCALING, ULTRA_PROFILE),
            tokens=("symbolic", "complete truth-table", "exponential", "bridge", "resource profile"),
            manifest_path=None,
            manifest_key="",
            expected_value=0,
            supported_decision="Large-scale evidence is framed as symbolic verification, resource-profile tradeoffs, and bounded truth-table bridges.",
            boundary="Do not claim exhaustive high-dimensional truth-table benchmarking.",
        ),
        ScreeningSpec(
            item="Reproducibility path visible",
            risk="Editor may desk-reject if the manuscript cannot be audited from submitted artifacts.",
            files=(PAPER, EDITOR_BRIEF, README, CHECKLIST, TRACEABILITY, ARCHIVE_MANIFEST),
            tokens=("rebuild_submission_package.sh", "verify_submission_package.sh", "payload", "traceability"),
            manifest_path=CITATION_SUPPORT,
            manifest_key="needs_revision_count",
            expected_value=0,
            supported_decision="The submission package exposes a clear reviewer path from claims to files and scripts.",
            boundary="The lightweight rebuild verifies paper-facing outputs; raw sweeps remain heavier rerun tiers.",
        ),
        ScreeningSpec(
            item="Author and venue gate explicit",
            risk="Submission may be blocked by missing declarations, anonymous-review policy, or archive links.",
            files=(TARGET_VENUE_BRIEF, AUTHOR_PACKET, CHECKLIST, README),
            tokens=("target_venue.name", "anonymous_review_required", "AUTHOR INPUT REQUIRED", "submission_metadata.json"),
            manifest_path=METADATA_CLOSURE,
            manifest_key="needs_revision_count",
            expected_value=0,
            supported_decision="The remaining nontechnical submission gate is explicit and private rather than implicit.",
            boundary="Author order, affiliations, funding, conflicts, venue choice, and archive links still require author input.",
        ),
        ScreeningSpec(
            item="Editorial reading path present",
            risk="Editor may miss the comparison boundary if the package lacks a short triage route.",
            files=(EDITOR_BRIEF,),
            tokens=("Recommended Editorial Reading Path", "baseline claim matrix", "counterpoint", "Data and Code Availability"),
            manifest_path=None,
            manifest_key="",
            expected_value=0,
            supported_decision="The support package gives editors a concise route to judge fit before full review.",
            boundary="This is a navigation aid, not an acceptance guarantee.",
        ),
    ]


def evaluate(spec: ScreeningSpec) -> dict[str, str]:
    missing_files = [rel(path) for path in spec.files if not path.exists()]
    hits, missing_tokens = token_hits(spec.files, spec.tokens)
    ok, manifest_evidence = manifest_ok(spec.manifest_path, spec.manifest_key, spec.expected_value)
    status = "pass" if not missing_files and hits == len(spec.tokens) and ok else "needs revision"
    evidence = (
        f"files_missing={missing_files or 'none'}; "
        f"tokens={hits}/{len(spec.tokens)}; "
        f"missing_tokens={missing_tokens or 'none'}; "
        f"manifest={manifest_evidence}"
    )
    return {
        "item": spec.item,
        "status": status,
        "risk": spec.risk,
        "evidence": evidence,
        "supported_decision": spec.supported_decision,
        "boundary": spec.boundary,
        "next_action": "No action needed." if status == "pass" else "Restore missing anchors or regenerate the supporting audit before submission.",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "risk", "evidence", "supported_decision", "boundary", "next_action"]
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
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Editorial Screening Audit",
        "",
        "This audit checks that the editor and reviewer support package exposes scope, novelty, comparison, counterpoint, AI, scale, reproducibility, and author-gate boundaries.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "## Screening Matrix", "", "| item | status | risk | evidence | supported decision | boundary |", "|---|---|---|---|---|---|"])
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append("| {item} | {status} | {risk} | {evidence} | {supported_decision} | {boundary} |".format(**safe))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.11\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.25\linewidth}}",
        r"\toprule",
        r"Screening item & Status & Supported decision & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["item"]),
                    tex_escape(row["status"]),
                    tex_escape(row["supported_decision"]),
                    tex_escape(row["boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": {status: sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
        "needs_revision_count": failures,
        "outputs": {
            "summary": "results/summary_editorial_screening_audit.csv",
            "analysis": "results/analysis_editorial_screening_audit.md",
            "manifest": "results/manifest_editorial_screening_audit.json",
            "table": "paper_latex/tables/editorial_screening_audit.tex",
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [evaluate(spec) for spec in specs()]
    write_csv(RESULTS / "summary_editorial_screening_audit.csv", rows)
    write_markdown(RESULTS / "analysis_editorial_screening_audit.md", rows)
    write_latex(THIS_DIR / "paper_latex" / "tables" / "editorial_screening_audit.tex", rows)
    write_manifest(RESULTS / "manifest_editorial_screening_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} editorial screening audit rows")
    if failures:
        print(f"warning: {failures} editorial screening row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
