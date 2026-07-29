#!/usr/bin/env python3
"""Build the curated XA-202609 competition delivery ZIP and hash manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "XA-202609_Resource-NMCTS_final"
DEFAULT_ZIP = ROOT / "submission_package" / "dist" / f"{PACKAGE_NAME}.zip"
DEFAULT_MANIFEST = ROOT / "submission_package" / "dist" / f"{PACKAGE_NAME}.manifest.json"
FIXED_ZIP_TIME = (2026, 7, 22, 0, 0, 0)


@dataclass(frozen=True)
class FileSpec:
    source: Path
    archive_path: str
    role: str


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def as_root_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (ROOT / path).resolve()


class Inventory:
    def __init__(self) -> None:
        self._items: dict[str, FileSpec] = {}

    def add(self, source: Path, archive_path: str, role: str) -> None:
        source = source.resolve()
        if not source.is_file():
            raise FileNotFoundError(f"required delivery file missing: {source}")
        archive_path = archive_path.replace("\\", "/").lstrip("/")
        if archive_path.startswith("../") or "/../" in archive_path:
            raise ValueError(f"unsafe archive path: {archive_path}")
        previous = self._items.get(archive_path)
        if previous and previous.source != source:
            raise ValueError(f"archive collision: {archive_path}: {previous.source} vs {source}")
        if previous is None:
            self._items[archive_path] = FileSpec(source, archive_path, role)

    def add_root_relative(self, relative: str, archive_path: str, role: str) -> None:
        self.add(ROOT / relative, archive_path, role)

    def values(self) -> list[FileSpec]:
        return [self._items[key] for key in sorted(self._items)]


def add_python_tree(inventory: Inventory, directory: str, archive_prefix: str, role: str) -> None:
    base = ROOT / directory
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(base).as_posix()
        inventory.add(path, f"{archive_prefix}/{relative}", role)


def canonical_evidence_archive(path: Path) -> str:
    path = path.resolve()
    if path.is_relative_to(ROOT / "results"):
        return f"results/raw/{path.relative_to(ROOT / 'results').as_posix()}"
    if path.is_relative_to(ROOT / "models"):
        return f"models/{path.name}"
    if path.is_relative_to(ROOT / "submission_competition" / "figures"):
        return f"paper/figures/{path.name}"
    if path.is_relative_to(ROOT / "submission_competition"):
        return f"evidence/{path.relative_to(ROOT / 'submission_competition').as_posix()}"
    raise ValueError(f"evidence file lies outside curated roots: {path}")


def build_inventory() -> Inventory:
    inventory = Inventory()

    # Reader-facing document and build inputs.
    for source_name, archive_name, role in (
        ("DELIVERY_README.md", "README.md", "delivery guide"),
        ("main.pdf", "paper/main.pdf", "final competition PDF"),
        ("main.tex", "paper/main.tex", "LaTeX manuscript source"),
        ("main.bbl", "paper/main.bbl", "resolved bibliography output"),
        ("references.bib", "paper/references.bib", "BibTeX source"),
        ("generated_final_numbers.tex", "paper/generated_final_numbers.tex", "frozen statistical macros"),
    ):
        inventory.add(ROOT / "submission_competition" / source_name, archive_name, role)

    figure_dir = ROOT / "submission_competition" / "figures"
    canonical_figure_names = {
        "CIRCUIT_FIGURE_CONTRACT.md",
        "make_standard_circuit_figures.py",
        "standard_circuit_figure_manifest.json",
        "standard_circuit_figure_source.csv",
        "FIGURE_CONTRACT_ARCHITECTURE.md",
        "make_architecture_figure.py",
        "architecture_figure_manifest.json",
        "architecture_figure_source.json",
        "FIGURE_CONTRACT_AI_ABLATION.md",
        "make_ai_ablation_figure.py",
        "ai_ablation_figure_manifest.json",
        "ai_ablation_figure_source.csv",
        "ai_ablation_figure_source.json",
        "FIGURE_CONTRACT_PRIMARY_RESULTS.md",
        "make_primary_results_figure.py",
        "primary_results_figure_manifest.json",
        "primary_results_figure_source.csv",
        "primary_results_figure_source.json",
        "PRIMARY_RESULTS_FIGURE_QA.md",
        "FIGURE_CONTRACT_COVERAGE_RESOURCE.md",
        "make_coverage_resource_figure.py",
        "coverage_resource_figure_manifest.json",
        "coverage_resource_figure_source.csv",
        "coverage_resource_figure_source.json",
        "coverage_resource_figure_qa.md",
    }
    for stem in (
        "F0_standard_oracle_comparison",
        "F1_standard_hardware_mapping",
        "A1a_standard_circuit_gallery_structured",
        "A1b_standard_circuit_gallery_randomized",
        "F2_system_architecture",
        "F3_ai_ablation_attribution",
        "F4_frozen_primary_results",
        "F5_coverage_correctness_resource",
    ):
        canonical_figure_names.update(f"{stem}.{suffix}" for suffix in ("svg", "pdf", "png"))
    for name in sorted(canonical_figure_names):
        inventory.add(figure_dir / name, f"paper/figures/{name}", "figure output/source/contract")

    # Implementation, experiment runners and tests.
    add_python_tree(inventory, "src", "src", "compiler implementation")
    add_python_tree(inventory, "scripts", "scripts", "training/experiment runner")
    add_python_tree(inventory, "tests", "tests", "regression test")
    inventory.add(
        ROOT / "submission" / "export_benchmarks.py",
        "submission/export_benchmarks.py",
        "benchmark export dependency used by smoke tests",
    )
    for name in (
        "analyze_competition_results.py",
        "audit_competition_literature.ps1",
        "audit_formal_coverage.py",
        "build_competition_delivery.py",
        "build_experiments_db.py",
        "build_final_primary20_report.py",
        "consolidate_verified_experiment.py",
        "filter_validated_hardware_rows.py",
        "ingest_hardware_validation.py",
        "qa_competition_pdf.py",
        "qa_competition_delivery_archive.py",
        "verify_delivery_manifest.py",
    ):
        inventory.add(ROOT / "analysis" / name, f"analysis/{name}", "analysis/audit source")
    inventory.add(
        ROOT / "analysis" / "verify_delivery_manifest.py",
        "verify_delivery_manifest.py",
        "portable delivery integrity checker",
    )
    for name in ("README.md", "DESIGN.md"):
        inventory.add(ROOT / name, f"project_docs/{name}", "project documentation")

    for name in ("action_scorer.pt", "action_scorer_competition.pt", "action_scorer_rollout_competition.pt"):
        inventory.add(ROOT / "models" / name, f"models/{name}", "frozen model checkpoint")

    # Frozen contracts, audits and environment evidence. Transitional/pre-fix
    # snapshots are deliberately not copied.
    evidence_names = (
        "EXPERIMENT_PROTOCOL.md",
        "GOAL_AND_ACCEPTANCE.md",
        "HARDWARE_COMPATIBILITY.md",
        "TERMINOLOGY_LEDGER.md",
        "benchmark_suite_v1.json",
        "benchmark_suite_v1.csv",
        "environment_manifest.json",
        "environment_packages.txt",
        "figure_environment.txt",
        "final_analysis_manifest.json",
        "final_core_recovery_manifest_v1.json",
        "formal_coverage_audit.json",
        "formal_coverage_by_case.csv",
        "formal_coverage_duplicates.csv",
        "formal_coverage_missing.csv",
        "formal_coverage_primary20_recovery_plan.csv",
        "formal_primary20_core3_final_manifest_v2.json",
        "literature_review_matrix.md",
        "literature_verification_audit.json",
        "literature_verification_audit.csv",
        "literature_verification_audit.md",
        "primary20_execution_environment_manifest.json",
        "primary20_execution_packages.txt",
        "training_manifest_competition.json",
        "training_manifest_rollout_competition.json",
    )
    for name in evidence_names:
        inventory.add(ROOT / "submission_competition" / name, f"evidence/{name}", "frozen evidence/contract")

    for name in (
        "VISUAL_QA.md",
        "page_metrics.csv",
        "visual_qa_manifest.json",
        "contact_sheet_01.png",
        "contact_sheet_02.png",
        "contact_sheet_03.png",
        "contact_sheet_04.png",
        "contact_sheet_05.png",
    ):
        inventory.add(
            ROOT / "submission_competition" / "pdf_qa" / name,
            f"evidence/pdf_qa/{name}",
            "final PDF visual QA",
        )

    inventory.add(
        ROOT / "results" / "competition_primary20_final.duckdb",
        "results/competition_primary20_final.duckdb",
        "frozen experiment database",
    )
    for path in sorted((ROOT / "results" / "final_stats").glob("*")):
        if path.is_file():
            inventory.add(path, f"results/final_stats/{path.name}", "function-level statistical output")

    # Preserve exactly the raw/recovered files named by the frozen primary
    # consolidation and the F3 AI-attribution evidence contract.
    consolidation = load_json(ROOT / "submission_competition" / "formal_primary20_core3_final_manifest_v2.json")
    for row in consolidation["sources"]:
        path = as_root_path(row["path"])
        inventory.add(path, canonical_evidence_archive(path), "primary20 raw/recovered JSONL")

    ai_source = load_json(ROOT / "submission_competition" / "figures" / "ai_ablation_figure_source.json")
    for row in ai_source["evidence_files"]:
        path = as_root_path(row["path"])
        inventory.add(path, canonical_evidence_archive(path), "AI attribution evidence")

    return inventory


def validate_frozen_state() -> dict[str, object]:
    analysis = load_json(ROOT / "submission_competition" / "final_analysis_manifest.json")
    coverage = load_json(ROOT / "submission_competition" / "formal_coverage_audit.json")
    literature = load_json(ROOT / "submission_competition" / "literature_verification_audit.json")
    visual = load_json(ROOT / "submission_competition" / "pdf_qa" / "visual_qa_manifest.json")
    pdf = ROOT / "submission_competition" / "main.pdf"
    database = ROOT / "results" / "competition_primary20_final.duckdb"

    expected_db_sha = "8cc494ed4506f245d29bebbb8e328a991558c0d4f67d0d2b9244bab2bad77be7"
    expected_analysis_id = "xa202609-primary20-836553591061"
    if sha256_file(database) != expected_db_sha or analysis["database_sha256"] != expected_db_sha:
        raise ValueError("frozen DuckDB hash mismatch")
    if analysis["analysis_id"] != expected_analysis_id:
        raise ValueError("unexpected final analysis ID")
    if analysis["strict_significant_better_count"] != 10:
        raise ValueError("strict-significance count drifted")
    if analysis["coverage"]["planned_cells"] != 360 or analysis["coverage"]["verified_cells"] != 360:
        raise ValueError("analysis coverage drifted")
    primary_coverage = coverage["coverage"]["primary20_core3"]
    if primary_coverage["intended_cells"] != 360 or primary_coverage["union_verified_cells"] != 360:
        raise ValueError("coverage audit drifted")
    status_counts = literature.get("counts", {})
    if status_counts.get("verified") != 23 or any(status_counts.get(key, 0) for key in ("suspicious", "mismatch", "not_found")):
        raise ValueError("literature verification is not 23/23 clean")
    pdf_sha = sha256_file(pdf)
    if visual["pdf_sha256"] != pdf_sha or visual["pages"] != 20 or visual["review_pages"]:
        raise ValueError("final PDF visual QA does not match the PDF")
    return {
        "analysis_id": expected_analysis_id,
        "database_sha256": expected_db_sha,
        "pdf_sha256": pdf_sha,
        "planned_cells": 360,
        "verified_cells": 360,
        "strict_significant_better_count": 10,
        "literature_verified": 23,
        "pdf_pages": 20,
        "pdf_visual_review_pages": [],
        "regression_tests": "60 passed, 15 subtests passed; smoke ok",
    }


def manifest_payload(inventory: Inventory, frozen: dict[str, object]) -> tuple[dict[str, object], bytes]:
    records = []
    for spec in inventory.values():
        records.append(
            {
                "path": spec.archive_path,
                "role": spec.role,
                "source": spec.source.relative_to(ROOT).as_posix(),
                "size_bytes": spec.source.stat().st_size,
                "sha256": sha256_file(spec.source),
            }
        )
    content_digest = sha256_bytes(
        "".join(f"{row['path']}\0{row['sha256']}\0{row['size_bytes']}\n" for row in records).encode("utf-8")
    )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "competition": "XA-202609",
        "package_name": PACKAGE_NAME,
        "build_date": "2026-07-22",
        "layout": "curated portable delivery; provenance manifests may retain original absolute execution paths",
        "frozen_evidence": frozen,
        "file_count_excluding_manifest": len(records),
        "content_manifest_sha256": content_digest,
        "files": records,
        "intentional_exclusions": [
            "pre-schema/pre-identity DuckDB snapshots",
            "legacy inventory databases",
            "early stress/pilot files not referenced by the frozen primary or F3 contracts",
            "LaTeX auxiliary/log files",
            "individual 144-dpi PDF page PNGs (five inspected contact sheets and metrics are included)",
        ],
    }
    payload = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return manifest, payload


def write_zip(zip_path: Path, inventory: Inventory, manifest_bytes: bytes) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for spec in inventory.values():
            info = zipfile.ZipInfo(f"{PACKAGE_NAME}/{spec.archive_path}", FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, spec.source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        info = zipfile.ZipInfo(f"{PACKAGE_NAME}/DELIVERY_MANIFEST.json", FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, manifest_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_zip(zip_path: Path, inventory: Inventory, manifest_bytes: bytes) -> None:
    expected = {
        f"{PACKAGE_NAME}/{spec.archive_path}": sha256_file(spec.source)
        for spec in inventory.values()
    }
    expected[f"{PACKAGE_NAME}/DELIVERY_MANIFEST.json"] = sha256_bytes(manifest_bytes)
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("ZIP member set mismatch or duplicate member")
        for name, digest in expected.items():
            if sha256_bytes(archive.read(name)) != digest:
                raise ValueError(f"ZIP member hash mismatch: {name}")
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"ZIP CRC failure: {bad_member}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--force", action="store_true", help="replace only the explicitly named output files")
    args = parser.parse_args()
    zip_path = args.zip.resolve()
    manifest_path = args.manifest.resolve()
    sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    existing = [path for path in (zip_path, manifest_path, sha_path) if path.exists()]
    if existing and not args.force:
        raise FileExistsError("delivery output already exists; pass --force to replace: " + ", ".join(map(str, existing)))
    if args.force:
        for path in existing:
            path.unlink()

    frozen = validate_frozen_state()
    inventory = build_inventory()
    manifest, manifest_bytes = manifest_payload(inventory, frozen)
    write_zip(zip_path, inventory, manifest_bytes)
    verify_zip(zip_path, inventory, manifest_bytes)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)
    zip_sha = sha256_file(zip_path)
    sha_path.write_text(f"{zip_sha}  {zip_path.name}\n", encoding="ascii")
    print(
        json.dumps(
            {
                "zip": str(zip_path.relative_to(ROOT)),
                "zip_bytes": zip_path.stat().st_size,
                "zip_sha256": zip_sha,
                "manifest": str(manifest_path.relative_to(ROOT)),
                "files_excluding_manifest": manifest["file_count_excluding_manifest"],
                "archive_members": manifest["file_count_excluding_manifest"] + 1,
                "verified": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
