#!/usr/bin/env python3
"""Audit the target-venue decision support packet.

The manuscript is technically uploadable only after the author chooses a
venue and confirms venue-specific policies.  This audit keeps that decision
explicit and source-backed without filling private author metadata.
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
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
VENUE_BRIEF = SUBMISSION_PACKAGE / "target_venue_brief.md"
METADATA_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_template.json"

CHECKED_DATE = "2026-07-09"
REQUIRED_TARGET_FIELDS = (
    "name",
    "manuscript_type",
    "formatting_policy_checked",
    "reference_style_checked",
    "word_limit_checked",
    "supplementary_material_policy_checked",
    "ai_disclosure_policy_checked",
    "anonymous_review_required",
)


@dataclass(frozen=True)
class VenueDecision:
    venue: str
    short_name: str
    recommended_order: int
    fit_label: str
    fit_score: int
    target_use: str
    main_risk: str
    pre_upload_action: str
    policy_gate: str
    source_url: str
    source_summary: str


VENUES = (
    VenueDecision(
        venue="ACM Transactions on Quantum Computing",
        short_name="ACM TQC",
        recommended_order=1,
        fit_label="strong",
        fit_score=5,
        target_use="Best fit when framed as quantum-computing design automation, oracle compilation, and resource-aware logical synthesis.",
        main_risk="Requires ACM-style packaging and a sharper computer-science/compilation framing.",
        pre_upload_action="Convert to the ACM article template, add ACM-style metadata/keywords if required, and keep artifact links ready.",
        policy_gate="Confirm ACM template, article type, references, artifact policy, and any author/AI disclosure requirements.",
        source_url="https://acm-stoc.org/stoc2020/acm-journals/tqc-new-announcement-06-2020.pdf",
        source_summary="Scope includes computational quantum computing, design automation, compilers, programming systems, and AI/ML applications.",
    ),
    VenueDecision(
        venue="Quantum",
        short_name="Quantum",
        recommended_order=2,
        fit_label="strong",
        fit_score=5,
        target_use="Best fit if an arXiv-first quantum-information venue is acceptable and the first pages emphasize assumptions and broad oracle-synthesis contribution.",
        main_risk="Editors may ask for broad quantum-science significance beyond an engineering benchmark package.",
        pre_upload_action="Post or cross-list the preprint to quant-ph, sharpen the first-pages contribution summary, and prepare author-contribution plus AI-use statements.",
        policy_gate="Confirm arXiv/quant-ph submission route, author contribution statement, AI-use disclosure, and optional template expectations.",
        source_url="https://quantum-journal.org/instructions/authors/",
        source_summary="Author instructions require arXiv submission/cross-listing, clear first-pages results/assumptions, author contributions, and AI-use disclosure.",
    ),
    VenueDecision(
        venue="IEEE Transactions on Quantum Engineering",
        short_name="IEEE TQE",
        recommended_order=3,
        fit_label="moderate-to-strong",
        fit_score=4,
        target_use="Good fit when positioned as reproducible quantum-software engineering for logical oracle synthesis.",
        main_risk="Open-access/APC and IEEE formatting constraints need author/funding confirmation.",
        pre_upload_action="Convert to IEEE style, confirm APC/funding, and keep the logical-layer boundary explicit.",
        policy_gate="Confirm IEEE style, article type, open-access/APC path, reference style, and disclosure requirements.",
        source_url="https://tqe.ieee.org/",
        source_summary="Journal scope covers engineering applications of quantum phenomena including quantum computation, information, software, hardware, devices, and metrology.",
    ),
    VenueDecision(
        venue="IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems",
        short_name="IEEE TCAD",
        recommended_order=4,
        fit_label="moderate",
        fit_score=3,
        target_use="Possible fit if reframed as a CAD/logical-synthesis and verification tool-flow contribution for quantum computing.",
        main_risk="Quantum-specific logical-oracle contribution may be seen as outside the main IC/system CAD audience unless the EDA framing is dominant.",
        pre_upload_action="Condense to TCAD page limits and emphasize synthesis algorithms, verification, tool reproducibility, and EDA relevance.",
        policy_gate="Confirm IEEE two-column format, regular-paper page limit, abstract length, index terms, keywords, and reference style.",
        source_url="https://ieee-ceda.org/publications/tcad/tcad-paper-submissions",
        source_summary="Submission instructions cover automated design algorithms/tools, IEEE formatting, page limits, abstract length, index terms, and keywords.",
    ),
    VenueDecision(
        venue="Quantum Science and Technology",
        short_name="QST",
        recommended_order=5,
        fit_label="selective/high-risk",
        fit_score=2,
        target_use="Use only if the introduction is strengthened around broad lasting impact for quantum algorithms and compilation.",
        main_risk="The journal is highly selective and warns that incremental steps are usually insufficient.",
        pre_upload_action="Strengthen the broad-impact motivation, confirm review model/anonymization, and align abstract/declarations with IOP requirements.",
        policy_gate="Confirm article type, abstract length, peer-review model, double-anonymous requirements, author contribution/funding/conflict fields, and supplementary data policy.",
        source_url="https://publishingsupport.iopscience.iop.org/journals/quantum-science-technology/",
        source_summary="Author guidance emphasizes important, rigorous, broadly interesting quantum results and venue-specific submission/declaration checks.",
    ),
)


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


def metadata_field_status() -> tuple[bool, list[str]]:
    data = read_json(METADATA_TEMPLATE)
    target = data.get("target_venue", {}) if isinstance(data, dict) else {}
    if not isinstance(target, dict):
        return False, [f"target_venue.{field}" for field in REQUIRED_TARGET_FIELDS]
    missing = [f"target_venue.{field}" for field in REQUIRED_TARGET_FIELDS if field not in target]
    return not missing, missing


def venue_status(venue: VenueDecision, brief: str, metadata_ok: bool) -> tuple[str, str]:
    missing_tokens = [
        token
        for token in (
            venue.venue,
            venue.short_name,
            venue.source_url,
            venue.fit_label,
            "target_venue.name",
            "anonymous_review_required",
            "ai_disclosure_policy_checked",
        )
        if token not in brief
    ]
    fields_present = all(
        [
            venue.recommended_order > 0,
            venue.fit_score > 0,
            venue.target_use,
            venue.main_risk,
            venue.pre_upload_action,
            venue.policy_gate,
            venue.source_url.startswith("https://"),
            venue.source_summary,
        ]
    )
    status = "pass" if fields_present and metadata_ok and not missing_tokens else "needs revision"
    evidence = (
        f"brief_tokens_missing={missing_tokens or 'none'}; "
        f"metadata_target_fields_present={metadata_ok}; "
        f"source_url={venue.source_url}"
    )
    return status, evidence


def build_rows() -> list[dict[str, str]]:
    brief = read_text(VENUE_BRIEF)
    metadata_ok, metadata_missing = metadata_field_status()
    rows: list[dict[str, str]] = []
    for venue in VENUES:
        status, evidence = venue_status(venue, brief, metadata_ok)
        if metadata_missing:
            evidence += f"; metadata_missing={metadata_missing}"
        rows.append(
            {
                "venue": venue.venue,
                "short_name": venue.short_name,
                "recommended_order": str(venue.recommended_order),
                "fit_label": venue.fit_label,
                "fit_score": str(venue.fit_score),
                "target_use": venue.target_use,
                "main_risk": venue.main_risk,
                "pre_upload_action": venue.pre_upload_action,
                "policy_gate": venue.policy_gate,
                "required_metadata_fields": "; ".join(f"target_venue.{field}" for field in REQUIRED_TARGET_FIELDS),
                "source_url": venue.source_url,
                "source_summary": venue.source_summary,
                "status": status,
                "evidence": evidence,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "venue",
        "short_name",
        "recommended_order",
        "fit_label",
        "fit_score",
        "target_use",
        "main_risk",
        "pre_upload_action",
        "policy_gate",
        "required_metadata_fields",
        "source_url",
        "source_summary",
        "status",
        "evidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    recommended = min(rows, key=lambda row: int(row["recommended_order"]))
    lines = [
        "# Target Venue Decision Audit",
        "",
        f"Checked date: {CHECKED_DATE}",
        "",
        "This audit makes the venue decision support packet source-backed and machine-checkable.  It does not choose the final journal for the author and does not fill private metadata.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Recommended first choice",
            "",
            f"- recommended_first_choice: {recommended['venue']}",
            f"- rationale: {recommended['target_use']}",
            "",
            "| order | venue | fit | fit score | pre-upload action | policy gate | source_url | status |",
            "|---:|---|---|---:|---|---|---|---|",
        ]
    )
    for row in sorted(rows, key=lambda item: int(item["recommended_order"])):
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {recommended_order} | {short_name} | {fit_label} | {fit_score} | {pre_upload_action} | {policy_gate} | {source_url} | {status} |".format(
                **safe
            )
        )
    lines.extend(
        [
            "",
            "## Required target-venue metadata fields",
            "",
        ]
    )
    for field in REQUIRED_TARGET_FIELDS:
        lines.append(f"- target_venue.{field}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This audit supports venue selection and policy checks only.",
            "- Final venue choice, manuscript type, anonymous-review status, archive links, author declarations, APC/funding constraints, and AI-disclosure wording remain author input.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        r"\begin{tabularx}{\linewidth}{r>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.23\linewidth}}",
        r"\toprule",
        r"Order & Venue & Fit & Pre-upload action & Boundary \\",
        r"\midrule",
    ]
    for row in sorted(rows, key=lambda item: int(item["recommended_order"])):
        boundary = f"{row['policy_gate']} Source: {row['source_url']}"
        lines.append(
            " & ".join(
                [
                    row["recommended_order"],
                    tex_escape(row["short_name"]),
                    tex_escape(row["fit_label"]),
                    tex_escape(row["pre_upload_action"]),
                    tex_escape(boundary),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    recommended = min(rows, key=lambda row: int(row["recommended_order"]))
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "checked_date": CHECKED_DATE,
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "recommended_first_choice": recommended["venue"],
        "strong_fit_count": sum(1 for row in rows if row["fit_label"] == "strong"),
        "required_target_metadata_fields": [f"target_venue.{field}" for field in REQUIRED_TARGET_FIELDS],
        "sources": [row["source_url"] for row in rows],
        "outputs": {
            "summary": "results/summary_target_venue_decision_audit.csv",
            "analysis": "results/analysis_target_venue_decision_audit.md",
            "manifest": "results/manifest_target_venue_decision_audit.json",
            "table": "paper_latex/tables/target_venue_decision_audit.tex",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_target_venue_decision_audit.csv", rows)
    write_markdown(RESULTS / "analysis_target_venue_decision_audit.md", rows)
    write_latex(TABLES / "target_venue_decision_audit.tex", rows)
    write_manifest(RESULTS / "manifest_target_venue_decision_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] != "pass")
    print(f"wrote {len(rows)} target-venue decision rows")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
