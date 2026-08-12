#!/usr/bin/env python3
"""Audit the ACM TQC formatting smoke draft.

The target-venue decision audit says ACM TQC is the recommended first target.
This terminal audit verifies that the current package includes a generated
ACM-style anonymous review draft, that the local TeX installation can compile
it, and that its text still exposes the core logical-layer contribution.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
PAPER_DIR = THIS_DIR / "paper_latex"
ACM_SOURCE = PAPER_DIR / "resource_nmcts_submission_acm_tqc.tex"
ACM_PDF = PAPER_DIR / "resource_nmcts_submission_acm_tqc.pdf"
ACM_LOG = PAPER_DIR / "resource_nmcts_submission_acm_tqc.log"
TARGET_VENUE_MANIFEST = RESULTS / "manifest_target_venue_decision_audit.json"
EXTRACTED_PAYLOAD_MODE = os.environ.get("RESOURCE_NMCTS_EXTRACTED_PAYLOAD") == "1"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def run_capture(command: list[str], cwd: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        return subprocess.CompletedProcess(command, 1, "", f"{type(exc).__name__}: {exc}")


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {
        "item": item,
        "status": status,
        "evidence": evidence,
        "next_action": next_action,
    }


def pdf_pages(path: Path) -> int:
    if not path.exists():
        return -1
    proc = run_capture(["pdfinfo", str(path)], timeout=10)
    match = re.search(r"^Pages:\s+(\d+)", proc.stdout, flags=re.MULTILINE)
    return int(match.group(1)) if match else -1


def pdf_text(path: Path) -> str:
    if not path.exists():
        return ""
    proc = run_capture(["pdftotext", str(path), "-"], timeout=30)
    return proc.stdout if proc.returncode == 0 else ""


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
    return int(tokens[1]), int(tokens[2]), int(tokens[3]), index


def ppm_ink_fraction(path: Path) -> tuple[int, int, float]:
    width, height, max_value, offset = read_ppm_header(path)
    if max_value != 255:
        raise ValueError(f"{path.name} has unsupported max value {max_value}")
    payload = path.read_bytes()[offset : offset + width * height * 3]
    if len(payload) < width * height * 3:
        raise ValueError(f"{path.name} has truncated pixel data")
    nonwhite = 0
    for index in range(0, len(payload), 3):
        if payload[index] < 250 or payload[index + 1] < 250 or payload[index + 2] < 250:
            nonwhite += 1
    return width, height, nonwhite / (width * height)


def render_sample(path: Path, pages: int) -> tuple[int, str, list[str]]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return 0, "missing", ["pdftoppm missing"]
    if not path.exists() or pages <= 0:
        return 0, "missing", ["pdf missing or page count unavailable"]
    render_to = min(3, pages)
    failures: list[str] = []
    ink_values: list[float] = []
    with tempfile.TemporaryDirectory(prefix="resource_nmcts_acm_tqc_render_") as tmp:
        prefix = Path(tmp) / "acm_tqc"
        proc = run_capture(
            [pdftoppm, "-r", "72", "-f", "1", "-l", str(render_to), str(path), str(prefix)],
            timeout=30,
        )
        if proc.returncode != 0:
            failures.append(f"pdftoppm returncode={proc.returncode}; stderr={proc.stderr.strip()[:160]}")
        rendered = sorted(Path(tmp).glob("acm_tqc-*.ppm"))
        if len(rendered) != render_to:
            failures.append(f"rendered_pages={len(rendered)} expected={render_to}")
        for page in rendered:
            try:
                width, height, ink = ppm_ink_fraction(page)
            except Exception as exc:
                failures.append(f"{page.name}:{type(exc).__name__}:{exc}")
                continue
            ink_values.append(ink)
            if width < 500 or height < 700:
                failures.append(f"{page.name}:small_dimensions={width}x{height}")
            if ink < 0.001:
                failures.append(f"{page.name}:near_blank_ink={ink:.6f}")
            if ink > 0.75:
                failures.append(f"{page.name}:overfilled_ink={ink:.6f}")
    ink_range = (
        f"{min(ink_values):.6f}--{max(ink_values):.6f}" if ink_values else "missing"
    )
    return len(ink_values), ink_range, failures


def unexpected_log_lines(path: Path) -> list[str]:
    if not path.exists():
        return ["log missing"]
    bad_patterns = re.compile(r"LaTeX Error|Undefined control sequence|Emergency stop|Fatal error")
    unexpected: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not bad_patterns.search(line):
            continue
        unexpected.append(f"{lineno}:{line.strip()}")
    return unexpected


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    kpse = run_capture(["kpsewhich", "acmart.cls"], timeout=10)
    acmart_path = kpse.stdout.strip()
    rows.append(
        row(
            "ACM class availability",
            "pass" if kpse.returncode == 0 and acmart_path else "needs revision",
            f"kpsewhich_returncode={kpse.returncode}; acmart_cls={acmart_path or 'missing'}.",
            "Install TeX Live acmart or choose a non-ACM target format before relying on the ACM/TQC draft.",
        )
    )

    source = ACM_SOURCE.read_text(encoding="utf-8", errors="replace") if ACM_SOURCE.exists() else ""
    required_source_tokens = (
        r"\documentclass[manuscript,screen,review,anonymous]{acmart}",
        r"\acmJournal{TQC}",
        r"\author{Anonymous Authors}",
        r"\bibliographystyle{ACM-Reference-Format}",
        "Final author metadata, rights text",
        r"\ccsdesc[500]{Theory of computation~Quantum computation theory}",
        r"\keywords{quantum Boolean oracle synthesis",
        r"\Description{Pipeline diagram",
    )
    missing_source = [token for token in required_source_tokens if token not in source]
    forbidden_source = [token for token in ("Zixiang Zhou", r"\documentclass[11pt]{article}") if token in source]
    rows.append(
        row(
            "ACM TQC review source",
            "pass" if ACM_SOURCE.exists() and not missing_source and not forbidden_source else "needs revision",
            f"source_exists={ACM_SOURCE.exists()}; missing_tokens={missing_source or 'none'}; forbidden_tokens={forbidden_source or 'none'}.",
            "Run make_acm_tqc_review_draft.py after changing the anonymous manuscript or ACM/TQC formatting preamble.",
        )
    )

    pages = pdf_pages(ACM_PDF)
    pdf_bytes = ACM_PDF.stat().st_size if ACM_PDF.exists() else 0
    log_issues = unexpected_log_lines(ACM_LOG)
    fatal_log_issues = [item for item in log_issues if item != "log missing"]
    rendered_pages, ink_range, render_issues = render_sample(ACM_PDF, pages)
    rows.append(
        row(
            "ACM TQC compiled PDF",
            "pass"
            if ACM_PDF.exists()
            and pages > 0
            and pdf_bytes > 100_000
            and not fatal_log_issues
            and rendered_pages == min(3, pages)
            and not render_issues
            else "needs revision",
            f"pdf_exists={ACM_PDF.exists()}; pages={pages}; bytes={pdf_bytes}; rendered_sample_pages={rendered_pages}; ink_range={ink_range}; unexpected_log_lines={log_issues[:3] or 'none'}; render_issues={render_issues[:3] or 'none'}.",
            "Compile paper_latex/resource_nmcts_submission_acm_tqc.tex and inspect unexpected log, blank-page, or render failures.",
        )
    )

    log_text = ACM_LOG.read_text(encoding="utf-8", errors="replace") if ACM_LOG.exists() else ""
    warning_tokens = (
        "A possible image without description",
        "Some images may lack descriptions",
        "ACM keywords are mandatory",
        "ACM reference format is mandatory",
        "CCS concepts are mandatory",
    )
    warning_hits = [token for token in warning_tokens if token in log_text]
    log_missing_allowed = EXTRACTED_PAYLOAD_MODE and not ACM_LOG.exists()
    rows.append(
        row(
            "ACM TQC metadata and accessibility warnings",
            "pass" if (ACM_LOG.exists() or log_missing_allowed) and not warning_hits else "needs revision",
            f"log_exists={ACM_LOG.exists()}; log_missing_allowed={log_missing_allowed}; warning_hits={warning_hits or 'none'}.",
            "Add ACM CCS concepts, keywords, reference-strip metadata, and figure descriptions to the generated ACM/TQC review draft.",
        )
    )

    text = pdf_text(ACM_PDF)
    required_text = (
        "Resource-Constrained Neural Monte Carlo Tree Search",
        "Resource-NMCTS",
        "logical-layer",
        "Data and Code Availability",
    )
    missing_text = [token for token in required_text if token not in text]
    local_user_path = "/".join(["", "Users", "zhouzixiang"])
    old_workspace_path = "/".join(["Desktop", "tzb"])
    forbidden_text = [token for token in ("Zixiang Zhou", local_user_path, old_workspace_path) if token in text]
    rows.append(
        row(
            "ACM TQC text anchors",
            "pass" if text and not missing_text and not forbidden_text else "needs revision",
            f"characters={len(text)}; missing_text={missing_text or 'none'}; forbidden_text={forbidden_text or 'none'}.",
            "Regenerate and recompile the ACM/TQC draft if title, method, scope, anonymity, or availability text is missing.",
        )
    )

    venue_manifest = read_json(TARGET_VENUE_MANIFEST)
    first_choice = venue_manifest.get("recommended_first_choice", "missing")
    rows.append(
        row(
            "Target-venue alignment",
            "pass" if first_choice == "ACM Transactions on Quantum Computing" else "needs revision",
            f"recommended_first_choice={first_choice}.",
            "Update the ACM/TQC smoke path if the target-venue decision changes.",
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
    counts = Counter(item["status"] for item in rows)
    lines = [
        "# Target Venue Format Smoke Audit",
        "",
        "This audit checks the generated ACM/TQC anonymous review-format draft.",
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
        "source": rel(ACM_SOURCE),
        "pdf": rel(ACM_PDF),
        "pdf_pages": pdf_pages(ACM_PDF),
        "pdf_bytes": ACM_PDF.stat().st_size if ACM_PDF.exists() else 0,
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "rows_detail": rows,
        "outputs": {
            "summary": rel(RESULTS / "summary_target_venue_format_smoke.csv"),
            "analysis": rel(RESULTS / "analysis_target_venue_format_smoke.md"),
            "manifest": rel(RESULTS / "manifest_target_venue_format_smoke.json"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_target_venue_format_smoke.csv", rows)
    write_markdown(RESULTS / "analysis_target_venue_format_smoke.md", rows)
    write_manifest(RESULTS / "manifest_target_venue_format_smoke.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} target-venue format smoke row(s)")
    if failures:
        print(f"warning: {failures} target-venue format smoke row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
