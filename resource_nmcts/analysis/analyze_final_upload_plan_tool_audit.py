#!/usr/bin/env python3
"""Audit the final upload-plan generator without using private author data."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

from analyze_submission_metadata_audit import METADATA_TEMPLATE, THIS_DIR, read_json, rel


RESULTS = THIS_DIR / "results"
from _paths import find as _find  # noqa: E402
SUMMARY = RESULTS / "summary_final_upload_plan_tool_audit.csv"
ANALYSIS = RESULTS / "analysis_final_upload_plan_tool_audit.md"
MANIFEST = RESULTS / "manifest_final_upload_plan_tool_audit.json"

GENERATOR = _find("make_final_upload_plan.py")
PRIVATE_OUTPUT = THIS_DIR / "submission_package" / "generated_upload_plan.md"
CURRENT_PLAN_MANIFEST = RESULTS / "manifest_final_upload_plan.json"


def stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def git_success(args: list[str]) -> bool:
    try:
        proc = subprocess.run(
            ["git", *args],
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


def fill_placeholders(value: object) -> object:
    if isinstance(value, str):
        return "not applicable" if value == "AUTHOR INPUT REQUIRED" else value
    if isinstance(value, list):
        return [fill_placeholders(item) for item in value]
    if isinstance(value, dict):
        return {key: fill_placeholders(item) for key, item in value.items()}
    return value


def synthetic_metadata(route: str) -> dict[str, object]:
    template = read_json(METADATA_TEMPLATE)
    data = fill_placeholders(deepcopy(template))
    if not isinstance(data, dict):
        raise RuntimeError("metadata template is not a JSON object")
    data["target_venue"] = {
        "name": "ACM Transactions on Quantum Computing" if route == "acm_tqc" else "Synthetic Logic Journal",
        "manuscript_type": "regular article",
        "formatting_policy_checked": "yes",
        "reference_style_checked": "yes",
        "word_limit_checked": "yes",
        "supplementary_material_policy_checked": "yes",
        "ai_disclosure_policy_checked": "yes",
        "anonymous_review_required": "yes" if route in {"generic_anonymous", "acm_tqc"} else "no",
    }
    data["authors"] = [
        {
            "order": "1",
            "name": "Synthetic Author",
            "orcid": "0000-0000-0000-0000",
            "affiliations": ["Synthetic University"],
            "email": "synthetic.author@example.com",
            "corresponding": "yes",
        }
    ]
    data["corresponding_author"] = {
        "name": "Synthetic Author",
        "email": "synthetic.author@example.com",
        "affiliation": "Synthetic University",
        "postal_address": "Synthetic address",
    }
    data["data_availability"] = {
        "archive_link_or_doi": "https://doi.org/10.0000/synthetic-data",
        "anonymous_review_link": "https://anonymous.example.com/data",
        "access_restrictions": "none",
        "statement": "Synthetic data availability statement.",
    }
    data["code_availability"] = {
        "repository_url": "https://github.com/synthetic/repo",
        "commit_hash": "0" * 40,
        "license": "MIT",
        "environment_notes": "Synthetic environment notes.",
        "anonymous_review_link": "https://anonymous.example.com/code",
        "statement": "Synthetic code availability statement.",
    }
    data["permissions"] = {
        "third_party_material_confirmed": "yes",
        "statement": "Synthetic permission statement.",
    }
    return data


def run_generator(route: str, tmpdir: Path) -> dict[str, object]:
    metadata = tmpdir / f"{route}_metadata.json"
    output = tmpdir / f"{route}_upload_plan.md"
    summary = tmpdir / f"{route}_summary.csv"
    analysis = tmpdir / f"{route}_analysis.md"
    manifest = tmpdir / f"{route}_manifest.json"
    metadata.write_text(json.dumps(synthetic_metadata(route), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--metadata",
            str(metadata),
            "--output",
            str(output),
            "--summary",
            str(summary),
            "--analysis",
            str(analysis),
            "--manifest",
            str(manifest),
        ],
        cwd=THIS_DIR,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    data = read_json(manifest)
    return {
        "returncode": proc.returncode,
        "stdout_lines": len(proc.stdout.splitlines()),
        "stderr": proc.stderr.strip(),
        "output_exists": output.exists(),
        "manifest": data,
    }


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    ignored = git_success(["check-ignore", rel(PRIVATE_OUTPUT)])
    tracked = git_success(["ls-files", "--error-unmatch", rel(PRIVATE_OUTPUT)])
    rows.append(
        row(
            "Private upload-plan Git protection",
            "pass" if GENERATOR.exists() and ignored and not tracked else "needs revision",
            f"generator_exists={GENERATOR.exists()}; output_ignored={ignored}; output_tracked={tracked}; private_output={rel(PRIVATE_OUTPUT)}.",
            "Keep generated_upload_plan.md ignored and untracked.",
        )
    )

    route_expectations = {
        "author": "author_labeled_submission",
        "generic_anonymous": "generic_anonymous_review",
        "acm_tqc": "acm_tqc_anonymous_review",
    }
    with tempfile.TemporaryDirectory(prefix="resource_nmcts_upload_plan_") as tmp:
        tmpdir = Path(tmp)
        for route, expected in route_expectations.items():
            result = run_generator(route, tmpdir)
            manifest = result.get("manifest", {})
            actual = manifest.get("route", "missing") if isinstance(manifest, dict) else "missing"
            counts = manifest.get("status_counts", {}) if isinstance(manifest, dict) else {}
            revisions = manifest.get("needs_revision_count", "missing") if isinstance(manifest, dict) else "missing"
            output_exists = bool(result.get("output_exists"))
            status = (
                "pass"
                if result.get("returncode") == 0
                and actual == expected
                and output_exists
                and revisions == 0
                and counts.get("pass", 0) == 1
                else "needs revision"
            )
            rows.append(
                row(
                    f"Synthetic route: {expected}",
                    status,
                    f"returncode={result.get('returncode')}; actual_route={actual}; output_exists={output_exists}; needs_revision_count={revisions}; status_counts={counts}; stdout_lines={result.get('stdout_lines')}; stderr={stringify(result.get('stderr')) or 'none'}.",
                    "Fix make_final_upload_plan.py route selection or required upload-file checks.",
                )
            )

    current = read_json(CURRENT_PLAN_MANIFEST)
    current_counts = current.get("status_counts", {}) if isinstance(current, dict) else {}
    current_revisions = int(current.get("needs_revision_count", -1)) if isinstance(current, dict) else -1
    current_route = current.get("route", "missing") if isinstance(current, dict) else "missing"
    current_private_ignored = bool(current.get("private_output_is_git_ignored", False)) if isinstance(current, dict) else False
    rows.append(
        row(
            "Current private upload-plan gate",
            "pass" if current and current_revisions == 0 and current_private_ignored else "needs revision",
            f"route={current_route}; status_counts={current_counts}; needs_revision_count={current_revisions}; private_output_is_git_ignored={current_private_ignored}.",
            "Run make_final_upload_plan.py after filling private metadata; missing metadata may remain needs author input, but needs revision must be zero.",
        )
    )
    return rows


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
        "# Final Upload Plan Tool Audit",
        "",
        "This audit tests the private upload-plan generator using synthetic metadata only.",
        "",
        "It verifies author-labeled, generic anonymous, and ACM/TQC anonymous upload routes without reading real author metadata.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | evidence | next action |", "|---|---|---|---|"])
    for item in rows:
        escaped = {key: value.replace("|", "\\|") for key, value in item.items()}
        lines.append("| {item} | {status} | {evidence} | {next_action} |".format(**escaped))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": counts,
        "needs_revision_count": sum(1 for item in rows if item["status"] == "needs revision"),
        "synthetic_routes": ["author_labeled_submission", "generic_anonymous_review", "acm_tqc_anonymous_review"],
        "uses_private_metadata": False,
        "private_output_path": rel(PRIVATE_OUTPUT),
        "current_plan_manifest": rel(CURRENT_PLAN_MANIFEST),
        "outputs": {
            "summary": rel(SUMMARY),
            "analysis": rel(ANALYSIS),
            "manifest": rel(MANIFEST),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {len(rows)} final upload-plan tool audit row(s)")
    return 0 if not any(item["status"] == "needs revision" for item in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
