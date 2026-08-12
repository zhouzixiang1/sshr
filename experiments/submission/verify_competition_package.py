#!/usr/bin/env python3
"""Independently verify an extracted or archived XA-202609 submission package.

The verifier does not import the builder or trust an allowlist shipped in the
package.  It checks a hard-coded narrow path policy, safe archive structure,
manifest/checksum closure, local-path and high-signal secret patterns, compact
evidence snapshots, SBOM/provenance consistency, and authorization state.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


AUTH_DECLARATIONS = (
    "registration_approved",
    "submitting_university_confirmed",
    "authorized_submitter_confirmed",
    "project_license_approved",
    "ip_statement_approved",
    "code_provenance_approved",
    "sshr_lib_prehistory_confirmed",
    "redistribution_authorized",
    "third_party_notices_approved",
    "model_data_redistribution_authorized",
    "transitive_sbom_reviewed",
)
TOP_FILES = {
    "AUTHORIZATION_STATUS.json",
    "CHECKSUMS.sha256",
    "INCOMPLETE_INTERNAL_AUDIT_DRAFT.md",
    "MANIFEST.json",
    "PROVENANCE.json",
    "README_PACKAGE.md",
    "SBOM-LITE.json",
    "TECHNICAL_RELEASE_STATUS.json",
}
AUTH_FILES = {
    "authorization/CODE_PROVENANCE.json",
    "authorization/IP_STATEMENT.md",
    "authorization/LICENSE",
    "authorization/REGISTRATION_APPROVAL.pdf",
    "authorization/SBOM.cdx.json",
    "authorization/SUBMISSION_AUTHORIZATION.json",
    "authorization/THIRD_PARTY_NOTICES.md",
}
EXACT_REPOSITORY_FILES = {
    "docs/papers/resource_nmcts/chinese/README.md",
    "docs/papers/resource_nmcts/chinese/main.tex",
    "docs/papers/resource_nmcts/chinese/algorithms/resource_nmcts_budgeted_search_zh.tex",
    "docs/papers/resource_nmcts/chinese/resource_nmcts_competition_current.pdf",
    "docs/papers/resource_nmcts/english/tables/worked_example_search.tex",
    "docs/papers/resource_nmcts/english/tables/worked_example_resources.tex",
    "docs/papers/resource_nmcts/english/tables/cirkit_aig_probe.tex",
    "docs/papers/resource_nmcts/english/tables/cirkit_aig_highdim_probe.tex",
    "docs/papers/resource_nmcts/english/tables/revkit_cli_multiflow_traditional.tex",
    "docs/papers/resource_nmcts/english/tables/search_contribution_decomposition.tex",
    "docs/papers/resource_nmcts/english/tables/phase_parity_affine.tex",
    "docs/papers/resource_nmcts/english/tables/phase_affine_budget_wide128_vs_32.tex",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig1_pipeline.pdf",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig2_traditional_resources.pdf",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig3_baseline_comparisons.pdf",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig4_phase_affine.pdf",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig5_validation.png",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig6_sparse_gate_sensitivity.pdf",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig7_learned_control_summary.pdf",
    "docs/papers/resource_nmcts/english/figures/submission_v36/fig8_worked_example.pdf",
    "docs/competition/evidence/README.md",
    "docs/competition/evidence/CLEAN_INSTALL_EVIDENCE.md",
    "docs/competition/evidence/E2_QAOA_SCHEDULER_EVIDENCE.md",
    "docs/competition/evidence/E3_NATIVE_FEEDBACK_EVIDENCE.md",
    "docs/competition/evidence/E4_AES_BIDIRECTIONAL_EVIDENCE.md",
    "docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx",
    "experiments/models/boolean_oracle_fm_v3.pt",
    "experiments/models/MODEL_CARD_boolean_oracle_fm_v3.md",
    "experiments/environment/environment.yml",
    "experiments/environment/requirements/README.md",
    "experiments/environment/requirements/core.txt",
    "experiments/environment/requirements/dev.txt",
    "experiments/environment/requirements/optional-sshr-gurobi.txt",
    "experiments/environment/requirements/quantum.txt",
    "experiments/environment/requirements/research.txt",
    "experiments/environment/requirements/server.txt",
    "experiments/configs/xa202609/README.md",
    "experiments/configs/xa202609/e2_qaoa_scheduler_v1.json",
    "experiments/configs/xa202609/e3_native_feedback_v1.json",
    "experiments/configs/xa202609/e4_v2_execution_aware_v1.json",
    "experiments/configs/xa202609/e4_v2_execution_aware_v1.protocol.lock.json",
    "experiments/tests/fixtures/e4_execution_aware_v2.superseded-test-only.json",
    "experiments/demo/README.md",
    "experiments/scripts/demo_competition.py",
    "experiments/scripts/verify_demo_output.py",
    "experiments/scripts/demo_offline_fallback.py",
    "experiments/scripts/verify_offline_fallback.py",
    "experiments/scripts/verify_clean_install.py",
    "experiments/scripts/train_expert_iteration.py",
    "experiments/scripts/run_qaoa_scheduler_pilot.py",
    "experiments/scripts/run_hardware_feedback_eval.py",
    "experiments/scripts/verify_hardware_feedback_bundle.py",
    "experiments/scripts/run_aes_bidirectional_pilot.py",
    "experiments/scripts/verify_aes_bidirectional_bundle.py",
    "experiments/submission/verify_competition_package.py",
}
FORMAL_V4_PREFIX = (
    "experiments/results/xa202609/"
    "20260812-foundation-v4-provenance-formal-s20260904"
)
FORMAL_V4_BASENAMES = {
    "checkpoint.pt", "command.json", "config_snapshot.json", "dataset_manifest.json",
    "model_card.json", "resource_estimate.json", "self_checks.json", "source_manifest.json",
    "training_log.jsonl", "training_summary.json", "artifacts.manifest.json",
    "checksums.sha256",
}
E6_RESULT_PREFIX = (
    "experiments/results/xa202609/"
    "20260812-e6-q4ai-causal-v1-full-s20260912"
)
E6_RESULT_FILE_SHA256 = {
    "config.json": "735c78cdc6a4d0c1ebd5c808bafba0471082ccd7b8e2f3b3f8d17653ebc2b5aa",
    "results.json": "a4ab20dbf8892355d6dc96c14817504da5117428fe97af1c75bcb04ee3313d1f",
    "raw.jsonl": "d0f64a9140b8e42a4eb242155b0ec58555eccbf2ebe666bc622507939efc69c3",
    "heldout_evaluation.json": "f0684623495424515dd17391bff56cbfcfcaba21efe19771cf74b01e771c909b",
    "checksums.sha256": "b52bf90bb97c829de5285c1e407172411d46537c5b4757d63e4e81d64a6d2f8f",
}
E6_RESULT_SNAPSHOT_SHA256 = (
    "18b758ac3e432a5d4e9f0ba1f8be7e17bd1b848b6212234eea9d2e842d4cc76a"
)
EXACT_REPOSITORY_FILES |= {
    "experiments/configs/xa202609/e5_external_crypto_holdout_v1.json",
    "experiments/configs/xa202609/e5_external_crypto_holdout_v1.protocol.lock.json",
    "experiments/configs/xa202609/e5_v11_portable_fresh_validation_v2.anchor.json",
    "experiments/configs/xa202609/e6_multioutput_shared_mvp_v1.json",
    "experiments/configs/xa202609/e6_q4ai_causal_v1.json",
    "experiments/configs/xa202609/foundation_v4_provenance.json",
    "experiments/src/hardware/README.md",
    "experiments/scripts/run_e4_v2_execution_aware.py",
    "experiments/scripts/verify_e4_v2_bundle.py",
    "experiments/scripts/run_e5_external_crypto_holdout.py",
    "experiments/scripts/verify_e5_external_crypto_holdout_bundle.py",
    "experiments/scripts/run_e6_q4ai_causal_v1.py",
    "experiments/scripts/verify_e6_replay_training_bundle_v1.py",
    "experiments/scripts/train_foundation_v4.py",
    "experiments/scripts/verify_foundation_v4_bundle.py",
    "experiments/scripts/_pilot_artifacts.py",
    "experiments/analysis/audit_e5_v11_negative_bundle.py",
    "experiments/analysis/verify_e5_v11_negative_audit_bundle.py",
    "experiments/analysis/build_e5_v11_fresh_validation_v2.py",
    "experiments/analysis/verify_e5_v11_fresh_validation_v2.py",
    "experiments/tests/test_e5_v11_negative_audit.py",
    "experiments/tests/test_e5_v11_fresh_validation_v2.py",
    "docs/competition/evidence/E6_Q4AI_CAUSAL_NEGATIVE_EVIDENCE.md",
    *(f"{FORMAL_V4_PREFIX}/{name}" for name in FORMAL_V4_BASENAMES),
    *(f"{E6_RESULT_PREFIX}/{name}" for name in E6_RESULT_FILE_SHA256),
}
EXTERNAL_ANCHOR_PATH = "experiments/configs/xa202609/e5_v11_portable_fresh_validation_v2.anchor.json"
EXTERNAL_ANCHOR_SHA256 = "036dc0cad2cbe6eabac70793e3be1de44fd8f1882753e595560870bc3eddd686"
EXTERNAL_BUNDLE_BASENAMES = {
    "artifacts.manifest.json", "checksums.sha256", "events.jsonl", "raw.jsonl",
    "run.json", "stderr.log", "stdout.log", "summary.json", "verifier.json",
}
EXTERNAL_BUNDLES = {
    "E5_V11_PREFLIGHT_SOURCE_LINK": {
        "role": "scientific_source_linked_preflight_only",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-preflight-external-crypto-v1-s840000"
        ),
        "snapshot_sha256": "467176bc8a7f592eca48172f028a5afbc183d6a5f7d41809a0aee53eb6da99d8",
    },
    "E5_V11_SEAL_SOURCE_LINK": {
        "role": "scientific_source_linked_seal_only",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-seal-external-crypto-v1-s840000"
        ),
        "snapshot_sha256": "6489be0c7bc808d2962082158799939cfa339187bf34917af8f7e719ff3f1d4b",
    },
    "E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR": {
        "role": "scientific_source_predecessor_only_unaccepted_endpoint",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-ascon-primary-present-secondary-v1-s940000"
        ),
        "snapshot_sha256": "922838ff8dc0d47d6a13a390b8b4e2c1a9fde2516f7c84abfebca5163cbc4313",
    },
    "E5_NEGATIVE_V1_PREDECESSOR": {
        "role": "provenance_predecessor_only",
        "anchor_key": "predecessor_snapshots",
        "anchor_run_id": "20260812-e5-v11-negative-audit-v1-s950000",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-negative-audit-v1-s950000"
        ),
        "snapshot_sha256": "eec9d17bd7d17e3d2219781d0f010d8bca553e530d23f2ea7efcb5546b0ea75c",
    },
    "E5_PORTABLE_V2_PREDECESSOR": {
        "role": "provenance_predecessor_only",
        "anchor_key": "predecessor_snapshots",
        "anchor_run_id": "20260812-e5-v11-portable-negative-audit-v2-s950000",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-portable-negative-audit-v2-s950000"
        ),
        "snapshot_sha256": "f57a5e2fe0605f413a1187e1de69b2a51a5e312f5205108a6532782dfa791974",
    },
    "E5_FRESH_V1_PREDECESSOR": {
        "role": "provenance_predecessor_only",
        "anchor_key": "predecessor_snapshots",
        "anchor_run_id": "20260812-e5-v11-portable-fresh-validation-v1-s960000",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-portable-fresh-validation-v1-s960000"
        ),
        "snapshot_sha256": "fc641602e29c1f8416dda6007d3ff64ce36d4b003b7e699ec0a5e202467ef4bc",
    },
    "E5_PORTABLE_V3": {
        "role": "current_negative_scientific_audit",
        "anchor_key": "scientific_v3_bundle",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-portable-negative-audit-v3-s950000"
        ),
        "snapshot_sha256": "4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea",
    },
    "E5_FRESH_V2": {
        "role": "current_fresh_software_validation",
        "anchor_key": "fresh_v2_bundle",
        "path": (
            "experiments/results/xa202609/"
            "20260812-e5-v11-portable-fresh-validation-v2-s970000"
        ),
        "snapshot_sha256": "dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23",
    },
}
EXACT_REPOSITORY_FILES |= {
    f"{bundle['path']}/{name}"
    for bundle in EXTERNAL_BUNDLES.values()
    for name in EXTERNAL_BUNDLE_BASENAMES
}
DEMO_BASENAMES = {
    "checksums.sha256", "demo_manifest.json", "execution.log", "input.json",
    "report.json", "report.md", "verification.json",
}
FALLBACK_BASENAMES = {
    "checksums.sha256", "execution.log", "fallback_manifest.json", "input.json",
    "logical.qasm", "native.qasm", "report.json", "report.md", "verification.json",
}
EVIDENCE_NAMES = {
    "CHECKSUMS.sha256", "SNAPSHOT_MANIFEST.json", "artifacts.manifest.json",
    "run.json", "source_bundle_checksums.sha256", "summary.json", "verifier.json",
}
EVIDENCE_SOURCES = {
    "E2": ("experiments/results/xa202609/20260810-e2-qaoa-scheduler-v1-s120000", "historical_evidence"),
    "E3_CAL": ("experiments/results/xa202609/20260811-e3-cal-native-feedback-v1-s310000", "historical_evidence"),
    "E3_TEST": ("experiments/results/xa202609/20260811-e3-test-native-feedback-v1-s410000", "historical_evidence"),
    "E4": ("experiments/results/xa202609/20260812-e4-aes-bidirectional-pilot-v1-s520000", "e4_aes_pilot"),
    "E4V2_CAL": ("experiments/results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-cal", "e4_v2_calibration_not_performance"),
    "E4V2_TEST": ("experiments/results/xa202609/20260812-e4-v2-frozen-replication-v1-s530000-test", "e4_v2_post_e4_replication_not_generalization"),
    "E5_V1_PREFLIGHT": ("experiments/results/xa202609/20260812-e5-preflight-external-crypto-v1-s840000", "e5_pre_endpoint_contract_only"),
    "E5_V1_SEAL": ("experiments/results/xa202609/20260812-e5-seal-external-crypto-v1-s840000", "e5_pre_endpoint_contract_only"),
    "E5_V11_PREFLIGHT": ("experiments/results/xa202609/20260812-e5-v11-preflight-external-crypto-v1-s840000", "e5_pre_endpoint_contract_only"),
    "E5_V11_SEAL": ("experiments/results/xa202609/20260812-e5-v11-seal-external-crypto-v1-s840000", "e5_pre_endpoint_contract_only"),
    "E5_V11_UNACCEPTED_EVAL": ("experiments/results/xa202609/20260812-e5-v11-ascon-primary-present-secondary-v1-s940000", "e5_unaccepted_endpoint"),
    "E5_V11_FAILED_ATTEMPT": ("experiments/results/xa202609/20260812-e5-v11-ascon-primary-present-secondary-v1-s940000-failed-attempt-a3eaff70252b", "e5_failed_attempt_not_completion"),
    "E5_V11_NEGATIVE_AUDIT": ("experiments/results/xa202609/20260812-e5-v11-negative-audit-v1-s950000", "e5_negative_audit_no_accepted_endpoint"),
}
EVIDENCE_IDS = set(EVIDENCE_SOURCES)
FORBIDDEN_SEGMENTS = {
    ".DS_Store", ".env", ".git", ".idea", ".pytest_cache", ".venv",
    "__pycache__", "misc", "node_modules",
}
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_BYTES = 250 * 1024 * 1024
PRESENTATION_PATH = "docs/competition/slides/XA-202609_双向智能Boolean_Oracle答辩稿.pptx"
PRESENTATION_SHA256 = "bf830dee8dd9adf5e9110cbf8b73f0ebbfbb3fe453c3aad03c057b031581d4e3"
MACHINE_MODEL_CARD_PATH = f"{FORMAL_V4_PREFIX}/model_card.json"
FINAL_CHECKPOINT_PATH = f"{FORMAL_V4_PREFIX}/checkpoint.pt"
REPORT_PATH = "docs/papers/resource_nmcts/chinese/resource_nmcts_competition_current.pdf"
REPORT_SHA256 = "fadd6965e39a390589086e1784e6e68984ce2121339dbace802775858d3fcfe3"
REPORT_PAGE_COUNT = 38
LOCKED_LOCAL_PATH_FILES = {
    (
        "experiments/results/xa202609/"
        "20260812-e5-v11-portable-fresh-validation-v1-s960000/raw.jsonl"
    ),
    (
        "experiments/results/xa202609/"
        "20260812-e5-v11-portable-fresh-validation-v2-s970000/raw.jsonl"
    ),
}
REQUIRED_CORE_PATHS = {
    "experiments/src/synthesizers.py",
    "experiments/src/nmcts_solver.py",
    "experiments/src/resource_model.py",
    "experiments/src/benchmarks/crypto_oracles.py",
    "experiments/src/contracts/artifacts.py",
    "experiments/src/contracts/experiment.py",
    "experiments/src/contracts/search.py",
    "experiments/src/contracts/synthesis.py",
    "experiments/src/foundation/adapter.py",
    "experiments/src/foundation/encoding.py",
    "experiments/src/foundation/equivariant.py",
    "experiments/src/foundation/heads.py",
    "experiments/src/hardware/noise.py",
    "experiments/src/hardware/qasm.py",
    "experiments/src/hardware/superconducting.py",
    "experiments/src/search/diversity_scheduler.py",
    "experiments/src/search/execution_aware_utility.py",
    "experiments/src/search/execution_feedback.py",
    "experiments/src/search/mcts_scheduler.py",
    "experiments/src/search/qaoa_scheduler.py",
    "experiments/src/search/value_net.py",
    "experiments/src/sshr_lib/sshr_i.py",
    "experiments/scripts/train_expert_iteration.py",
    "experiments/scripts/train_foundation_v4.py",
    "experiments/scripts/verify_foundation_v4_bundle.py",
    "experiments/scripts/_pilot_artifacts.py",
    "experiments/e6/__init__.py",
    "experiments/e6/shared_oracle.py",
    "experiments/e6/shared_scheduler.py",
    "experiments/configs/xa202609/e6_multioutput_shared_mvp_v1.json",
    "experiments/demo/output/checksums.sha256",
    "experiments/demo/output/demo_manifest.json",
    "experiments/demo/output/execution.log",
    "experiments/demo/output/input.json",
    "experiments/demo/output/report.json",
    "experiments/demo/output/report.md",
    "experiments/demo/output/verification.json",
    "experiments/demo/offline_fallback/checksums.sha256",
    "experiments/demo/offline_fallback/execution.log",
    "experiments/demo/offline_fallback/fallback_manifest.json",
    "experiments/demo/offline_fallback/input.json",
    "experiments/demo/offline_fallback/logical.qasm",
    "experiments/demo/offline_fallback/native.qasm",
    "experiments/demo/offline_fallback/report.json",
    "experiments/demo/offline_fallback/report.md",
    "experiments/demo/offline_fallback/verification.json",
    "experiments/tests/tests_smoke.py",
    "experiments/tests/test_competition_demo.py",
    "experiments/tests/test_qaoa_scheduler.py",
    "experiments/tests/test_superconducting_backend.py",
    "experiments/tests/test_aes_bidirectional_pilot.py",
    "experiments/tests/test_e4_v2_runner.py",
    "experiments/tests/test_e5_v11_negative_audit.py",
    "experiments/tests/test_foundation_v4_provenance.py",
    "experiments/tests/test_e6_shared_semantics.py",
    "experiments/tests/test_e6_shared_scheduler.py",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def e6_result_snapshot_sha256(path: Path) -> str | None:
    files = {item.name for item in path.iterdir() if item.is_file() and not item.is_symlink()}
    if files != set(E6_RESULT_FILE_SHA256):
        return None
    records = [
        {"name": name, "sha256": sha256_file(path / name), "bytes": (path / name).stat().st_size}
        for name in sorted(files)
    ]
    payload = (json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def safe_rel(value: str) -> PurePosixPath | None:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        return None
    if "\\" in value or any(part in FORBIDDEN_SEGMENTS for part in path.parts):
        return None
    return path


def path_allowed(rel: str, mode: str) -> bool:
    if rel in TOP_FILES:
        return rel != "INCOMPLETE_INTERNAL_AUDIT_DRAFT.md" or mode == "internal_audit_draft"
    if rel in AUTH_FILES:
        return mode == "final"
    if rel in EXACT_REPOSITORY_FILES:
        return True
    if rel == MACHINE_MODEL_CARD_PATH:
        return True
    path = PurePosixPath(rel)
    if len(path.parts) >= 3 and path.parts[:2] == ("experiments", "src") and path.suffix == ".py":
        return True
    if len(path.parts) == 3 and path.parts[:2] == ("experiments", "e6") and path.suffix == ".py":
        return True
    if len(path.parts) == 3 and path.parts[:2] == ("experiments", "tests") and path.suffix == ".py":
        return True
    if len(path.parts) == 4 and path.parts[:3] == ("experiments", "demo", "output"):
        return path.name in DEMO_BASENAMES
    if len(path.parts) == 4 and path.parts[:3] == ("experiments", "demo", "offline_fallback"):
        return path.name in FALLBACK_BASENAMES
    if len(path.parts) == 3 and path.parts[0] == "evidence_snapshots":
        return path.parts[1] in EVIDENCE_IDS and path.name in EVIDENCE_NAMES
    return False


def forbidden_byte_patterns() -> list[tuple[str, bytes]]:
    # Construct high-signal patterns without embedding a machine path in this
    # verifier source (the verifier verifies itself when shipped).
    return [
        ("mac_home", b"/" + b"Users" + b"/"),
        ("linux_home", b"/" + b"home" + b"/"),
        ("file_mac_home", b"file:" + b"///" + b"Users" + b"/"),
        ("private_key", b"BEGIN " + b"PRIVATE KEY"),
        ("rsa_private_key", b"BEGIN " + b"RSA PRIVATE KEY"),
        ("openssh_private_key", b"BEGIN " + b"OPENSSH PRIVATE KEY"),
        ("aws_access_key", b"AK" + b"IA"),
        ("github_pat", b"github" + b"_pat_"),
        ("openai_key", b"sk" + b"-proj-"),
    ]


def locked_local_path_exception_is_exact(rel: str | None, data: bytes) -> bool:
    if rel not in LOCKED_LOCAL_PATH_FILES or data.count(b"/" + b"Users" + b"/") != 1:
        return False
    try:
        rows = [json.loads(line) for line in data.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    marker = "/" + "Users" + "/"
    target = (
        marker + "zhouzixiang/Desktop/tzb/experiments/results/xa202609/"
        "20260812-e5-v11-portable-negative-audit-v3-s950000"
    )
    matched = [
        row
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("stdout"), dict)
        and marker in str(row["stdout"].get("text", ""))
    ]
    return bool(
        len(matched) == 1
        and matched[0].get("command_id") == "portable_v3_verifier"
        and matched[0].get("stdout", {}).get("text", "").count(target) == 1
        and matched[0].get("stdout", {}).get("text", "").count(marker) == 1
    )


def scan_content(path: Path, rel: str | None = None) -> list[str]:
    issues = []
    data_sets = [("file", path.read_bytes())]
    if path.suffix.lower() == ".pptx":
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    issues.append("pptx contains duplicate member names")
                for name in names:
                    if name.endswith("/"):
                        continue
                    member = PurePosixPath(name)
                    if member.is_absolute() or ".." in member.parts:
                        issues.append(f"unsafe pptx member: {name}")
                        continue
                    info = archive.getinfo(name)
                    if info.file_size > MAX_FILE_BYTES:
                        issues.append(f"oversized pptx member: {name}")
                        continue
                    data_sets.append((f"pptx:{name}", archive.read(name)))
                if sum(len(data) for _, data in data_sets) > MAX_TOTAL_BYTES:
                    issues.append("pptx expanded content exceeds total size cap")
        except (OSError, zipfile.BadZipFile) as exc:
            return [f"invalid pptx: {exc}"]
    for scope, data in data_sets:
        for label, pattern in forbidden_byte_patterns():
            if label == "aws_access_key":
                if re.search(rb"AKIA[0-9A-Z]{16}", data):
                    issues.append(f"{scope}: high-signal secret pattern {label}")
            elif label == "mac_home" and scope == "file" and locked_local_path_exception_is_exact(rel, data):
                continue
            elif pattern in data:
                issues.append(f"{scope}: forbidden content pattern {label}")
    return issues


def parse_checksums(path: Path) -> tuple[dict[str, str], list[str]]:
    checksums: dict[str, str] = {}
    issues = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            issues.append(f"invalid checksum line {number}")
            continue
        digest, rel = match.groups()
        if safe_rel(rel) is None or rel in checksums:
            issues.append(f"unsafe or duplicate checksum path at line {number}: {rel}")
            continue
        checksums[rel] = digest
    return checksums, issues


def directory_snapshot_binding(path: Path) -> dict[str, Any]:
    records = [
        [item.name, item.stat().st_size, sha256_file(item)]
        for item in sorted(path.iterdir(), key=lambda candidate: candidate.name)
        if item.is_file() and not item.is_symlink()
    ]
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "run_id": path.name,
        "snapshot_algorithm": "sha256(compact-json(sorted([name,size,sha256])))",
        "snapshot_sha256": hashlib.sha256(payload).hexdigest(),
        "snapshot_files": [
            {"path": name, "size_bytes": size, "sha256": digest}
            for name, size, digest in records
        ],
    }


def verify_externally_anchored_evidence(
    root: Path,
    manifest: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    anchor_path = root / EXTERNAL_ANCHOR_PATH
    anchor = load_object(anchor_path, "external E5 anchor", issues)
    observed_anchor_sha = sha256_file(anchor_path) if anchor_path.is_file() else None
    if observed_anchor_sha != EXTERNAL_ANCHOR_SHA256:
        issues.append("external E5 anchor SHA mismatch")
    if anchor.get("schema_version") != "xa.e5-v11-portable-fresh-validation-anchor.v2":
        issues.append("external E5 anchor schema mismatch")

    expected_source_paths = {
        "analysis/build_e5_v11_fresh_validation_v2.py",
        "analysis/verify_e5_v11_fresh_validation_v2.py",
        "tests/test_e5_v11_fresh_validation_v2.py",
        "analysis/audit_e5_v11_negative_bundle.py",
        "analysis/verify_e5_v11_negative_audit_bundle.py",
        "tests/test_e5_v11_negative_audit.py",
    }
    source_rows = anchor.get("source_files", {})
    if not isinstance(source_rows, dict) or {
        row.get("path") for row in source_rows.values() if isinstance(row, dict)
    } != expected_source_paths:
        issues.append("external E5 anchor source inventory mismatch")
    else:
        for label, row in source_rows.items():
            rel = f"experiments/{row.get('path', '')}"
            target = root / rel
            if (
                safe_rel(rel) is None
                or not target.is_file()
                or target.stat().st_size != row.get("bytes")
                or sha256_file(target) != row.get("sha256")
            ):
                issues.append(f"external E5 source binding mismatch: {label}")

    requirement_rows = anchor.get("requirements_closure", {}).get("files", [])
    if not isinstance(requirement_rows, list) or {
        row.get("path") for row in requirement_rows if isinstance(row, dict)
    } != {"environment/requirements/core.txt", "environment/requirements/dev.txt"}:
        issues.append("external E5 requirements closure mismatch")
    else:
        for row in requirement_rows:
            rel = f"experiments/{row.get('path', '')}"
            target = root / rel
            if (
                not target.is_file()
                or target.stat().st_size != row.get("bytes")
                or sha256_file(target) != row.get("sha256")
            ):
                issues.append(f"external E5 requirement binding mismatch: {rel}")

    bundle_reports = []
    bindings: dict[str, dict[str, Any]] = {}
    for bundle_id, expected in EXTERNAL_BUNDLES.items():
        rel = expected["path"]
        directory = root / rel
        if not directory.is_dir() or directory.is_symlink():
            issues.append(f"externally anchored bundle missing: {bundle_id}")
            continue
        actual_names = {
            item.name for item in directory.iterdir() if item.is_file() and not item.is_symlink()
        }
        if actual_names != EXTERNAL_BUNDLE_BASENAMES:
            issues.append(f"externally anchored bundle exact file set mismatch: {bundle_id}")
        binding = directory_snapshot_binding(directory)
        bindings[bundle_id] = binding
        anchor_key = expected.get("anchor_key")
        anchored_binding = anchor.get(anchor_key) if anchor_key else None
        anchor_run_id = expected.get("anchor_run_id")
        if anchor_run_id:
            anchored_snapshot = anchored_binding.get(anchor_run_id) if isinstance(anchored_binding, dict) else None
            anchor_matches = binding.get("snapshot_sha256") == anchored_snapshot
        elif anchor_key:
            anchor_matches = binding == anchored_binding
        else:
            anchor_matches = bundle_id in {
                "E5_V11_PREFLIGHT_SOURCE_LINK",
                "E5_V11_SEAL_SOURCE_LINK",
                "E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR",
            }
        if not anchor_matches:
            issues.append(f"externally anchored bundle/anchor mismatch: {bundle_id}")
        if binding.get("snapshot_sha256") != expected["snapshot_sha256"]:
            issues.append(f"externally anchored bundle snapshot mismatch: {bundle_id}")
        try:
            checksums, checksum_issues = parse_checksums(directory / "checksums.sha256")
        except OSError as exc:
            checksums, checksum_issues = {}, [f"unreadable checksums: {exc}"]
        issues.extend(f"{bundle_id}: {issue}" for issue in checksum_issues)
        if set(checksums) != EXTERNAL_BUNDLE_BASENAMES - {"checksums.sha256"}:
            issues.append(f"externally anchored bundle checksum coverage mismatch: {bundle_id}")
        for name, digest in checksums.items():
            target = directory / name
            if not target.is_file() or sha256_file(target) != digest:
                issues.append(f"externally anchored bundle checksum mismatch: {bundle_id}/{name}")
        bundle_reports.append(
            {
                "id": bundle_id,
                "path": rel,
                "anchor_key": anchor_key,
                "anchor_run_id": anchor_run_id,
                "role": expected.get("role"),
                "run_id": binding["run_id"],
                "snapshot_algorithm": binding["snapshot_algorithm"],
                "snapshot_sha256": binding["snapshot_sha256"],
                "files": binding["snapshot_files"],
                "exact_nine_file_set": True,
                "bundle_checksums_verified": True,
            }
        )

    local_path_occurrences = 0
    for bundle_id, expected in EXTERNAL_BUNDLES.items():
        directory = root / expected["path"]
        bundle_occurrences = sum(
            item.read_bytes().count(b"/" + b"Users" + b"/")
            for item in directory.iterdir()
            if item.is_file()
        ) if directory.is_dir() else 0
        local_path_occurrences += bundle_occurrences
        raw_rel = f"{expected['path']}/raw.jsonl"
        if raw_rel in LOCKED_LOCAL_PATH_FILES:
            raw_path = root / raw_rel
            if bundle_occurrences != 1 or not raw_path.is_file() or not locked_local_path_exception_is_exact(
                raw_rel, raw_path.read_bytes()
            ):
                issues.append(f"locked local-path exception mismatch: {bundle_id}")
        elif bundle_occurrences:
            issues.append(f"unexpected local path in externally anchored bundle: {bundle_id}")
    if local_path_occurrences != 2:
        issues.append("externally anchored bundles must contain exactly two locked local-path exceptions")

    portable = load_object(
        root / EXTERNAL_BUNDLES["E5_PORTABLE_V3"]["path"] / "summary.json",
        "portable E5 V3 summary",
        issues,
    )
    portable_verifier = load_object(
        root / EXTERNAL_BUNDLES["E5_PORTABLE_V3"]["path"] / "verifier.json",
        "portable E5 V3 declared verifier",
        issues,
    )
    fresh = load_object(
        root / EXTERNAL_BUNDLES["E5_FRESH_V2"]["path"] / "summary.json",
        "fresh E5 V2 summary",
        issues,
    )
    fresh_declared = load_object(
        root / EXTERNAL_BUNDLES["E5_FRESH_V2"]["path"] / "verifier.json",
        "fresh E5 V2 declared verifier",
        issues,
    )
    scientific_source = load_object(
        root / EXTERNAL_BUNDLES["E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR"]["path"] / "summary.json",
        "E5 v1.1 scientific source predecessor summary",
        issues,
    )
    scientific_source_verifier = load_object(
        root / EXTERNAL_BUNDLES["E5_V11_SCIENTIFIC_SOURCE_PREDECESSOR"]["path"] / "verifier.json",
        "E5 v1.1 scientific source predecessor verifier",
        issues,
    )
    if not (
        scientific_source.get("trial_count") == 90
        and scientific_source.get("complete_matrix") is True
        and scientific_source.get("v4_four_arm_fairness", {}).get(
            "family_schedulable_group_counts", {}
        ).get("ASCON") == 0
        and scientific_source_verifier.get("ok") is False
        and scientific_source_verifier.get("checks", {}).get(
            "each_family_has_schedulable_activity"
        ) is False
        and portable.get("schema_version") == "xa.e5-v11-portable-negative-audit-summary.v3"
        and portable.get("protocol_acceptance") is False
        and portable.get("experiment_completed") is False
        and portable.get("performance_claim_supported") is False
        and portable_verifier.get("ok") is True
        and portable_verifier.get("protocol_acceptance") is False
        and fresh.get("schema_version") == "xa.e5-v11-portable-fresh-validation-summary.v2"
        and fresh.get("full_pytest_passed") == 383
        and fresh.get("successful_command_count") == 9
        and fresh.get("software_validation_ok") is True
        and fresh.get("scientific_bundle_independently_recomputed") is True
        and fresh.get("scientific_evidence") is False
        and fresh.get("protocol_acceptance") is False
        and fresh.get("hardware_execution") is False
        and fresh_declared.get("ok") is True
        and fresh_declared.get("protocol_acceptance") is False
        and fresh_declared.get("scientific_evidence") is False
    ):
        issues.append("externally anchored E5 claim boundary mismatch")

    expected_status = {
        "schema_version": "xa.externally-anchored-evidence.v1",
        "status": "closed_software_validation_only",
        "anchor": {
            "path": EXTERNAL_ANCHOR_PATH,
            "sha256": observed_anchor_sha,
            "schema_version": anchor.get("schema_version"),
        },
        "bundles": bundle_reports,
        "source_files_verified": True,
        "requirements_closure_verified": True,
        "predecessor_role": "provenance_predecessor_only_not_performance_or_recommendation",
        "scientific_source_predecessor_role": "scientific_source_predecessor_only_unaccepted_endpoint",
        "scientific_source_link_roles": [
            "scientific_source_linked_preflight_only",
            "scientific_source_linked_seal_only",
        ],
        "locked_local_path_exceptions": {
            "count": 2,
            "files": sorted(LOCKED_LOCAL_PATH_FILES),
            "json_field": "stdout.text",
            "command_id": "portable_v3_verifier",
            "target_run": "20260812-e5-v11-portable-negative-audit-v3-s950000",
            "purpose": "immutable historical stdout bytes; not a runtime dependency",
        },
        "fresh_validation": {
            "successful_command_count": 9,
            "full_pytest_passed": 383,
            "targeted_e5_passed": fresh.get("targeted_e5_passed"),
            "software_validation_ok": True,
            "historical_commands_authenticated": fresh.get("historical_commands_authenticated"),
            "historical_commands_independently_rerun_by_bundle_verifier": False,
        },
        "claim_boundary": (
            "Externally anchored software/portability evidence only; the scientific V3 bundle remains "
            "a negative audit with protocol_acceptance=false and supplies no accepted E5 endpoint, "
            "hardware result, performance evidence, or quantum-advantage claim."
        ),
    }
    if manifest.get("externally_anchored_evidence") != expected_status:
        issues.append("manifest externally anchored E5 inventory mismatch")
    manifest_rows = {
        row.get("path"): row for row in manifest.get("files", []) if isinstance(row, dict)
    }
    for bundle_id, binding in bindings.items():
        prefix = EXTERNAL_BUNDLES[bundle_id]["path"]
        for row in binding["snapshot_files"]:
            rel = f"{prefix}/{row['path']}"
            outer = manifest_rows.get(rel, {})
            if (
                outer.get("source_path") != rel
                or outer.get("source_sha256") != row["sha256"]
                or outer.get("sha256") != row["sha256"]
                or outer.get("bytes") != row["size_bytes"]
            ):
                issues.append(f"outer manifest does not bind anchored artifact: {rel}")

    verifier_args = [
        sys.executable,
        "-B",
        "analysis/verify_e5_v11_fresh_validation_v2.py",
        "results/xa202609/20260812-e5-v11-portable-fresh-validation-v2-s970000",
        "--anchor",
        "configs/xa202609/e5_v11_portable_fresh_validation_v2.anchor.json",
        "--expected-anchor-sha256",
        EXTERNAL_ANCHOR_SHA256,
    ]
    try:
        nested_env = os.environ.copy()
        nested_env["XA_E5_PROJECT_ROOT"] = str((root / "experiments").resolve())
        nested = subprocess.run(
            verifier_args,
            cwd=root / "experiments",
            env=nested_env,
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
        nested_payload = json.loads(nested.stdout) if nested.stdout.strip() else {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        nested = None
        nested_payload = {}
        issues.append(f"fresh-v2 independent verifier could not run: {exc}")
    if nested is not None and not (
        nested.returncode == 0
        and nested_payload.get("ok") is True
        and nested_payload.get("anchor_sha256") == EXTERNAL_ANCHOR_SHA256
        and nested_payload.get("bundle_snapshot_sha256")
        == EXTERNAL_BUNDLES["E5_FRESH_V2"]["snapshot_sha256"]
        and nested_payload.get("scientific_bundle_independently_recomputed") is True
        and nested_payload.get("protocol_acceptance") is False
        and len(nested_payload.get("checks", {})) == 19
        and all(value is True for value in nested_payload.get("checks", {}).values())
    ):
        issues.append("fresh-v2 independent verifier failed its 19-check anchored contract")
    return issues, expected_status


def inspect_archive(path: Path, temp: Path) -> tuple[Path | None, list[str]]:
    issues = []
    roots = set()
    try:
        with tarfile.open(path, "r:*") as archive:
            members = archive.getmembers()
            member_names = [member.name for member in members]
            if len(member_names) != len(set(member_names)):
                issues.append("archive contains duplicate member names")
            if len(members) > 1000:
                issues.append(f"archive member count exceeds cap: {len(members)}")
            total_size = sum(member.size for member in members if member.isfile())
            if total_size > MAX_TOTAL_BYTES:
                issues.append(f"archive expanded size exceeds cap: {total_size}")
            for member in members:
                member_path = PurePosixPath(member.name)
                if member_path.is_absolute() or ".." in member_path.parts or not member_path.parts:
                    issues.append(f"unsafe archive member path: {member.name}")
                    continue
                roots.add(member_path.parts[0])
                if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                    issues.append(f"forbidden archive member type: {member.name}")
                if member.size > MAX_FILE_BYTES:
                    issues.append(f"archive member exceeds size cap: {member.name}")
            if len(roots) != 1:
                issues.append(f"archive must have one top-level root, found {sorted(roots)}")
            if issues:
                return None, issues
            archive.extractall(temp, filter="data")
    except (OSError, tarfile.TarError) as exc:
        return None, [f"invalid archive: {exc}"]
    return temp / next(iter(roots)), issues


def verify_snapshot(root: Path, bundle_id: str) -> list[str]:
    issues = []
    directory = root / "evidence_snapshots" / bundle_id
    manifest_path = directory / "SNAPSHOT_MANIFEST.json"
    checksums_path = directory / "CHECKSUMS.sha256"
    if not manifest_path.is_file() or not checksums_path.is_file():
        return [f"{bundle_id}: missing snapshot manifest/checksums"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{bundle_id}: invalid snapshot manifest: {exc}"]
    if manifest.get("schema_version") != "xa.evidence-snapshot.v1" or manifest.get("bundle_id") != bundle_id:
        issues.append(f"{bundle_id}: snapshot schema/id mismatch")
    expected_source, expected_profile = EVIDENCE_SOURCES[bundle_id]
    if manifest.get("source_bundle") != expected_source or manifest.get("claim_profile") != expected_profile:
        issues.append(f"{bundle_id}: source bundle/claim profile mismatch")
    source_inventory = manifest.get("source_inventory")
    included = manifest.get("included")
    omitted = manifest.get("omitted_large_or_log_artifacts")
    inventories_are_rows = (
        isinstance(source_inventory, list)
        and isinstance(included, list)
        and isinstance(omitted, list)
        and all(isinstance(row, dict) for row in [*source_inventory, *included, *omitted])
    )
    if not inventories_are_rows:
        issues.append(f"{bundle_id}: source/included/omitted inventories are malformed")
    elif {row.get("name") for row in source_inventory} != {
        *(row.get("source_name") for row in included),
        *(row.get("name") for row in omitted),
    }:
        issues.append(f"{bundle_id}: source inventory is not partitioned by included/omitted rows")
    if not omitted:
        issues.append(f"{bundle_id}: omitted large/log artifact inventory is missing")
    checksums, parse_issues = parse_checksums(checksums_path)
    issues.extend(f"{bundle_id}: {issue}" for issue in parse_issues)
    actual = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name != "CHECKSUMS.sha256"
    }
    if set(checksums) != actual:
        issues.append(f"{bundle_id}: snapshot checksum coverage mismatch")
    for name, digest in checksums.items():
        target = directory / name
        if not target.is_file() or sha256_file(target) != digest:
            issues.append(f"{bundle_id}: snapshot checksum mismatch: {name}")
    return issues


def verify_sbom(root: Path, final: bool) -> list[str]:
    issues = []
    try:
        sbom = json.loads((root / "SBOM-LITE.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid SBOM-LITE.json: {exc}"]
    if sbom.get("schema_version") != "xa.sbom-lite.v1" or sbom.get("not_a_transitive_sbom") is not True:
        issues.append("SBOM-lite scope/schema is not explicit")
    requirement_rows = sbom.get("requirements", [])
    for row in requirement_rows:
        rel = row.get("path", "")
        target = root / rel
        if safe_rel(rel) is None or not target.is_file() or sha256_file(target) != row.get("sha256"):
            issues.append(f"SBOM-lite requirement hash mismatch: {rel}")
    exact = {
        (row.get("group"), row.get("name"), row.get("constraint"))
        for row in sbom.get("components", [])
        if row.get("exact_pin") is True
    }
    required_exact = {
        ("core", "numpy", "==2.4.6"),
        ("core", "scipy", "==1.17.1"),
        ("core", "PuLP", "==3.3.1"),
        ("core", "torch", "==2.12.0"),
        ("dev", "pytest", "==9.0.3"),
    }
    if not required_exact.issubset(exact):
        issues.append("SBOM-lite is missing exact frozen core/dev dependencies")
    if final:
        cyclonedx = root / "authorization/SBOM.cdx.json"
        try:
            payload = json.loads(cyclonedx.read_text(encoding="utf-8"))
            if payload.get("bomFormat") != "CycloneDX":
                issues.append("final transitive SBOM is not CycloneDX")
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(f"final transitive SBOM missing/invalid: {exc}")
    return issues


def verify_authorization(root: Path, mode: str) -> list[str]:
    issues = []
    try:
        status = json.loads((root / "AUTHORIZATION_STATUS.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid authorization status: {exc}"]
    if status.get("schema_version") != "xa.authorization-status.v1":
        issues.append("authorization status schema mismatch")
    if mode == "internal_audit_draft":
        if status.get("distributable") is not False or status.get("package_gate_status") != "incomplete":
            issues.append("draft authorization state is not fail-closed")
        if not (root / "INCOMPLETE_INTERNAL_AUDIT_DRAFT.md").is_file():
            issues.append("draft marker is missing")
        if any((root / rel).exists() for rel in AUTH_FILES):
            issues.append("draft must not package unapproved authorization documents")
        return issues
    if status.get("status") != "approved" or status.get("distributable") is not True:
        issues.append("final authorization is not approved")
    if status.get("package_gate_status") != "ready":
        issues.append("final package authorization gate is not ready")
    if status.get("missing_documents") or status.get("invalid_documents_or_fields") or status.get("failed_declarations"):
        issues.append("final authorization status contains unresolved gates")
    if set(status.get("document_sha256", {})) != {PurePosixPath(path).name for path in AUTH_FILES}:
        issues.append("authorization document hash inventory is incomplete")
    for rel in AUTH_FILES:
        target = root / rel
        if not target.is_file():
            issues.append(f"missing authorization document: {rel}")
            continue
        expected = status.get("document_sha256", {}).get(target.name)
        if expected != sha256_file(target):
            issues.append(f"authorization document hash mismatch: {rel}")
    auth_path = root / "authorization/SUBMISSION_AUTHORIZATION.json"
    try:
        auth = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return issues + [f"invalid human authorization JSON: {exc}"]
    if auth.get("schema_version") != "xa.submission-authorization.v1" or auth.get("competition_id") != "XA-202609" or auth.get("status") != "approved":
        issues.append("human authorization schema/id/status mismatch")
    for key in AUTH_DECLARATIONS:
        if auth.get("declarations", {}).get(key) is not True:
            issues.append(f"human declaration is not true: {key}")
    archive_name = auth.get("archive_name", "")
    if not re.fullmatch(r"XA-202609_[A-Za-z0-9][A-Za-z0-9._-]*\.tar\.gz", archive_name) or "draft" in archive_name.lower():
        issues.append("human-authorized archive name is invalid")
    return issues


def packaged_source_tree_sha256(root: Path) -> tuple[str, int]:
    files = sorted(
        [
            *(path for path in (root / "experiments/src").rglob("*.py") if path.is_file()),
            root / "experiments/scripts/train_expert_iteration.py",
            root / "experiments/scripts/train_foundation_v4.py",
            root / "experiments/scripts/verify_foundation_v4_bundle.py",
            root / "experiments/scripts/_pilot_artifacts.py",
        ],
        key=lambda path: path.relative_to(root).as_posix(),
    )
    digest = hashlib.sha256()
    count = 0
    for path in files:
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\n")
        count += 1
    return digest.hexdigest(), count


def load_object(path: Path, label: str, issues: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        issues.append(f"invalid {label}: {exc}")
        return {}
    if not isinstance(payload, dict):
        issues.append(f"{label} must be a JSON object")
        return {}
    return payload


def verify_formal_v4(root: Path) -> list[str]:
    issues: list[str] = []
    bundle = root / FORMAL_V4_PREFIX
    actual = {path.name for path in bundle.iterdir() if path.is_file()} if bundle.is_dir() else set()
    if actual != FORMAL_V4_BASENAMES:
        return ["formal v4 bundle file set mismatch"]
    checksums, parse_issues = parse_checksums(bundle / "checksums.sha256")
    issues.extend(f"formal v4: {issue}" for issue in parse_issues)
    if set(checksums) != FORMAL_V4_BASENAMES - {"checksums.sha256"}:
        issues.append("formal v4 checksum coverage mismatch")
    for name, digest in checksums.items():
        target = bundle / name
        if not target.is_file() or sha256_file(target) != digest:
            issues.append(f"formal v4 checksum mismatch: {name}")

    command = load_object(bundle / "command.json", "formal v4 command", issues)
    config = load_object(bundle / "config_snapshot.json", "formal v4 config", issues)
    dataset = load_object(bundle / "dataset_manifest.json", "formal v4 dataset manifest", issues)
    card = load_object(bundle / "model_card.json", "formal v4 model card", issues)
    summary = load_object(bundle / "training_summary.json", "formal v4 training summary", issues)
    self_checks = load_object(bundle / "self_checks.json", "formal v4 self checks", issues)
    source = load_object(bundle / "source_manifest.json", "formal v4 source manifest", issues)
    artifacts = load_object(bundle / "artifacts.manifest.json", "formal v4 artifact manifest", issues)

    argv = command.get("argv", [])
    local_path_markers = ("/" + "Users" + "/", "/" + "home" + "/")
    def contains_local_path(value: Any) -> bool:
        rendered = str(value)
        return any(marker in rendered for marker in local_path_markers) or bool(
            re.search(r"[A-Za-z]:\\\\", rendered)
        )

    if not (
        command.get("schema_version") == "xa.foundation-training-command.v4"
        and command.get("cwd") == "${PROJECT_ROOT}"
        and command.get("executable") == "python"
        and isinstance(argv, list)
        and argv[:1] == ["scripts/train_foundation_v4.py"]
        and not any(contains_local_path(item) for item in argv)
    ):
        issues.append("formal v4 portable training command is not closed")
    formal_profile = config.get("profiles", {}).get("formal", {})
    seed = formal_profile.get("seed")
    if not (
        config.get("schema_version") == "xa.foundation-training-config.v4"
        and config.get("selected_profile") == "formal"
        and isinstance(seed, int)
        and formal_profile.get("purpose") == "provenance_closed_candidate_training"
    ):
        issues.append("formal v4 config/profile/seed mismatch")
    records = dataset.get("records", [])
    rows = [row for row in records if isinstance(row, dict)] if isinstance(records, list) else []
    identities = [(row.get("num_vars"), row.get("truth_table_sha256")) for row in rows]
    crypto = dataset.get("crypto_exclusion", {})
    if not (
        dataset.get("schema_version") == "xa.foundation-dataset-manifest.v4"
        and len(rows) == 208
        and len(identities) == len(set(identities))
        and {"train", "holdout"} <= {row.get("split") for row in rows}
        and dataset.get("split_contract", {}).get("holdout_used_for_fit") is False
        and crypto.get("evaluation_not_accessed") is True
        and crypto.get("evaluation_module_imported_during_training") is False
    ):
        issues.append("formal v4 split/crypto-exclusion evidence mismatch")
    source_identity = source.get("git_identity", {})
    if not (
        source.get("schema_version") == "xa.foundation-source-manifest.v4"
        and re.fullmatch(r"[0-9a-f]{40}", str(source_identity.get("commit_sha", "")))
        and re.fullmatch(r"[0-9a-f]{64}", str(source_identity.get("source_tree_sha256", "")))
        and source_identity.get("dirty") is True
        and bool(source.get("files"))
        and bool(source.get("trees"))
    ):
        issues.append("formal v4 exact source-SHA provenance mismatch")
    try:
        log_rows = [
            json.loads(line)
            for line in (bundle / "training_log.jsonl").read_text(encoding="utf-8").splitlines()
        ]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        log_rows = []
    if not log_rows or {row.get("event") for row in log_rows if isinstance(row, dict)} < {
        "initial_validation", "training_iteration", "final_validation"
    }:
        issues.append("formal v4 training log is missing required events")
    checkpoint_sha = sha256_file(bundle / "checkpoint.pt")
    card_links = card.get("training", {}).get("hash_links", {})
    link_names = {
        "command_sha256": "command.json",
        "config_sha256": "config_snapshot.json",
        "dataset_manifest_sha256": "dataset_manifest.json",
        "resource_estimate_sha256": "resource_estimate.json",
        "source_manifest_sha256": "source_manifest.json",
        "training_log_sha256": "training_log.jsonl",
    }
    if not all(card_links.get(key) == checksums.get(name) for key, name in link_names.items()):
        issues.append("formal v4 model-card hash links mismatch")
    checks = self_checks.get("checks", {})
    if not (
        checkpoint_sha == "5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7"
        and card.get("schema_version") == "xa.foundation-model-card.v4"
        and card.get("model_id") == "boolean_oracle_fm_v4"
        and card.get("artifact", {}).get("sha256") == checkpoint_sha
        and card.get("training", {}).get("seed") == seed
        and card.get("data", {}).get("crypto_oracle_training_examples") == 0
        and card.get("data", {}).get("evaluation_not_accessed") is True
        and summary.get("checkpoint", {}).get("sha256") == checkpoint_sha
        and summary.get("formal_training_completed") is True
        and summary.get("performance_evidence") is False
        and artifacts.get("bundle_metadata", {}).get("performance_evidence") is False
        and bool(checks)
        and all(value is True for value in checks.values())
    ):
        issues.append("formal v4 provenance/claim boundary mismatch")
    artifact_rows = artifacts.get("artifacts", [])
    artifact_hashes = {
        row.get("relative_path"): row.get("sha256")
        for row in artifact_rows
        if isinstance(row, dict)
    }
    if any(artifact_hashes.get(name) != digest for name, digest in checksums.items() if name != "artifacts.manifest.json"):
        issues.append("formal v4 artifact manifest/hash inventory mismatch")
    return issues


def snapshot_json(root: Path, bundle_id: str, name: str, issues: list[str]) -> dict[str, Any]:
    return load_object(root / "evidence_snapshots" / bundle_id / name, f"{bundle_id}/{name}", issues)


def verify_research_claims(root: Path, status: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    expected_claims = {
        "formal_v4": {
            "provenance_closed": True,
            "performance_evidence": False,
            "final_model": False,
        },
        "e4_v2": {
            "role": "post_e4_frozen_aes_replication",
            "generalization_claim": False,
            "historically_seen_in_e4": True,
            "mean_native_2q_delta": -513.9375,
            "bootstrap_95_ci": [-2059.0625, 589.9375],
            "improvement_supported": False,
        },
        "e5": {
            "v1_first_release_trial_rows": 0,
            "v11_matrix_rows": 90,
            "protocol_acceptance": False,
            "accepted_endpoint": False,
            "performance_claim_supported": False,
            "ascon_schedulable_groups": 0,
            "portable_v3_snapshot_sha256": "4ba1d958296866ce50df2a695223091db96296189f218fb1cec8412ed1ad02ea",
            "fresh_v2_snapshot_sha256": "dd75a9bcf06f37390c43acf6a019ea8a130ba26a998269ae10fe8bce78441d23",
            "external_anchor_sha256": EXTERNAL_ANCHOR_SHA256,
            "fresh_full_pytest_passed": 383,
            "fresh_successful_command_count": 9,
            "software_validation_ok": True,
            "scientific_evidence": False,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
        },
        "e6": {
            "status": "development_causal_negative_result_verified",
            "mechanism_status": "development_mechanism_mvp_not_formal_experiment",
            "development_result_bundle_present": True,
            "formal_result_bundle_present": False,
            "bundle_path": E6_RESULT_PREFIX,
            "bundle_snapshot_sha256": E6_RESULT_SNAPSHOT_SHA256,
            "run_id": "20260812-e6-q4ai-causal-v1-full-s20260912",
            "source_commit": "e850c0ce91aa0ae9897f4ce0f5268171dbb22532",
            "training_or_finetuning_performed": True,
            "train_case_count": 64,
            "heldout_case_count": 32,
            "primary_comparison": (
                "qaoa_final_measurement_replay_minus_qaoa_permuted_label_control"
            ),
            "mean_effect": 0.09497779579431545,
            "bootstrap_95_ci": [0.06963836434546339, 0.12376730228100935],
            "signflip_p": 0.00000999990000099999,
            "wins": 0,
            "ties": 3,
            "losses": 29,
            "claim_supported": False,
            "compute_budget_equal": False,
            "development_conditional_only": True,
            "formal_evaluation": False,
            "performance_evidence": False,
            "generalization_claim": False,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
        },
    }
    if status.get("research_claims") != expected_claims:
        issues.append("technical research-claim boundary inventory mismatch")

    e4_cal = snapshot_json(root, "E4V2_CAL", "summary.json", issues)
    e4_cal_verifier = snapshot_json(root, "E4V2_CAL", "verifier.json", issues)
    if not (
        e4_cal.get("schema_version") == "xa.e4-v2-calibration-summary.v1"
        and e4_cal.get("performance_evidence") is False
        and e4_cal.get("generalization_claim") is False
        and e4_cal.get("experiment_role") == "frozen_replication"
        and e4_cal_verifier.get("ok") is True
        and e4_cal_verifier.get("checks", {}).get("not_performance_evidence") is True
    ):
        issues.append("E4-v2 calibration is not bound as non-performance evidence")
    e4 = snapshot_json(root, "E4V2_TEST", "summary.json", issues)
    e4_verifier = snapshot_json(root, "E4V2_TEST", "verifier.json", issues)
    scope = e4.get("scope", {})
    comparison = e4.get("primary_comparison", {})
    ci = comparison.get("bootstrap_95_ci", [])
    if not (
        e4.get("schema_version") == "xa.e4-v2-test-summary.v1"
        and e4.get("trial_count") == 64
        and scope.get("dataset_role") == "post_e4_frozen_aes_replication"
        and scope.get("generalization_claim") is False
        and scope.get("historically_seen_in_E4") is True
        and scope.get("hardware_execution") is False
        and scope.get("quantum_advantage_claimed") is False
        and comparison.get("mean_delta_execution_minus_historical") == -513.9375
        and ci == [-2059.0625, 589.9375]
        and ci[0] <= 0 <= ci[1]
        and e4_verifier.get("ok") is True
        and e4_verifier.get("checks", {}).get("replication_boundary_explicit") is True
    ):
        issues.append("E4-v2 replication/no-improvement claim boundary mismatch")

    for bundle_id in ("E5_V1_PREFLIGHT", "E5_V1_SEAL", "E5_V11_PREFLIGHT", "E5_V11_SEAL"):
        summary = snapshot_json(root, bundle_id, "summary.json", issues)
        verifier = snapshot_json(root, bundle_id, "verifier.json", issues)
        if summary.get("performance_evidence") is not False or verifier.get("ok") is not True:
            issues.append(f"{bundle_id} is not bound as pre-endpoint/non-performance evidence")
    e5 = snapshot_json(root, "E5_V11_UNACCEPTED_EVAL", "summary.json", issues)
    e5_verifier = snapshot_json(root, "E5_V11_UNACCEPTED_EVAL", "verifier.json", issues)
    if not (
        e5.get("trial_count") == 90
        and e5.get("complete_matrix") is True
        and "first v1 attempt failed before producing any trial row" in e5.get("claim_boundary", "")
        and e5.get("v4_four_arm_fairness", {}).get("family_schedulable_group_counts", {}).get("ASCON") == 0
        and e5_verifier.get("ok") is False
        and e5_verifier.get("checks", {}).get("each_family_has_schedulable_activity") is False
    ):
        issues.append("E5-v1.1 evaluation is not preserved as an unaccepted endpoint")
    failed = snapshot_json(root, "E5_V11_FAILED_ATTEMPT", "summary.json", issues)
    failed_verifier = snapshot_json(root, "E5_V11_FAILED_ATTEMPT", "verifier.json", issues)
    if not (
        failed.get("status") == "failed_attempt_evidence"
        and failed.get("experiment_completed") is False
        and failed.get("endpoint_summary_available") is False
        and failed.get("comparison_available") is False
        and failed_verifier.get("ok") is True
        and failed_verifier.get("checks", {}).get("failure_not_mislabelled_complete") is True
    ):
        issues.append("E5-v1.1 failed attempt is misclassified")
    negative = snapshot_json(root, "E5_V11_NEGATIVE_AUDIT", "summary.json", issues)
    negative_verifier = snapshot_json(root, "E5_V11_NEGATIVE_AUDIT", "verifier.json", issues)
    if not (
        negative.get("protocol_acceptance") is False
        and negative.get("performance_claim_supported") is False
        and negative.get("experiment_completed") is False
        and negative.get("family_schedulable_group_counts", {}).get("ASCON") == 0
        and negative_verifier.get("ok") is True
        and negative_verifier.get("protocol_acceptance") is False
        and negative_verifier.get("checks", {}).get("protocol_and_experiment_remain_incomplete") is True
    ):
        issues.append("E5 negative audit does not preserve protocol rejection")

    e6_mechanism = load_object(
        root / "experiments/configs/xa202609/e6_multioutput_shared_mvp_v1.json",
        "E6 MVP config",
        issues,
    )
    if not (
        e6_mechanism.get("schema_version") == "xa.e6-multioutput-shared-mvp-config.v1.1"
        and e6_mechanism.get("status") == "development_mechanism_mvp_not_formal_experiment"
        and e6_mechanism.get("scope", {}).get("formal_result_bundle_present") is False
        and e6_mechanism.get("scope", {}).get("performance_evidence") is False
        and e6_mechanism.get("development_regression", {}).get("not_formal_evidence") is True
        and e6_mechanism.get("ai_quantum_boundary", {}).get("shared_model_architecture_implemented") is True
    ):
        issues.append("E6 mechanism baseline is not bound as development-only evidence")

    e6_config = load_object(
        root / "experiments/configs/xa202609/e6_q4ai_causal_v1.json",
        "E6 Q4AI causal config",
        issues,
    )
    e6_bundle = root / E6_RESULT_PREFIX
    actual_e6_files = (
        {item.name for item in e6_bundle.iterdir() if item.is_file() and not item.is_symlink()}
        if e6_bundle.is_dir()
        else set()
    )
    if actual_e6_files != set(E6_RESULT_FILE_SHA256):
        issues.append("E6 development result file set mismatch")
    for name, expected_sha in E6_RESULT_FILE_SHA256.items():
        target = e6_bundle / name
        if not target.is_file() or target.is_symlink() or sha256_file(target) != expected_sha:
            issues.append(f"E6 development result SHA mismatch: {name}")
    if e6_bundle.is_dir() and e6_result_snapshot_sha256(e6_bundle) != E6_RESULT_SNAPSHOT_SHA256:
        issues.append("E6 development result snapshot mismatch")
    try:
        e6_checksums, e6_checksum_issues = parse_checksums(e6_bundle / "checksums.sha256")
    except OSError as exc:
        e6_checksums, e6_checksum_issues = {}, [f"unreadable checksums: {exc}"]
    issues.extend(f"E6 development result: {issue}" for issue in e6_checksum_issues)
    expected_e6_payload_hashes = {
        name: digest
        for name, digest in E6_RESULT_FILE_SHA256.items()
        if name != "checksums.sha256"
    }
    if e6_checksums != expected_e6_payload_hashes:
        issues.append("E6 development result checksum inventory mismatch")

    e6_results = load_object(e6_bundle / "results.json", "E6 development results", issues)
    e6_heldout = load_object(
        e6_bundle / "heldout_evaluation.json", "E6 heldout development evaluation", issues
    )
    e6_primary = e6_heldout.get("statistics", {}).get("primary", {})
    e6_claim_gate = e6_heldout.get("statistics", {}).get("claim_gate", {})
    e6_reports = e6_results.get("training_report_by_arm", {})
    expected_arms = [
        "classical_random_bitstring_replay",
        "classical_greedy_repeated_selection_replay",
        "qaoa_final_measurement_replay",
        "qaoa_permuted_label_control",
    ]
    reports_ok = (
        isinstance(e6_reports, dict)
        and set(e6_reports) == set(expected_arms)
        and all(
            isinstance(report, dict)
            and report.get("source_arm") == arm
            and report.get("sample_count") == 64
            and report.get("head_training_status") == "modified_unsealed"
            and report.get("formal_evaluation") is False
            and report.get("performance_evidence") is False
            and report.get("final_head_tensor_sha256")
            == e6_results.get("final_head_sha_by_arm", {}).get(arm)
            for arm, report in e6_reports.items()
        )
    )
    case_rows = e6_heldout.get("case_rows", [])
    rows_ok = (
        isinstance(case_rows, list)
        and len(case_rows) == 32
        and sum(row.get("input_count") == 4 for row in case_rows if isinstance(row, dict)) == 16
        and sum(row.get("input_count") == 5 for row in case_rows if isinstance(row, dict)) == 16
        and all(
            isinstance(row, dict)
            and row.get("formal_evaluation") is False
            and row.get("performance_evidence") is False
            and isinstance(row.get("direct_semantic_verification"), dict)
            and row["direct_semantic_verification"].get("ok") is True
            and isinstance(row.get("arms"), dict)
            and set(row["arms"]) == set(expected_arms)
            and all(
                isinstance(arm_row, dict)
                and arm_row.get("semantic_verification") is True
                and arm_row.get("degraded") is False
                and arm_row.get("direct_fallback_used") is False
                for arm_row in row["arms"].values()
            )
            for row in case_rows
        )
    )
    if not (
        e6_config.get("schema_version") == "xa.e6-q4ai-causal-config.v1"
        and e6_config.get("status")
        == "development_causal_experiment_not_formal_or_performance_evidence"
        and e6_config.get("profiles", {}).get("full", {}).get("train_case_count") == 64
        and e6_config.get("profiles", {}).get("full", {}).get("heldout_cases_per_input_count") == 16
        and e6_config.get("profiles", {}).get("full", {}).get("heldout_dataset_seed") == 20260921
        and e6_results.get("schema_version") == "xa.e6-replay-training-results.v1-development"
        and e6_results.get("run_id") == "20260812-e6-q4ai-causal-v1-full-s20260912"
        and e6_results.get("source_commit") == "e850c0ce91aa0ae9897f4ce0f5268171dbb22532"
        and e6_results.get("source_dirty") is False
        and e6_results.get("arms") == expected_arms
        and e6_results.get("performance_evidence") is False
        and reports_ok
        and e6_heldout.get("schema_version")
        == "xa.e6-replay-training-heldout-evaluation.v1-development"
        and e6_heldout.get("heldout_development_evaluation") is True
        and e6_heldout.get("formal_evaluation") is False
        and e6_heldout.get("performance_evidence") is False
        and e6_primary.get("comparison")
        == "qaoa_final_measurement_replay_minus_qaoa_permuted_label_control"
        and e6_primary.get("case_count") == 32
        and e6_primary.get("effect_estimate") == 0.09497779579431545
        and e6_primary.get("bootstrap", {}).get("ci_lower") == 0.06963836434546339
        and e6_primary.get("bootstrap", {}).get("ci_upper") == 0.12376730228100935
        and e6_primary.get("signflip", {}).get("p_value") == 0.00000999990000099999
        and (e6_primary.get("wins"), e6_primary.get("ties"), e6_primary.get("losses"))
        == (0, 3, 29)
        and e6_claim_gate.get("claim_supported") is False
        and e6_claim_gate.get("formal_evaluation") is False
        and e6_claim_gate.get("performance_evidence") is False
        and rows_ok
    ):
        issues.append("E6 development negative result/claim boundary mismatch")
    return issues


def verify_technical_release(
    root: Path,
    mode: str,
    manifest: dict[str, Any],
    provenance: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    path = root / "TECHNICAL_RELEASE_STATUS.json"
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid TECHNICAL_RELEASE_STATUS.json: {exc}"]
    if status.get("schema_version") != "xa.technical-release-status.v2":
        issues.append("technical release status schema mismatch")
    if manifest.get("technical_release") != status:
        issues.append("manifest/technical release status mismatch")
    if status.get("externally_anchored_evidence") != manifest.get("externally_anchored_evidence"):
        issues.append("technical/manifest externally anchored evidence mismatch")
    checkpoint = root / FINAL_CHECKPOINT_PATH
    checkpoint_sha = sha256_file(checkpoint) if checkpoint.is_file() else None
    if (
        checkpoint_sha != "5b7cb23accde48915f619562b5be34221d4f0637422b7ec2e980e1a348c719f7"
        or status.get("checkpoint", {}).get("path") != FINAL_CHECKPOINT_PATH
        or status.get("checkpoint", {}).get("sha256") != checkpoint_sha
    ):
        issues.append("technical status/checkpoint SHA mismatch")
    source_sha, source_count = packaged_source_tree_sha256(root)
    source = status.get("source", {})
    if source.get("source_tree_algorithm") != "xa-python-source-tree.v1":
        issues.append("technical source-tree algorithm mismatch")
    if source.get("source_tree_sha256") != source_sha or source.get("source_tree_file_count") != source_count:
        issues.append("technical source-tree SHA/count mismatch")
    if source.get("commit_sha") != provenance.get("git", {}).get("commit_sha"):
        issues.append("technical/provenance commit SHA mismatch")
    legacy_card_path = root / "experiments/models/MODEL_CARD_boolean_oracle_fm_v3.md"
    legacy_card = legacy_card_path.read_text(encoding="utf-8", errors="replace") if legacy_card_path.is_file() else ""
    development_markers = (
        "开发候选（development candidate）",
        "是否为 XA-202609 最终冻结模型**：否",
        "尚不能作为比赛最终模型交付",
    )
    legacy_development = any(marker in legacy_card for marker in development_markers)
    blockers = set(status.get("blockers", []))
    expected_current_blockers = {
        "final_external_performance_evidence_missing",
        "legacy_v3_demo_model_is_development_candidate",
        "machine_model_card_is_provenance_candidate_not_final_frozen",
    }
    repository_dirty = source.get("repository_dirty") is not False
    provenance_dirty = provenance.get("git", {}).get("dirty") is not False
    repository_blocked = "repository_not_clean_frozen_commit" in blockers
    if repository_dirty != provenance_dirty:
        issues.append("technical/provenance repository dirty status mismatch")
    if repository_blocked != repository_dirty:
        issues.append("repository dirty/blocker mismatch")
    if legacy_development and "legacy_v3_demo_model_is_development_candidate" not in blockers:
        issues.append("legacy v3 development-candidate status is not reflected in technical blockers")
    machine_path = root / MACHINE_MODEL_CARD_PATH
    try:
        card = json.loads(machine_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return issues + [f"formal v4 model card missing/invalid: {exc}"]
    machine_status = status.get("machine_model_card", {})
    if not (
        card.get("schema_version") == "xa.foundation-model-card.v4"
        and machine_status.get("path") == MACHINE_MODEL_CARD_PATH
        and machine_status.get("schema_version") == "xa.foundation-model-card.v4"
        and machine_status.get("required_final_schema_version") == "xa.final-model-card.v1"
        and machine_status.get("final_frozen") is False
        and machine_status.get("development_candidate") is True
    ):
        issues.append("formal v4 candidate/final model-card status mismatch")
    if card.get("artifact", {}).get("sha256") != checkpoint_sha:
        issues.append("machine model card checkpoint identity mismatch")
    training = status.get("training_provenance", {})
    if not (
        status.get("candidate_status") == "provenance_closed_development_candidate"
        and training.get("status") == "provenance_closed_development_candidate"
        and training.get("closed") is True
        and training.get("checkpoint_sha256") == checkpoint_sha
        and training.get("model_card_schema") == "xa.foundation-model-card.v4"
        and training.get("training_command_verified") is True
        and training.get("config_verified") is True
        and training.get("split_manifest_verified") is True
        and training.get("seed") == 20260904
        and training.get("training_log_verified") is True
        and training.get("source_sha_provenance_verified") is True
        and training.get("performance_evidence") is False
    ):
        issues.append("formal v4 training provenance status is not closed or is overstated")
    issues.extend(verify_formal_v4(root))
    issues.extend(verify_research_claims(root, status))
    if mode != "final":
        if status.get("ready_for_final") is not False or status.get("status") != "incomplete":
            issues.append("draft technical release must remain incomplete")
        if not expected_current_blockers <= blockers:
            issues.append("draft technical release is missing current fail-closed blockers")
        forbidden_stale = {
            "training_command_unverified", "training_config_unverified",
            "dataset_split_manifest_unverified", "training_seeds_unverified",
            "training_logs_or_hashes_unverified", "training_source_sha_provenance_unverified",
        }
        if blockers & forbidden_stale:
            issues.append("formal v4 closed training provenance is still reported as missing")
        return issues
    if status.get("ready_for_final") is not True or status.get("status") != "ready" or blockers:
        issues.append("final package has unresolved technical release blockers")
    if card.get("schema_version") != "xa.final-model-card.v1" or machine_status.get("final_frozen") is not True:
        issues.append("final package contains only a provenance-candidate model card")
    if training.get("performance_evidence") is not True:
        issues.append("final package lacks accepted external performance evidence")
    if provenance.get("git", {}).get("dirty") is not False or source.get("repository_dirty") is not False:
        issues.append("final package is not bound to a clean frozen commit")
    return issues


def verify_tree(root: Path, allow_incomplete: bool) -> dict[str, Any]:
    issues: list[str] = []
    if not root.is_dir() or root.is_symlink():
        return {"ok": False, "issues": ["target is not a real directory"]}
    manifest_path = root / "MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "issues": [f"invalid MANIFEST.json: {exc}"]}
    mode = manifest.get("mode")
    if mode not in {"final", "internal_audit_draft"}:
        issues.append(f"invalid package mode: {mode!r}")
        mode = "invalid"
    if manifest.get("schema_version") != "xa.competition-package-manifest.v1" or manifest.get("competition_id") != "XA-202609":
        issues.append("package manifest schema/competition mismatch")
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            issues.append(f"symlink is forbidden: {path.relative_to(root)}")
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        files.append(rel)
        if safe_rel(rel) is None:
            issues.append(f"unsafe package path: {rel}")
        if not path_allowed(rel, mode):
            issues.append(f"path outside independent allowlist: {rel}")
        if path.stat().st_size > MAX_FILE_BYTES:
            issues.append(f"file exceeds size cap: {rel}")
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            except (SyntaxError, UnicodeDecodeError) as exc:
                issues.append(f"invalid Python source: {rel}: {exc}")
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                issues.append(f"invalid JSON: {rel}: {exc}")
        if path.suffix == ".pdf" and not path.read_bytes().startswith(b"%PDF-"):
            issues.append(f"invalid PDF signature: {rel}")
        for content_issue in scan_content(path, rel):
            issues.append(f"{rel}: {content_issue}")
    actual = set(files)
    presentation_status = manifest.get("presentation", {})
    if presentation_status.get("included"):
        presentation_file = root / PRESENTATION_PATH
        if (
            presentation_status.get("path") != PRESENTATION_PATH
            or not presentation_file.is_file()
            or presentation_status.get("sha256") != PRESENTATION_SHA256
            or sha256_file(presentation_file) != PRESENTATION_SHA256
        ):
            issues.append("presentation presence/path/SHA binding mismatch")
    elif PRESENTATION_PATH in actual or presentation_status.get("sha256") is not None:
        issues.append("presentation manifest says missing but a presentation/SHA is present")
    report_status = manifest.get("report_release", {})
    report_file = root / REPORT_PATH
    if not (
        report_file.is_file()
        and sha256_file(report_file) == REPORT_SHA256
        and report_status == {
            "path": REPORT_PATH,
            "sha256": REPORT_SHA256,
            "page_count": REPORT_PAGE_COUNT,
            "release_note": "SHA-locked 38-page Chinese competition manuscript",
        }
    ):
        issues.append("38-page Chinese manuscript release identity mismatch")
    required_exact = EXACT_REPOSITORY_FILES - {PRESENTATION_PATH}
    missing_required = sorted((required_exact | REQUIRED_CORE_PATHS) - actual)
    if missing_required:
        issues.append("required package files are missing: " + ", ".join(missing_required))
    manifest_rows = manifest.get("files", [])
    manifest_paths = [row.get("path") for row in manifest_rows if isinstance(row, dict)]
    if len(manifest_paths) != len(set(manifest_paths)):
        issues.append("duplicate paths in MANIFEST.json")
    expected_manifest_set = actual - {"MANIFEST.json", "CHECKSUMS.sha256"}
    if set(manifest_paths) != expected_manifest_set:
        issues.append("manifest file coverage does not equal package file set")
    for row in manifest_rows:
        rel = row.get("path", "")
        target = root / rel
        if safe_rel(rel) is None or not target.is_file():
            issues.append(f"manifest references unsafe/missing file: {rel}")
            continue
        if target.stat().st_size != row.get("bytes") or sha256_file(target) != row.get("sha256"):
            issues.append(f"manifest size/hash mismatch: {rel}")
        source_path = row.get("source_path")
        if source_path is not None and safe_rel(source_path) is None:
            issues.append(f"manifest source_path is unsafe: {source_path}")
    checksums_path = root / "CHECKSUMS.sha256"
    try:
        checksums, parse_issues = parse_checksums(checksums_path)
        issues.extend(parse_issues)
        if set(checksums) != actual - {"CHECKSUMS.sha256"}:
            issues.append("top-level checksum coverage does not equal package file set")
        for rel, digest in checksums.items():
            target = root / rel
            if not target.is_file() or sha256_file(target) != digest:
                issues.append(f"top-level checksum mismatch: {rel}")
    except OSError as exc:
        issues.append(f"missing/unreadable CHECKSUMS.sha256: {exc}")
    external_issues, _ = verify_externally_anchored_evidence(root, manifest)
    issues.extend(external_issues)
    for bundle_id in sorted(EVIDENCE_IDS):
        issues.extend(verify_snapshot(root, bundle_id))
    expected_snapshot_reports = []
    for bundle_id in EVIDENCE_SOURCES:
        snapshot_manifest = load_object(
            root / "evidence_snapshots" / bundle_id / "SNAPSHOT_MANIFEST.json",
            f"{bundle_id} snapshot manifest",
            issues,
        )
        source_rows = snapshot_manifest.get("source_inventory")
        included_rows = snapshot_manifest.get("included")
        omitted_rows = snapshot_manifest.get("omitted_large_or_log_artifacts")
        expected_snapshot_reports.append(
            {
                "bundle_id": bundle_id,
                "source_bundle": EVIDENCE_SOURCES[bundle_id][0],
                "claim_profile": EVIDENCE_SOURCES[bundle_id][1],
                "source_file_count": len(source_rows) if isinstance(source_rows, list) else -1,
                "included_file_count": len(included_rows) if isinstance(included_rows, list) else -1,
                "omitted_file_count": len(omitted_rows) if isinstance(omitted_rows, list) else -1,
            }
        )
    if manifest.get("evidence_snapshots") != expected_snapshot_reports:
        issues.append("manifest evidence-snapshot inventory mismatch")
    issues.extend(verify_sbom(root, mode == "final"))
    issues.extend(verify_authorization(root, mode))
    provenance: dict[str, Any] = {}
    try:
        provenance = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
        if provenance.get("schema_version") != "xa.package-provenance.v1" or provenance.get("mode") != mode:
            issues.append("provenance schema/mode mismatch")
        if provenance.get("git", {}).get("repository_root") != ".":
            issues.append("provenance repository root must be relative")
        manifest_by_path = {row.get("path"): row for row in manifest_rows}
        for row in provenance.get("files", []):
            packaged = manifest_by_path.get(row.get("path"))
            if packaged is None or packaged.get("sha256") != row.get("sha256"):
                issues.append(f"provenance/manifest mismatch: {row.get('path')}")
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"invalid PROVENANCE.json: {exc}")
    issues.extend(verify_technical_release(root, mode, manifest, provenance))
    if mode == "final":
        if (
            manifest.get("distributable") is not True
            or not manifest.get("presentation", {}).get("included")
            or PRESENTATION_PATH not in actual
        ):
            issues.append("final manifest is not distributable or lacks presentation")
    else:
        if manifest.get("distributable") is not False:
            issues.append("draft manifest must be non-distributable")
        if not allow_incomplete:
            issues.append("authorization gate: internal audit draft is not a final submission")
    return {
        "ok": not issues,
        "mode": mode,
        "distributable": mode == "final" and not issues,
        "file_count": len(actual),
        "issues": issues,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("target", type=Path, help="staging directory or .tar.gz archive")
    command.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="accept a technically sound INTERNAL_AUDIT_DRAFT; still reports distributable=false",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    target = args.target.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="xa202609-verify-") as temp_name:
        if target.is_file():
            root, archive_issues = inspect_archive(target, Path(temp_name))
            if root is None:
                result = {"ok": False, "mode": "unknown", "distributable": False, "issues": archive_issues}
            else:
                result = verify_tree(root, args.allow_incomplete)
                result["issues"] = archive_issues + result["issues"]
                try:
                    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
                    if root.name != manifest.get("archive_root"):
                        result["issues"].append("archive top-level root does not match MANIFEST.json")
                    if manifest.get("mode") == "internal_audit_draft":
                        if target.name != "XA-202609_INTERNAL_AUDIT_DRAFT.tar.gz":
                            result["issues"].append("internal audit draft archive has a misleading name")
                    elif manifest.get("mode") == "final":
                        authorization = json.loads(
                            (root / "authorization/SUBMISSION_AUTHORIZATION.json").read_text(encoding="utf-8")
                        )
                        if target.name != authorization.get("archive_name"):
                            result["issues"].append("archive filename does not match human authorization")
                except (OSError, json.JSONDecodeError) as exc:
                    result["issues"].append(f"cannot verify archive name/root binding: {exc}")
                result["ok"] = not result["issues"]
        else:
            result = verify_tree(target, args.allow_incomplete)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
