#!/usr/bin/env python3
"""Create a deterministic reviewer/upload payload archive.

The archive packages the stable source/data payload groups, the compiled
manuscript PDF, and the package-level traceability/archive audits.  It excludes
its own tarball, the readiness audit, and the goal-completion audit so the
final terminal checks can run after archive creation without changing the
archive's contents.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import tarfile
import sys
from pathlib import Path

from analyze_submission_archive_manifest import collect, rel, sha256_file, specs


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.pdf"
ANONYMOUS_PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.pdf"
DIST = THIS_DIR / "submission_package" / "dist"
ARCHIVE = DIST / "resource_nmcts_submission_payload.tar.gz"
SHA256 = DIST / "resource_nmcts_submission_payload.tar.gz.sha256"
PAYLOAD_ROOT = "resource_nmcts_submission_payload"

EXTRA_FILES = (
    PAPER,
    ANONYMOUS_PAPER,
    RESULTS / "summary_submission_archive_manifest.csv",
    RESULTS / "analysis_submission_archive_manifest.md",
    RESULTS / "manifest_submission_archive_manifest.json",
    TABLES / "submission_archive_manifest.tex",
    RESULTS / "summary_submission_traceability_audit.csv",
    RESULTS / "analysis_submission_traceability_audit.md",
    RESULTS / "manifest_submission_traceability_audit.json",
    TABLES / "submission_traceability_audit.tex",
)

SELF_OUTPUTS = {
    ARCHIVE,
    SHA256,
    RESULTS / "summary_submission_payload_archive.csv",
    RESULTS / "analysis_submission_payload_archive.md",
    RESULTS / "manifest_submission_payload_archive.json",
}


def collect_payload_files() -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    missing: list[Path] = []
    for spec in specs():
        found, missing_for_spec = collect(spec)
        files.extend(found)
        missing.extend(missing_for_spec)
    for path in EXTRA_FILES:
        if path.exists():
            files.append(path)
        else:
            missing.append(path)
    filtered = [path for path in files if path not in SELF_OUTPUTS]
    return sorted(set(filtered), key=rel), sorted(set(missing), key=rel)


def tar_mode(path: Path) -> int:
    if path.suffix == ".sh":
        return 0o755
    return 0o644


def write_archive(path: Path, files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for file_path in files:
                    data = file_path.read_bytes()
                    info = tarfile.TarInfo(f"{PAYLOAD_ROOT}/{rel(file_path)}")
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = tar_mode(file_path)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    tar.addfile(info, io.BytesIO(data))


def write_sha256(path: Path, archive: Path) -> str:
    digest = sha256_file(archive)
    path.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return digest


def write_summary_csv(path: Path, files: list[Path], missing: list[Path], archive_digest: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = sum(file_path.stat().st_size for file_path in files)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["archive", "files", "missing", "input_bytes", "archive_bytes", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "archive": rel(ARCHIVE),
                "files": len(files),
                "missing": len(missing),
                "input_bytes": total_bytes,
                "archive_bytes": ARCHIVE.stat().st_size,
                "sha256": archive_digest,
            }
        )


def write_analysis(path: Path, files: list[Path], missing: list[Path], archive_digest: str) -> None:
    total_bytes = sum(file_path.stat().st_size for file_path in files)
    lines = [
        "# Submission Payload Archive",
        "",
        "This report records the deterministic reviewer/upload archive generated from the current paper-facing payload.",
        "",
        f"- archive: `{rel(ARCHIVE)}`",
        f"- sha256 file: `{rel(SHA256)}`",
        f"- file count: {len(files)}",
        f"- missing expected files: {len(missing)}",
        f"- input bytes: {total_bytes}",
        f"- archive bytes: {ARCHIVE.stat().st_size}",
        f"- archive sha256: `{archive_digest}`",
        "",
        "The archive excludes itself and the readiness audit; the readiness audit runs after archive creation and checks that this archive exists.",
    ]
    if missing:
        lines.extend(["", "## Missing files", ""])
        lines.extend(f"- `{rel(path)}`" for path in missing)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, files: list[Path], missing: list[Path], archive_digest: str) -> None:
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "archive": rel(ARCHIVE),
        "sha256_file": rel(SHA256),
        "sha256": archive_digest,
        "file_count": len(files),
        "missing": [rel(path) for path in missing],
        "input_bytes": sum(file_path.stat().st_size for file_path in files),
        "archive_bytes": ARCHIVE.stat().st_size,
        "excluded_from_payload": [
            rel(ARCHIVE),
            rel(SHA256),
            rel(RESULTS / "summary_submission_payload_archive.csv"),
            rel(RESULTS / "analysis_submission_payload_archive.md"),
            rel(RESULTS / "manifest_submission_payload_archive.json"),
            rel(RESULTS / "summary_submission_readiness_audit.csv"),
            rel(RESULTS / "analysis_submission_readiness_audit.md"),
            rel(RESULTS / "summary_goal_completion_audit.csv"),
            rel(RESULTS / "analysis_goal_completion_audit.md"),
            rel(RESULTS / "manifest_goal_completion_audit.json"),
            rel(RESULTS / "summary_payload_extraction_smoke_audit.csv"),
            rel(RESULTS / "analysis_payload_extraction_smoke_audit.md"),
            rel(RESULTS / "manifest_payload_extraction_smoke_audit.json"),
            rel(RESULTS / "summary_payload_latex_compile_audit.csv"),
            rel(RESULTS / "analysis_payload_latex_compile_audit.md"),
            rel(RESULTS / "manifest_payload_latex_compile_audit.json"),
            rel(RESULTS / "summary_latex_dependency_audit.csv"),
            rel(RESULTS / "analysis_latex_dependency_audit.md"),
            rel(RESULTS / "manifest_latex_dependency_audit.json"),
            rel(RESULTS / "summary_pdf_visual_audit.csv"),
            rel(RESULTS / "analysis_pdf_visual_audit.md"),
            rel(RESULTS / "manifest_pdf_visual_audit.json"),
            rel(RESULTS / "summary_pdf_text_audit.csv"),
            rel(RESULTS / "analysis_pdf_text_audit.md"),
            rel(RESULTS / "manifest_pdf_text_audit.json"),
            rel(RESULTS / "summary_pdf_metadata_audit.csv"),
            rel(RESULTS / "analysis_pdf_metadata_audit.md"),
            rel(RESULTS / "manifest_pdf_metadata_audit.json"),
        ],
        "files": [
            {
                "path": rel(file_path),
                "bytes": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
            for file_path in files
        ],
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    files, missing = collect_payload_files()
    write_archive(ARCHIVE, files)
    digest = write_sha256(SHA256, ARCHIVE)
    write_summary_csv(RESULTS / "summary_submission_payload_archive.csv", files, missing, digest)
    write_analysis(RESULTS / "analysis_submission_payload_archive.md", files, missing, digest)
    write_manifest(RESULTS / "manifest_submission_payload_archive.json", files, missing, digest)
    print(f"wrote {rel(ARCHIVE)} with {len(files)} files")
    print(f"wrote {rel(SHA256)}")
    if missing:
        print(f"warning: {len(missing)} expected files are missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
