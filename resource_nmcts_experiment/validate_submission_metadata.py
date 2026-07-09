#!/usr/bin/env python3
"""Validate private submission metadata without leaking private values.

The metadata audit enumerates fields that must be filled.  This validator runs
after a private `submission_metadata.json` exists and checks common
submission-time mistakes: malformed email/ORCID/URL/DOI values, unchecked venue
policy fields, inconsistent corresponding-author data, and stale code commit
hashes.  Public outputs include only field names, counts, and statuses.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

from analyze_submission_metadata_audit import (
    METADATA_FILE,
    METADATA_TEMPLATE,
    REQUIRED_METADATA_PATHS,
    THIS_DIR,
    has_author_placeholder,
    read_json,
    rel,
    value_at,
)


RESULTS = THIS_DIR / "results"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
DOI_RE = re.compile(r"^(?:https?://doi\.org/)?10\.\d{4,9}/\S+$", re.IGNORECASE)
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)

TRUTHY_FALSEY = {
    "yes",
    "no",
    "true",
    "false",
    "checked",
    "not checked",
    "not applicable",
    "n/a",
    "required",
    "not required",
}

EXPLICIT_NONE = {"none", "n/a", "not applicable", "not available", "no orcid"}


def current_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=THIS_DIR,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except Exception:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def is_missing(value: object) -> bool:
    return has_author_placeholder(value)


def as_string(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def placeholder_paths(data: object, prefix: str = "") -> list[str]:
    if isinstance(data, str):
        return [prefix or "<root>"] if "AUTHOR INPUT REQUIRED" in data or not data.strip() else []
    if isinstance(data, list):
        if not data:
            return [prefix or "<root>"]
        paths: list[str] = []
        for idx, item in enumerate(data):
            paths.extend(placeholder_paths(item, f"{prefix}[{idx}]" if prefix else f"[{idx}]"))
        return paths
    if isinstance(data, dict):
        if not data:
            return [prefix or "<root>"]
        paths = []
        for key, item in data.items():
            paths.extend(placeholder_paths(item, f"{prefix}.{key}" if prefix else str(key)))
        return paths
    return []


def row(item: str, status: str, evidence: str, next_action: str, fields: list[str] | None = None) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "field_names": "; ".join(fields or []),
        "evidence": evidence,
        "next_action": next_action,
    }


def check_required_completeness(data: object) -> dict[str, str]:
    missing = {path for path in REQUIRED_METADATA_PATHS if is_missing(value_at(data, path))}
    missing.update(placeholder_paths(data))
    missing_list = sorted(missing)
    return row(
        "Required metadata completeness",
        "needs author input" if missing_list else "pass",
        f"{len(missing_list)} required or placeholder field(s) remain incomplete.",
        "Fill every AUTHOR INPUT REQUIRED field before generating final submission text.",
        missing_list[:12] + (["..."] if len(missing_list) > 12 else []),
    )


def check_target_policy_fields(data: object) -> dict[str, str]:
    fields = [
        "target_venue.formatting_policy_checked",
        "target_venue.reference_style_checked",
        "target_venue.word_limit_checked",
        "target_venue.supplementary_material_policy_checked",
        "target_venue.ai_disclosure_policy_checked",
        "target_venue.anonymous_review_required",
        "permissions.third_party_material_confirmed",
    ]
    bad: list[str] = []
    for field in fields:
        value = value_at(data, field)
        if isinstance(value, bool):
            continue
        normalized = as_string(value).lower()
        if normalized not in TRUTHY_FALSEY:
            bad.append(field)
    return row(
        "Target policy flags",
        "needs revision" if bad else "pass",
        f"{len(fields) - len(bad)}/{len(fields)} policy flag(s) are parseable as checked/yes/no/not-applicable values.",
        "Use explicit yes/no/checked/not applicable wording for target-venue policy fields.",
        bad,
    )


def check_author_structure(data: object) -> dict[str, str]:
    authors = value_at(data, "authors")
    if not isinstance(authors, list) or not authors:
        return row("Author list structure", "needs revision", "Author list is missing or not a non-empty list.", "Provide at least one author object.", ["authors"])
    bad: list[str] = []
    orders: list[int] = []
    corresponding_count = 0
    for idx, author in enumerate(authors):
        if not isinstance(author, dict):
            bad.append(f"authors[{idx}]")
            continue
        order = author.get("order")
        try:
            orders.append(int(str(order).strip()))
        except Exception:
            bad.append(f"authors[{idx}].order")
        for key in ("name", "affiliations", "email", "corresponding"):
            if is_missing(author.get(key)):
                bad.append(f"authors[{idx}].{key}")
        corr = as_string(author.get("corresponding")).lower()
        if corr in {"yes", "true", "1", "corresponding"}:
            corresponding_count += 1
    if sorted(orders) != list(range(1, len(authors) + 1)):
        bad.append("authors.order_sequence")
    if corresponding_count < 1:
        bad.append("authors.corresponding")
    return row(
        "Author list structure",
        "needs revision" if bad else "pass",
        f"{len(authors)} author row(s) checked; corresponding_count={corresponding_count}.",
        "Use sequential author order values and mark at least one corresponding author.",
        bad,
    )


def check_author_contact_formats(data: object) -> dict[str, str]:
    authors = value_at(data, "authors")
    bad: list[str] = []
    if isinstance(authors, list):
        for idx, author in enumerate(authors):
            if not isinstance(author, dict):
                continue
            email = as_string(author.get("email"))
            if not EMAIL_RE.match(email):
                bad.append(f"authors[{idx}].email")
            orcid = as_string(author.get("orcid"))
            if orcid.lower() not in EXPLICIT_NONE and not ORCID_RE.match(orcid):
                bad.append(f"authors[{idx}].orcid")
    corr_email = as_string(value_at(data, "corresponding_author.email"))
    if not EMAIL_RE.match(corr_email):
        bad.append("corresponding_author.email")
    return row(
        "Author contact formats",
        "needs revision" if bad else "pass",
        "Email and ORCID-like fields checked without exposing values.",
        "Use valid email addresses and ORCID format 0000-0000-0000-0000, or an explicit no-ORCID statement if allowed by the venue.",
        bad,
    )


def check_corresponding_author_consistency(data: object) -> dict[str, str]:
    authors = value_at(data, "authors")
    corr_name = as_string(value_at(data, "corresponding_author.name")).lower()
    corr_email = as_string(value_at(data, "corresponding_author.email")).lower()
    matched = False
    if isinstance(authors, list):
        for author in authors:
            if not isinstance(author, dict):
                continue
            if as_string(author.get("name")).lower() == corr_name and as_string(author.get("email")).lower() == corr_email:
                matched = True
                break
    return row(
        "Corresponding author consistency",
        "needs revision" if not matched else "pass",
        "Corresponding-author name/email are checked against the author list without exposing values.",
        "Ensure corresponding_author.name/email match one author entry.",
        [] if matched else ["corresponding_author.name", "corresponding_author.email", "authors"],
    )


def check_links(data: object) -> dict[str, str]:
    fields = [
        "data_availability.archive_link_or_doi",
        "data_availability.anonymous_review_link",
        "code_availability.repository_url",
        "code_availability.anonymous_review_link",
        "preprint_and_prior_submission.preprint_url_or_doi",
    ]
    bad: list[str] = []
    explicit_none_count = 0
    for field in fields:
        value = as_string(value_at(data, field))
        lower = value.lower()
        if lower in EXPLICIT_NONE:
            explicit_none_count += 1
            continue
        if not (URL_RE.match(value) or DOI_RE.match(value)):
            bad.append(field)
    return row(
        "Availability and repository links",
        "needs revision" if bad else "pass",
        f"{len(fields) - len(bad)}/{len(fields)} link-like field(s) are URL/DOI or explicit none; explicit_none_count={explicit_none_count}.",
        "Use https URLs, DOI strings, or explicit none/not-applicable statements for optional links.",
        bad,
    )


def check_code_commit(data: object) -> dict[str, str]:
    value = as_string(value_at(data, "code_availability.commit_hash"))
    head = current_head()
    bad: list[str] = []
    if not COMMIT_RE.match(value):
        bad.append("code_availability.commit_hash")
    elif head and not (head.startswith(value.lower()) or value.lower().startswith(head)):
        bad.append("code_availability.commit_hash")
    return row(
        "Code commit hash",
        "needs revision" if bad else "pass",
        "Commit hash is checked for hex format and consistency with the current checkout.",
        "Use the final pushed commit hash for the uploaded code/archive.",
        bad,
    )


def check_statement_lengths(data: object) -> dict[str, str]:
    fields = [
        "funding.statement",
        "acknowledgements.statement",
        "competing_interests.statement",
        "data_availability.statement",
        "code_availability.statement",
        "ai_assistance.statement",
        "preprint_and_prior_submission.statement",
        "cover_letter.editorial_routing_statement",
    ]
    bad = [field for field in fields if len(as_string(value_at(data, field)).split()) < 3]
    return row(
        "Submission statements",
        "needs revision" if bad else "pass",
        f"{len(fields) - len(bad)}/{len(fields)} prose statement field(s) have at least three words.",
        "Use explicit venue-ready prose rather than terse placeholders.",
        bad,
    )


def build_rows() -> list[dict[str, str]]:
    if not METADATA_TEMPLATE.exists():
        return [
            row(
                "Metadata template",
                "needs revision",
                f"{rel(METADATA_TEMPLATE)} is missing.",
                "Restore submission_metadata_template.json.",
                ["submission_metadata_template.json"],
            )
        ]
    if not METADATA_FILE.exists():
        return [
            row(
                "Metadata file presence",
                "needs author input",
                f"{rel(METADATA_FILE)} is missing.",
                "Copy submission_metadata_template.json to submission_metadata.json, fill it, and rerun the rebuild.",
                ["submission_metadata.json"],
            )
        ]
    data = read_json(METADATA_FILE)
    if not isinstance(data, dict):
        return [
            row(
                "Metadata JSON syntax",
                "needs revision",
                f"{rel(METADATA_FILE)} exists but is not valid JSON.",
                "Fix JSON syntax before upload.",
                ["submission_metadata.json"],
            )
        ]
    completeness = check_required_completeness(data)
    rows = [completeness]
    if completeness["status"] != "pass":
        return rows
    rows.extend(
        [
            check_target_policy_fields(data),
            check_author_structure(data),
            check_author_contact_formats(data),
            check_corresponding_author_consistency(data),
            check_links(data),
            check_code_commit(data),
            check_statement_lengths(data),
        ]
    )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "field_names", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Submission Metadata Validator",
        "",
        "This audit validates private `submission_metadata.json` without exposing private values in tracked outputs.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | field names | evidence | next action |", "|---|---|---|---|---|"])
    for item in rows:
        lines.append(
            "| {item} | {status} | {field_names} | {evidence} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "metadata_present": METADATA_FILE.exists(),
        "metadata_private": True,
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "needs_author_input_count": counts.get("needs author input", 0),
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_submission_metadata_validator.csv"),
            "analysis": rel(RESULTS / "analysis_submission_metadata_validator.md"),
            "manifest": rel(RESULTS / "manifest_submission_metadata_validator.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_metadata_validator.csv", rows)
    write_markdown(RESULTS / "analysis_submission_metadata_validator.md", rows)
    write_manifest(RESULTS / "manifest_submission_metadata_validator.json", rows)
    print(f"wrote {len(rows)} submission metadata validator row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
