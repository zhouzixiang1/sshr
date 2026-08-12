from __future__ import annotations

import io
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parent
BUILDER = EXPERIMENT_ROOT / "submission/build_competition_staging.py"
VERIFIER = EXPERIMENT_ROOT / "submission/verify_competition_package.py"
SPEC = EXPERIMENT_ROOT / "submission/competition_staging_spec.json"


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *(str(arg) for arg in args)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_verifier_module():
    spec = importlib.util.spec_from_file_location("_competition_package_verifier_test", VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verifier_self_scan_has_no_literal_path_false_positive(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    assert verifier.scan_content(VERIFIER) == []
    probe = tmp_path / "absolute-path-probe.txt"
    probe.write_text("/" + "Users" + "/alice/project\n/" + "home" + "/bob/project\n", encoding="utf-8")
    issues = verifier.scan_content(probe)
    assert "file: forbidden content pattern mac_home" in issues
    assert "file: forbidden content pattern linux_home" in issues
    for rel in verifier.LOCKED_LOCAL_PATH_FILES:
        source = REPO_ROOT / rel
        assert verifier.scan_content(source, rel) == []
        assert "file: forbidden content pattern mac_home" in verifier.scan_content(source)


def test_staging_spec_is_explicit_and_excludes_archives_except_anchored_raw() -> None:
    payload = json.loads(SPEC.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "xa.competition-staging-spec.v1"
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "misc/archive" not in serialized
    assert payload["evidence_snapshot_files"] == [
        "run.json", "summary.json", "verifier.json", "artifacts.manifest.json",
        "checksums.sha256",
    ]
    anchored = payload["externally_anchored_bundles"]
    assert anchored["anchor"] == {
        "path": "experiments/configs/xa202609/e5_v11_portable_fresh_validation_v2.anchor.json",
        "sha256": "036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686",
    }
    assert {row["id"] for row in anchored["bundles"]} == {
        "E5_V11_PREFLIGHT_SOURCE_LINK", "E5_V11_SEAL_SOURCE_LINK",
        "E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR",
        "E5_NEGATIVE_V1_PREDECESSOR", "E5_PORTABLE_V2_PREDECESSOR",
        "E5_FRESH_V1_PREDECESSOR", "E5_PORTABLE_V3", "E5_FRESH_V2",
    }
    assert {
        row["id"] for row in anchored["bundles"] if row.get("role") == "provenance_predecessor_only"
    } == {"E5_NEGATIVE_V1_PREDECESSOR", "E5_PORTABLE_V2_PREDECESSOR", "E5_FRESH_V1_PREDECESSOR"}
    assert next(
        row["role"] for row in anchored["bundles"]
        if row["id"] == "E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR"
    ) == "scientific_source_predecessor_only_unaccepted_endpoint"
    for row in anchored["bundles"]:
        assert set(row["files"]) == {
            "artifacts.manifest.json", "checksums.sha256", "events.jsonl", "raw.jsonl",
            "run.json", "stderr.log", "stdout.log", "summary.json", "verifier.json",
        }
    required_files = set(payload["required_files"])
    assert {
        "experiments/demo/output/checksums.sha256",
        "experiments/demo/output/demo_manifest.json",
        "experiments/demo/output/execution.log",
        "experiments/demo/output/input.json",
        "experiments/demo/output/report.json",
        "experiments/demo/output/report.md",
        "experiments/demo/output/verification.json",
    } <= required_files
    assert {
        "experiments/demo/offline_fallback/checksums.sha256",
        "experiments/demo/offline_fallback/execution.log",
        "experiments/demo/offline_fallback/fallback_manifest.json",
        "experiments/demo/offline_fallback/input.json",
        "experiments/demo/offline_fallback/logical.qasm",
        "experiments/demo/offline_fallback/native.qasm",
        "experiments/demo/offline_fallback/report.json",
        "experiments/demo/offline_fallback/report.md",
        "experiments/demo/offline_fallback/verification.json",
    } <= required_files
    e6_bundle = (
        "experiments/results/xa202609/"
        "20260812-e6-q4ai-causal-v1-full-s20260912"
    )
    assert {
        "docs/competition/evidence/E6_Q4AI_CAUSAL_NEGATIVE_EVIDENCE.md",
        "experiments/configs/xa202609/e6_q4ai_causal_v1.json",
        "experiments/scripts/run_e6_q4ai_causal_v1.py",
        "experiments/scripts/verify_e6_replay_training_bundle_v1.py",
        *(f"{e6_bundle}/{name}" for name in (
            "config.json", "results.json", "raw.jsonl",
            "heldout_evaluation.json", "checksums.sha256",
        )),
    } <= required_files
    e6_d2_bundle = (
        "experiments/results/xa202609/"
        "20260813-e6-d2-resource-gain-teacher-v1-full-s20261011"
    )
    assert {
        "docs/competition/evidence/E6_D2_RESOURCE_GAIN_MECHANISM_EVIDENCE.md",
        "experiments/configs/xa202609/e6_d2_resource_gain_teacher_v1.json",
        "experiments/scripts/run_e6_d2_resource_gain_teacher_v1.py",
        *(f"{e6_d2_bundle}/{name}" for name in (
            "config.json", "results.json", "raw.jsonl",
            "diagnostics.json", "checksums.sha256",
        )),
    } <= required_files
    assert payload["final_authorization_documents"] == [
        "LICENSE",
        "IP_STATEMENT.md",
        "CODE_PROVENANCE.json",
        "THIRD_PARTY_NOTICES.md",
        "REGISTRATION_APPROVAL.pdf",
        "SUBMISSION_AUTHORIZATION.json",
        "SBOM.cdx.json",
    ]
    assert payload["final_model_release"]["machine_model_card"] == (
        "experiments/results/xa202609/"
        "20260812-foundation-v4-provenance-formal-s20260904/model_card.json"
    )
    assert payload["final_model_release"]["expected_checkpoint_sha256"] == (
        "5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7"
    )
    assert payload["final_model_release"]["evidence_files"]
    assert payload["report_release"] == {
        "path": "docs/papers/resource_nmcts/chinese/resource_nmcts_competition_current.pdf",
        "sha256": "f6826f61595e5a7de9b311a13e6027b061c99323fbbdc626196986a7c3cbda95",
        "page_count": 39,
    }
    assert payload["presentation_release"] == {
        "path": "docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx",
        "sha256": "fa7b319fa620a37a62302be24c04ed70fb432be91d7d0fafbd8cf2e08377412f",
    }
    assert payload["presentation_candidates"] == [payload["presentation_release"]["path"]]
    assert "experiments/e6/*.py" in payload["required_globs"]
    assert {
        "E4V2_CAL", "E4V2_TEST", "E5_V1_PREFLIGHT", "E5_V1_SEAL",
        "E5_V11_PREFLIGHT", "E5_V11_SEAL", "E5_V11_UNACCEPTED_EVAL",
        "E5_V11_FAILED_ATTEMPT", "E5_V11_NEGATIVE_AUDIT",
    } <= {row["id"] for row in payload["evidence_bundles"]}


def test_final_build_fails_closed_without_authorization(tmp_path: Path) -> None:
    output = tmp_path / "XA-202609-final"
    result = run(BUILDER, "--output-dir", output)
    assert result.returncode == 2
    assert "final staging refused by authorization gate" in result.stderr
    assert "legacy_v3_demo_model_is_development_candidate" in result.stderr
    assert "machine_model_card_is_provenance_candidate_not_final_frozen" in result.stderr
    assert "final_external_performance_evidence_missing" in result.stderr
    assert "training_command_unverified" not in result.stderr
    assert "dataset_split_manifest_unverified" not in result.stderr
    assert "training_source_sha_provenance_unverified" not in result.stderr
    assert not output.exists()


def test_incomplete_build_cannot_be_named_as_final(tmp_path: Path) -> None:
    misleading_output = tmp_path / "XA-202609-internal-audit-draft-final"
    result = run(
        BUILDER,
        "--allow-incomplete",
        "--omit-presentation",
        "--output-dir",
        misleading_output,
    )
    assert result.returncode == 2
    assert "must not be named as final" in result.stderr
    assert not misleading_output.exists()
    draft_output = tmp_path / "XA-202609-internal-audit-draft"
    result = run(
        BUILDER,
        "--allow-incomplete",
        "--omit-presentation",
        "--output-dir",
        draft_output,
        "--archive",
        tmp_path / "XA-202609_final.tar.gz",
    )
    assert result.returncode == 2
    assert "fixed internal-draft name" in result.stderr
    assert not draft_output.exists()


def test_placeholder_authorization_cannot_open_final_gate(tmp_path: Path) -> None:
    auth = tmp_path / "auth"
    auth.mkdir()
    (auth / "LICENSE").write_text("PLACEHOLDER license text\n", encoding="utf-8")
    (auth / "IP_STATEMENT.md").write_text(
        "IP statement approved by an authorized reviewer.\n", encoding="utf-8"
    )
    (auth / "CODE_PROVENANCE.json").write_text(
        '{"status": "approved"}\n', encoding="utf-8"
    )
    (auth / "THIRD_PARTY_NOTICES.md").write_text(
        "Third-party notices reviewed by an authorized reviewer.\n", encoding="utf-8"
    )
    (auth / "REGISTRATION_APPROVAL.pdf").write_bytes(b"%PDF-1.4\nsynthetic-test-only")
    (auth / "SBOM.cdx.json").write_text(
        json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6"}) + "\n",
        encoding="utf-8",
    )
    (auth / "SUBMISSION_AUTHORIZATION.json").write_text(
        json.dumps(
            {
                "schema_version": "xa.submission-authorization.v1",
                "competition_id": "XA-202609",
                "status": "approved",
                "archive_name": "XA-202609_team.tar.gz",
                "attested_by": "Test Attestor",
                "attested_role": "Test Role",
                "attested_at_utc": "2026-08-12T00:00:00Z",
                "submitting_university": "Test University",
                "authorized_submitter": "Test Submitter",
                "declarations": {
                    "registration_approved": True,
                    "submitting_university_confirmed": True,
                    "authorized_submitter_confirmed": True,
                    "project_license_approved": True,
                    "ip_statement_approved": True,
                    "code_provenance_approved": True,
                    "sshr_lib_prehistory_confirmed": True,
                    "redistribution_authorized": True,
                    "third_party_notices_approved": True,
                    "model_data_redistribution_authorized": True,
                    "transitive_sbom_reviewed": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "XA-202609-final"
    result = run(BUILDER, "--authorization-dir", auth, "--output-dir", output)
    assert result.returncode == 2
    assert "LICENSE: contains placeholder markers" in result.stderr
    assert not output.exists()


@pytest.fixture(scope="module")
def draft_package(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    base = tmp_path_factory.mktemp("xa202609_submission")
    staging = base / "XA-202609-internal-audit-draft"
    archive = base / "XA-202609_INTERNAL_AUDIT_DRAFT.tar.gz"
    built = run(
        BUILDER,
        "--allow-incomplete",
        "--omit-presentation",
        "--output-dir",
        staging,
        "--archive",
        archive,
    )
    assert built.returncode == 0, built.stderr
    return staging, archive


def test_internal_draft_has_closed_manifest_and_verifies_only_with_override(
    draft_package: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging, archive = draft_package
    manifest = json.loads((staging / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "internal_audit_draft"
    assert manifest["distributable"] is False
    assert (staging / "INCOMPLETE_INTERNAL_AUDIT_DRAFT.md").is_file()
    assert not (staging / "authorization").exists()
    technical = json.loads(
        (staging / "TECHNICAL_RELEASE_STATUS.json").read_text(encoding="utf-8")
    )
    assert technical["ready_for_final"] is False
    assert technical["candidate_status"] == "provenance_closed_development_candidate"
    assert technical["training_provenance"]["closed"] is True
    assert technical["training_provenance"]["performance_evidence"] is False
    external = technical["externally_anchored_evidence"]
    assert external["status"] == "closed_software_validation_only"
    assert external["anchor"]["sha256"] == (
        "036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686"
    )
    assert external["fresh_validation"]["full_pytest_passed"] == 383
    assert external["predecessor_role"] == "provenance_predecessor_only_not_performance_or_recommendation"
    assert external["scientific_source_predecessor_role"] == (
        "scientific_source_predecessor_only_unaccepted_endpoint"
    )
    assert external["scientific_source_link_roles"] == [
        "scientific_source_linked_preflight_only", "scientific_source_linked_seal_only",
    ]
    assert external["locked_local_path_exceptions"]["count"] == 2
    assert manifest["externally_anchored_evidence"] == external
    assert technical["legacy_demo_model_card"]["status"] == "development_candidate"
    assert "legacy_v3_demo_model_is_development_candidate" in technical["blockers"]
    assert "machine_model_card_is_provenance_candidate_not_final_frozen" in technical["blockers"]
    assert "final_external_performance_evidence_missing" in technical["blockers"]
    assert (
        "repository_not_clean_frozen_commit" in technical["blockers"]
    ) is technical["source"]["repository_dirty"]
    assert manifest["technical_release"] == technical
    package_readme = (staging / "README_PACKAGE.md").read_text(encoding="utf-8")
    assert "Formal v4 closes training provenance only" in package_readme
    assert "E5 has no accepted endpoint" in package_readme
    assert not any("misc/archive" in path.as_posix() for path in staging.rglob("*"))
    included_raw = {
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file() and path.name in {"raw.jsonl", "events.jsonl"}
    }
    anchored_run_ids = {
        "20260812-e5-v11-preflight-external-crypto-v1-s840000",
        "20260812-e5-v11-seal-external-crypto-v1-s840000",
        "20260812-e5-v11-ascon-primary-present-secondary-v1-s940000",
        "20260812-e5-v11-negative-audit-v1-s950000",
        "20260812-e5-v11-portable-negative-audit-v2-s950000",
        "20260812-e5-v11-portable-fresh-validation-v1-s960000",
        "20260812-e5-v11-portable-negative-audit-v3-s950000",
        "20260812-e5-v11-portable-fresh-validation-v2-s970000",
    }
    expected_raw = {
        f"experiments/results/xa202609/{run_id}/{name}"
        for run_id in anchored_run_ids
        for name in ("raw.jsonl", "events.jsonl")
    }
    expected_raw.add(
        "experiments/results/xa202609/"
        "20260812-e6-q4ai-causal-v1-full-s20260912/raw.jsonl"
    )
    expected_raw.add(
        "experiments/results/xa202609/"
        "20260813-e6-d2-resource-gain-teacher-v1-full-s20261011/raw.jsonl"
    )
    assert included_raw == expected_raw
    for rel in (
        "experiments/demo/output/checksums.sha256",
        "experiments/demo/output/demo_manifest.json",
        "experiments/demo/output/execution.log",
        "experiments/demo/offline_fallback/checksums.sha256",
        "experiments/demo/offline_fallback/execution.log",
        "experiments/demo/offline_fallback/fallback_manifest.json",
        "experiments/demo/offline_fallback/logical.qasm",
        "experiments/demo/offline_fallback/native.qasm",
    ):
        assert (staging / rel).is_file(), rel
    # Full-suite collection imports the E5 verifier in the live checkout and
    # leaves this process-global variable behind.  Package verification must
    # rebind it to the copied package rather than inherit the collector state.
    monkeypatch.setenv("XA_E5_PROJECT_ROOT", str(REPO_ROOT / "poisoned-live-root"))
    accepted = run(VERIFIER, "--allow-incomplete", staging)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    accepted_payload = json.loads(accepted.stdout)
    assert accepted_payload["ok"] is True
    assert accepted_payload["distributable"] is False
    assert not any(path.name == "__pycache__" for path in staging.rglob("*"))
    rejected = run(VERIFIER, staging)
    assert rejected.returncode == 2
    assert "authorization gate" in rejected.stdout
    archive_check = run(VERIFIER, "--allow-incomplete", archive)
    assert archive_check.returncode == 0, archive_check.stdout + archive_check.stderr


def test_compact_evidence_is_sanitized_and_inventories_omissions(
    draft_package: tuple[Path, Path],
) -> None:
    staging, _ = draft_package
    for bundle_id in (
        "E2", "E3_CAL", "E3_TEST", "E4", "E4V2_CAL", "E4V2_TEST",
        "E5_V1_PREFLIGHT", "E5_V1_SEAL", "E5_V11_PREFLIGHT", "E5_V11_SEAL",
        "E5_V11_UNACCEPTED_EVAL", "E5_V11_FAILED_ATTEMPT", "E5_V11_NEGATIVE_AUDIT",
    ):
        snapshot = staging / "evidence_snapshots" / bundle_id
        payload = json.loads((snapshot / "SNAPSHOT_MANIFEST.json").read_text(encoding="utf-8"))
        assert payload["source_inventory"]
        assert payload["omitted_large_or_log_artifacts"]
        assert not (snapshot / "raw.jsonl").exists()
        assert not (snapshot / "events.jsonl").exists()
        for path in snapshot.iterdir():
            if path.is_file():
                assert b"/" + b"Users" + b"/" not in path.read_bytes()
    external = json.loads(
        (staging / "MANIFEST.json").read_text(encoding="utf-8")
    )["externally_anchored_evidence"]
    assert {row["id"] for row in external["bundles"]} == {
        "E5_V11_PREFLIGHT_SOURCE_LINK", "E5_V11_SEAL_SOURCE_LINK",
        "E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR",
        "E5_NEGATIVE_V1_PREDECESSOR", "E5_PORTABLE_V2_PREDECESSOR",
        "E5_FRESH_V1_PREDECESSOR", "E5_PORTABLE_V3", "E5_FRESH_V2",
    }
    for row in external["bundles"]:
        directory = staging / row["path"]
        assert {path.name for path in directory.iterdir() if path.is_file()} == {
            "artifacts.manifest.json", "checksums.sha256", "events.jsonl", "raw.jsonl",
            "run.json", "stderr.log", "stdout.log", "summary.json", "verifier.json",
        }


def test_claim_boundaries_are_explicit_and_not_promoted(
    draft_package: tuple[Path, Path],
) -> None:
    staging, _ = draft_package
    status = json.loads((staging / "TECHNICAL_RELEASE_STATUS.json").read_text(encoding="utf-8"))
    claims = status["research_claims"]
    assert claims["formal_v4"] == {
        "provenance_closed": True,
        "performance_evidence": False,
        "final_model": False,
    }
    assert claims["e4_v2"]["generalization_claim"] is False
    assert claims["e4_v2"]["improvement_supported"] is False
    assert claims["e4_v2"]["bootstrap_95_ci"] == [-2059.0625, 589.9375]
    assert claims["e5"]["protocol_acceptance"] is False
    assert claims["e5"]["accepted_endpoint"] is False
    assert claims["e5"]["v1_first_release_trial_rows"] == 0
    assert claims["e5"]["v11_matrix_rows"] == 90
    assert claims["e5"]["ascon_schedulable_groups"] == 0
    assert claims["e5"]["portable_v3_snapshot_sha256"] == (
        "4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea"
    )
    assert claims["e5"]["fresh_v2_snapshot_sha256"] == (
        "dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23"
    )
    assert claims["e5"]["fresh_full_pytest_passed"] == 383
    assert claims["e5"]["scientific_evidence"] is False
    assert claims["e5"]["hardware_execution"] is False
    assert claims["e6"]["status"] == "development_causal_negative_result_verified"
    assert claims["e6"]["development_result_bundle_present"] is True
    assert claims["e6"]["formal_result_bundle_present"] is False
    assert claims["e6"]["bundle_snapshot_sha256"] == (
        "18b758ac3e432a5d4e9f0ba1f8be7e17bd1b848b6212234eea9d2e842d4cc76a"
    )
    assert claims["e6"]["training_or_finetuning_performed"] is True
    assert claims["e6"]["train_case_count"] == 64
    assert claims["e6"]["heldout_case_count"] == 32
    assert claims["e6"]["mean_effect"] == 0.09497779579431545
    assert claims["e6"]["bootstrap_95_ci"] == [
        0.06963836434546339,
        0.12376730228100935,
    ]
    assert claims["e6"]["signflip_p"] == 0.00000999990000099999
    assert (claims["e6"]["wins"], claims["e6"]["ties"], claims["e6"]["losses"]) == (0, 3, 29)
    assert claims["e6"]["claim_supported"] is False
    assert claims["e6"]["formal_evaluation"] is False
    assert claims["e6"]["performance_evidence"] is False
    assert claims["e6_d2"] == {
        "status": "development_resource_gain_mechanism_repaired",
        "bundle_path": (
            "experiments/results/xa202609/"
            "20260813-e6-d2-resource-gain-teacher-v1-full-s20261011"
        ),
        "bundle_snapshot_sha256": (
            "b16715196ff1e456184eaae6654f73f28c12454c5190d288384739f8bc1576c1"
        ),
        "run_id": "20260813-e6-d2-resource-gain-teacher-v1-full-s20261011",
        "source_commit": "51288b1e2aab3c420ee93a7afd85bbc9c22b2243",
        "source_dirty": False,
        "train_case_count": 64,
        "structured_case_count": 32,
        "ood_case_count": 32,
        "split_overlap_counts": {
            "ood_vs_structured_validation": {
                "orbit_cluster_sha256": 0,
                "vector_sha256": 0,
                "whole_vector_cluster_sha256": 0,
            },
            "ood_vs_train": {
                "orbit_cluster_sha256": 0,
                "vector_sha256": 0,
                "whole_vector_cluster_sha256": 0,
            },
            "train_vs_structured_validation": {
                "orbit_cluster_sha256": 0,
                "vector_sha256": 0,
                "whole_vector_cluster_sha256": 0,
            },
        },
        "primary_comparison": (
            "gain_weighted_qaoa_vw0_minus_gain_weighted_permuted_vw0"
        ),
        "structured_mean_effect": -0.16887894417475724,
        "structured_wins": 32,
        "structured_ties": 0,
        "structured_losses": 0,
        "ood_mean_effect": -0.15351147345563865,
        "ood_wins": 31,
        "ood_ties": 1,
        "ood_losses": 0,
        "strongest_greedy_improvement_supported": False,
        "development_mechanism_repair_only": True,
        "formal_evaluation": False,
        "performance_evidence": False,
        "generalization_claim": False,
        "hardware_execution": False,
        "quantum_advantage_claimed": False,
    }
    e6_config = json.loads(
        (staging / "experiments/configs/xa202609/e6_multioutput_shared_mvp_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert e6_config["schema_version"] == "xa.e6-multioutput-shared-mvp-config.v1.1"
    assert e6_config["ai_quantum_boundary"]["shared_model_architecture_implemented"] is True
    assert e6_config["ai_quantum_boundary"]["learned_multioutput_head_connected"] is False
    assert e6_config["ai_quantum_boundary"]["qaoa_trajectory_replay_update_connected"] is False
    assert e6_config["ai_quantum_boundary"]["training_or_finetuning_performed"] is False
    assert e6_config["scope"]["formal_result_bundle_present"] is False
    assert e6_config["scope"]["performance_evidence"] is False
    e6_bundle = staging / claims["e6"]["bundle_path"]
    assert {path.name for path in e6_bundle.iterdir()} == {
        "config.json", "results.json", "raw.jsonl",
        "heldout_evaluation.json", "checksums.sha256",
    }
    e6_results = json.loads((e6_bundle / "results.json").read_text(encoding="utf-8"))
    e6_heldout = json.loads(
        (e6_bundle / "heldout_evaluation.json").read_text(encoding="utf-8")
    )
    assert e6_results["schema_version"] == "xa.e6-replay-training-results.v1-development"
    assert {report["sample_count"] for report in e6_results["training_report_by_arm"].values()} == {64}
    assert e6_heldout["formal_evaluation"] is False
    assert e6_heldout["performance_evidence"] is False
    assert e6_heldout["statistics"]["claim_gate"]["claim_supported"] is False
    assert len(e6_heldout["case_rows"]) == 32
    e6_d2_bundle = staging / claims["e6_d2"]["bundle_path"]
    assert {path.name for path in e6_d2_bundle.iterdir()} == {
        "config.json", "results.json", "raw.jsonl",
        "diagnostics.json", "checksums.sha256",
    }
    e6_d2_results = json.loads(
        (e6_d2_bundle / "results.json").read_text(encoding="utf-8")
    )
    e6_d2_diagnostics = json.loads(
        (e6_d2_bundle / "diagnostics.json").read_text(encoding="utf-8")
    )
    assert e6_d2_results["raw_row_count"] == 800
    assert e6_d2_results["source"]["dirty"] is False
    assert e6_d2_diagnostics["formal_evaluation"] is False
    assert e6_d2_diagnostics["performance_evidence"] is False
    assert (
        e6_d2_diagnostics["structured_primary_pair_contrasts"]
        ["expanded_cap256"]["difference"]["score_ratio_y"]
        == -0.16887894417475724
    )
    assert (
        e6_d2_diagnostics["ood_primary_pair_contrast"]["difference"]
        ["score_ratio_y"]
        == -0.15351147345563865
    )
    assert (staging / "experiments/e6/shared_oracle.py").is_file()
    assert (staging / "experiments/e6/shared_scheduler.py").is_file()
    assert (staging / "experiments/tests/test_e6_shared_semantics.py").is_file()
    assert (staging / "experiments/tests/test_e6_shared_scheduler.py").is_file()


def test_manifest_or_payload_tampering_is_detected(
    draft_package: tuple[Path, Path], tmp_path: Path
) -> None:
    staging, _ = draft_package
    tampered = tmp_path / "XA-202609-internal-audit-draft-tampered"
    shutil.copytree(staging, tampered)
    target = tampered / "experiments/demo/output/report.md"
    target.write_text(target.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")
    result = run(VERIFIER, "--allow-incomplete", tampered)
    assert result.returncode == 2
    assert "checksum mismatch" in result.stdout or "manifest size/hash mismatch" in result.stdout


def test_archive_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "malicious.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        data = b"escape"
        member = tarfile.TarInfo("XA-202609_submission/../../escape.txt")
        member.size = len(data)
        handle.addfile(member, io.BytesIO(data))
    result = run(VERIFIER, archive)
    assert result.returncode == 2
    assert "unsafe archive member path" in result.stdout
    assert not (tmp_path / "escape.txt").exists()
