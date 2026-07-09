#!/usr/bin/env python3
"""Audit the public cover-letter, venue, and declaration support packet.

This audit checks the human-facing files that are used immediately before
journal upload: cover letter template, author declarations template, venue
brief, final checklist, handoff notes, metadata template, and editor/reviewer
briefs.  It verifies that these files preserve the logical-layer claim
boundary, expose author-gated fields, and point to the reproducible package
checks without reading or generating private author metadata.
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

COVER = SUBMISSION_PACKAGE / "cover_letter_template.md"
DECLARATIONS = SUBMISSION_PACKAGE / "author_declarations_template.md"
VENUE = SUBMISSION_PACKAGE / "target_venue_brief.md"
CHECKLIST = SUBMISSION_PACKAGE / "submission_checklist.md"
FINAL_HANDOFF = SUBMISSION_PACKAGE / "FINAL_SUBMISSION_HANDOFF_zh.md"
README = SUBMISSION_PACKAGE / "README.md"
AUTHOR_PACKET = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
METADATA_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_template.json"
EDITOR_BRIEF = SUBMISSION_PACKAGE / "editor_screening_brief.md"
REVIEWER_BRIEF = SUBMISSION_PACKAGE / "reviewer_concern_brief.md"

CLAIM_SCOPE = RESULTS / "manifest_claim_scope_lint.json"
COMPARISON_PROTOCOL = RESULTS / "manifest_comparison_protocol_audit.json"
EDITORIAL_SCREENING = RESULTS / "manifest_editorial_screening_audit.json"
METADATA_CLOSURE = RESULTS / "manifest_submission_metadata_closure_path.json"
TEXT_PREVIEW = RESULTS / "manifest_submission_text_preview.json"
ANONYMOUS_REVIEW = RESULTS / "manifest_anonymous_review_readiness.json"
TARGET_VENUE_DECISION = RESULTS / "manifest_target_venue_decision_audit.json"


@dataclass(frozen=True)
class PacketSpec:
    item: str
    upload_risk: str
    files: tuple[Path, ...]
    tokens: tuple[str, ...]
    manifest_path: Path | None
    manifest_key: str
    expected: object
    supported_use: str
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


def token_hits(files: tuple[Path, ...], tokens: tuple[str, ...]) -> tuple[int, list[str]]:
    combined = "\n".join(read_text(path) for path in files)
    missing = [token for token in tokens if token not in combined]
    return len(tokens) - len(missing), missing


def manifest_ok(path: Path | None, key: str, expected: object) -> tuple[bool, str]:
    if path is None:
        return True, "not_applicable"
    manifest = read_json(path)
    if not manifest:
        return False, f"{rel(path)} missing_or_invalid"
    actual = manifest.get(key)
    if isinstance(expected, int) and isinstance(actual, list):
        actual_cmp: object = len(actual)
    else:
        actual_cmp = actual
    return actual_cmp == expected, f"{rel(path)}::{key}={actual_cmp}"


def specs() -> list[PacketSpec]:
    return [
        PacketSpec(
            item="Cover letter preserves logical-layer scope",
            upload_risk="Cover-letter prose could accidentally frame the paper as a hardware compiler.",
            files=(COVER,),
            tokens=(
                "logical-layer synthesis",
                "does not claim hardware mapping",
                "resource-constrained search",
                "rebuild_submission_package.sh",
            ),
            manifest_path=CLAIM_SCOPE,
            manifest_key="unresolved_count",
            expected=0,
            supported_use="The cover letter can introduce the manuscript without overclaiming hardware mapping or physical execution.",
            boundary="The cover letter still needs author, editor, reviewer, and prior-dissemination fields before upload.",
        ),
        PacketSpec(
            item="Cover letter exposes the comparison envelope",
            upload_risk="Editor may see only a narrow SSHR comparison or miss external-toolchain evidence.",
            files=(COVER,),
            tokens=(
                "177 traditional functions",
                "ESOP",
                "SSHR-H/SSHR-I",
                "mockturtle",
                "CirKit",
                "RevKit CLI exact-oracle",
                "complete truth-table bridge",
            ),
            manifest_path=COMPARISON_PROTOCOL,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The cover letter summarizes layered baselines and directs editors to the comparison evidence.",
            boundary="It should not be read as universal dominance over every synthesis or compilation method.",
        ),
        PacketSpec(
            item="Author declarations keep private fields explicit",
            upload_risk="Declarations could be mistaken as complete or private author metadata could be committed.",
            files=(DECLARATIONS, AUTHOR_PACKET, METADATA_TEMPLATE),
            tokens=(
                "AUTHOR INPUT REQUIRED",
                "submission_metadata.json",
                "generated_author_declarations.md",
                "Competing Interests",
                "Data Availability",
                "Code Availability",
                "AI-Assisted Writing or Coding Statement",
            ),
            manifest_path=METADATA_CLOSURE,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The declarations packet is a structured intake path rather than a hidden or implicit author task.",
            boundary="Final authorship, funding, conflicts, archive links, and AI disclosure remain human-gated.",
        ),
        PacketSpec(
            item="Venue policy gate is visible before upload",
            upload_risk="Target venue style, anonymous review, AI disclosure, or archive policy could be missed.",
            files=(VENUE, CHECKLIST, AUTHOR_PACKET),
            tokens=(
                "target_venue.name",
                "target_venue.manuscript_type",
                "anonymous_review_required",
                "ai_disclosure_policy_checked",
                "Target venue decision audit",
                "recommended_first_choice",
                "fit_score",
                "source_url",
                "ACM Transactions on Quantum Computing",
                "Quantum",
                "IEEE Transactions on Quantum Engineering",
                "TCAD",
            ),
            manifest_path=TARGET_VENUE_DECISION,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The venue-choice step is concrete enough for the author to fill the private metadata file.",
            boundary="The audit does not choose the journal; it only checks that the choice is explicit and policy-gated.",
        ),
        PacketSpec(
            item="Private preview path remains safe",
            upload_risk="Generated cover-letter/declaration previews could leak private metadata into Git or the payload.",
            files=(DECLARATIONS, README, FINAL_HANDOFF),
            tokens=(
                "generated_cover_letter.md",
                "generated_submission_text.md",
                "private",
                "ignored by Git",
                "validate_submission_metadata.py",
            ),
            manifest_path=TEXT_PREVIEW,
            manifest_key="private_outputs_are_git_ignored",
            expected=True,
            supported_use="Authors can generate private submission-system text after filling metadata without committing it.",
            boundary="Tracked audit outputs remain public and redacted; private generated Markdown files stay ignored.",
        ),
        PacketSpec(
            item="Anonymous-review fork is not conflated with author version",
            upload_risk="A double-blind venue could receive author-labeled material or non-anonymous links.",
            files=(FINAL_HANDOFF, CHECKLIST, DECLARATIONS),
            tokens=(
                "double-blind",
                "anonymous_review_required",
                "anonymous review link",
                "author-labeled",
            ),
            manifest_path=ANONYMOUS_REVIEW,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The support packet separates the current author-labeled manuscript from the venue-dependent anonymous path.",
            boundary="Anonymous-review policy and anonymous archive links still require target-venue input.",
        ),
        PacketSpec(
            item="Editor and reviewer triage is aligned",
            upload_risk="Cover letter, editor brief, and reviewer brief could emphasize different claims or boundaries.",
            files=(COVER, EDITOR_BRIEF, REVIEWER_BRIEF),
            tokens=(
                "comparison boundaries",
                "Recommended Editorial Reading Path",
                "Baseline comparability audit",
                "Search-control baseline audit",
                "No claim of universal",
            ),
            manifest_path=EDITORIAL_SCREENING,
            manifest_key="needs_revision_count",
            expected=0,
            supported_use="The editor-facing and reviewer-facing triage path points to the same bounded evidence package.",
            boundary="Triage briefs are navigation aids, not acceptance guarantees.",
        ),
        PacketSpec(
            item="Upload checklist cites terminal verifiers",
            upload_risk="Final upload could skip the one-command package verifier or the support-packet audit.",
            files=(CHECKLIST, README, FINAL_HANDOFF),
            tokens=(
                "rebuild_submission_package.sh",
                "verify_submission_package.sh",
                "analysis_submission_package_verifier.md",
                "analysis_submission_support_packet_audit.md",
            ),
            manifest_path=None,
            manifest_key="",
            expected=0,
            supported_use="The public handoff points authors to the same terminal checks used by the repository.",
            boundary="The checklist cannot replace final venue-system proof review.",
        ),
    ]


def evaluate(spec: PacketSpec) -> dict[str, str]:
    missing_files = [rel(path) for path in spec.files if not path.exists()]
    hits, missing_tokens = token_hits(spec.files, spec.tokens)
    ok, manifest_evidence = manifest_ok(spec.manifest_path, spec.manifest_key, spec.expected)
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
        "upload_risk": spec.upload_risk,
        "evidence": evidence,
        "supported_use": spec.supported_use,
        "boundary": spec.boundary,
        "next_action": "No action needed." if status == "pass" else "Restore missing support-packet anchors or rerun upstream audits.",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "upload_risk", "evidence", "supported_use", "boundary", "next_action"]
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
        "# Submission Support Packet Audit",
        "",
        "This audit checks the public cover-letter, declaration, venue, checklist, handoff, and editor/reviewer support packet before final author metadata is filled.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "## Packet Matrix", "", "| item | status | upload risk | evidence | supported use | boundary |", "|---|---|---|---|---|---|"])
    for row in rows:
        safe = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append("| {item} | {status} | {upload_risk} | {evidence} | {supported_use} | {boundary} |".format(**safe))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.11\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.25\linewidth}}",
        r"\toprule",
        r"Support-packet item & Status & Supported use & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(row["item"]),
                    tex_escape(row["status"]),
                    tex_escape(row["supported_use"]),
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
            "summary": "results/summary_submission_support_packet_audit.csv",
            "analysis": "results/analysis_submission_support_packet_audit.md",
            "manifest": "results/manifest_submission_support_packet_audit.json",
            "table": "paper_latex/tables/submission_support_packet_audit.tex",
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = [evaluate(spec) for spec in specs()]
    write_csv(RESULTS / "summary_submission_support_packet_audit.csv", rows)
    write_markdown(RESULTS / "analysis_submission_support_packet_audit.md", rows)
    write_latex(TABLES / "submission_support_packet_audit.tex", rows)
    write_manifest(RESULTS / "manifest_submission_support_packet_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} submission support packet audit rows")
    if failures:
        print(f"warning: {failures} submission support packet row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
