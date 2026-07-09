#!/usr/bin/env python3
"""Compile the LaTeX manuscripts from an extracted upload payload.

The local manuscript PDFs can compile while the upload archive is still
missing a source dependency.  This terminal audit extracts the payload tarball
into a temporary directory, forces ``latexmk`` to rebuild the author and
anonymous TeX sources from inside the extracted tree, and checks the generated
PDFs and logs.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from make_submission_payload_archive import ARCHIVE, PAYLOAD_ROOT, THIS_DIR


RESULTS = THIS_DIR / "results"


@dataclass(frozen=True)
class CompileSpec:
    label: str
    tex_path: str
    pdf_path: str
    log_path: str
    strict_log: bool = True


COMPILE_SPECS = (
    CompileSpec(
        label="author",
        tex_path="paper_latex/resource_nmcts_submission_v1.tex",
        pdf_path="paper_latex/resource_nmcts_submission_v1.pdf",
        log_path="paper_latex/resource_nmcts_submission_v1.log",
    ),
    CompileSpec(
        label="anonymous",
        tex_path="paper_latex/resource_nmcts_submission_anonymous.tex",
        pdf_path="paper_latex/resource_nmcts_submission_anonymous.pdf",
        log_path="paper_latex/resource_nmcts_submission_anonymous.log",
    ),
    CompileSpec(
        label="acm_tqc",
        tex_path="paper_latex/resource_nmcts_submission_acm_tqc.tex",
        pdf_path="paper_latex/resource_nmcts_submission_acm_tqc.pdf",
        log_path="paper_latex/resource_nmcts_submission_acm_tqc.log",
        strict_log=False,
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def row(
    item: str,
    status: str,
    source: str,
    returncode: int | str,
    pages: int | str,
    bytes_out: int | str,
    compile_seconds: float | str,
    evidence: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "source": source,
        "returncode": str(returncode),
        "pages": str(pages),
        "bytes": str(bytes_out),
        "compile_seconds": f"{compile_seconds:.3f}" if isinstance(compile_seconds, float) else str(compile_seconds),
        "evidence": evidence,
        "next_action": next_action,
    }


def safe_payload_path(path: str) -> bool:
    return bool(path) and not path.startswith("/") and not path.startswith("../") and "/../" not in path


def extract_payload(root: Path) -> tuple[Path | None, int, str]:
    if not ARCHIVE.exists():
        return None, 0, f"missing archive: {rel(ARCHIVE)}"
    payload_dir = root / PAYLOAD_ROOT
    try:
        count = 0
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                if not member.name.startswith(f"{PAYLOAD_ROOT}/"):
                    return None, count, f"unsafe archive root: {member.name}"
                payload_rel = member.name.removeprefix(f"{PAYLOAD_ROOT}/")
                if not safe_payload_path(payload_rel):
                    return None, count, f"unsafe payload path: {member.name}"
                target = payload_dir / payload_rel
                resolved = target.resolve()
                if not str(resolved).startswith(str(payload_dir.resolve())):
                    return None, count, f"path escapes payload root: {member.name}"
                extracted = tar.extractfile(member)
                if extracted is None:
                    return None, count, f"cannot extract: {member.name}"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(extracted.read())
                target.chmod(member.mode & 0o777)
                count += 1
        return payload_dir, count, ""
    except Exception as exc:
        return None, 0, f"{type(exc).__name__}: {exc}"


def pdf_pages(path: Path) -> int:
    if not path.exists():
        return -1
    try:
        proc = subprocess.run(
            ["pdfinfo", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        )
    except Exception:
        return -1
    match = re.search(r"^Pages:\s+(\d+)", proc.stdout, flags=re.MULTILINE)
    return int(match.group(1)) if match else -1


def unexpected_log_lines(path: Path, strict: bool = True) -> list[str]:
    if not path.exists():
        return ["log missing"]
    bad_patterns = (
        re.compile(r"Warning|Overfull|Underfull|LaTeX Error|Undefined|Rerun")
        if strict
        else re.compile(r"LaTeX Error|Undefined control sequence|Emergency stop|Fatal error")
    )
    allowed = (
        "Package: rerunfilecheck",
        r"LaTeX Warning: Command \showhyphens",
    )
    unexpected: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not bad_patterns.search(line):
            continue
        if any(token in line for token in allowed):
            continue
        unexpected.append(f"{lineno}:{line.strip()}")
    return unexpected


def compile_one(payload_dir: Path, spec: CompileSpec, latexmk: str) -> dict[str, str]:
    tex = payload_dir / spec.tex_path
    pdf = payload_dir / spec.pdf_path
    log = payload_dir / spec.log_path
    if not tex.exists():
        return row(
            f"{spec.label} payload LaTeX compile",
            "needs revision",
            spec.tex_path,
            "missing",
            "missing",
            "0",
            "0.000",
            f"missing TeX source={spec.tex_path}.",
            "Regenerate the payload archive with manuscript TeX sources included.",
        )
    proc = subprocess.run(
        [latexmk, "-pdf", "-g", "-interaction=nonstopmode", "-halt-on-error", tex.name],
        cwd=tex.parent,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
    pages = pdf_pages(pdf)
    pdf_bytes = pdf.stat().st_size if pdf.exists() else 0
    log_unexpected = unexpected_log_lines(log, spec.strict_log)
    raw_stderr_lines = proc.stderr.strip().splitlines()
    allowed_stderr = (
        "Latexmk: Missing bbl file",
        "Latexmk: Using bibtex to make bibliography file(s).",
        "No file resource_nmcts_submission_v1.bbl",
        "No file resource_nmcts_submission_anonymous.bbl",
        "No file resource_nmcts_submission_acm_tqc.bbl",
    )
    stderr_lines = [line for line in raw_stderr_lines if not any(token in line for token in allowed_stderr)]
    status = "pass" if proc.returncode == 0 and pages > 0 and pdf_bytes > 100_000 and not log_unexpected else "needs revision"
    evidence = (
        f"stdout_lines={len(proc.stdout.splitlines())}; stderr={stderr_lines[:2] or 'none'}; "
        f"allowed_bibliography_bootstrap_lines={len(raw_stderr_lines) - len(stderr_lines)}; "
        f"unexpected_log_lines={log_unexpected[:3] or 'none'}."
    )
    return row(
        f"{spec.label} payload LaTeX compile",
        status,
        spec.tex_path,
        proc.returncode,
        pages,
        pdf_bytes,
        "not_recorded",
        evidence,
        "Inspect the extracted payload LaTeX log and restore missing table, figure, bibliography, or style dependencies.",
    )


def build_rows() -> list[dict[str, str]]:
    latexmk = os.environ.get("LATEXMK_BIN") or shutil.which("latexmk")
    with tempfile.TemporaryDirectory(prefix="resource_nmcts_payload_latex_") as tmp:
        payload_dir, count, error = extract_payload(Path(tmp))
        rows = [
            row(
                "Payload extraction for LaTeX compile",
                "pass" if payload_dir is not None and count > 0 and not error else "needs revision",
                rel(ARCHIVE),
                "n/a",
                "n/a",
                count,
                "0.000",
                f"extracted_files={count}; error={error or 'none'}.",
                "Regenerate the payload archive if it cannot be safely extracted.",
            )
        ]
        if payload_dir is None:
            return rows
        if not latexmk:
            rows.append(
                row(
                    "latexmk availability",
                    "needs revision",
                    "PATH",
                    "missing",
                    "n/a",
                    "0",
                    "0.000",
                    "latexmk is not available on PATH and LATEXMK_BIN is unset.",
                    "Install latexmk or set LATEXMK_BIN before running the payload compile audit.",
                )
            )
            return rows
        rows.extend(compile_one(payload_dir, spec, latexmk) for spec in COMPILE_SPECS)
        return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "source", "returncode", "pages", "bytes", "compile_seconds", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    lines = [
        "# Payload LaTeX Compile Audit",
        "",
        "This terminal audit extracts the upload payload and rebuilds the author, anonymous, and ACM/TQC PDFs from the extracted LaTeX sources.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| item | status | source | returncode | pages | bytes | compile seconds | evidence |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for item in rows:
        lines.append(
            "| {item} | {status} | `{source}` | {returncode} | {pages} | {bytes} | {compile_seconds} | {evidence} |".format(
                **{key: value.replace("|", "\\|") for key, value in item.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(item["status"] for item in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "archive": rel(ARCHIVE),
        "rows": len(rows),
        "compiled_manuscripts": len([item for item in rows if item["item"].endswith("payload LaTeX compile")]),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "rows_detail": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_payload_latex_compile_audit.csv"),
            "analysis": rel(RESULTS / "analysis_payload_latex_compile_audit.md"),
            "manifest": rel(RESULTS / "manifest_payload_latex_compile_audit.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_payload_latex_compile_audit.csv", rows)
    write_markdown(RESULTS / "analysis_payload_latex_compile_audit.md", rows)
    write_manifest(RESULTS / "manifest_payload_latex_compile_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} payload LaTeX compile row(s)")
    if failures:
        print(f"warning: {failures} payload LaTeX compile row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
