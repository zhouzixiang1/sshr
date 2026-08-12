#!/usr/bin/env python3
"""Audit author- and venue-specific metadata required before upload.

The scientific package can be rebuilt from local artifacts, but the final
submission still needs information that cannot be inferred from code: authors,
affiliations, funding, declarations, target-venue fields, and archive links.
This audit keeps those human-gated fields explicit and machine-checkable.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
AUTHOR_TEMPLATE = SUBMISSION_PACKAGE / "author_declarations_template.md"
COVER_TEMPLATE = SUBMISSION_PACKAGE / "cover_letter_template.md"
CHECKLIST = SUBMISSION_PACKAGE / "submission_checklist.md"
METADATA_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_template.json"
METADATA_FILE = SUBMISSION_PACKAGE / "submission_metadata.json"

REQUIRED_METADATA_PATHS = (
    "target_venue.name",
    "target_venue.manuscript_type",
    "target_venue.formatting_policy_checked",
    "target_venue.reference_style_checked",
    "target_venue.word_limit_checked",
    "target_venue.supplementary_material_policy_checked",
    "target_venue.ai_disclosure_policy_checked",
    "target_venue.anonymous_review_required",
    "authors",
    "corresponding_author.name",
    "corresponding_author.email",
    "corresponding_author.affiliation",
    "corresponding_author.postal_address",
    "author_contributions.conceptualization",
    "author_contributions.methodology",
    "author_contributions.software",
    "author_contributions.validation",
    "author_contributions.formal_analysis",
    "author_contributions.investigation",
    "author_contributions.data_curation",
    "author_contributions.writing_original_draft",
    "author_contributions.writing_review_editing",
    "author_contributions.visualization",
    "author_contributions.supervision",
    "author_contributions.funding_acquisition",
    "funding.statement",
    "funding.grant_numbers",
    "acknowledgements.statement",
    "competing_interests.statement",
    "data_availability.archive_link_or_doi",
    "data_availability.anonymous_review_link",
    "data_availability.access_restrictions",
    "data_availability.statement",
    "code_availability.repository_url",
    "code_availability.commit_hash",
    "code_availability.license",
    "code_availability.environment_notes",
    "code_availability.anonymous_review_link",
    "code_availability.statement",
    "ai_assistance.statement",
    "preprint_and_prior_submission.preprint_url_or_doi",
    "preprint_and_prior_submission.prior_submission_history",
    "preprint_and_prior_submission.related_manuscripts",
    "preprint_and_prior_submission.statement",
    "cover_letter.target_editor",
    "cover_letter.suggested_reviewers",
    "cover_letter.excluded_reviewers",
    "cover_letter.editorial_routing_statement",
    "permissions.third_party_material_confirmed",
    "permissions.statement",
)


@dataclass(frozen=True)
class MetadataBlock:
    item: str
    source: Path
    section: str
    required_fields: tuple[str, ...]
    reason: str
    next_action: str


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def extract_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def marker_count(text: str) -> int:
    return text.count("AUTHOR INPUT REQUIRED")


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def value_at(data: object, dotted_path: str) -> object:
    current = data
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def has_author_placeholder(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return not stripped or stripped == "AUTHOR INPUT REQUIRED"
    if isinstance(value, list):
        return not value or any(has_author_placeholder(item) for item in value)
    if isinstance(value, dict):
        return not value or any(has_author_placeholder(item) for item in value.values())
    return False


def structured_metadata_row() -> dict[str, str]:
    required = "; ".join(REQUIRED_METADATA_PATHS)
    if not METADATA_TEMPLATE.exists():
        return {
            "item": "Structured metadata intake file",
            "status": "missing source",
            "source": rel(METADATA_TEMPLATE),
            "required_fields": required,
            "reason": "A structured private metadata path keeps author and venue metadata from being scattered across templates.",
            "evidence": f"{rel(METADATA_TEMPLATE)} is missing.",
            "next_action": "Restore the metadata template.",
        }
    if not METADATA_FILE.exists():
        return {
            "item": "Structured metadata intake file",
            "status": "needs author input",
            "source": rel(METADATA_TEMPLATE),
            "required_fields": required,
            "reason": "A structured private metadata path keeps author and venue metadata from being scattered across templates.",
            "evidence": "Answer template and metadata template exist; create ignored submission_metadata_answers.json, fill every AUTHOR INPUT REQUIRED value, then generate submission_metadata.json.",
            "next_action": "Run `make_submission_metadata_from_answers.py --init-private-answers`, fill `submission_package/submission_metadata_answers.json`, then run `make_submission_metadata_from_answers.py --write-private` and rerun the rebuild script.",
        }
    data = read_json(METADATA_FILE)
    if data is None:
        return {
            "item": "Structured metadata intake file",
            "status": "needs author input",
            "source": rel(METADATA_FILE),
            "required_fields": required,
            "reason": "A structured private metadata path keeps author and venue metadata from being scattered across templates.",
            "evidence": f"{rel(METADATA_FILE)} exists but is not valid JSON.",
            "next_action": "Fix the JSON syntax and rerun the rebuild script.",
        }
    missing = [path for path in REQUIRED_METADATA_PATHS if has_author_placeholder(value_at(data, path))]
    if missing:
        return {
            "item": "Structured metadata intake file",
            "status": "needs author input",
            "source": rel(METADATA_FILE),
            "required_fields": required,
            "reason": "A single structured intake file keeps author and venue metadata from being scattered across templates.",
            "evidence": f"{len(missing)} required metadata path(s) are empty or still contain AUTHOR INPUT REQUIRED.",
            "next_action": "Fill: " + "; ".join(missing[:8]) + ("; ..." if len(missing) > 8 else ""),
        }
    return {
        "item": "Structured metadata intake file",
        "status": "pass",
        "source": rel(METADATA_FILE),
        "required_fields": required,
        "reason": "A single structured intake file keeps author and venue metadata from being scattered across templates.",
        "evidence": f"{rel(METADATA_FILE)} exists and all required metadata paths are filled.",
        "next_action": "Use the filled metadata to update author declarations, cover letter, and final availability text.",
    }


def blocks() -> list[MetadataBlock]:
    return [
        MetadataBlock(
            item="Author identity and affiliations",
            source=AUTHOR_TEMPLATE,
            section="Authors and Affiliations",
            required_fields=("author order", "ORCID IDs", "affiliations", "corresponding author", "emails"),
            reason="These identify the accountable authors and cannot be inferred from experiment artifacts.",
            next_action="Fill the author list, affiliations, ORCIDs, corresponding author, and email addresses.",
        ),
        MetadataBlock(
            item="CRediT author contributions",
            source=AUTHOR_TEMPLATE,
            section="Author Contributions",
            required_fields=("conceptualization", "methodology", "software", "validation", "writing", "supervision"),
            reason="Contribution roles require author confirmation.",
            next_action="Assign CRediT-style roles for every author before upload.",
        ),
        MetadataBlock(
            item="Funding statement",
            source=AUTHOR_TEMPLATE,
            section="Funding",
            required_fields=("funding sources", "grant numbers", "no-funding statement if applicable"),
            reason="Funding sources and grant numbers are external to the experiment package.",
            next_action="Insert the exact target-venue funding or no-funding wording.",
        ),
        MetadataBlock(
            item="Acknowledgements",
            source=AUTHOR_TEMPLATE,
            section="Acknowledgements",
            required_fields=("technical help", "institutional support", "people to acknowledge", "no-acknowledgement statement if applicable"),
            reason="Acknowledgements require author approval and consent where appropriate.",
            next_action="Add acknowledgements or the venue-required no-acknowledgement statement.",
        ),
        MetadataBlock(
            item="Competing interests",
            source=AUTHOR_TEMPLATE,
            section="Competing Interests",
            required_fields=("financial interests", "non-financial interests", "none-declared wording if applicable"),
            reason="Conflict-of-interest declarations must be made by the authors.",
            next_action="Insert the exact competing-interest statement required by the target venue.",
        ),
        MetadataBlock(
            item="Data availability archive link",
            source=AUTHOR_TEMPLATE,
            section="Data Availability",
            required_fields=("repository DOI or URL", "anonymous review link if needed", "access restrictions if any"),
            reason="The local artifact paths must be replaced or supplemented by a submission-time archive link.",
            next_action="Create or select the final archive/repository link and paste it into the statement.",
        ),
        MetadataBlock(
            item="Code availability and license",
            source=AUTHOR_TEMPLATE,
            section="Code Availability",
            required_fields=("repository URL", "commit hash", "license", "environment notes", "anonymous review link if needed"),
            reason="The final public or anonymous code location is a submission decision.",
            next_action="Add the final repository URL, commit hash, license, and any anonymous review link.",
        ),
        MetadataBlock(
            item="AI assistance disclosure",
            source=AUTHOR_TEMPLATE,
            section="AI-Assisted Writing or Coding Statement",
            required_fields=("venue wording", "scope of assistance", "author verification statement"),
            reason="Disclosure requirements vary by target venue and must be approved by the authors.",
            next_action="Use the venue-required disclosure wording or confirm that no disclosure is required.",
        ),
        MetadataBlock(
            item="Preprint and prior submission history",
            source=AUTHOR_TEMPLATE,
            section="Preprint and Prior Submission",
            required_fields=("preprint DOI/URL", "prior submission history", "related manuscripts"),
            reason="Editorial declarations depend on author publication history.",
            next_action="Record any preprint, previous submission, or related manuscript under review.",
        ),
        MetadataBlock(
            item="Cover-letter routing metadata",
            source=COVER_TEMPLATE,
            section="",
            required_fields=("corresponding author", "target venue", "manuscript type", "reviewer suggestions", "excluded reviewers"),
            reason="The cover letter needs venue and editorial-routing information.",
            next_action="Fill the cover-letter required fields after selecting the target venue.",
        ),
        MetadataBlock(
            item="Target-venue policy check",
            source=CHECKLIST,
            section="Required Author Input",
            required_fields=("formatting policy", "reference style", "word limit", "supplement policy", "AI disclosure policy"),
            reason="Venue-specific policies can only be finalized after the target venue is chosen.",
            next_action="Check the target venue guide and update manuscript or support files accordingly.",
        ),
    ]


def block_text(block: MetadataBlock) -> str:
    text = read_text(block.source)
    if not text:
        return ""
    if block.section:
        return extract_section(text, block.section)
    return text


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = [structured_metadata_row()]
    for block in blocks():
        text = block_text(block)
        markers = marker_count(text)
        if not block.source.exists():
            status = "missing source"
            evidence = f"{rel(block.source)} is missing."
        elif block.section and not text:
            status = "missing section"
            evidence = f"Section '{block.section}' was not found in {rel(block.source)}."
        elif markers:
            status = "needs author input"
            evidence = f"{markers} AUTHOR INPUT REQUIRED marker(s) remain in {rel(block.source)}."
        else:
            status = "pass"
            evidence = f"No AUTHOR INPUT REQUIRED marker remains in {rel(block.source)}."
        rows.append(
            {
                "item": block.item,
                "status": status,
                "source": rel(block.source),
                "required_fields": "; ".join(block.required_fields),
                "reason": block.reason,
                "evidence": evidence,
                "next_action": block.next_action,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "source", "required_fields", "reason", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Submission Metadata Audit",
        "",
        "This audit enumerates author- and venue-specific fields that cannot be inferred from the experimental artifact package.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "| item | status | source | required fields | evidence | next action |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {item} | {status} | `{source}` | {required_fields} | {evidence} | {next_action} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "status_counts": counts,
        "source_files": sorted({row["source"] for row in rows}),
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_submission_metadata_audit.csv"),
            "analysis": rel(RESULTS / "analysis_submission_metadata_audit.md"),
            "manifest": rel(RESULTS / "manifest_submission_metadata_audit.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_metadata_audit.csv", rows)
    write_markdown(RESULTS / "analysis_submission_metadata_audit.md", rows)
    write_manifest(RESULTS / "manifest_submission_metadata_audit.json", rows)
    print(f"wrote {len(rows)} submission metadata rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
