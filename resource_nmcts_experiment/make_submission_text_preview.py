#!/usr/bin/env python3
"""Generate private submission-system text from filled metadata.

The input `submission_package/submission_metadata.json` is intentionally
ignored by Git.  When all required fields are filled, this script writes
private Markdown previews for author declarations, availability statements,
and the cover letter.  Public audit outputs record only status, missing field
names, and generated file paths, never the private values.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from analyze_submission_metadata_audit import (
    METADATA_FILE,
    METADATA_TEMPLATE,
    REQUIRED_METADATA_PATHS,
    SUBMISSION_PACKAGE,
    THIS_DIR,
    has_author_placeholder,
    read_json,
    rel,
    value_at,
)


RESULTS = THIS_DIR / "results"

AUTHOR_DECLARATIONS = SUBMISSION_PACKAGE / "generated_author_declarations.md"
AVAILABILITY_STATEMENTS = SUBMISSION_PACKAGE / "generated_availability_statements.md"
COVER_LETTER = SUBMISSION_PACKAGE / "generated_cover_letter.md"
SUBMISSION_TEXT = SUBMISSION_PACKAGE / "generated_submission_text.md"
PRIVATE_OUTPUTS = (AUTHOR_DECLARATIONS, AVAILABILITY_STATEMENTS, COVER_LETTER, SUBMISSION_TEXT)
VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"


def stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "; ".join(stringify(item) for item in value if stringify(item))
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            rendered = stringify(item)
            if rendered:
                parts.append(f"{key}: {rendered}")
        return "; ".join(parts)
    return str(value)


def md_escape(value: object) -> str:
    return stringify(value).replace("|", "\\|")


def missing_paths(data: object) -> list[str]:
    missing = {path for path in REQUIRED_METADATA_PATHS if has_author_placeholder(value_at(data, path))}
    missing.update(placeholder_paths(data))
    return sorted(missing)


def placeholder_paths(value: object, prefix: str = "") -> list[str]:
    if isinstance(value, str):
        if "AUTHOR INPUT REQUIRED" in value or not value.strip():
            return [prefix or "<root>"]
        return []
    if isinstance(value, list):
        if not value:
            return [prefix or "<root>"]
        paths: list[str] = []
        for idx, item in enumerate(value):
            child = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            paths.extend(placeholder_paths(item, child))
        return paths
    if isinstance(value, dict):
        if not value:
            return [prefix or "<root>"]
        paths = []
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(placeholder_paths(item, child))
        return paths
    return []


def clear_private_outputs() -> int:
    removed = 0
    for path in PRIVATE_OUTPUTS:
        if path.exists():
            path.unlink()
            removed += 1
    return removed


def author_rows(authors: object) -> list[str]:
    if not isinstance(authors, list):
        return []
    lines = ["| order | name | ORCID | affiliations | email | corresponding |", "|---:|---|---|---|---|---|"]
    for author in authors:
        if not isinstance(author, dict):
            continue
        lines.append(
            "| {order} | {name} | {orcid} | {affiliations} | {email} | {corresponding} |".format(
                order=md_escape(author.get("order")),
                name=md_escape(author.get("name")),
                orcid=md_escape(author.get("orcid")),
                affiliations=md_escape(author.get("affiliations")),
                email=md_escape(author.get("email")),
                corresponding=md_escape(author.get("corresponding")),
            )
        )
    return lines


def contribution_lines(data: dict[str, object]) -> list[str]:
    contributions = data.get("author_contributions", {})
    if not isinstance(contributions, dict):
        return []
    labels = {
        "conceptualization": "Conceptualization",
        "methodology": "Methodology",
        "software": "Software",
        "validation": "Validation",
        "formal_analysis": "Formal analysis",
        "investigation": "Investigation",
        "data_curation": "Data curation",
        "writing_original_draft": "Writing - original draft",
        "writing_review_editing": "Writing - review and editing",
        "visualization": "Visualization",
        "supervision": "Supervision",
        "funding_acquisition": "Funding acquisition",
    }
    return [f"- {label}: {stringify(contributions.get(key))}" for key, label in labels.items() if stringify(contributions.get(key))]


def build_author_declarations(data: dict[str, object]) -> str:
    lines = [
        "# Generated Author Declarations",
        "",
        "Private preview generated from `submission_metadata.json`. Review and adapt to the target venue before upload.",
        "",
        "## Manuscript",
        "",
        f"- Title: {stringify(value_at(data, 'manuscript.title'))}",
        f"- Scope boundary: {stringify(value_at(data, 'manuscript.scope_boundary'))}",
        "",
        "## Target Venue",
        "",
        f"- Name: {stringify(value_at(data, 'target_venue.name'))}",
        f"- Manuscript type: {stringify(value_at(data, 'target_venue.manuscript_type'))}",
        f"- Anonymous review required: {stringify(value_at(data, 'target_venue.anonymous_review_required'))}",
        "",
        "## Authors",
        "",
    ]
    lines.extend(author_rows(data.get("authors")))
    lines.extend(
        [
            "",
            "## Corresponding Author",
            "",
            f"- Name: {stringify(value_at(data, 'corresponding_author.name'))}",
            f"- Email: {stringify(value_at(data, 'corresponding_author.email'))}",
            f"- Affiliation: {stringify(value_at(data, 'corresponding_author.affiliation'))}",
            f"- Postal address: {stringify(value_at(data, 'corresponding_author.postal_address'))}",
            "",
            "## Author Contributions",
            "",
        ]
    )
    lines.extend(contribution_lines(data))
    lines.extend(
        [
            "",
            "## Funding",
            "",
            stringify(value_at(data, "funding.statement")),
            "",
            f"Grant numbers: {stringify(value_at(data, 'funding.grant_numbers'))}",
            "",
            "## Acknowledgements",
            "",
            stringify(value_at(data, "acknowledgements.statement")),
            "",
            "## Competing Interests",
            "",
            stringify(value_at(data, "competing_interests.statement")),
            "",
            "## AI-Assistance Disclosure",
            "",
            stringify(value_at(data, "ai_assistance.statement")),
            "",
            "## Preprint and Prior Submission",
            "",
            stringify(value_at(data, "preprint_and_prior_submission.statement")),
            "",
            "## Permissions",
            "",
            stringify(value_at(data, "permissions.statement")),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_availability_statements(data: dict[str, object]) -> str:
    lines = [
        "# Generated Availability Statements",
        "",
        "Private preview generated from `submission_metadata.json`. Review and adapt to the target venue before upload.",
        "",
        "## Data Availability",
        "",
        stringify(value_at(data, "data_availability.statement")),
        "",
        f"Archive link or DOI: {stringify(value_at(data, 'data_availability.archive_link_or_doi'))}",
        f"Anonymous review link: {stringify(value_at(data, 'data_availability.anonymous_review_link'))}",
        f"Access restrictions: {stringify(value_at(data, 'data_availability.access_restrictions'))}",
        "",
        "## Code Availability",
        "",
        stringify(value_at(data, "code_availability.statement")),
        "",
        f"Repository URL: {stringify(value_at(data, 'code_availability.repository_url'))}",
        f"Commit hash: {stringify(value_at(data, 'code_availability.commit_hash'))}",
        f"License: {stringify(value_at(data, 'code_availability.license'))}",
        f"Environment notes: {stringify(value_at(data, 'code_availability.environment_notes'))}",
        f"Anonymous review link: {stringify(value_at(data, 'code_availability.anonymous_review_link'))}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_cover_letter(data: dict[str, object]) -> str:
    corresponding = value_at(data, "corresponding_author.name")
    lines = [
        "# Generated Cover Letter",
        "",
        "Private preview generated from `submission_metadata.json`. Review and adapt to the target venue before upload.",
        "",
        f"Dear {stringify(value_at(data, 'cover_letter.target_editor')) or 'Editor'},",
        "",
        f'Please consider our manuscript, "{stringify(value_at(data, "manuscript.title"))}", for publication as a {stringify(value_at(data, "target_venue.manuscript_type"))} in {stringify(value_at(data, "target_venue.name"))}.',
        "",
        "This manuscript studies logical-layer synthesis of quantum Boolean bit-flip oracles. We formulate synthesis as a resource-constrained search over ANF/FPRM term sets and present Resource-NMCTS, combining neural action priors, Monte Carlo tree search, Boolean-ring actions, Pareto archives, frontier controllers, and baseline-preserving guards. The work is intentionally limited to logical resource estimation and does not claim hardware mapping, routing, native-gate scheduling, or noise-aware compilation.",
        "",
        "The submission package includes the LaTeX manuscript, generated tables and figures, raw and summary CSV files, manifest JSON files, trained local policy artifacts, tool-adapter source files, and a lightweight rebuild script.",
        "",
        stringify(value_at(data, "cover_letter.editorial_routing_statement")),
        "",
        "Suggested reviewers:",
        "",
        stringify(value_at(data, "cover_letter.suggested_reviewers")),
        "",
        "Excluded reviewers:",
        "",
        stringify(value_at(data, "cover_letter.excluded_reviewers")),
        "",
        "Prior dissemination, preprint, or related submission information:",
        "",
        stringify(value_at(data, "preprint_and_prior_submission.statement")),
        "",
        "Sincerely,",
        "",
        stringify(corresponding),
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_submission_text(data: dict[str, object]) -> str:
    parts = [
        "# Generated Submission Text Packet",
        "",
        "Private preview generated from `submission_metadata.json`. Review every section against the target venue's submission system before upload.",
        "",
        build_cover_letter(data),
        build_author_declarations(data),
        build_availability_statements(data),
    ]
    return "\n\n".join(part.rstrip() for part in parts if part.strip()) + "\n"


def write_private_outputs(data: dict[str, object]) -> list[Path]:
    outputs = {
        AUTHOR_DECLARATIONS: build_author_declarations(data),
        AVAILABILITY_STATEMENTS: build_availability_statements(data),
        COVER_LETTER: build_cover_letter(data),
        SUBMISSION_TEXT: build_submission_text(data),
    }
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    return list(outputs)


def build_rows() -> list[dict[str, str]]:
    if not METADATA_FILE.exists():
        removed = clear_private_outputs()
        return [
            {
                "item": "Private submission text preview",
                "status": "needs author input",
                "source": rel(METADATA_TEMPLATE),
                "private_outputs": "; ".join(rel(path) for path in PRIVATE_OUTPUTS),
                "evidence": f"{rel(METADATA_FILE)} is missing; removed stale private output files={removed}.",
                "next_action": "Run /opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private, or copy submission_metadata_template.json manually, fill every AUTHOR INPUT REQUIRED value, then rerun the rebuild script.",
            }
        ]

    data = read_json(METADATA_FILE)
    if not isinstance(data, dict):
        removed = clear_private_outputs()
        return [
            {
                "item": "Private submission text preview",
                "status": "needs author input",
                "source": rel(METADATA_FILE),
                "private_outputs": "; ".join(rel(path) for path in PRIVATE_OUTPUTS),
                "evidence": f"{rel(METADATA_FILE)} is not valid JSON; removed stale private output files={removed}.",
                "next_action": "Fix submission_metadata.json and rerun the rebuild script.",
            }
        ]

    missing = missing_paths(data)
    if missing:
        removed = clear_private_outputs()
        return [
            {
                "item": "Private submission text preview",
                "status": "needs author input",
                "source": rel(METADATA_FILE),
                "private_outputs": "; ".join(rel(path) for path in PRIVATE_OUTPUTS),
                "evidence": f"{len(missing)} required metadata path(s) remain incomplete; removed stale private output files={removed}.",
                "next_action": "Fill: " + "; ".join(missing[:8]) + ("; ..." if len(missing) > 8 else ""),
            }
        ]

    validator = read_json(VALIDATOR_MANIFEST)
    needs_revision = int(validator.get("needs_revision_count", -1)) if isinstance(validator, dict) else -1
    if needs_revision != 0:
        removed = clear_private_outputs()
        return [
            {
                "item": "Private submission text preview",
                "status": "needs revision",
                "source": rel(METADATA_FILE),
                "private_outputs": "; ".join(rel(path) for path in PRIVATE_OUTPUTS),
                "evidence": f"Metadata validator reports needs_revision_count={needs_revision}; removed stale private output files={removed}.",
                "next_action": "Fix results/analysis_submission_metadata_validator.md rows, rerun the rebuild script, then review generated private preview files.",
            }
        ]

    outputs = write_private_outputs(data)
    return [
        {
            "item": "Private submission text preview",
            "status": "pass",
            "source": rel(METADATA_FILE),
            "private_outputs": "; ".join(rel(path) for path in outputs),
            "evidence": f"Generated {len(outputs)} ignored private Markdown preview file(s); no private values are written to tracked audit outputs.",
            "next_action": "Review generated_*.md against the target venue submission system before upload.",
        }
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "source", "private_outputs", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Submission Text Preview",
        "",
        "This audit records whether private author/venue metadata was sufficient to generate ignored Markdown previews for the submission system.",
        "",
        "Tracked outputs intentionally do not include author names, emails, funding details, or venue-private text.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | source | private outputs | evidence | next action |", "|---|---|---|---|---|---|"])
    for row in rows:
        lines.append(
            "| {item} | {status} | `{source}` | {private_outputs} | {evidence} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in row.items()}
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
        "private_output_paths": [rel(path) for path in PRIVATE_OUTPUTS],
        "private_outputs_are_git_ignored": True,
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_submission_text_preview.csv"),
            "analysis": rel(RESULTS / "analysis_submission_text_preview.md"),
            "manifest": rel(RESULTS / "manifest_submission_text_preview.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_text_preview.csv", rows)
    write_markdown(RESULTS / "analysis_submission_text_preview.md", rows)
    write_manifest(RESULTS / "manifest_submission_text_preview.json", rows)
    print(f"wrote {len(rows)} submission text preview row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
