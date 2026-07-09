#!/usr/bin/env python3
"""Build an archive-level manifest for the submission artifact package.

The archive manifest is a packaging audit, not a scientific result.  It hashes
the stable submission payload groups that a reviewer or archive maintainer
would need to reconstruct the paper-facing evidence.  Terminal package/audit
outputs and the compiled manuscript PDF are intentionally excluded from the
digest set to avoid self-referential hashes: the PDF contains this table, and
the readiness audit checks the PDF and uploadable tarball separately.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
FIGURES = THIS_DIR / "paper_latex" / "figures" / "submission_v36"
SOURCE_DATA = FIGURES / "source_data"
MODELS = THIS_DIR / "models"
TOOLS = THIS_DIR / "tools"
SUBMISSION_PACKAGE = THIS_DIR / "submission_package"

SELF_OUTPUTS = {
    RESULTS / "summary_submission_archive_manifest.csv",
    RESULTS / "analysis_submission_archive_manifest.md",
    RESULTS / "manifest_submission_archive_manifest.json",
    TABLES / "submission_archive_manifest.tex",
}

TERMINAL_PACKAGE_OUTPUTS = {
    RESULTS / "summary_submission_readiness_audit.csv",
    RESULTS / "analysis_submission_readiness_audit.md",
    RESULTS / "summary_submission_package_verifier.csv",
    RESULTS / "analysis_submission_package_verifier.md",
    RESULTS / "manifest_submission_package_verifier.json",
    RESULTS / "summary_goal_completion_audit.csv",
    RESULTS / "analysis_goal_completion_audit.md",
    RESULTS / "manifest_goal_completion_audit.json",
    RESULTS / "summary_submission_traceability_audit.csv",
    RESULTS / "analysis_submission_traceability_audit.md",
    RESULTS / "manifest_submission_traceability_audit.json",
    RESULTS / "summary_submission_payload_archive.csv",
    RESULTS / "analysis_submission_payload_archive.md",
    RESULTS / "manifest_submission_payload_archive.json",
    RESULTS / "summary_payload_roundtrip_audit.csv",
    RESULTS / "analysis_payload_roundtrip_audit.md",
    RESULTS / "manifest_payload_roundtrip_audit.json",
    RESULTS / "summary_payload_extraction_smoke_audit.csv",
    RESULTS / "analysis_payload_extraction_smoke_audit.md",
    RESULTS / "manifest_payload_extraction_smoke_audit.json",
    RESULTS / "summary_payload_verifier_smoke_audit.csv",
    RESULTS / "analysis_payload_verifier_smoke_audit.md",
    RESULTS / "manifest_payload_verifier_smoke_audit.json",
    RESULTS / "summary_payload_latex_compile_audit.csv",
    RESULTS / "analysis_payload_latex_compile_audit.md",
    RESULTS / "manifest_payload_latex_compile_audit.json",
    RESULTS / "summary_latex_dependency_audit.csv",
    RESULTS / "analysis_latex_dependency_audit.md",
    RESULTS / "manifest_latex_dependency_audit.json",
    RESULTS / "summary_pdf_visual_audit.csv",
    RESULTS / "analysis_pdf_visual_audit.md",
    RESULTS / "manifest_pdf_visual_audit.json",
    RESULTS / "summary_pdf_text_audit.csv",
    RESULTS / "analysis_pdf_text_audit.md",
    RESULTS / "manifest_pdf_text_audit.json",
    RESULTS / "summary_pdf_metadata_audit.csv",
    RESULTS / "analysis_pdf_metadata_audit.md",
    RESULTS / "manifest_pdf_metadata_audit.json",
    RESULTS / "summary_source_path_privacy_audit.csv",
    RESULTS / "analysis_source_path_privacy_audit.md",
    RESULTS / "manifest_source_path_privacy_audit.json",
    TABLES / "submission_traceability_audit.tex",
}

PRIVATE_SUBMISSION_TEXT_OUTPUTS = {
    SUBMISSION_PACKAGE / "generated_author_declarations.md",
    SUBMISSION_PACKAGE / "generated_availability_statements.md",
    SUBMISSION_PACKAGE / "generated_cover_letter.md",
    SUBMISSION_PACKAGE / "generated_submission_text.md",
}


@dataclass(frozen=True)
class CategorySpec:
    category: str
    explicit: tuple[Path, ...]
    patterns: tuple[tuple[Path, str], ...]
    boundary: str
    exclude_terminal_outputs: bool = False


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_sorted(paths: list[Path]) -> list[Path]:
    return sorted(set(paths), key=lambda item: rel(item))


def collect(spec: CategorySpec) -> tuple[list[Path], list[Path]]:
    found: list[Path] = []
    missing: list[Path] = []
    for path in spec.explicit:
        if path.exists():
            found.append(path)
        else:
            missing.append(path)
    for root, pattern in spec.patterns:
        if root.exists():
            found.extend(path for path in root.glob(pattern) if path.is_file())

    exclusions = set(SELF_OUTPUTS) | PRIVATE_SUBMISSION_TEXT_OUTPUTS
    if spec.exclude_terminal_outputs:
        exclusions |= TERMINAL_PACKAGE_OUTPUTS
    found = [path for path in found if path not in exclusions]
    return unique_sorted(found), unique_sorted(missing)


def category_digest(files: list[Path]) -> tuple[str, list[dict[str, object]], int]:
    aggregate = hashlib.sha256()
    entries: list[dict[str, object]] = []
    total_bytes = 0
    for path in files:
        size = path.stat().st_size
        digest = sha256_file(path)
        relative = rel(path)
        total_bytes += size
        aggregate.update(f"{relative}\t{size}\t{digest}\n".encode("utf-8"))
        entries.append({"path": relative, "bytes": size, "sha256": digest})
    if not files:
        return "", entries, total_bytes
    return aggregate.hexdigest(), entries, total_bytes


def specs() -> list[CategorySpec]:
    return [
        CategorySpec(
            category="Manuscript source",
            explicit=(
                THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex",
                THIS_DIR / "paper_latex" / "resource_nmcts_submission_anonymous.tex",
                THIS_DIR / "paper_latex" / "references.bib",
                THIS_DIR / "paper_latex" / "README.md",
            ),
            patterns=(),
            boundary="Compiled PDF is checked by readiness audit to avoid self-referential hashes.",
        ),
        CategorySpec(
            category="Paper tables",
            explicit=(),
            patterns=((TABLES, "*.tex"),),
            boundary="Terminal submission audit tables are excluded from the stable payload digest.",
            exclude_terminal_outputs=True,
        ),
        CategorySpec(
            category="Submission figures",
            explicit=(),
            patterns=((FIGURES, "*.pdf"), (FIGURES, "*.png"), (FIGURES, "*.svg"), (SOURCE_DATA, "*.csv")),
            boundary="Includes generated figure assets and plotted source data, not raw benchmark reruns.",
        ),
        CategorySpec(
            category="Raw measurements",
            explicit=(),
            patterns=((RESULTS, "raw_*.csv"),),
            boundary="Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild.",
        ),
        CategorySpec(
            category="Derived summaries",
            explicit=(),
            patterns=((RESULTS, "summary_*.csv"), (RESULTS, "analysis_*.md")),
            boundary="Terminal submission/package outputs are excluded so this manifest remains stable.",
            exclude_terminal_outputs=True,
        ),
        CategorySpec(
            category="Run manifests",
            explicit=(),
            patterns=((RESULTS, "manifest_*.json"),),
            boundary="Submission-level terminal manifests are excluded from this digest group.",
            exclude_terminal_outputs=True,
        ),
        CategorySpec(
            category="Scripts and docs",
            explicit=(
                THIS_DIR / "README.md",
                THIS_DIR / "DELIVERABLE_zh.md",
                THIS_DIR / "rebuild_submission_package.sh",
                THIS_DIR / "verify_submission_package.sh",
                THIS_DIR / "validate_submission_metadata.py",
                THIS_DIR / "selftest_submission_metadata_pipeline.py",
            ),
            patterns=((THIS_DIR, "run_*.py"), (THIS_DIR, "train_*.py"), (THIS_DIR, "analyze_*.py"), (THIS_DIR, "make_*.py")),
            boundary="Documents reproducible entry points; raw sweeps still require their individual drivers.",
        ),
        CategorySpec(
            category="Models",
            explicit=(),
            patterns=((MODELS, "*.pt"), (MODELS, "*.json"), (MODELS, "*.csv")),
            boundary="Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild.",
        ),
        CategorySpec(
            category="External adapters",
            explicit=(),
            patterns=((TOOLS, "*"),),
            boundary="Includes local adapter source files used for external toolchain probes, not vendored tool repositories.",
        ),
        CategorySpec(
            category="Submission support",
            explicit=(),
            patterns=((SUBMISSION_PACKAGE, "*.md"), (SUBMISSION_PACKAGE, "*_template.json")),
            boundary="Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded.",
        ),
    ]


def build_rows() -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    rows: list[dict[str, str]] = []
    manifest_entries: list[dict[str, object]] = []
    for spec in specs():
        files, missing = collect(spec)
        digest, entries, total_bytes = category_digest(files)
        representatives = "; ".join(rel(path) for path in files[:4])
        if len(files) > 4:
            representatives += f"; +{len(files) - 4} more"
        rows.append(
            {
                "category": spec.category,
                "files": str(len(files)),
                "missing": str(len(missing)),
                "bytes": str(total_bytes),
                "sha256_digest": digest,
                "representative_paths": representatives,
                "boundary": spec.boundary,
            }
        )
        manifest_entries.append(
            {
                "category": spec.category,
                "file_count": len(files),
                "missing": [rel(path) for path in missing],
                "bytes": total_bytes,
                "sha256_digest": digest,
                "files": entries,
                "boundary": spec.boundary,
            }
        )
    return rows, manifest_entries


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["category", "files", "missing", "bytes", "sha256_digest", "representative_paths", "boundary"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MiB"
    if value >= 1024:
        return f"{value / 1024:.1f} KiB"
    return f"{value} B"


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    complete = sum(1 for row in rows if row["missing"] == "0")
    lines = [
        "# Submission Archive Manifest",
        "",
        "This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.",
        "",
        "## Status counts",
        "",
        f"- complete categories: {complete}/{len(rows)}",
        "",
        "| category | files | missing | size | digest | boundary |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        digest = row["sha256_digest"][:16] if row["sha256_digest"] else "empty"
        lines.append(
            f"| {row['category']} | {row['files']} | {row['missing']} | "
            f"{fmt_bytes(int(row['bytes']))} | `{digest}` | {row['boundary']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.22\linewidth}rr>{\raggedright\arraybackslash}p{0.14\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Payload group & Files & Missing & Digest & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        digest = row["sha256_digest"][:12] if row["sha256_digest"] else "empty"
        lines.append(
            " & ".join(
                [
                    tex_escape(row["category"]),
                    row["files"],
                    row["missing"],
                    r"\texttt{" + tex_escape(digest) + r"}",
                    tex_escape(row["boundary"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, entries: list[dict[str, object]]) -> None:
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "note": (
            "Compiled PDF and terminal submission/package outputs are excluded "
            "from payload hashes to avoid self-referential digests."
        ),
        "outputs": {
            "summary": rel(RESULTS / "summary_submission_archive_manifest.csv"),
            "analysis": rel(RESULTS / "analysis_submission_archive_manifest.md"),
            "table": rel(TABLES / "submission_archive_manifest.tex"),
        },
        "categories": entries,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows, entries = build_rows()
    write_csv(RESULTS / "summary_submission_archive_manifest.csv", rows)
    write_markdown(RESULTS / "analysis_submission_archive_manifest.md", rows)
    write_latex(TABLES / "submission_archive_manifest.tex", rows)
    write_manifest(RESULTS / "manifest_submission_archive_manifest.json", entries)
    missing = sum(int(row["missing"]) for row in rows)
    print(f"wrote {len(rows)} submission archive manifest groups")
    if missing:
        print(f"warning: {missing} expected files are missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
