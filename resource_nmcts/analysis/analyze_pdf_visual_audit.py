#!/usr/bin/env python3
"""Render compiled PDFs and check for basic visual integrity.

This terminal audit complements the LaTeX log and ``pdfinfo`` checks.  It uses
Poppler's ``pdftoppm`` to render every page of the author and anonymous PDFs,
then checks that page counts match, rendered pages have stable dimensions, and
each page contains non-trivial visible content.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
AUTHOR_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def pdf_pages(path: Path) -> int:
    if not path.exists():
        return -1
    try:
        proc = subprocess.run(
            ["pdfinfo", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except Exception:
        return -1
    match = re.search(r"^Pages:\s+(\d+)", proc.stdout, flags=re.MULTILINE)
    return int(match.group(1)) if match else -1


def read_ppm_header(path: Path) -> tuple[int, int, int, int]:
    data = path.read_bytes()
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 4 and index < len(data):
        while index < len(data) and data[index] in b" \t\r\n":
            index += 1
        if index < len(data) and data[index] == ord("#"):
            while index < len(data) and data[index] not in b"\r\n":
                index += 1
            continue
        start = index
        while index < len(data) and data[index] not in b" \t\r\n":
            index += 1
        if start < index:
            tokens.append(data[start:index])
    if len(tokens) != 4 or tokens[0] != b"P6":
        raise ValueError(f"{path.name} is not an 8-bit binary PPM")
    while index < len(data) and data[index] in b" \t\r\n":
        index += 1
    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    return width, height, max_value, index


def ppm_ink_fraction(path: Path) -> tuple[int, int, float]:
    width, height, max_value, offset = read_ppm_header(path)
    if max_value != 255:
        raise ValueError(f"{path.name} has unsupported max value {max_value}")
    payload = path.read_bytes()[offset:]
    expected = width * height * 3
    if len(payload) < expected:
        raise ValueError(f"{path.name} has truncated pixel data")
    payload = payload[:expected]
    nonwhite = 0
    for idx in range(0, expected, 3):
        if payload[idx] < 250 or payload[idx + 1] < 250 or payload[idx + 2] < 250:
            nonwhite += 1
    return width, height, nonwhite / (width * height)


def page_number(path: Path) -> int:
    match = re.search(r"-(\d+)\.ppm$", path.name)
    return int(match.group(1)) if match else -1


def render_pdf(label: str, pdf_path: Path) -> dict[str, str]:
    pages = pdf_pages(pdf_path)
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return {
            "manuscript": label,
            "status": "needs revision",
            "pdf": rel(pdf_path),
            "pages": str(pages),
            "rendered_pages": "0",
            "dimensions": "missing",
            "min_ink_fraction": "nan",
            "max_ink_fraction": "nan",
            "min_page_bytes": "0",
            "max_page_bytes": "0",
            "render_seconds": "0.000",
            "failures": "pdftoppm missing",
            "next_action": "Install Poppler or restore pdftoppm on PATH, then rerun the visual audit.",
        }
    if pages <= 0:
        return {
            "manuscript": label,
            "status": "needs revision",
            "pdf": rel(pdf_path),
            "pages": str(pages),
            "rendered_pages": "0",
            "dimensions": "missing",
            "min_ink_fraction": "nan",
            "max_ink_fraction": "nan",
            "min_page_bytes": "0",
            "max_page_bytes": "0",
            "render_seconds": "0.000",
            "failures": "pdfinfo could not read page count",
            "next_action": "Rebuild the PDF and inspect pdfinfo output.",
        }

    failures: list[str] = []
    widths: set[int] = set()
    heights: set[int] = set()
    ink_fractions: list[float] = []
    page_bytes: list[int] = []
    with tempfile.TemporaryDirectory(prefix=f"resource_nmcts_{label}_render_") as tmp:
        prefix = Path(tmp) / label
        proc = subprocess.run(
            [pdftoppm, "-r", "72", "-f", "1", "-l", str(pages), str(pdf_path), str(prefix)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            failures.append(f"pdftoppm returncode={proc.returncode}; stderr={proc.stderr.strip()[:200]}")
        rendered = sorted(Path(tmp).glob(f"{label}-*.ppm"), key=page_number)
        if len(rendered) != pages:
            failures.append(f"rendered_pages={len(rendered)} expected={pages}")
        for page_path in rendered:
            try:
                width, height, ink = ppm_ink_fraction(page_path)
            except Exception as exc:
                failures.append(f"{page_path.name}:{type(exc).__name__}:{exc}")
                continue
            widths.add(width)
            heights.add(height)
            ink_fractions.append(ink)
            page_bytes.append(page_path.stat().st_size)
            if width < 500 or height < 700:
                failures.append(f"{page_path.name}:small-dimensions={width}x{height}")
            if ink < 0.001:
                failures.append(f"{page_path.name}:near-blank ink={ink:.6f}")
            if ink > 0.75:
                failures.append(f"{page_path.name}:overfilled ink={ink:.6f}")
    dimensions = "x".join([str(next(iter(widths))) if len(widths) == 1 else f"mixed:{sorted(widths)}", str(next(iter(heights))) if len(heights) == 1 else f"mixed:{sorted(heights)}"])
    status = "pass" if not failures and len(ink_fractions) == pages else "needs revision"
    return {
        "manuscript": label,
        "status": status,
        "pdf": rel(pdf_path),
        "pages": str(pages),
        "rendered_pages": str(len(ink_fractions)),
        "dimensions": dimensions,
        "min_ink_fraction": f"{min(ink_fractions):.6f}" if ink_fractions else "nan",
        "max_ink_fraction": f"{max(ink_fractions):.6f}" if ink_fractions else "nan",
        "min_page_bytes": str(min(page_bytes)) if page_bytes else "0",
        "max_page_bytes": str(max(page_bytes)) if page_bytes else "0",
        "render_seconds": "not_recorded",
        "failures": "; ".join(failures) if failures else "none",
        "next_action": "No action needed." if status == "pass" else "Inspect the rendered PDF pages and fix missing, blank, clipped, or overfilled output.",
    }


def build_rows() -> list[dict[str, str]]:
    return [
        render_pdf("author", AUTHOR_PDF),
        render_pdf("anonymous", ANONYMOUS_PDF),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "manuscript",
        "status",
        "pdf",
        "pages",
        "rendered_pages",
        "dimensions",
        "min_ink_fraction",
        "max_ink_fraction",
        "min_page_bytes",
        "max_page_bytes",
        "render_seconds",
        "failures",
        "next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# PDF Visual Audit",
        "",
        "This terminal audit renders every page of the author and anonymous PDFs with Poppler and checks for readable, nonblank page images.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(["", "| manuscript | status | pages | rendered | dimensions | ink range | failures |", "|---|---|---:|---:|---|---|---|"])
    for row in rows:
        lines.append(
            "| {manuscript} | {status} | {pages} | {rendered_pages} | {dimensions} | {min_ink_fraction}--{max_ink_fraction} | {failures} |".format(
                **{key: value.replace("|", "\\|") for key, value in row.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "needs_revision_count": counts.get("needs revision", 0),
        "status_counts": dict(sorted(counts.items())),
        "source_files": {
            "author_pdf": rel(AUTHOR_PDF),
            "anonymous_pdf": rel(ANONYMOUS_PDF),
        },
        "outputs": {
            "summary": "results/summary_pdf_visual_audit.csv",
            "analysis": "results/analysis_pdf_visual_audit.md",
            "manifest": "results/manifest_pdf_visual_audit.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_pdf_visual_audit.csv", rows)
    write_markdown(RESULTS / "analysis_pdf_visual_audit.md", rows)
    write_manifest(RESULTS / "manifest_pdf_visual_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} PDF visual audit row(s)")
    if failures:
        print(f"warning: {failures} PDF visual row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
