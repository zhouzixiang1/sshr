#!/usr/bin/env python3
"""Smoke-test the upload payload after extracting it to a clean directory.

The round-trip audit proves that files and hashes inside the tarball match the
manifest.  This audit goes one step further: it extracts the payload into a
temporary directory and runs a small set of reviewer-facing Python audits from
inside that extracted tree.  The selected scripts are intentionally lightweight
and do not invoke LaTeX, external synthesis tools, private metadata, or raw
experiment reruns.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from make_submission_payload_archive import ARCHIVE, PAYLOAD_ROOT, THIS_DIR


RESULTS = THIS_DIR / "results"


@dataclass(frozen=True)
class SmokeSpec:
    name: str
    script: str
    manifest: str
    expected_key: str
    expected_value: int
    minimum_rows_key: str
    minimum_rows: int
    timeout_seconds: int = 60


SMOKE_SPECS = (
    SmokeSpec(
        name="Comparison protocol audit",
        script="analyze_comparison_protocol_audit.py",
        manifest="results/manifest_comparison_protocol_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="layers",
        minimum_rows=7,
    ),
    SmokeSpec(
        name="Comparison target validity audit",
        script="analyze_comparison_target_validity_audit.py",
        manifest="results/manifest_comparison_target_validity_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=7,
    ),
    SmokeSpec(
        name="Comparison answer scorecard",
        script="analyze_comparison_answer_scorecard.py",
        manifest="results/manifest_comparison_answer_scorecard.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=7,
    ),
    SmokeSpec(
        name="Score-weight robustness audit",
        script="analyze_weight_robustness.py",
        manifest="results/manifest_weight_robustness.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="compact_checks",
        minimum_rows=28,
    ),
    SmokeSpec(
        name="Resource-weight sensitivity audit",
        script="analyze_resource_weight_sensitivity_audit.py",
        manifest="results/manifest_resource_weight_sensitivity_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=12000,
    ),
    SmokeSpec(
        name="CNOT constraint profile audit",
        script="analyze_cnot_constraint_profile_audit.py",
        manifest="results/manifest_cnot_constraint_profile_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="summary_rows",
        minimum_rows=6,
    ),
    SmokeSpec(
        name="SSHR reproduction-scope audit",
        script="analyze_sshr_reproduction_scope_audit.py",
        manifest="results/manifest_sshr_reproduction_scope_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Novelty/comparison scorecard",
        script="analyze_novelty_comparison_scorecard.py",
        manifest="results/manifest_novelty_comparison_scorecard.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=6,
    ),
    SmokeSpec(
        name="Threats-to-validity audit",
        script="analyze_threats_to_validity_audit.py",
        manifest="results/manifest_threats_to_validity_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=7,
    ),
    SmokeSpec(
        name="ROS reproduction gap audit",
        script="analyze_ros_reproduction_gap_audit.py",
        manifest="results/manifest_ros_reproduction_gap_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="ROS-style LUT garbage proxy",
        script="analyze_ros_lut_garbage_proxy.py",
        manifest="results/manifest_ros_lut_garbage_proxy.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=927,
    ),
    SmokeSpec(
        name="ROS-style LUT garbage budget frontier",
        script="analyze_ros_lut_garbage_budget_frontier.py",
        manifest="results/manifest_ros_lut_garbage_budget_frontier.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=1059,
    ),
    SmokeSpec(
        name="ROS-style LUT checkpoint optimizer",
        script="analyze_ros_lut_checkpoint_optimizer.py",
        manifest="results/manifest_ros_lut_checkpoint_optimizer.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=474,
    ),
    SmokeSpec(
        name="Published STG counterpoint",
        script="analyze_stg_published_benchmark.py",
        manifest="results/manifest_stg_published_benchmark.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=270,
    ),
    SmokeSpec(
        name="Schedule-proxy tradeoff audit",
        script="analyze_schedule_proxy_audit.py",
        manifest="results/manifest_schedule_proxy_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Ultra-scale n=48--64 stress audit",
        script="analyze_ultra_scale64_stress.py",
        manifest="results/manifest_screen_scale_ultra_scale64_stress.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=480,
    ),
    SmokeSpec(
        name="Ultra-scale n=48--64 resource profile",
        script="analyze_ultra_scale64_resource_profile.py",
        manifest="results/manifest_screen_scale_ultra_scale64_resource_profile.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=480,
    ),
    SmokeSpec(
        name="Search-budget contract audit",
        script="analyze_search_budget_contract.py",
        manifest="results/manifest_search_budget_contract.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Search-control baseline audit",
        script="analyze_search_control_baseline_audit.py",
        manifest="results/manifest_search_control_baseline_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Bit-flip low-budget learned-prior sweep",
        script="analyze_bitflip_neural_budget_sweep.py",
        manifest="results/manifest_bitflip_neural_budget_sweep.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="raw_rows",
        minimum_rows=2124,
    ),
    SmokeSpec(
        name="Bit-flip learned-prior feature gate",
        script="analyze_bitflip_prior_feature_gate.py",
        manifest="results/manifest_bitflip_prior_feature_gate.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="aggregate_pairs",
        minimum_rows=1593,
    ),
    SmokeSpec(
        name="Bit-flip learned-prior cross-validated feature gate",
        script="analyze_bitflip_prior_feature_gate_cv.py",
        manifest="results/manifest_bitflip_prior_feature_gate_cv.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="aggregate_pairs",
        minimum_rows=1593,
    ),
    SmokeSpec(
        name="Bit-flip learned-prior random-interval gate control",
        script="analyze_bitflip_prior_feature_gate_cv_random_control.py",
        manifest="results/manifest_bitflip_prior_feature_gate_cv_random_control.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="random_repeats",
        minimum_rows=200,
    ),
    SmokeSpec(
        name="Root-action ranker audit",
        script="analyze_root_action_ranker_audit.py",
        manifest="results/manifest_root_action_ranker_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=5,
    ),
    SmokeSpec(
        name="Phase rotation-precision audit",
        script="analyze_phase_rotation_precision_audit.py",
        manifest="results/manifest_phase_rotation_precision_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=28,
    ),
    SmokeSpec(
        name="Phase rotation-sequence smoke audit",
        script="analyze_phase_rotation_sequence_smoke_audit.py",
        manifest="results/manifest_phase_rotation_sequence_smoke_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="smoke_pass_count",
        minimum_rows=20,
    ),
    SmokeSpec(
        name="Rotation-synthesis backend audit",
        script="analyze_rotation_synthesis_backend_audit.py",
        manifest="results/manifest_rotation_synthesis_backend_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=4,
    ),
    SmokeSpec(
        name="Phase policy budget frontier",
        script="analyze_phase_policy_budget_frontier.py",
        manifest="results/manifest_phase_policy_budget_frontier.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Learned-control audit",
        script="analyze_learned_control_audit.py",
        manifest="results/manifest_learned_control_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=9,
    ),
    SmokeSpec(
        name="Neural/MCTS claim calibration",
        script="analyze_neural_mcts_claim_calibration.py",
        manifest="results/manifest_neural_mcts_claim_calibration.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=7,
    ),
    SmokeSpec(
        name="Bit-flip random-prior control",
        script="analyze_bitflip_random_prior_control.py",
        manifest="results/manifest_bitflip_random_prior_control.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=18,
    ),
    SmokeSpec(
        name="Frontier random-depth control",
        script="analyze_frontier_random_depth_control.py",
        manifest="results/manifest_frontier_random_depth_control.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=3,
    ),
    SmokeSpec(
        name="Stochastic-control stability",
        script="analyze_stochastic_control_stability.py",
        manifest="results/manifest_stochastic_control_stability.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=6,
    ),
    SmokeSpec(
        name="Editorial screening audit",
        script="analyze_editorial_screening_audit.py",
        manifest="results/manifest_editorial_screening_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Target venue decision audit",
        script="analyze_target_venue_decision_audit.py",
        manifest="results/manifest_target_venue_decision_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=5,
    ),
    SmokeSpec(
        name="Target venue ACM/TQC format smoke",
        script="analyze_target_venue_format_smoke.py",
        manifest="results/manifest_target_venue_format_smoke.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=5,
    ),
    SmokeSpec(
        name="Submission support packet audit",
        script="analyze_submission_support_packet_audit.py",
        manifest="results/manifest_submission_support_packet_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Headline numeric consistency",
        script="analyze_headline_numeric_consistency.py",
        manifest="results/manifest_headline_numeric_consistency.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="claims",
        minimum_rows=15,
    ),
    SmokeSpec(
        name="Citation support audit",
        script="analyze_citation_support_audit.py",
        manifest="results/manifest_citation_support_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=10,
    ),
    SmokeSpec(
        name="PDF visual audit",
        script="analyze_pdf_visual_audit.py",
        manifest="results/manifest_pdf_visual_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=2,
    ),
    SmokeSpec(
        name="PDF text audit",
        script="analyze_pdf_text_audit.py",
        manifest="results/manifest_pdf_text_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=2,
    ),
    SmokeSpec(
        name="PDF metadata audit",
        script="analyze_pdf_metadata_audit.py",
        manifest="results/manifest_pdf_metadata_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=2,
    ),
    SmokeSpec(
        name="Source path privacy audit",
        script="analyze_source_path_privacy_audit.py",
        manifest="results/manifest_source_path_privacy_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=6,
    ),
    SmokeSpec(
        name="Author-input closure audit",
        script="analyze_author_input_closure_audit.py",
        manifest="results/manifest_author_input_closure_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=7,
    ),
    SmokeSpec(
        name="Author questionnaire coverage audit",
        script="analyze_author_questionnaire_coverage.py",
        manifest="results/manifest_author_questionnaire_coverage.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=6,
    ),
    SmokeSpec(
        name="Author minimal response-form coverage audit",
        script="analyze_author_minimal_form_coverage.py",
        manifest="results/manifest_author_minimal_form_coverage.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=6,
    ),
    SmokeSpec(
        name="Submission metadata closure path",
        script="analyze_submission_metadata_closure_path.py",
        manifest="results/manifest_submission_metadata_closure_path.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=8,
    ),
    SmokeSpec(
        name="Claim-scope lint",
        script="analyze_claim_scope_lint.py",
        manifest="results/manifest_claim_scope_lint.json",
        expected_key="unresolved_count",
        expected_value=0,
        minimum_rows_key="required_boundary_count",
        minimum_rows=5,
    ),
    SmokeSpec(
        name="Payload Git policy audit",
        script="analyze_payload_git_policy_audit.py",
        manifest="results/manifest_payload_git_policy_audit.json",
        expected_key="needs_revision_count",
        expected_value=0,
        minimum_rows_key="rows",
        minimum_rows=2,
    ),
    SmokeSpec(
        name="Artifact rerun registry",
        script="analyze_artifact_rerun_registry.py",
        manifest="results/manifest_artifact_rerun_registry.json",
        expected_key="complete_rows",
        expected_value=-1,
        minimum_rows_key="rows",
        minimum_rows=10,
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def row(item: str, status: str, evidence: str, next_action: str) -> dict[str, str]:
    return {"item": item, "status": status, "evidence": evidence, "next_action": next_action}


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


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def count_value(value: object, default: int) -> int:
    if isinstance(value, list):
        return len(value)
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def smoke_script(payload_dir: Path, spec: SmokeSpec) -> dict[str, str]:
    script_path = payload_dir / spec.script
    if not script_path.exists():
        return row(
            spec.name,
            "needs revision",
            f"missing script={spec.script}.",
            "Regenerate the payload archive so the extracted smoke-test script is present.",
        )
    try:
        env = {**dict(os.environ), "RESOURCE_NMCTS_EXTRACTED_PAYLOAD": "1"}
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=payload_dir,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=spec.timeout_seconds,
            env=env,
        )
    except Exception as exc:
        return row(
            spec.name,
            "needs revision",
            f"execution failed: {type(exc).__name__}: {exc}.",
            "Fix the lightweight audit so it runs from an extracted payload directory.",
        )

    manifest = read_json(payload_dir / spec.manifest)
    expected_actual = count_value(manifest.get(spec.expected_key), -999999) if manifest else -999999
    minimum_actual = count_value(manifest.get(spec.minimum_rows_key), -1) if manifest else -1
    expected_ok = expected_actual == spec.expected_value
    if spec.expected_value == -1 and spec.expected_key == "complete_rows":
        expected_ok = expected_actual >= spec.minimum_rows
    status = "pass" if proc.returncode == 0 and manifest and expected_ok and minimum_actual >= spec.minimum_rows else "needs revision"
    stderr = proc.stderr.strip().splitlines()
    evidence = (
        f"returncode={proc.returncode}; manifest={spec.manifest}; "
        f"{spec.expected_key}={expected_actual}; {spec.minimum_rows_key}={minimum_actual}; "
        f"stderr={stderr[:2] or 'none'}"
    )
    return row(
        spec.name,
        status,
        evidence,
        "Inspect the extracted payload audit output and regenerate the archive if this smoke test fails.",
    )


def build_rows() -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory(prefix="resource_nmcts_payload_smoke_") as tmp:
        payload_dir, count, error = extract_payload(Path(tmp))
        rows = [
            row(
                "Payload extraction",
                "pass" if payload_dir is not None and count > 0 and not error else "needs revision",
                f"archive={rel(ARCHIVE)}; extracted_files={count}; error={error or 'none'}.",
                "Regenerate the payload archive if it cannot be safely extracted.",
            )
        ]
        if payload_dir is None:
            return rows
        rows.extend(smoke_script(payload_dir, spec) for spec in SMOKE_SPECS)
        return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["item", "status", "evidence", "next_action"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    lines = [
        "# Payload Extraction Smoke Audit",
        "",
        "This terminal audit extracts the reviewer/upload payload into a temporary directory and runs lightweight reviewer-facing checks from the extracted tree.",
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
    counts: dict[str, int] = {}
    for item in rows:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "archive": rel(ARCHIVE),
        "status_counts": counts,
        "needs_revision_count": counts.get("needs revision", 0),
        "smoke_scripts": [
            {
                "name": spec.name,
                "script": spec.script,
                "manifest": spec.manifest,
                "expected_key": spec.expected_key,
                "minimum_rows_key": spec.minimum_rows_key,
            }
            for spec in SMOKE_SPECS
        ],
        "outputs": {
            "summary": rel(RESULTS / "summary_payload_extraction_smoke_audit.csv"),
            "analysis": rel(RESULTS / "analysis_payload_extraction_smoke_audit.md"),
            "manifest": rel(RESULTS / "manifest_payload_extraction_smoke_audit.json"),
        },
        "rows": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_payload_extraction_smoke_audit.csv", rows)
    write_markdown(RESULTS / "analysis_payload_extraction_smoke_audit.md", rows)
    write_manifest(RESULTS / "manifest_payload_extraction_smoke_audit.json", rows)
    failures = sum(1 for item in rows if item["status"] == "needs revision")
    print(f"wrote {len(rows)} payload extraction smoke row(s)")
    if failures:
        print(f"warning: {failures} payload extraction smoke row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
