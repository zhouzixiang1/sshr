#!/usr/bin/env python3
"""Audit the final author/venue metadata closure path.

The research artifact can be rebuilt without private author information, but
the final journal upload cannot be closed until author identities, declarations,
venue policy checks, and archival links are supplied.  This audit checks that
the remaining human-gated path is explicit, private, and machine-verifiable
without writing or exposing any private values.
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
    SUBMISSION_PACKAGE,
    THIS_DIR,
    has_author_placeholder,
    read_json,
    rel,
    value_at,
)
from make_submission_metadata_starter import build_starter
from make_submission_text_preview import PRIVATE_OUTPUTS


RESULTS = THIS_DIR / "results"
AUTHOR_PACKET = SUBMISSION_PACKAGE / "AUTHOR_INPUT_REQUIRED.md"
AUTHOR_QUESTIONNAIRE_ZH = SUBMISSION_PACKAGE / "AUTHOR_METADATA_QUESTIONNAIRE_zh.md"
AUTHOR_MINIMAL_FORM_ZH = SUBMISSION_PACKAGE / "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md"
LAST_MILE_ACTION_CARD_ZH = SUBMISSION_PACKAGE / "LAST_MILE_ACTION_CARD_zh.md"
METADATA_ANSWERS_TEMPLATE = SUBMISSION_PACKAGE / "submission_metadata_answers_template.json"
METADATA_ANSWERS_FILE = SUBMISSION_PACKAGE / "submission_metadata_answers.json"
README = SUBMISSION_PACKAGE / "README.md"
CHECKLIST = SUBMISSION_PACKAGE / "submission_checklist.md"
TARGET_VENUE_BRIEF = SUBMISSION_PACKAGE / "target_venue_brief.md"
TARGET_POLICY_CHECKLIST_ZH = SUBMISSION_PACKAGE / "TARGET_VENUE_POLICY_CHECKLIST_zh.md"
FINAL_HANDOFF = SUBMISSION_PACKAGE / "FINAL_SUBMISSION_HANDOFF_zh.md"

METADATA_AUDIT_MANIFEST = RESULTS / "manifest_submission_metadata_audit.json"
VALIDATOR_MANIFEST = RESULTS / "manifest_submission_metadata_validator.json"
PREVIEW_MANIFEST = RESULTS / "manifest_submission_text_preview.json"
SELFTEST_MANIFEST = RESULTS / "manifest_submission_metadata_pipeline_selftest.json"
ANONYMOUS_MANIFEST = RESULTS / "manifest_anonymous_review_readiness.json"
AUTHOR_INPUT_CLOSURE_MANIFEST = RESULTS / "manifest_author_input_closure_audit.json"
GOAL_MANIFEST = RESULTS / "manifest_goal_completion_audit.json"
ANSWER_TEMPLATE_COVERAGE_MANIFEST = RESULTS / "manifest_metadata_answer_template_coverage.json"
MINIMAL_FORM_COVERAGE_MANIFEST = RESULTS / "manifest_author_minimal_form_coverage.json"

PRIVATE_PATHS = (METADATA_ANSWERS_FILE, METADATA_FILE, *PRIVATE_OUTPUTS)


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=THIS_DIR,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )


def in_git_worktree() -> bool:
    proc = run_git(["rev-parse", "--is-inside-work-tree"])
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def read_manifest(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


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
        paths = []
        for key, item in value.items():
            paths.extend(placeholder_paths(item, f"{prefix}.{key}" if prefix else str(key)))
        return paths
    return []


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def manifest_counts(path: Path) -> dict[str, int]:
    counts = read_manifest(path).get("status_counts", {})
    return counts if isinstance(counts, dict) else {}


def manifest_int(path: Path, key: str, default: int = -1) -> int:
    value = read_manifest(path).get(key, default)
    try:
        return int(value)
    except Exception:
        return default


def needs_revision_count(path: Path) -> int:
    manifest = read_manifest(path)
    if "needs_revision_count" in manifest:
        try:
            return int(manifest["needs_revision_count"])
        except Exception:
            return -1
    counts = manifest.get("status_counts", {}) if manifest else {}
    if isinstance(counts, dict):
        try:
            return int(counts.get("needs revision", 0))
        except Exception:
            return -1
    return -1


def check_required_inventory() -> dict[str, str]:
    data = read_json(METADATA_TEMPLATE)
    template_placeholders = placeholder_paths(data)
    uncovered = sorted(
        path
        for path in template_placeholders
        if not any(
            path == required
            or path.startswith(required + ".")
            or path.startswith(required + "[")
            or path.startswith(required + "[]")
            for required in REQUIRED_METADATA_PATHS
        )
    )
    return row(
        "Structured metadata inventory",
        "pass" if METADATA_TEMPLATE.exists() and not uncovered and len(REQUIRED_METADATA_PATHS) >= 45 else "needs revision",
        f"required_paths={len(REQUIRED_METADATA_PATHS)}; template_placeholders={len(template_placeholders)}; uncovered_placeholders={uncovered[:5] or 'none'}.",
        "Keep REQUIRED_METADATA_PATHS aligned with every AUTHOR INPUT REQUIRED field in submission_metadata_template.json.",
    )


def check_answer_template_coverage() -> dict[str, str]:
    manifest = read_manifest(ANSWER_TEMPLATE_COVERAGE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    revisions = manifest_int(ANSWER_TEMPLATE_COVERAGE_MANIFEST, "needs_revision_count")
    missing = manifest.get("missing_required_paths", "missing") if manifest else "missing"
    unknown = manifest.get("unknown_answer_paths", "missing") if manifest else "missing"
    starter_only = manifest.get("starter_only_required_paths", "missing") if manifest else "missing"
    return row(
        "Public answer-template coverage",
        "pass" if manifest and revisions == 0 and not missing and not unknown else "needs revision",
        f"status_counts={counts}; required_paths={len(REQUIRED_METADATA_PATHS)}; starter_only={starter_only}; missing={missing}; unknown_answer_paths={unknown}; needs_revision_count={revisions}.",
        "Keep the public short-answer template aligned with REQUIRED_METADATA_PATHS and the safe public starter fields.",
    )


def check_minimal_form_coverage() -> dict[str, str]:
    manifest = read_manifest(MINIMAL_FORM_COVERAGE_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    revisions = manifest_int(MINIMAL_FORM_COVERAGE_MANIFEST, "needs_revision_count")
    required = manifest.get("required_paths", "missing") if manifest else "missing"
    missing = manifest.get("missing_required_paths", "missing") if manifest else "missing"
    missing_template = manifest.get("missing_template_paths", "missing") if manifest else "missing"
    return row(
        "Minimal author response-form coverage",
        "pass" if manifest and revisions == 0 and not missing and not missing_template else "needs revision",
        f"status_counts={counts}; required_paths={required}; missing={missing}; missing_template_paths={missing_template}; needs_revision_count={revisions}.",
        "Keep AUTHOR_MINIMAL_RESPONSE_FORM_zh.md aligned with REQUIRED_METADATA_PATHS and the structured metadata template.",
    )


def check_starter_prefill() -> dict[str, str]:
    git_worktree = in_git_worktree()
    try:
        starter, filled, unavailable = build_starter()
    except Exception as exc:
        return row(
            "Private metadata starter dry-run",
            "needs revision",
            f"build_starter exception={type(exc).__name__}.",
            "Fix make_submission_metadata_starter.py before asking the author to fill metadata.",
        )
    still_private = [
        path
        for path in (
            "authors",
            "target_venue.name",
            "funding.statement",
            "competing_interests.statement",
            "data_availability.archive_link_or_doi",
            "code_availability.license",
        )
            if has_author_placeholder(value_at(starter, path))
    ]
    repo_url = value_at(starter, "code_availability.repository_url")
    commit_hash = value_at(starter, "code_availability.commit_hash")
    environment_notes = value_at(starter, "code_availability.environment_notes")
    repo_url_shape = (
        isinstance(repo_url, str)
        and repo_url.startswith("https://github.com/")
        and not repo_url.endswith(".git")
    )
    commit_hash_shape = isinstance(commit_hash, str) and bool(re.fullmatch(r"[0-9a-f]{40}", commit_hash))
    environment_notes_present = (
        isinstance(environment_notes, str)
        and "mcts-qoracle" in environment_notes
        and "./rebuild_submission_package.sh" in environment_notes
    )
    if not git_worktree:
        return row(
            "Private metadata starter dry-run",
            "pass" if len(still_private) == 6 else "needs revision",
            f"git_worktree=False; public_prefill_fields={len(filled)}; unavailable_public_fields={len(unavailable)}; author_gated_examples={len(still_private)}.",
            "In extracted payloads the starter cannot infer Git remote/HEAD, but it must still leave author/venue declarations human-gated.",
        )
    release_shape_ok = repo_url_shape and commit_hash_shape and environment_notes_present
    return row(
        "Private metadata starter dry-run",
        "pass" if len(filled) >= 2 and not unavailable and len(still_private) == 6 and release_shape_ok else "needs revision",
        f"public_prefill_fields={len(filled)}; unavailable={unavailable or 'none'}; repo_url_shape={repo_url_shape}; commit_hash_40hex={commit_hash_shape}; environment_notes_present={environment_notes_present}; author_gated_examples={len(still_private)}.",
        "The starter should prefill safe public repository fields with release-shaped values and leave author/venue declarations human-gated.",
    )


def check_private_git_protection() -> dict[str, str]:
    if not in_git_worktree():
        present = [rel(path) for path in PRIVATE_PATHS if path.exists()]
        return row(
            "Private metadata Git protection",
            "pass" if not present else "needs revision",
            f"git_worktree=False; private_paths_present={present or 'none'}; metadata_present={METADATA_FILE.exists()}.",
            "Extracted payloads must not contain private metadata or generated private previews.",
        )
    not_ignored: list[str] = []
    tracked: list[str] = []
    for path in PRIVATE_PATHS:
        if run_git(["check-ignore", "-q", rel(path)]).returncode != 0:
            not_ignored.append(rel(path))
        if run_git(["ls-files", "--error-unmatch", rel(path)]).returncode == 0:
            tracked.append(rel(path))
    return row(
        "Private metadata Git protection",
        "pass" if not not_ignored and not tracked else "needs revision",
        f"private_paths={len(PRIVATE_PATHS)}; not_ignored={not_ignored or 'none'}; tracked={tracked or 'none'}; metadata_present={METADATA_FILE.exists()}.",
        "Keep submission_metadata.json and generated private previews ignored and untracked.",
    )


def check_validator_and_preview_gates() -> dict[str, str]:
    validator_counts = manifest_counts(VALIDATOR_MANIFEST)
    preview_counts = manifest_counts(PREVIEW_MANIFEST)
    preview_manifest = read_manifest(PREVIEW_MANIFEST)
    ignored = bool(preview_manifest.get("private_outputs_are_git_ignored", False)) if preview_manifest else False
    validator_revisions = needs_revision_count(VALIDATOR_MANIFEST)
    preview_revisions = needs_revision_count(PREVIEW_MANIFEST)
    validator_author_input = int(validator_counts.get("needs author input", 0))
    preview_author_input = int(preview_counts.get("needs author input", 0))
    return row(
        "Validator and private-preview gates",
        "pass" if validator_revisions == 0 and preview_revisions == 0 and ignored else "needs revision",
        f"validator_counts={validator_counts}; preview_counts={preview_counts}; needs_author_input={validator_author_input + preview_author_input}; private_outputs_are_git_ignored={ignored}.",
        "Rerun validate_submission_metadata.py and make_submission_text_preview.py after private metadata is filled.",
    )


def check_synthetic_rehearsal() -> dict[str, str]:
    manifest = read_manifest(SELFTEST_MANIFEST)
    counts = manifest.get("status_counts", {}) if manifest else {}
    revisions = manifest_int(SELFTEST_MANIFEST, "needs_revision_count")
    synthetic = bool(manifest.get("uses_synthetic_metadata_only", False)) if manifest else False
    writes_private = bool(manifest.get("writes_private_metadata", True)) or bool(
        manifest.get("writes_private_preview_files", True)
    )
    return row(
        "Filled-metadata rehearsal",
        "pass" if revisions == 0 and synthetic and not writes_private else "needs revision",
        f"status_counts={counts}; needs_revision_count={revisions}; synthetic_only={synthetic}; writes_private_outputs={writes_private}.",
        "Keep the synthetic self-test aligned with validator and private-preview renderer changes.",
    )


def check_anonymous_gate() -> dict[str, str]:
    counts = manifest_counts(ANONYMOUS_MANIFEST)
    revisions = manifest_int(ANONYMOUS_MANIFEST, "needs_revision_count")
    author_inputs = manifest_int(ANONYMOUS_MANIFEST, "needs_author_input_count")
    return row(
        "Anonymous-review decision gate",
        "pass" if revisions == 0 and author_inputs >= 0 else "needs revision",
        f"status_counts={counts}; needs_revision_count={revisions}; needs_author_input_count={author_inputs}.",
        "After selecting the venue, set anonymous-review policy and provide anonymous links if double-blind review is required.",
    )


def check_support_docs() -> dict[str, str]:
    required_docs = (
        AUTHOR_PACKET,
        AUTHOR_QUESTIONNAIRE_ZH,
        AUTHOR_MINIMAL_FORM_ZH,
        LAST_MILE_ACTION_CARD_ZH,
        METADATA_ANSWERS_TEMPLATE,
        README,
        CHECKLIST,
        TARGET_VENUE_BRIEF,
        TARGET_POLICY_CHECKLIST_ZH,
        FINAL_HANDOFF,
    )
    missing = [rel(path) for path in required_docs if not path.exists()]
    required_tokens = {
        rel(AUTHOR_PACKET): ("AUTHOR_METADATA_QUESTIONNAIRE_zh.md", "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md", "LAST_MILE_ACTION_CARD_zh.md", "submission_metadata.json", "generated_", "verify_submission_package.sh"),
        rel(AUTHOR_QUESTIONNAIRE_ZH): ("target_venue.name", "authors[].name", "code_availability.commit_hash", "validate_submission_metadata.py"),
        rel(AUTHOR_MINIMAL_FORM_ZH): ("target_venue.*", "authors[]", "code_availability.*", "validate_submission_metadata.py", "不要把真实私人信息写进 tracked 文件"),
        rel(LAST_MILE_ACTION_CARD_ZH): ("最后一步行动卡", "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md", "submission_metadata_answers.json", "validate_submission_metadata.py", "does not claim hardware mapping", "not full ROS reproduction"),
        rel(METADATA_ANSWERS_TEMPLATE): ("target_venue", "authors", "code_availability", "AUTHOR INPUT REQUIRED"),
        rel(README): ("AUTHOR_METADATA_QUESTIONNAIRE_zh.md", "AUTHOR_MINIMAL_RESPONSE_FORM_zh.md", "LAST_MILE_ACTION_CARD_zh.md", "submission_metadata_answers.json", "submission_metadata.json", "generated_", "validate_submission_metadata.py"),
        rel(CHECKLIST): ("AUTHOR_METADATA_QUESTIONNAIRE_zh.md", "LAST_MILE_ACTION_CARD_zh.md", "AUTHOR INPUT REQUIRED", "submission_metadata_answers.json", "submission_metadata.json", "generated_*.md"),
        rel(TARGET_VENUE_BRIEF): ("target_venue.name", "anonymous_review_required"),
        rel(TARGET_POLICY_CHECKLIST_ZH): ("目标期刊政策核对表", "target_venue.ai_disclosure_policy_checked", "data_availability.*", "code_availability.*"),
        rel(FINAL_HANDOFF): ("LAST_MILE_ACTION_CARD_zh.md", "submission_metadata.json", "generated_", "needs author input"),
    }
    token_misses: list[str] = []
    for path in required_docs:
        text = read_text(path)
        for token in required_tokens.get(rel(path), ()):
            if token not in text:
                token_misses.append(f"{rel(path)}::{token}")
    return row(
        "Human handoff document coverage",
        "pass" if not missing and not token_misses else "needs revision",
        f"docs={len(required_docs)}; missing={missing or 'none'}; token_misses={token_misses[:5] or 'none'}.",
        "Keep README, checklist, target-venue brief, target-venue policy checklist, handoff, questionnaire, minimal response form, last-mile card, answer template, and author packet aligned with the private metadata workflow.",
    )


def check_closure_audit_consistency() -> dict[str, str]:
    metadata_counts = manifest_counts(METADATA_AUDIT_MANIFEST)
    closure_counts = manifest_counts(AUTHOR_INPUT_CLOSURE_MANIFEST)
    goal = read_manifest(GOAL_MANIFEST)
    overall = goal.get("overall_closure", "missing") if goal else "missing"
    git_worktree = in_git_worktree()
    status = (
        "pass"
        if metadata_counts.get("needs author input", 0) >= 1
        and closure_counts.get("pass", 0) >= 1
        and (overall == "not complete" or (not git_worktree and overall == "missing"))
        else "needs revision"
    )
    return row(
        "Goal-closure gate consistency",
        status,
        f"git_worktree={git_worktree}; metadata_counts={metadata_counts}; author_input_closure_counts={closure_counts}; goal_overall={overall}.",
        "Do not mark the overall goal complete until author/venue metadata are filled and the readiness audit has no unresolved author-input rows.",
    )


def build_rows() -> list[dict[str, str]]:
    return [
        check_required_inventory(),
        check_answer_template_coverage(),
        check_minimal_form_coverage(),
        check_starter_prefill(),
        check_private_git_protection(),
        check_validator_and_preview_gates(),
        check_synthetic_rehearsal(),
        check_anonymous_gate(),
        check_support_docs(),
        check_closure_audit_consistency(),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Submission Metadata Closure Path",
        "",
        "This audit verifies that the final author/venue metadata step is explicit, private, and machine-checkable without exposing private values.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "## Closure Sequence",
            "",
            "1. Use `submission_package/LAST_MILE_ACTION_CARD_zh.md`, then `submission_package/AUTHOR_METADATA_QUESTIONNAIRE_zh.md` or the checked short form `submission_package/AUTHOR_MINIMAL_RESPONSE_FORM_zh.md` to collect author and venue answers.",
            "2. Create ignored private short answers with `make_submission_metadata_from_answers.py --init-private-answers`.",
            "3. Fill every `AUTHOR INPUT REQUIRED` value in `submission_package/submission_metadata_answers.json`.",
            "4. Generate ignored private metadata with `make_submission_metadata_from_answers.py --write-private`.",
            "5. Rerun `./rebuild_submission_package.sh` and `./verify_submission_package.sh`.",
            "6. Review ignored `submission_package/generated_*.md` previews against the target venue.",
            "7. Replace repository-relative availability text with final archive, repository, or anonymous-review links before upload.",
            "",
            "| item | status | evidence | next action |",
            "|---|---|---|---|",
        ]
    )
    for item in rows:
        lines.append(
            "| {item} | {status} | {evidence} | {next_action} |".format(
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
        "private_paths": [rel(path) for path in PRIVATE_PATHS],
        "required_metadata_paths": len(REQUIRED_METADATA_PATHS),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "closure_path_ready": counts.get("needs revision", 0) == 0,
        "rows": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_submission_metadata_closure_path.csv"),
            "analysis": rel(RESULTS / "analysis_submission_metadata_closure_path.md"),
            "manifest": rel(RESULTS / "manifest_submission_metadata_closure_path.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_submission_metadata_closure_path.csv", rows)
    write_markdown(RESULTS / "analysis_submission_metadata_closure_path.md", rows)
    write_manifest(RESULTS / "manifest_submission_metadata_closure_path.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} submission metadata closure path row(s)")
    if failures:
        print(f"warning: {failures} metadata closure path row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
