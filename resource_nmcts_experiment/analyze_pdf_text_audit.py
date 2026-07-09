#!/usr/bin/env python3
"""Extract compiled PDF text and check reviewer-facing manuscript anchors.

The visual audit proves that pages render, but a submission PDF can still be
image-only or lose searchable text.  This terminal audit runs Poppler
``pdftotext`` on the author and anonymous PDFs, then checks that key title,
scope, baseline, availability, reference, and headline-number anchors survive
in the final compiled artifacts.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
AUTHOR_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
ANONYMOUS_PDF = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"


@dataclass(frozen=True)
class AnchorSpec:
    label: str
    variants: tuple[str, ...]


REQUIRED_ANCHORS = (
    AnchorSpec("title", ("resource-constrained neural monte carlo tree search",)),
    AnchorSpec("method name", ("resource-nmcts", "resource nmcts")),
    AnchorSpec("logical-layer boundary", ("logical-layer", "logical layer")),
    AnchorSpec("problem scope", ("quantum boolean oracle synthesis",)),
    AnchorSpec("abstract", ("abstract",)),
    AnchorSpec("related work", ("related work",)),
    AnchorSpec("baseline discussion", ("baselines used", "traditional slice contains", "external abc")),
    AnchorSpec("data and code availability", ("data and code availability",)),
    AnchorSpec("references", ("references",)),
    AnchorSpec("traditional baseline count", ("177-function", "177 function", "177 functions")),
    AnchorSpec("abstract headline 72.25", ("72.25",)),
    AnchorSpec("abstract headline 67.80", ("67.80",)),
    AnchorSpec("large external evidence count", ("15,774", "15774")),
    AnchorSpec("truth-table bridge count", ("400/400", "400 / 400")),
    AnchorSpec("SSHR baseline", ("sshr",)),
    AnchorSpec("ABC baseline", ("abc-aig", "abc aig", "abc-xag", "abc xag")),
    AnchorSpec("RevKit baseline", ("revkit",)),
    AnchorSpec("CirKit baseline", ("cirkit",)),
)

FORBIDDEN_PATTERNS = (
    r"\btodo\b",
    r"\btbd\b",
    r"\bplaceholder\b",
    r"author input required",
    r"\?\?",
    r"undefined citation",
    r"citation undefined",
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def normalize(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[\u2010-\u2015]", "-", lowered)
    lowered = re.sub(r"-\s+", "-", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "", normalize(text))


def variant_present(text_norm: str, text_compact: str, variant: str) -> bool:
    variant_norm = normalize(variant)
    variant_compact = compact(variant)
    return variant_norm in text_norm or variant_compact in text_compact


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


def extract_text(pdf_path: Path) -> tuple[int, str, str]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return -1, "", "pdftotext missing"
    if not pdf_path.exists():
        return -1, "", "pdf missing"
    try:
        proc = subprocess.run(
            [pdftotext, "-layout", str(pdf_path), "-"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
    except Exception as exc:
        return -1, "", f"{type(exc).__name__}: {exc}"
    return proc.returncode, proc.stdout, proc.stderr.strip()


def audit_pdf(label: str, pdf_path: Path) -> dict[str, str]:
    pages = pdf_pages(pdf_path)
    returncode, text, stderr = extract_text(pdf_path)
    text_norm = normalize(text)
    text_compact = compact(text)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9.+/-]*", text)
    missing = [
        anchor.label
        for anchor in REQUIRED_ANCHORS
        if not any(variant_present(text_norm, text_compact, variant) for variant in anchor.variants)
    ]
    forbidden_hits = [
        pattern
        for pattern in FORBIDDEN_PATTERNS
        if re.search(pattern, text_norm, flags=re.IGNORECASE)
    ]
    author_hit = "zixiang zhou" in text_norm
    anonymous_hit = "anonymous authors" in text_norm
    if label == "author":
        identity_issue = "" if author_hit and not anonymous_hit else "author identity anchor mismatch"
    else:
        identity_issue = "" if anonymous_hit and not author_hit else "anonymous identity anchor mismatch"
    failures = []
    if returncode != 0:
        failures.append(f"pdftotext returncode={returncode}")
    if pages <= 0:
        failures.append("pdfinfo page count missing")
    if len(text) < 20_000:
        failures.append(f"short extracted text={len(text)}")
    if len(words) < 2_000:
        failures.append(f"low word count={len(words)}")
    if missing:
        failures.append(f"missing anchors={','.join(missing)}")
    if forbidden_hits:
        failures.append(f"forbidden text={','.join(forbidden_hits)}")
    if identity_issue:
        failures.append(identity_issue)
    status = "pass" if not failures else "needs revision"
    return {
        "manuscript": label,
        "status": status,
        "pdf": rel(pdf_path),
        "pages": str(pages),
        "characters": str(len(text)),
        "words": str(len(words)),
        "required_anchors": str(len(REQUIRED_ANCHORS)),
        "missing_anchors": "; ".join(missing) if missing else "none",
        "forbidden_hits": "; ".join(forbidden_hits) if forbidden_hits else "none",
        "author_identity_anchor": str(author_hit),
        "anonymous_identity_anchor": str(anonymous_hit),
        "pdftotext_returncode": str(returncode),
        "stderr": stderr[:240] if stderr else "none",
        "failures": "; ".join(failures) if failures else "none",
        "next_action": "No action needed." if status == "pass" else "Inspect pdftotext output and fix missing searchable text, anchors, or public placeholder remnants.",
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
        "characters",
        "words",
        "required_anchors",
        "missing_anchors",
        "forbidden_hits",
        "author_identity_anchor",
        "anonymous_identity_anchor",
        "pdftotext_returncode",
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
        "# PDF Text Audit",
        "",
        "This terminal audit extracts searchable text from the author and anonymous PDFs with Poppler and checks manuscript anchors, identity separation, and public-placeholder hygiene.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| manuscript | status | pages | characters | words | missing anchors | forbidden hits | identity anchors | failures |",
            "|---|---|---:|---:|---:|---|---|---|---|",
        ]
    )
    for row in rows:
        identity = f"author={row['author_identity_anchor']}; anonymous={row['anonymous_identity_anchor']}"
        lines.append(
            "| {manuscript} | {status} | {pages} | {characters} | {words} | {missing_anchors} | {forbidden_hits} | {identity} | {failures} |".format(
                identity=identity,
                **{key: value.replace("|", "\\|") for key, value in row.items()},
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "required_anchor_count": len(REQUIRED_ANCHORS),
        "needs_revision_count": counts.get("needs revision", 0),
        "status_counts": dict(sorted(counts.items())),
        "source_files": {
            "author_pdf": rel(AUTHOR_PDF),
            "anonymous_pdf": rel(ANONYMOUS_PDF),
        },
        "outputs": {
            "summary": "results/summary_pdf_text_audit.csv",
            "analysis": "results/analysis_pdf_text_audit.md",
            "manifest": "results/manifest_pdf_text_audit.json",
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_pdf_text_audit.csv", rows)
    write_markdown(RESULTS / "analysis_pdf_text_audit.md", rows)
    write_manifest(RESULTS / "manifest_pdf_text_audit.json", rows)
    failures = sum(1 for row in rows if row["status"] == "needs revision")
    print(f"wrote {len(rows)} PDF text audit row(s)")
    if failures:
        print(f"warning: {failures} PDF text row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
