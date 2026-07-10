#!/usr/bin/env python3
"""Generate a private final upload plan from filled submission metadata.

The generated upload plan is a local author-facing checklist.  It is written to
`submission_package/generated_upload_plan.md`, which is ignored by Git.  Public
audit outputs record only status, route labels, file counts, and missing-field
names; they never include private author names, e-mail addresses, funding text,
or venue-specific cover-letter text.
"""
from __future__ import annotations

import argparse
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
DEFAULT_OUTPUT = SUBMISSION_PACKAGE / "generated_upload_plan.md"
VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
UPLOAD_BUNDLE_MANIFEST = RESULTS / "manifest_upload_bundle_matrix_audit.json"

SUMMARY = RESULTS / "summary_final_upload_plan.csv"
ANALYSIS = RESULTS / "analysis_final_upload_plan.md"
MANIFEST = RESULTS / "manifest_final_upload_plan.json"

AUTHOR_FILES = (
    "paper_latex/resource_nmcts_submission_v1.pdf",
    "paper_latex/resource_nmcts_submission_v1.tex",
)
GENERIC_ANONYMOUS_FILES = (
    "paper_latex/resource_nmcts_submission_anonymous.pdf",
    "paper_latex/resource_nmcts_submission_anonymous.tex",
)
ACM_TQC_FILES = (
    "paper_latex/resource_nmcts_submission_acm_tqc.pdf",
    "paper_latex/resource_nmcts_submission_acm_tqc.tex",
)
COMMON_FILES = (
    "paper_latex/references.bib",
    "paper_latex/figures/submission_v36",
    "paper_latex/tables",
    "submission_package/dist/resource_nmcts_submission_payload.tar.gz",
    "submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256",
)
PRIVATE_PREVIEW_FILES = (
    "submission_package/generated_author_declarations.md",
    "submission_package/generated_availability_statements.md",
    "submission_package/generated_cover_letter.md",
    "submission_package/generated_submission_text.md",
)

YES = {"yes", "true", "1", "required", "double-blind", "double blind", "anonymous", "匿名", "是", "需要"}
NO = {"no", "false", "0", "not required", "single-blind", "single blind", "none", "不需要", "否"}
EXPLICIT_NONE = {"", "none", "n/a", "not applicable", "not required", "no", "false"}


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
        return "; ".join(f"{key}: {stringify(item)}" for key, item in value.items() if stringify(item))
    return str(value)


def placeholder_paths(value: object, prefix: str = "") -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped == "AUTHOR INPUT REQUIRED":
            return [prefix or "<root>"]
        return []
    if isinstance(value, list):
        if not value:
            return [prefix or "<root>"]
        paths: list[str] = []
        for idx, item in enumerate(value):
            paths.extend(placeholder_paths(item, f"{prefix}[{idx}]" if prefix else f"[{idx}]"))
        return paths
    if isinstance(value, dict):
        if not value:
            return [prefix or "<root>"]
        paths: list[str] = []
        for key, item in value.items():
            paths.extend(placeholder_paths(item, f"{prefix}.{key}" if prefix else str(key)))
        return paths
    return []


def missing_paths(data: object) -> list[str]:
    missing = {path for path in REQUIRED_METADATA_PATHS if has_author_placeholder(value_at(data, path))}
    missing.update(placeholder_paths(data))
    return sorted(missing)


def boolish(value: object) -> str:
    normalized = stringify(value).lower()
    if normalized in YES:
        return "yes"
    if normalized in NO:
        return "no"
    return "unknown"


def is_acm_tqc(metadata: dict[str, object]) -> bool:
    venue = stringify(value_at(metadata, "target_venue.name")).lower()
    return "transactions on quantum computing" in venue or "acm tqc" in venue or venue.strip() in {"tqc", "acm"}


def choose_route(metadata: dict[str, object]) -> tuple[str, tuple[str, ...], list[str]]:
    anonymous = boolish(value_at(metadata, "target_venue.anonymous_review_required"))
    route_warnings: list[str] = []
    if anonymous == "yes":
        if is_acm_tqc(metadata):
            return "acm_tqc_anonymous_review", ACM_TQC_FILES, route_warnings
        return "generic_anonymous_review", GENERIC_ANONYMOUS_FILES, route_warnings
    if anonymous == "unknown":
        route_warnings.append("target_venue.anonymous_review_required")
    return "author_labeled_submission", AUTHOR_FILES, route_warnings


def route_private_requirements(metadata: dict[str, object], route: str) -> list[str]:
    missing: list[str] = []
    if route in {"generic_anonymous_review", "acm_tqc_anonymous_review"}:
        for path in ("data_availability.anonymous_review_link", "code_availability.anonymous_review_link"):
            value = stringify(value_at(metadata, path)).lower()
            if value in EXPLICIT_NONE:
                missing.append(path)
    else:
        for path in ("data_availability.archive_link_or_doi", "code_availability.repository_url"):
            value = stringify(value_at(metadata, path)).lower()
            if value in EXPLICIT_NONE:
                missing.append(path)
    return missing


def required_existing_files(route_files: tuple[str, ...]) -> tuple[list[str], list[str]]:
    required = list(route_files) + list(COMMON_FILES)
    missing = [path for path in required if not (THIS_DIR / path).exists()]
    return required, missing


def git_ignored(path: Path) -> bool:
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "check-ignore", rel(path)],
            cwd=THIS_DIR,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except Exception:
        return False
    return proc.returncode == 0


def remove_output(output: Path) -> int:
    if output.exists():
        output.unlink()
        return 1
    return 0


def build_upload_plan(metadata: dict[str, object], route: str, route_files: tuple[str, ...]) -> str:
    title = stringify(value_at(metadata, "manuscript.title"))
    venue = stringify(value_at(metadata, "target_venue.name"))
    manuscript_type = stringify(value_at(metadata, "target_venue.manuscript_type"))
    anonymous = stringify(value_at(metadata, "target_venue.anonymous_review_required"))
    required, _ = required_existing_files(route_files)
    lines = [
        "# Generated Final Upload Plan",
        "",
        "Private local plan generated from `submission_metadata.json`. Review against the target venue before upload.",
        "",
        "## Route",
        "",
        f"- Manuscript: {title}",
        f"- Venue: {venue}",
        f"- Manuscript type: {manuscript_type}",
        f"- Anonymous review required: {anonymous}",
        f"- Selected route: `{route}`",
        "",
        "## Files To Upload Or Keep Ready",
        "",
    ]
    for path in required:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "## Private Text Previews To Review",
            "",
        ]
    )
    for path in PRIVATE_PREVIEW_FILES:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "## Upload Checks",
            "",
            "- Run `./verify_submission_package.sh` immediately before upload.",
            "- Confirm the selected route matches `results/analysis_upload_bundle_matrix_audit.md`.",
            "- Replace repository-relative availability wording with the final public archive/repository link or anonymous review link.",
            "- Keep private metadata and generated private previews out of Git and out of the public source/data payload.",
            "- Do not add hardware-mapping, routing, native-gate scheduling, noise-model, or universal-dominance claims in the submission system.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def read_manifest_counts(path: Path) -> dict[str, object]:
    data = read_json(path)
    return data.get("status_counts", {}) if isinstance(data, dict) else {}


def build_row(metadata_path: Path, output_path: Path) -> dict[str, str]:
    output_ignored = git_ignored(output_path) if output_path.is_relative_to(THIS_DIR) else True
    if not metadata_path.exists():
        removed = remove_output(output_path)
        return {
            "item": "Final upload plan",
            "status": "needs author input",
            "route": "missing_metadata",
            "private_output": str(output_path if not output_path.is_relative_to(THIS_DIR) else rel(output_path)),
            "evidence": f"metadata_missing=True; removed_stale_private_output={removed}; output_ignored={output_ignored}.",
            "next_action": "Fill ignored submission_metadata.json, then rerun make_final_upload_plan.py.",
        }

    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict):
        removed = remove_output(output_path)
        return {
            "item": "Final upload plan",
            "status": "needs revision",
            "route": "invalid_metadata",
            "private_output": str(output_path if not output_path.is_relative_to(THIS_DIR) else rel(output_path)),
            "evidence": f"metadata_valid_json=False; removed_stale_private_output={removed}; output_ignored={output_ignored}.",
            "next_action": "Fix the private metadata JSON and rerun validation.",
        }

    required_missing = missing_paths(metadata)
    if required_missing:
        removed = remove_output(output_path)
        return {
            "item": "Final upload plan",
            "status": "needs author input",
            "route": "incomplete_metadata",
            "private_output": str(output_path if not output_path.is_relative_to(THIS_DIR) else rel(output_path)),
            "evidence": f"incomplete_required_paths={len(required_missing)}; removed_stale_private_output={removed}; output_ignored={output_ignored}.",
            "next_action": "Fill: " + "; ".join(required_missing[:8]) + ("; ..." if len(required_missing) > 8 else ""),
        }

    route, route_files, route_warnings = choose_route(metadata)
    route_missing = route_private_requirements(metadata, route)
    required_files, missing_files = required_existing_files(route_files)
    validator_counts = read_manifest_counts(VALIDATOR_MANIFEST)
    preview_counts = read_manifest_counts(TEXT_PREVIEW_MANIFEST)
    bundle_counts = read_manifest_counts(UPLOAD_BUNDLE_MANIFEST)
    if route_warnings or route_missing or missing_files or not output_ignored:
        removed = remove_output(output_path)
        problems = route_warnings + route_missing + missing_files
        return {
            "item": "Final upload plan",
            "status": "needs revision",
            "route": route,
            "private_output": str(output_path if not output_path.is_relative_to(THIS_DIR) else rel(output_path)),
            "evidence": f"route_fields_needing_attention={problems or 'none'}; required_files={len(required_files)}; missing_files={missing_files or 'none'}; output_ignored={output_ignored}; validator_counts={validator_counts}; preview_counts={preview_counts}; bundle_counts={bundle_counts}.",
            "next_action": "Fix route metadata, required upload artifacts, or Git ignore protection before generating the final upload plan.",
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_upload_plan(metadata, route, route_files), encoding="utf-8")
    return {
        "item": "Final upload plan",
        "status": "pass",
        "route": route,
        "private_output": str(output_path if not output_path.is_relative_to(THIS_DIR) else rel(output_path)),
        "evidence": f"generated_private_plan=True; required_files={len(required_files)}; missing_files=none; output_ignored={output_ignored}; validator_counts={validator_counts}; preview_counts={preview_counts}; bundle_counts={bundle_counts}.",
        "next_action": "Review generated_upload_plan.md against the target venue and upload the listed route-specific files.",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "route", "private_output", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Final Upload Plan",
        "",
        "This public audit records whether a private route-specific upload plan can be generated from filled author/venue metadata.",
        "",
        "Tracked outputs intentionally contain only route labels, counts, and field names; the generated upload plan itself is ignored by Git.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| item | status | route | private output | evidence | next action |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        escaped = {key: value.replace("|", "\\|") for key, value in row.items()}
        lines.append(
            "| {item} | {status} | `{route}` | `{private_output}` | {evidence} | {next_action} |".format(
                **escaped
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]], output_path: Path) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    needs_revision = sum(1 for row in rows if row["status"] == "needs revision")
    generated = output_path.exists()
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "status_counts": counts,
        "needs_revision_count": needs_revision,
        "needs_author_input_count": counts.get("needs author input", 0),
        "route": rows[0]["route"] if rows else "missing",
        "generated_private_upload_plan": generated,
        "private_output_path": str(output_path if not output_path.is_relative_to(THIS_DIR) else rel(output_path)),
        "private_output_is_git_ignored": git_ignored(output_path) if output_path.is_relative_to(THIS_DIR) else True,
        "rows": rows,
        "outputs": {
            "summary": rel(SUMMARY),
            "analysis": rel(ANALYSIS),
            "manifest": rel(MANIFEST),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", default=str(METADATA_FILE), help="private metadata JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="ignored private upload-plan Markdown output")
    parser.add_argument("--summary", default=str(SUMMARY), help="public CSV audit output")
    parser.add_argument("--analysis", default=str(ANALYSIS), help="public Markdown audit output")
    parser.add_argument("--manifest", default=str(MANIFEST), help="public JSON audit output")
    args = parser.parse_args()

    metadata_path = Path(args.metadata)
    output_path = Path(args.output)
    if not metadata_path.is_absolute():
        metadata_path = THIS_DIR / metadata_path
    if not output_path.is_absolute():
        output_path = THIS_DIR / output_path

    rows = [build_row(metadata_path, output_path)]
    write_csv(Path(args.summary), rows)
    write_markdown(Path(args.analysis), rows)
    write_manifest(Path(args.manifest), rows, output_path)
    print(f"wrote {len(rows)} final upload-plan row(s)")
    return 0 if not any(row["status"] == "needs revision" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
