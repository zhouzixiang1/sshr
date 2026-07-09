#!/usr/bin/env python3
"""Audit source and payload path/privacy boundaries.

Some result files intentionally record local toolchain paths as provenance for
ABC, mockturtle, CirKit, RevKit, and model checkpoints.  Those paths are useful
for reproducibility, but they should not leak into primary manuscript sources,
submission-support documents, or unsafe payload member names.  This terminal
audit separates strict privacy/path gates from allowed provenance locations.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
PAPER_LATEX = THIS_DIR / "paper_latex"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"

PRIVATE_BASENAMES = {
    "submission_metadata.json",
    "generated_author_declarations.md",
    "generated_availability_statements.md",
    "generated_cover_letter.md",
    "generated_submission_text.md",
}

LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[^\s`),;]+"),
    re.compile(r"Desktop/tzb"),
)
OLD_WORKSPACE_PATTERN = re.compile(r"/Users/zhouzixiang/Desktop/tzb/claude")
AUTHOR_IDENTITY_PATTERNS = (
    re.compile(r"Zixiang Zhou"),
    re.compile(r"\\author\{Zixiang Zhou\}"),
)
TEXT_SUFFIXES = {
    ".bib",
    ".bst",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".sty",
    ".tex",
    ".txt",
}
PROVENANCE_PREFIXES = (
    "results/",
    "DELIVERABLE_zh.md",
    "README.md",
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def safe_read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except Exception:
        return {}


def payload_paths() -> list[Path]:
    manifest = safe_read_json(PAYLOAD_MANIFEST)
    paths: list[Path] = []
    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            continue
        value = item.get("path")
        if isinstance(value, str):
            paths.append(THIS_DIR / value)
    return sorted(paths, key=rel)


def text_payload_paths() -> list[Path]:
    self_path = Path(__file__).resolve()
    return [
        path
        for path in payload_paths()
        if path.suffix.lower() in TEXT_SUFFIXES and path.exists() and path.resolve() != self_path
    ]


def path_hits(path: Path) -> list[str]:
    text = read_text(path)
    hits: list[str] = []
    for pattern in LOCAL_PATH_PATTERNS:
        hits.extend(pattern.findall(text))
    return sorted(set(hits))


def private_name_hits(paths: list[Path]) -> list[str]:
    return sorted(rel(path) for path in paths if path.name in PRIVATE_BASENAMES)


def row(
    item: str,
    status: str,
    scope: str,
    files_scanned: int,
    hits: int,
    evidence: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "scope": scope,
        "files_scanned": str(files_scanned),
        "hits": str(hits),
        "evidence": evidence,
        "next_action": next_action,
    }


def scan_paths(paths: list[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in paths:
        hits = path_hits(path)
        if hits:
            found[rel(path)] = hits
    return found


def manuscript_source_row() -> dict[str, str]:
    paths = [
        PAPER_LATEX / "resource_nmcts_submission_v1.tex",
        PAPER_LATEX / "resource_nmcts_submission_anonymous.tex",
        PAPER_LATEX / "references.bib",
    ]
    paths.extend(sorted((PAPER_LATEX / "tables").glob("*.tex")))
    found = scan_paths([path for path in paths if path.exists()])
    old_hits = [name for name, hits in found.items() if any(OLD_WORKSPACE_PATTERN.search(hit) for hit in hits)]
    status = "pass" if not found and not old_hits else "needs revision"
    return row(
        "Manuscript source local-path hygiene",
        status,
        "author/anonymous TeX, bibliography, and generated table inputs",
        len(paths),
        sum(len(hits) for hits in found.values()),
        f"local_path_files={sorted(found)[:5] or 'none'}; old_workspace_files={old_hits or 'none'}.",
        "Remove absolute local paths from manuscript, bibliography, or table TeX inputs; keep environment paths in provenance results instead.",
    )


def submission_support_row() -> dict[str, str]:
    paths = sorted(
        path
        for path in SUBMISSION_PACKAGE.iterdir()
        if path.is_file() and path.suffix.lower() in {".md", ".json"}
    )
    found = scan_paths(paths)
    old_hits = [name for name, hits in found.items() if any(OLD_WORKSPACE_PATTERN.search(hit) for hit in hits)]
    status = "pass" if not found and not old_hits else "needs revision"
    return row(
        "Submission support local-path hygiene",
        status,
        "public submission_package Markdown/JSON support files",
        len(paths),
        sum(len(hits) for hits in found.values()),
        f"local_path_files={sorted(found)[:5] or 'none'}; old_workspace_files={old_hits or 'none'}.",
        "Rewrite public support documents to repository-relative paths or venue-neutral commands.",
    )


def anonymous_source_identity_row() -> dict[str, str]:
    path = PAPER_LATEX / "resource_nmcts_submission_anonymous.tex"
    text = read_text(path) if path.exists() else ""
    missing_anonymous = "Anonymous Authors" not in text
    identity_hits = [pattern.pattern for pattern in AUTHOR_IDENTITY_PATTERNS if pattern.search(text)]
    status = "pass" if path.exists() and not missing_anonymous and not identity_hits else "needs revision"
    return row(
        "Anonymous source identity boundary",
        status,
        rel(path),
        1 if path.exists() else 0,
        len(identity_hits) + int(missing_anonymous),
        f"anonymous_author_present={not missing_anonymous}; identity_hits={identity_hits or 'none'}.",
        "Regenerate the anonymous draft and remove author identity from the anonymous source if double-blind review is selected.",
    )


def payload_private_membership_row() -> dict[str, str]:
    paths = payload_paths()
    private_hits = private_name_hits(paths)
    unsafe = [
        rel(path)
        for path in paths
        if path.is_absolute() and not str(path.resolve()).startswith(str(THIS_DIR.resolve()))
    ]
    status = "pass" if not private_hits and not unsafe else "needs revision"
    return row(
        "Payload private-file membership",
        status,
        rel(PAYLOAD_MANIFEST),
        len(paths),
        len(private_hits) + len(unsafe),
        f"private_members={private_hits or 'none'}; unsafe_members={unsafe or 'none'}.",
        "Regenerate the payload after removing private metadata/previews or unsafe archive members.",
    )


def payload_local_path_classification_row() -> dict[str, str]:
    paths = text_payload_paths()
    found = scan_paths(paths)
    strict = {
        name: hits
        for name, hits in found.items()
        if not name.startswith(PROVENANCE_PREFIXES)
    }
    provenance = {name: hits for name, hits in found.items() if name not in strict}
    status = "pass" if not strict else "needs revision"
    return row(
        "Payload local-path provenance classification",
        status,
        "all text files listed in the upload payload manifest",
        len(paths),
        sum(len(hits) for hits in found.values()),
        (
            f"local_path_files={len(found)}; strict_local_path_files={sorted(strict)[:8] or 'none'}; "
            f"provenance_local_path_files={len(provenance)}."
        ),
        "Move local absolute paths out of manuscripts/support/scripts and into reproducibility provenance files, or rewrite them to relative paths.",
    )


def old_workspace_cleanup_row() -> dict[str, str]:
    paths = text_payload_paths()
    hits: dict[str, int] = {}
    for path in paths:
        count = len(OLD_WORKSPACE_PATTERN.findall(read_text(path)))
        if count:
            hits[rel(path)] = count
    status = "pass" if not hits else "needs revision"
    return row(
        "Old claude workspace path cleanup",
        status,
        "all text files listed in the upload payload manifest",
        len(paths),
        sum(hits.values()),
        f"old_workspace_path_files={hits or 'none'}.",
        "Rewrite stale /Users/zhouzixiang/Desktop/tzb/claude paths to the current src-root layout.",
    )


def build_rows() -> list[dict[str, str]]:
    return [
        manuscript_source_row(),
        submission_support_row(),
        anonymous_source_identity_row(),
        payload_private_membership_row(),
        payload_local_path_classification_row(),
        old_workspace_cleanup_row(),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "scope", "files_scanned", "hits", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    lines = [
        "# Source Path Privacy Audit",
        "",
        "This terminal audit separates strict source/privacy gates from allowed local-path provenance in experiment result files.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| item | status | scope | files scanned | hits | evidence |", "|---|---|---|---:|---:|---|"])
    for item in rows:
        lines.append(
            "| {item} | {status} | {scope} | {files_scanned} | {hits} | {evidence} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    payload_text_files = text_payload_paths()
    payload_local_path_files = scan_paths(payload_text_files)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "needs_revision_count": counts.get("needs revision", 0),
        "status_counts": dict(sorted(counts.items())),
        "payload_manifest": rel(PAYLOAD_MANIFEST),
        "payload_text_files_scanned": len(payload_text_files),
        "payload_local_path_files": len(payload_local_path_files),
        "outputs": {
            "summary": "results/summary_source_path_privacy_audit.csv",
            "analysis": "results/analysis_source_path_privacy_audit.md",
            "manifest": "results/manifest_source_path_privacy_audit.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_source_path_privacy_audit.csv", rows)
    write_markdown(RESULTS / "analysis_source_path_privacy_audit.md", rows)
    write_manifest(RESULTS / "manifest_source_path_privacy_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} source/path privacy audit row(s)")
    if failures:
        print(f"warning: {failures} source/path privacy row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
