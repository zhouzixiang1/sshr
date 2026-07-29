#!/usr/bin/env python3
"""Rebuild the primary20 main analysis from 354/360 to 360/360.

This orchestrator runs the competition pipeline stages after the 6 sshr_beam
n=8 AES cells (aes_sbox_b0/b7 x seeds {7,17,29}) have been re-run with the
vectorised quad-mode fix. It merges the new rows into the frozen experiment,
refreshes coverage, paired statistics, the headline report, and the delivery
ZIP, and finally prints the new frozen constants that must be mirrored into
build_competition_delivery.validate_frozen_state().

Run from resource_nmcts/ with the mcts-qoracle interpreter. Stages are
idempotent where possible; the DuckDB and delivery ZIP are overwritten.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # resource_nmcts/
PYEXE = sys.executable
RESULTS = ROOT / "results"
RECOVERY_V4 = RESULTS / "recovery_v4c"
SUBMISSION = ROOT / "submission_competition"

# Frozen-analysis contract (must match consolidate_verified_experiment defaults).
METHODS = "direct_anf,greedy_factor,mcts_factor,resource_nmcts,sshr_beam,sshr_h"
SEEDS = "7,17,29"
TARGET_ID = "cx_full_12"
TRANSPILE_SEED = "3"
OPT_LEVEL = "1"
SLUG = "primary20-core3"
TITLE = "single-experiment verified paired analysis for primary20 core3"

# Original 25 source files that produced the 354/360 frozen manifest.
ORIGINAL_SOURCES = [
    "results/recovered/final_core_structured_v1_ok.jsonl",
    "results/recovered/final_core_random_truth_v1_ok.jsonl",
    "results/recovered/final_core_random_anf_v1_ok.jsonl",
    "results/recovered/final_core_aes_v1_ok.jsonl",
    "results/recovered/recovery_aes_b0_s7_v2_ok.jsonl",
    "results/stress_aes_b0_direct_s17_b8t8_v1.jsonl",
    "results/stress_aes_b0_direct_s29_b8t8e8_v1.jsonl",
    "results/stress_aes_b7_direct_s7_b16t16e16_v1.jsonl",
    "results/recovery_primary20_aes_b0_fast_v3.jsonl",
    "results/recovery_primary20_aes_b7_s17_s29_fast_v3.jsonl",
    "results/recovery_primary20_aes_b7_s7_fast_v3.jsonl",
    "results/recovery_primary20_beam_aes_b7_parallel_v3.jsonl",
    "results/recovery_primary20_beam_aes_v3.jsonl",
    "results/recovery_primary20_beam_struct_random_v3.jsonl",
    "results/recovery_primary20_maj7_s17_fast_v3.jsonl",
    "results/recovery_primary20_maj7_s29_fast_v3.jsonl",
    "results/recovery_primary20_maj7_s7_fast_v3.jsonl",
    "results/recovery_primary20_randanf7_resource_v3.jsonl",
    "results/recovery_primary20_randanf7_sshrh_s7_v3.jsonl",
    "results/recovery_primary20_randanf8_s173_resource_v3.jsonl",
    "results/recovery_primary20_randanf8_s173_sshrbeam_s29_v3.jsonl",
    "results/recovery_primary20_randanf8_s173_v3.jsonl",
    "results/recovery_primary20_randtt5_s113_s29_v3.jsonl",
    "results/recovery_primary20_randtt6_fast_v3.jsonl",
    "results/recovery_primary20_thr6_t3_fast_v3.jsonl",
]

STATS_DIR = RESULTS / "final_stats"
DB = RESULTS / "competition_primary20_final.duckdb"
BASELINES = ["direct_anf", "greedy_factor", "mcts_factor", "sshr_h", "sshr_beam"]


def run(cmd: list[str], **kw) -> None:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    rc = subprocess.call(cmd, cwd=str(ROOT), **kw)
    if rc != 0:
        raise SystemExit(f"stage failed (rc={rc}): {' '.join(cmd)}")


def safe_backup(path: Path, suffix: str = ".pre_360") -> None:
    """Move `path` aside to `<path><suffix>` so guarded tools can write a fresh copy.

    Windows os.rename refuses to overwrite an existing target (WinError 183),
    so remove any prior backup first. The originals are version-controlled,
    so deleting a stale intermediate backup is non-destructive.
    """
    if not path.exists():
        return
    target = path.with_suffix(path.suffix + suffix)
    if target.exists():
        target.unlink()
    path.rename(target)


def main() -> None:
    new_cells = sorted(RECOVERY_V4.glob("beam_aes_sbox_b*_s*.jsonl"))
    if len(new_cells) != 6:
        raise SystemExit(f"expected 6 new sshr_beam cells, found {len(new_cells)}: {new_cells}")
    for c in new_cells:
        if c.stat().st_size == 0:
            raise SystemExit(f"empty cell output (still running or failed?): {c}")

    # Stage 1 — filter the 6 new cells into per-cell success-only ok files.
    # Do NOT concatenate them: load_jsonl requires a single run_id per source
    # file, and the 6 cells were independent processes with distinct run_ids.
    # The per-cell ok files are passed individually to consolidate in Stage 3.
    filter_manifest = RESULTS / "recovered" / "manifest_beam_aes_v4.json"
    safe_backup(filter_manifest)
    # clear stale per-cell ok parts from a previous run
    for stale in (RESULTS / "recovered").glob("beam_aes_sbox_b*_s*_ok.jsonl"):
        stale.unlink()
    run([
        PYEXE, "analysis/filter_validated_hardware_rows.py",
        *[f"--input={str(c)}" for c in new_cells],
        f"--output-dir={RESULTS / 'recovered'}",
        f"--manifest={filter_manifest}",
    ])

    # Stage 3 — consolidate original 25 sources + the 6 new per-cell ok files
    # into the frozen DB. Pass each new ok file separately (NOT concatenated),
    # because load_jsonl requires a single run_id per source file and the 6 cells
    # were run as independent processes with distinct run_ids.
    # consolidate refuses to overwrite an existing manifest (safety guard), so
    # move the old frozen manifest + DB aside to .pre_360 backups first. Both are
    # already version-controlled, so this is non-destructive.
    manifest = SUBMISSION / "formal_primary20_core3_final_manifest_v2.json"
    coverage_audit = SUBMISSION / "formal_coverage_audit.json"
    safe_backup(manifest)
    safe_backup(DB)
    new_ok_files = sorted((RESULTS / "recovered").glob("beam_aes_sbox_b*_s*_ok.jsonl"))
    if len(new_ok_files) != 6:
        raise SystemExit(f"expected 6 new ok files, found {len(new_ok_files)}: {new_ok_files}")
    new_ok_rel = [f"results/recovered/{p.name}" for p in new_ok_files]
    inputs = ORIGINAL_SOURCES + new_ok_rel
    run([
        PYEXE, "analysis/consolidate_verified_experiment.py",
        *[f"--input={p}" for p in inputs],
        f"--coverage-audit={coverage_audit}",
        f"--methods={METHODS}", f"--seeds={SEEDS}",
        f"--target-id={TARGET_ID}", f"--transpile-seed={TRANSPILE_SEED}",
        f"--optimization-level={OPT_LEVEL}",
        f"--manifest={manifest}",
        f"--db={DB}",
        f"--experiment-slug={SLUG}", f"--experiment-title={TITLE}",
    ])

    # Stage 4 — refresh coverage audit. Pass the 6 new ok files (repeatable).
    run([
        PYEXE, "analysis/audit_formal_coverage.py",
        f"--db={DB}",
        *[f"--recovered-jsonl={p}" for p in new_ok_rel],
        f"--output-dir={SUBMISSION}",
    ])

    # Stage 5 — paired statistics for each baseline vs resource_nmcts.
    # The experiment slug and the full candidate method name (resource_nmcts may
    # carry a model-config hash suffix) must be read from the freshly built DB,
    # because consolidate re-derives them. Match the original analysis contract:
    # bootstrap 20000 samples, seed 202609, suite xa202609-final-v1.
    import sqlite3
    try:
        import duckdb as _duckdb
        _con = _duckdb.connect(str(DB), read_only=True)
        exp_slug = _con.execute("SELECT slug FROM experiments LIMIT 1").fetchone()[0]
        cand = _con.execute(
            "SELECT method_name FROM canonical_logical_results "
            "WHERE method_name LIKE 'resource_nmcts%' LIMIT 1"
        ).fetchone()[0]
        suite_val = _con.execute(
            "SELECT suite FROM canonical_logical_results WHERE suite LIKE 'xa202609%' LIMIT 1"
        ).fetchone()[0]
        _con.close()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"cannot read experiment/method/suite from new DB: {exc}")
    print(f"\n[stage5] experiment={exp_slug} candidate={cand} suite={suite_val}")
    for ref in BASELINES:
        run([
            PYEXE, "analysis/analyze_competition_results.py",
            f"--db={DB}",
            f"--csv={STATS_DIR / f'resource_vs_{ref}.csv'}",
            f"--json={STATS_DIR / f'resource_vs_{ref}.json'}",
            f"--experiment={exp_slug}", f"--suite={suite_val}",
            f"--reference-method={ref}", f"--candidate-method={cand}",
            "--required-seeds=7,17,29",
            "--bootstrap-samples=20000", "--bootstrap-seed=202609", "--alpha=0.05",
        ])

    # Stage 6 — headline report.
    run([
        PYEXE, "analysis/build_final_primary20_report.py",
        f"--database={DB}", f"--stats-dir={STATS_DIR}",
        f"--coverage={SUBMISSION / 'formal_coverage_audit.json'}",
        f"--consolidation-manifest={SUBMISSION / 'formal_primary20_core3_final_manifest_v2.json'}",
        f"--output-json={STATS_DIR / 'primary20_headline.json'}",
        f"--output-csv={STATS_DIR / 'primary20_headline.csv'}",
        f"--output-manifest={SUBMISSION / 'final_analysis_manifest.json'}",
        f"--output-tex={SUBMISSION / 'generated_final_numbers.tex'}",
    ])

    # Print the NEW frozen constants to mirror into validate_frozen_state().
    import hashlib, json
    db_sha = hashlib.sha256(DB.read_bytes()).hexdigest()
    fa = json.loads((SUBMISSION / "final_analysis_manifest.json").read_text(encoding="utf-8"))
    print("\n" + "=" * 70)
    print("NEW FROZEN CONSTANTS — update build_competition_delivery.py:268-298")
    print("=" * 70)
    print(f'expected_db_sha = "{db_sha}"')
    print(f'expected_analysis_id = "{fa.get("analysis_id")}"')
    print(f'strict_significant_better_count = {fa.get("strict_significant_better_count")}')
    cov = fa.get("coverage", {})
    print(f'planned_cells = {cov.get("planned_cells")}, verified_cells = {cov.get("verified_cells")}')
    print("=" * 70)


if __name__ == "__main__":
    main()
