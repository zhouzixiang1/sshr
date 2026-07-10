#!/usr/bin/env python3
"""Audit that weak learned-control diagnostics stay bounded.

This derived audit is intentionally not a performance experiment.  It checks
that learned-control components classified as limited remain visible as
claim-boundary evidence, carry their negative cost evidence, and are not
promoted by the manuscript or support packet.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
REVIEWER_BRIEF = THIS_DIR / "submission_package" / "reviewer_concern_brief.md"
EDITOR_BRIEF = THIS_DIR / "submission_package" / "editor_screening_brief.md"

LEARNED_CONTROL_SUMMARY = RESULTS / "summary_learned_control_audit.csv"
LEARNED_CONTROL_MANIFEST = RESULTS / "manifest_learned_control_audit.json"

SUMMARY = RESULTS / "summary_limited_learned_control_boundary.csv"
ANALYSIS = RESULTS / "analysis_limited_learned_control_boundary.md"
MANIFEST = RESULTS / "manifest_limited_learned_control_boundary.json"
TABLE = TABLES / "limited_learned_control_boundary.tex"

EXPECTED_LIMITED = {"Bit-flip learned prior", "Boolean neural guard"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def status_from(condition: bool) -> str:
    return "pass" if condition else "needs revision"


def token_present(text: str, token: str) -> bool:
    return token.lower() in text.lower()


def missing_tokens(text: str, tokens: tuple[str, ...]) -> list[str]:
    return [token for token in tokens if not token_present(text, token)]


def percent_values(text: str) -> list[float]:
    return [float(match.group(1)) for match in re.finditer(r"([+-]?\d+(?:\.\d+)?)%", text)]


def first_percent(text: str) -> float | None:
    values = percent_values(text)
    return values[0] if values else None


def make_row(
    check: str,
    condition: bool,
    evidence: str,
    boundary: str,
    files: tuple[Path, ...],
) -> dict[str, str]:
    return {
        "check": check,
        "status": status_from(condition),
        "evidence": evidence,
        "boundary": boundary,
        "files": "; ".join(rel(path) for path in files),
    }


def build_rows() -> list[dict[str, str]]:
    learned_rows = read_csv(LEARNED_CONTROL_SUMMARY)
    limited_rows = [row for row in learned_rows if row.get("claim_class") == "limited"]
    limited_names = {row.get("component", "") for row in limited_rows}
    learned_manifest = read_json(LEARNED_CONTROL_MANIFEST)
    paper = read_text(PAPER)
    support = read_text(REVIEWER_BRIEF) + "\n" + read_text(EDITOR_BRIEF)

    cost_percentages = {
        row["component"]: first_percent(row.get("cost", "")) for row in limited_rows
    }
    quality_percentages = {
        row["component"]: percent_values(row.get("quality", "")) for row in limited_rows
    }
    small_quality = all(
        values and min(abs(value) for value in values) <= 0.5
        for values in quality_percentages.values()
    )
    runtime_penalized = all(
        value is not None and value > 0.0 for value in cost_percentages.values()
    )
    roles_bounded = all(
        token_present(row.get("role", ""), "limited")
        and token_present(row.get("role", ""), "not runtime claim")
        for row in limited_rows
    )
    class_counts = learned_manifest.get("claim_class_counts", {}) if learned_manifest else {}

    paper_boundary_missing = missing_tokens(
        paper,
        (
            "tab:limited-learned-control-boundary",
            "generic bit-flip prior remain limited diagnostics",
            "runtime overhead is visible",
            "deep-learning-only",
        ),
    )
    support_boundary_missing = missing_tokens(
        support,
        (
            "Is the AI contribution overstated?",
            "bounded controls",
            "Limited learned-control boundary audit",
            "deep-learning-only explanation",
        ),
    )
    limited_promotions = [
        row["component"]
        for row in learned_rows
        if row.get("component") in EXPECTED_LIMITED and row.get("claim_class") != "limited"
    ]
    class_count_text = ", ".join(f"{key}={value}" for key, value in sorted(class_counts.items()))
    cost_text = "; ".join(
        f"{name}: {cost_percentages.get(name):+.2f}% runtime"
        for name in sorted(EXPECTED_LIMITED)
    )
    quality_text = "; ".join(
        f"{name}: {quality_percentages.get(name, ['missing'])[0]:+.2f}% quality"
        for name in sorted(EXPECTED_LIMITED)
    )
    role_text = "; ".join(row.get("role", "") for row in limited_rows)

    return [
        make_row(
            "Limited component inventory",
            limited_names == EXPECTED_LIMITED
            and int(learned_manifest.get("limited_count", -1)) == len(EXPECTED_LIMITED),
            f"limited components are {', '.join(sorted(limited_names))}; class counts {class_count_text}.",
            "Only the generic bit-flip learned prior and Boolean neural guard are classified as limited.",
            (LEARNED_CONTROL_SUMMARY, LEARNED_CONTROL_MANIFEST),
        ),
        make_row(
            "Limited rows retain negative cost context",
            len(limited_rows) == len(EXPECTED_LIMITED) and small_quality and runtime_penalized,
            f"{quality_text}; {cost_text}.",
            "Small quality deltas with positive runtime overhead cannot be cited as runtime or headline wins.",
            (LEARNED_CONTROL_SUMMARY,),
        ),
        make_row(
            "Limited rows are not promoted by class or role",
            len(limited_rows) == len(EXPECTED_LIMITED) and roles_bounded and not limited_promotions,
            f"promotions={limited_promotions or 'none'}; roles: {role_text}.",
            "The learned-control audit must keep these components out of promoted or bounded headline evidence.",
            (LEARNED_CONTROL_SUMMARY,),
        ),
        make_row(
            "Manuscript exposes the limited boundary",
            not paper_boundary_missing,
            f"missing_tokens={paper_boundary_missing or 'none'}.",
            "The paper-facing text must say why limited diagnostics are not promoted.",
            (PAPER,),
        ),
        make_row(
            "Support packet answers AI-overclaim risk",
            not support_boundary_missing,
            f"missing_tokens={support_boundary_missing or 'none'}.",
            "Reviewer-facing support must route AI/MCTS attribution questions to bounded-control evidence.",
            (REVIEWER_BRIEF, EDITOR_BRIEF),
        ),
        make_row(
            "Neural/MCTS title remains calibrated",
            token_present(paper, "tab:neural-mcts-claim-calibration")
            and token_present(paper, "should not be described as a")
            and token_present(paper, "deep-learning-only"),
            "neural_mcts_table_anchor_present="
            f"{token_present(paper, 'tab:neural-mcts-claim-calibration')}.",
            "The title can use neural MCTS only as a bounded ranking, gating, and budget-allocation framework.",
            (PAPER,),
        ),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["check", "status", "evidence", "boundary", "files"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Limited Learned-Control Boundary Audit",
        "",
        "This audit checks that runtime-negative or weak learned-control diagnostics are retained as claim-boundary evidence rather than promoted as headline AI improvements.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| check | evidence | boundary | status |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['check']} | {row['evidence']} | {row['boundary']} | {row['status']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    escaped = (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )
    return escaped


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.33\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.08\linewidth}}",
        r"\toprule",
        r"Check & Evidence & Claim boundary & Status \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["check"]),
                    tex_escape(row["evidence"]),
                    tex_escape(row["boundary"]),
                    tex_escape(row["status"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "expected_limited_components": sorted(EXPECTED_LIMITED),
        "limited_boundary_count": len(EXPECTED_LIMITED),
        "outputs": {
            "summary": rel(SUMMARY),
            "analysis": rel(ANALYSIS),
            "manifest": rel(MANIFEST),
            "table": rel(TABLE),
        },
        "sources": [
            rel(LEARNED_CONTROL_SUMMARY),
            rel(LEARNED_CONTROL_MANIFEST),
            rel(PAPER),
            rel(REVIEWER_BRIEF),
            rel(EDITOR_BRIEF),
        ],
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {len(rows)} limited learned-control boundary rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
