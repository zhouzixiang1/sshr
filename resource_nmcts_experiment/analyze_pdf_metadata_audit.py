#!/usr/bin/env python3
"""Check compiled PDF metadata and privacy-sensitive PDF flags.

The visual and text audits cover rendered pages and searchable content.  This
terminal audit inspects Poppler ``pdfinfo`` metadata for the author and
anonymous PDFs so that private names, placeholder text, encryption, JavaScript,
or unexpected page geometry do not silently enter the submission artifacts.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
AUTHOR_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"

COMMON_FORBIDDEN_METADATA_PATTERNS = (
    r"author input required",
    r"\btodo\b",
    r"\btbd\b",
    r"\bplaceholder\b",
    r"/users/",
    r"desktop/tzb",
)
IDENTITY_METADATA_PATTERNS = (
    r"zixiang",
    r"zhou",
)
MIN_EXPECTED_PAGES = 20
MAX_EXPECTED_PAGES = 45


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def parse_pdfinfo(output: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def run_pdfinfo(path: Path) -> tuple[int, dict[str, str], str]:
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return -1, {}, "pdfinfo missing"
    if not path.exists():
        return -1, {}, "pdf missing"
    try:
        proc = subprocess.run(
            [pdfinfo, str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
    except Exception as exc:
        return -1, {}, f"{type(exc).__name__}: {exc}"
    return proc.returncode, parse_pdfinfo(proc.stdout), proc.stderr.strip()


def float_pair(text: str) -> tuple[float, float] | None:
    match = re.search(r"([0-9.]+)\s+x\s+([0-9.]+)\s+pts", text)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def page_size_ok(value: str) -> bool:
    pair = float_pair(value)
    if pair is None:
        return False
    width, height = pair
    return 590.0 <= width <= 600.0 and 835.0 <= height <= 850.0


def metadata_blob(fields: dict[str, str]) -> str:
    keys = ("Title", "Subject", "Keywords", "Author", "Creator", "Producer")
    return " ".join(fields.get(key, "") for key in keys).lower()


def audit_pdf(label: str, pdf_path: Path) -> dict[str, str]:
    returncode, fields, stderr = run_pdfinfo(pdf_path)
    blob = metadata_blob(fields)
    forbidden_hits = [
        pattern
        for pattern in COMMON_FORBIDDEN_METADATA_PATTERNS
        if re.search(pattern, blob, flags=re.IGNORECASE)
    ]
    identity_hits = [
        pattern
        for pattern in IDENTITY_METADATA_PATTERNS
        if re.search(pattern, blob, flags=re.IGNORECASE)
    ]
    failures: list[str] = []
    if returncode != 0:
        failures.append(f"pdfinfo returncode={returncode}")
    try:
        page_count = int(fields.get("Pages", "0"))
    except ValueError:
        page_count = 0
    if not (MIN_EXPECTED_PAGES <= page_count <= MAX_EXPECTED_PAGES):
        failures.append(f"pages={fields.get('Pages', 'missing')}")
    if fields.get("Encrypted") != "no":
        failures.append(f"encrypted={fields.get('Encrypted', 'missing')}")
    if fields.get("JavaScript") != "no":
        failures.append(f"javascript={fields.get('JavaScript', 'missing')}")
    if fields.get("Form") not in {"none", "AcroForm"}:
        failures.append(f"form={fields.get('Form', 'missing')}")
    if fields.get("Tagged") not in {"no", "yes"}:
        failures.append(f"tagged={fields.get('Tagged', 'missing')}")
    if not page_size_ok(fields.get("Page size", "")):
        failures.append(f"page_size={fields.get('Page size', 'missing')}")
    if forbidden_hits:
        failures.append(f"forbidden metadata={','.join(forbidden_hits)}")
    if label == "anonymous" and identity_hits:
        failures.append(f"anonymous metadata identity={','.join(identity_hits)}")
    status = "pass" if not failures else "needs revision"
    return {
        "manuscript": label,
        "status": status,
        "pdf": rel(pdf_path),
        "pages": fields.get("Pages", "missing"),
        "encrypted": fields.get("Encrypted", "missing"),
        "javascript": fields.get("JavaScript", "missing"),
        "form": fields.get("Form", "missing"),
        "page_size": fields.get("Page size", "missing"),
        "title": fields.get("Title", ""),
        "author": fields.get("Author", ""),
        "creator": fields.get("Creator", ""),
        "producer": fields.get("Producer", ""),
        "forbidden_metadata_hits": "; ".join(forbidden_hits) if forbidden_hits else "none",
        "identity_metadata_hits": "; ".join(identity_hits) if identity_hits else "none",
        "pdfinfo_returncode": str(returncode),
        "stderr": stderr[:240] if stderr else "none",
        "failures": "; ".join(failures) if failures else "none",
        "next_action": "No action needed." if status == "pass" else "Inspect pdfinfo metadata and rebuild PDFs with sanitized hyperref metadata or PDF settings.",
    }


def build_rows() -> list[dict[str, str]]:
    return [
        audit_pdf("author", AUTHOR_PDF),
        audit_pdf("anonymous", ANONYMOUS_PDF),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "manuscript",
        "status",
        "pdf",
        "pages",
        "encrypted",
        "javascript",
        "form",
        "page_size",
        "title",
        "author",
        "creator",
        "producer",
        "forbidden_metadata_hits",
        "identity_metadata_hits",
        "pdfinfo_returncode",
        "stderr",
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
        "# PDF Metadata Audit",
        "",
        "This terminal audit checks author and anonymous PDF metadata with Poppler pdfinfo for privacy-sensitive fields and PDF flags.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| manuscript | status | pages | encrypted | javascript | page size | title | author | forbidden metadata | identity metadata | failures |",
            "|---|---|---:|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {manuscript} | {status} | {pages} | {encrypted} | {javascript} | {page_size} | {title} | {author} | {forbidden_metadata_hits} | {identity_metadata_hits} | {failures} |".format(
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
        "expected_page_range": {
            "min": MIN_EXPECTED_PAGES,
            "max": MAX_EXPECTED_PAGES,
        },
        "outputs": {
            "summary": "results/summary_pdf_metadata_audit.csv",
            "analysis": "results/analysis_pdf_metadata_audit.md",
            "manifest": "results/manifest_pdf_metadata_audit.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_pdf_metadata_audit.csv", rows)
    write_markdown(RESULTS / "analysis_pdf_metadata_audit.md", rows)
    write_manifest(RESULTS / "manifest_pdf_metadata_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} PDF metadata audit row(s)")
    if failures:
        print(f"warning: {failures} PDF metadata row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
