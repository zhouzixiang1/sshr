#!/usr/bin/env python3
"""Audit the author/venue input closure path.

The remaining submission gate is intentionally human-gated: author order,
venue policy, declarations, archive links, and double-blind choices cannot be
derived from experiments.  This audit verifies that the manual gate is still
complete, private, and visible across the public support package.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from analyze_submission_metadata_audit import (
    METADATA_FILE,
    METADATA_TEMPLATE,
    REQUIRED_METADATA_PATHS,
    RESULTS,
    SUBMISSION_PACKAGE,
    THIS_DIR,
    read_json,
    rel,
)


AUTHOR_PACKET = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
AUTHOR_QUESTIONNAIRE_ZH = SUBMISSION_PACKAGE / "AUTHOR_METADATA_QUESTIONNAIRE_zh.md"
AUTHOR_MINIMAL_FORM_ZH = SUBMISSION_PACKAGE / "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md"
METADATA_ANSWERS_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_answers_template.json"
METADATA_ANSWERS_FILE = SUBMISSION_PACKAGE / "submission_metadata_answers.json"
FINAL_HANDOFF = SUBMISSION_PACKAGE / "FINAL_SUBMISSION_HANDOFF_zh.md"
README = SUBMISSION_PACKAGE / "README.md"
CHECKLIST = SUBMISSION_PACKAGE / "submission_checklist.md"
TARGET_POLICY_CHECKLIST_ZH = SUBMISSION_PACKAGE / "TARGET_VENUE_POLICY_CHECKLIST_zh.md"
AUTHOR_TEMPLATE = SUBMISSION_PACKAGE / "author_declarations_template.md"
COVER_TEMPLATE = SUBMISSION_PACKAGE / "cover_letter_template.md"
METADATA_AUDIT_MANIFEST = RESULTS / "manifest_submission_metadata_audit.json"
AUTHOR_PACKET_MANIFEST = RESULTS / "manifest_author_input_packet.json"
VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
TEXT_PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
ANONYMOUS_REVIEW_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
ANSWER_TEMPLATE_COVERAGE_MANIFEST = RESULTS / "manifest_metadata_answer_template_coverage.json"

PRIVATE_OUTPUTS = (
    METADATA_ANSWERS_FILE,
    METADATA_FILE,
    SUBMISSION_PACKAGE / "generated_author_declarations.md",
    SUBMISSION_PACKAGE / "generated_availability_statements.md",
    SUBMISSION_PACKAGE / "generated_cover_letter.md",
    SUBMISSION_PACKAGE / "generated_submission_text.md",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def placeholder_paths(value: object, prefix: str = "") -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [prefix or "<root>"] if not stripped or stripped == "AUTHOR INPUT REQUIRED" else []
    if isinstance(value, list):
        if not value:
            return [prefix or "<root>"]
        paths: list[str] = []
        for item in value:
            child = f"{prefix}[]" if prefix else "[]"
            paths.extend(placeholder_paths(item, child))
        return paths
    if isinstance(value, dict):
        if not value:
            return [prefix or "<root>"]
        paths: list[str] = []
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(placeholder_paths(item, child))
        return paths
    return []


def covered_by_required(path: str) -> bool:
    for required in REQUIRED_METADATA_PATHS:
        if path == required:
            return True
        if path.startswith(required + ".") or path.startswith(required + "["):
            return True
        if path.startswith(required + "[]"):
            return True
    return False


def git_success(args: list[str]) -> bool:
    proc = subprocess.run(
        ["git", *args],
        cwd=THIS_DIR,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=10,
    )
    return proc.returncode == 0


def inside_git_repo() -> bool:
    return git_success(["rev-parse", "--is-inside-work-tree"])


def manifest_counts(path: Path) -> dict[str, int]:
    data = read_json(path)
    counts = data.get("status_counts", {}) if isinstance(data, dict) else {}
    return {str(key): int(value) for key, value in counts.items()} if isinstance(counts, dict) else {}


def metadata_gate_filled() -> bool:
    validator = read_json(VALIDATOR_MANIFEST)
    if not isinstance(validator, dict):
        return False
    return bool(METADATA_FILE.exists()) and int(validator.get("needs_revision_count", -1)) == 0 and int(
        validator.get("needs_author_input_count", -1)
    ) == 0


def check_template_placeholder_coverage() -> dict[str, str]:
    template = read_json(METADATA_TEMPLATE)
    if not isinstance(template, dict):
        return row(
            "Metadata template placeholder coverage",
            "needs revision",
            f"{rel(METADATA_TEMPLATE)} is missing or invalid JSON.",
            "Restore the metadata template before author intake.",
        )
    placeholders = sorted(set(placeholder_paths(template)))
    uncovered = sorted(path for path in placeholders if not covered_by_required(path))
    return row(
        "Metadata template placeholder coverage",
        "pass" if not uncovered else "needs revision",
        f"placeholders={len(placeholders)}; required_paths={len(REQUIRED_METADATA_PATHS)}; uncovered={uncovered or 'none'}.",
        "Add every template AUTHOR INPUT REQUIRED path to REQUIRED_METADATA_PATHS, or cover it with an explicit parent field.",
    )


def check_author_packet_coverage() -> dict[str, str]:
    text = read_text(AUTHOR_PACKET)
    missing = sorted(path for path in REQUIRED_METADATA_PATHS if path not in text)
    manifest = read_json(AUTHOR_PACKET_MANIFEST)
    needs = manifest.get("needs_author_input", "missing") if isinstance(manifest, dict) else "missing"
    return row(
        "Author packet required-field coverage",
        "pass" if AUTHOR_PACKET.exists() and not missing else "needs revision",
        f"packet_exists={AUTHOR_PACKET.exists()}; required_paths={len(REQUIRED_METADATA_PATHS)}; missing={missing[:8] or 'none'}; needs_author_input={needs}.",
        "Rerun make_author_input_packet.py after changing metadata requirements.",
    )


def check_answer_template_coverage() -> dict[str, str]:
    manifest = read_json(ANSWER_TEMPLATE_COVERAGE_MANIFEST)
    counts = manifest.get("status_counts", {}) if isinstance(manifest, dict) else {}
    revisions = int(manifest.get("needs_revision_count", -1)) if isinstance(manifest, dict) else -1
    missing = manifest.get("missing_required_paths", "missing") if isinstance(manifest, dict) else "missing"
    unknown = manifest.get("unknown_answer_paths", "missing") if isinstance(manifest, dict) else "missing"
    starter_only = manifest.get("starter_only_required_paths", "missing") if isinstance(manifest, dict) else "missing"
    status = "pass" if manifest and revisions == 0 and not missing and not unknown else "needs revision"
    return row(
        "Answer-template required-field coverage",
        status,
        f"required_paths={len(REQUIRED_METADATA_PATHS)}; starter_only={starter_only}; missing={missing}; unknown_answer_paths={unknown}; status_counts={counts}; needs_revision_count={revisions}.",
        "Rerun analyze_metadata_answer_template_coverage.py after changing required metadata paths, starter prefill fields, or submission_metadata_answers_template.json.",
    )


def check_support_document_visibility() -> dict[str, str]:
    required_docs = (
        FINAL_HANDOFF,
        README,
        CHECKLIST,
        AUTHOR_TEMPLATE,
        COVER_TEMPLATE,
        AUTHOR_QUESTIONNAIRE_ZH,
        AUTHOR_MINIMAL_FORM_ZH,
        TARGET_POLICY_CHECKLIST_ZH,
        METADATA_ANSWERS_TEMPLATE,
    )
    missing_docs = [rel(path) for path in required_docs if not path.exists()]
    tokens = {
        rel(FINAL_HANDOFF): ("AUTHOR_INPUT_REQUIRED.md", "submission_metadata.json", "needs author input"),
        rel(README): ("AUTHOR_INPUT_REQUIRED.md", "AUTHOR_METADATA_QUESTIONNAIRE_zh.md", "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md", "submission_metadata.json", "generated private previews"),
        rel(CHECKLIST): ("Required Author Input", "AUTHOR_METADATA_QUESTIONNAIRE_zh.md", "AUTHOR INPUT REQUIRED", "verify_submission_package.sh"),
        rel(AUTHOR_TEMPLATE): ("AUTHOR INPUT REQUIRED", "Code Availability", "Competing Interests"),
        rel(COVER_TEMPLATE): ("AUTHOR INPUT REQUIRED", "logical-layer", "SSHR"),
        rel(AUTHOR_QUESTIONNAIRE_ZH): ("target_venue.name", "authors[].name", "validate_submission_metadata.py"),
        rel(AUTHOR_MINIMAL_FORM_ZH): ("target_venue.*", "authors[]", "code_availability.*", "validate_submission_metadata.py"),
        rel(TARGET_POLICY_CHECKLIST_ZH): ("目标期刊政策核对表", "target_venue.ai_disclosure_policy_checked", "data_availability.*", "code_availability.*"),
        rel(METADATA_ANSWERS_TEMPLATE): ("target_venue", "authors", "code_availability", "AUTHOR INPUT REQUIRED"),
    }
    missing_tokens: list[str] = []
    for doc_rel, doc_tokens in tokens.items():
        text = read_text(THIS_DIR / doc_rel)
        for token in doc_tokens:
            if token not in text:
                missing_tokens.append(f"{doc_rel}:{token}")
    status = "pass" if not missing_docs and not missing_tokens else "needs revision"
    return row(
        "Support document author-gate visibility",
        status,
        f"missing_docs={missing_docs or 'none'}; missing_tokens={missing_tokens or 'none'}.",
        "Keep README, checklist, handoff, declaration template, cover-letter template, questionnaire, minimal response form, target-venue policy checklist, and answer template aligned with the private metadata workflow.",
    )


def check_private_git_protection() -> dict[str, str]:
    if not inside_git_repo():
        existing_private = [rel(path) for path in PRIVATE_OUTPUTS if path.exists()]
        return row(
            "Private author metadata git protection",
            "pass" if not existing_private else "needs revision",
            f"inside_git_repo=False; existing_private={existing_private or 'none'}.",
            "When this audit runs from an extracted payload, private metadata files must be absent.",
        )
    not_ignored = [rel(path) for path in PRIVATE_OUTPUTS if not git_success(["check-ignore", rel(path)])]
    tracked = [rel(path) for path in PRIVATE_OUTPUTS if git_success(["ls-files", "--error-unmatch", rel(path)])]
    existing_private = [rel(path) for path in PRIVATE_OUTPUTS if path.exists()]
    return row(
        "Private author metadata git protection",
        "pass" if not not_ignored and not tracked else "needs revision",
        f"ignored={len(PRIVATE_OUTPUTS) - len(not_ignored)}/{len(PRIVATE_OUTPUTS)}; tracked={tracked or 'none'}; existing_private={existing_private or 'none'}.",
        "Keep submission_metadata_answers.json, submission_metadata.json, and generated private previews ignored and untracked.",
    )


def check_validator_and_preview_gate() -> dict[str, str]:
    validator_counts = manifest_counts(VALIDATOR_MANIFEST)
    preview = read_json(TEXT_PREVIEW_MANIFEST)
    preview_counts = manifest_counts(TEXT_PREVIEW_MANIFEST)
    ignored = bool(preview.get("private_outputs_are_git_ignored", False)) if isinstance(preview, dict) else False
    filled = metadata_gate_filled()
    validator_ok = validator_counts.get("needs revision", 0) == 0 and (
        filled or validator_counts.get("needs author input", 0) >= 1
    )
    preview_ok = ignored and preview_counts.get("needs revision", 0) == 0 and (
        filled or preview_counts.get("needs author input", 0) >= 1
    )
    return row(
        "Validator and private-preview gate",
        "pass" if validator_ok and preview_ok else "needs revision",
        f"metadata_filled={filled}; validator_counts={validator_counts}; preview_counts={preview_counts}; private_outputs_are_git_ignored={ignored}.",
        "Rerun validate_submission_metadata.py and make_submission_text_preview.py; fix needs-revision rows before upload.",
    )


def check_anonymous_review_gate() -> dict[str, str]:
    manifest = read_json(ANONYMOUS_REVIEW_MANIFEST)
    counts = manifest_counts(ANONYMOUS_REVIEW_MANIFEST)
    revisions = int(manifest.get("needs_revision_count", -1)) if isinstance(manifest, dict) else -1
    needs_author = int(manifest.get("needs_author_input_count", -1)) if isinstance(manifest, dict) else -1
    return row(
        "Anonymous-review decision gate",
        "pass" if manifest and revisions == 0 and needs_author >= 0 else "needs revision",
        f"needs_revision_count={revisions}; needs_author_input_count={needs_author}; status_counts={counts}.",
        "Keep the anonymous-review audit aligned with target_venue.anonymous_review_required and anonymous artifact-link instructions.",
    )


def check_metadata_audit_consistency() -> dict[str, str]:
    metadata_counts = manifest_counts(METADATA_AUDIT_MANIFEST)
    author_packet = read_json(AUTHOR_PACKET_MANIFEST)
    author_needs = int(author_packet.get("needs_author_input", -1)) if isinstance(author_packet, dict) else -1
    metadata_needs = metadata_counts.get("needs author input", 0)
    status = "pass" if metadata_needs == author_needs and metadata_needs >= 0 else "needs revision"
    return row(
        "Metadata audit and packet count consistency",
        status,
        f"metadata_counts={metadata_counts}; author_packet_needs_author_input={author_needs}.",
        "Rerun analyze_submission_metadata_audit.py and make_author_input_packet.py if counts diverge.",
    )


def build_rows() -> list[dict[str, str]]:
    return [
        check_template_placeholder_coverage(),
        check_answer_template_coverage(),
        check_author_packet_coverage(),
        check_support_document_visibility(),
        check_private_git_protection(),
        check_validator_and_preview_gate(),
        check_anonymous_review_gate(),
        check_metadata_audit_consistency(),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    lines = [
        "# Author Input Closure Audit",
        "",
        "This audit verifies that the remaining author- and venue-specific gate is complete, private, and visible across the submission package.",
        "",
        "It does not require private author metadata to be present; it checks that the manual path is ready and cannot leak into Git or the payload.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "required_metadata_paths": len(REQUIRED_METADATA_PATHS),
        "metadata_present": METADATA_FILE.exists(),
        "metadata_gate_filled": metadata_gate_filled(),
        "status_counts": dict(counts),
        "needs_revision_count": counts.get("needs revision", 0),
        "rows_detail": rows,
        "private_outputs": [rel(path) for path in PRIVATE_OUTPUTS],
        "outputs": {
            "summary": rel(RESULTS / "summary_author_input_closure_audit.csv"),
            "analysis": rel(RESULTS / "analysis_author_input_closure_audit.md"),
            "manifest": rel(RESULTS / "manifest_author_input_closure_audit.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_author_input_closure_audit.csv", rows)
    write_markdown(RESULTS / "analysis_author_input_closure_audit.md", rows)
    write_manifest(RESULTS / "manifest_author_input_closure_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} author-input closure audit row(s)")
    if failures:
        print(f"warning: {failures} author-input closure row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
