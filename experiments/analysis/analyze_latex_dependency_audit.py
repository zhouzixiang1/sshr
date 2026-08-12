#!/usr/bin/env python3
"""Audit LaTeX dependency closure for the submission sources.

This terminal audit parses the author, anonymous, and ACM/TQC LaTeX sources, resolves
table inputs, included figures, and bibliography files, then checks that every
resolved dependency exists locally and is present in the upload payload
manifest.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
PAPER_DIR = THIS_DIR / "paper_latex"
AUTHOR_TEX = PAPER_DIR / "resource_nmcts_submission_v1.tex"
ANONYMOUS_TEX = PAPER_DIR / "resource_nmcts_submission_anonymous.tex"
ACM_TQC_TEX = PAPER_DIR / "resource_nmcts_submission_acm_tqc.tex"
PAYLOAD_MANIFEST = RESULTS / "manifest_submission_payload_archive.json"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_payload_paths() -> set[str]:
    if not PAYLOAD_MANIFEST.exists():
        return set()
    try:
        data = json.loads(PAYLOAD_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return set()
    files = data.get("files", [])
    if not isinstance(files, list):
        return set()
    out: set[str] = set()
    for item in files:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            out.add(item["path"])
    return out


def parse_graphicspath(text: str) -> list[Path]:
    paths: list[Path] = []
    for block in re.findall(r"\\graphicspath\{((?:\{[^{}]+\})+)\}", text, flags=re.DOTALL):
        for path_text in re.findall(r"\{([^{}]+)\}", block):
            paths.append(PAPER_DIR / path_text)
    return paths or [PAPER_DIR]


def with_default_suffix(path: Path, suffix: str) -> Path:
    return path if path.suffix else path.with_suffix(suffix)


def resolve_existing(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def resolve_input(path_text: str) -> Path:
    path = with_default_suffix(Path(path_text), ".tex")
    return PAPER_DIR / path


def resolve_bibliography(path_text: str) -> Path:
    path = with_default_suffix(Path(path_text.strip()), ".bib")
    return PAPER_DIR / path


def resolve_graphic(path_text: str, graphic_paths: list[Path]) -> Path:
    path = Path(path_text)
    suffixes = [path.suffix] if path.suffix else [".pdf", ".png", ".svg", ".eps"]
    bases = [path] if path.parent != Path(".") else [root / path for root in graphic_paths] + [PAPER_DIR / path]
    candidates: list[Path] = []
    for base in bases:
        for suffix in suffixes:
            candidates.append(base if base.suffix else base.with_suffix(suffix))
    return resolve_existing(candidates)


def dependency_rows(label: str, tex_path: Path) -> list[dict[str, str]]:
    text = read_text(tex_path)
    graphic_paths = parse_graphicspath(text)
    deps: list[tuple[str, str, Path]] = [("main_source", rel(tex_path), tex_path)]

    for match in re.finditer(r"\\(?:input|include)\{([^{}]+)\}", text):
        ref = match.group(1).strip()
        deps.append(("tex_input", ref, resolve_input(ref)))

    for match in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}", text):
        ref = match.group(1).strip()
        deps.append(("figure", ref, resolve_graphic(ref, graphic_paths)))

    for match in re.finditer(r"\\bibliography\{([^{}]+)\}", text):
        for ref in match.group(1).split(","):
            deps.append(("bibliography", ref.strip(), resolve_bibliography(ref)))

    for match in re.finditer(r"\\addbibresource\{([^{}]+)\}", text):
        ref = match.group(1).strip()
        deps.append(("bibliography", ref, resolve_bibliography(ref)))

    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for dep_type, ref, path in deps:
        resolved = rel(path) if path.exists() and path.is_relative_to(THIS_DIR) else str(path)
        key = (label, dep_type, resolved)
        unique[key] = {
            "manuscript": label,
            "dependency_type": dep_type,
            "tex_reference": ref,
            "resolved_path": resolved,
            "local_exists": str(path.exists()),
            "payload_present": "False",
            "status": "needs revision",
        }
    return list(unique.values())


def build_rows() -> list[dict[str, str]]:
    payload_paths = read_payload_paths()
    rows = (
        dependency_rows("author", AUTHOR_TEX)
        + dependency_rows("anonymous", ANONYMOUS_TEX)
        + dependency_rows("acm_tqc", ACM_TQC_TEX)
    )
    for row in rows:
        payload_present = row["resolved_path"] in payload_paths
        row["payload_present"] = str(payload_present)
        row["status"] = "pass" if row["local_exists"] == "True" and payload_present else "needs revision"
        row["next_action"] = (
            "No action needed."
            if row["status"] == "pass"
            else "Restore the local dependency and rerun make_submission_payload_archive.py so it is packaged."
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "manuscript",
        "dependency_type",
        "tex_reference",
        "resolved_path",
        "local_exists",
        "payload_present",
        "status",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    type_counts = Counter(row["dependency_type"] for row in rows)
    missing = [row for row in rows if row["status"] != "pass"]
    lines = [
        "# LaTeX Dependency Audit",
        "",
        "This terminal audit parses the author, anonymous, and ACM/TQC LaTeX sources and checks that every resolved table, figure, and bibliography dependency exists locally and is present in the upload payload manifest.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "## Dependency types", ""])
    for dep_type in sorted(type_counts):
        lines.append(f"- {dep_type}: {type_counts[dep_type]}")
    lines.extend(["", "## Missing dependencies", ""])
    if missing:
        for row in missing:
            lines.append(
                f"- {row['manuscript']} {row['dependency_type']} `{row['tex_reference']}` -> `{row['resolved_path']}`; local={row['local_exists']}; payload={row['payload_present']}"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Dependencies",
            "",
            "| manuscript | type | reference | resolved path | local | payload | status |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['manuscript']} | {row['dependency_type']} | `{row['tex_reference']}` | `{row['resolved_path']}` | {row['local_exists']} | {row['payload_present']} | {row['status']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = Counter(row["status"] for row in rows)
    type_counts = Counter(row["dependency_type"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "dependency_count": len(rows),
        "needs_revision_count": status_counts.get("needs revision", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "dependency_type_counts": dict(sorted(type_counts.items())),
        "payload_manifest": rel(PAYLOAD_MANIFEST),
        "source_files": {
            "author_tex": rel(AUTHOR_TEX),
            "anonymous_tex": rel(ANONYMOUS_TEX),
            "acm_tqc_tex": rel(ACM_TQC_TEX),
        },
        "outputs": {
            "summary": "results/summary_latex_dependency_audit.csv",
            "analysis": "results/analysis_latex_dependency_audit.md",
            "manifest": "results/manifest_latex_dependency_audit.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_latex_dependency_audit.csv", rows)
    write_markdown(RESULTS / "analysis_latex_dependency_audit.md", rows)
    write_manifest(RESULTS / "manifest_latex_dependency_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} LaTeX dependency row(s)")
    if failures:
        print(f"warning: {failures} LaTeX dependency row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
