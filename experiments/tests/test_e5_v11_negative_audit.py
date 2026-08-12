from __future__ import annotations

import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from src.contracts.artifacts import ArtifactBundleWriter, verify_bundle
from src.contracts.codec import (
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_file,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = (
    PROJECT_ROOT
    / "results"
    / "xa202609"
    / "20260812-e5-v11-ascon-primary-present-secondary-v1-s940000"
)
PRODUCER_PATH = PROJECT_ROOT / "analysis" / "audit_e5_v11_negative_bundle.py"
VERIFIER_PATH = PROJECT_ROOT / "analysis" / "verify_e5_v11_negative_audit_bundle.py"
PORTABLE_AUDIT_ROOT = Path(
    os.environ.get(
        "XA_E5_PORTABLE_AUDIT_ROOT",
        str(
            PROJECT_ROOT
            / "results"
            / "xa202609"
            / "20260812-e5-v11-portable-negative-audit-v2-s950000"
        ),
    )
).resolve()
LEGACY_V1_AUDIT_ROOT = (
    PROJECT_ROOT
    / "results"
    / "xa202609"
    / "20260812-e5-v11-negative-audit-v1-s950000"
)
LEGACY_V1_AUDIT_FILE_SHA256 = {
    "artifacts.manifest.json": "17bcaf5bebf9c52ad9595fb1011d485916f48967674d69d52b56c92c0beb450e",
    "checksums.sha256": "e01837b340d5d5a33d4a21a57a1d807ff83aacd084997bb606930dfd77c2299f",
    "events.jsonl": "fee08463e754f304274fdc654870b81fdfb8680c262783d9ec23961bbd854def",
    "raw.jsonl": "7e183e4d1c6d2c06cd53799af5a07569d245a1509fe5a4e9c0cdc2fa61a2e34b",
    "run.json": "dec952901cb4cfe862f568f75aa9fa5f581ca4cd4126b4f23b97be6eab0e4baa",
    "stderr.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "stdout.log": "fb086e3731589623a59d9be1a9745b96b759af357ad9f2cd22514de3c0993cae",
    "summary.json": "55808082038a598d0fc418d50bda89b03cf1485c1373e106f9a2b1044d867916",
    "verifier.json": "43b16f784de9f2c72faa65552e049a08822a64ed451437cb6446c110f3722956",
}
LEGACY_V2_AUDIT_FILE_SHA256 = {
    "artifacts.manifest.json": "973c536fedb5e5546ac81ab989d3b496cce12e0a74d4effa844ce39c5e21f6d5",
    "checksums.sha256": "eb01d5b49ddde7a577bfca094df28bb550da8b6be5a3f479a58b5e95e34c83c8",
    "events.jsonl": "3669e1cc503e3bdb69b074554b11af04da3c5e2bead4ccbcc3ce096a1fbf4b2c",
    "raw.jsonl": "b4707deca496f1f538403d9b2d190cddcbb0a667c5864f83bc3ae9097ec350ba",
    "run.json": "8a588d3e873559cf40c84a1e409f821a77128360f9194406ed85eaac5f4e2751",
    "stderr.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "stdout.log": "7830a4b5a18bf3b4e874e60de02abb56ad461c999dab1a70582aa843de4cd264",
    "summary.json": "65f1ab73d12bf73dc26f7192359b7cca7847ea0c8eddd542e60cf740743d758a",
    "verifier.json": "57d7ba4cdcf16d9efcd20b70837c49c7e0a6dbc6b7cd1fb9cd6fc30096ca30aa",
}


def _load(name: str, path: Path):
    os.environ["XA_E5_PROJECT_ROOT"] = str(PROJECT_ROOT)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verifier():
    return _load("_e5_v11_negative_audit_verifier_test", VERIFIER_PATH)


@pytest.fixture(scope="module")
def producer():
    return _load("_e5_v11_negative_audit_producer_test", PRODUCER_PATH)


@pytest.fixture(scope="module")
def source_context(verifier):
    context = verifier._authenticate_source(SOURCE_ROOT)
    yield context
    # Preserve the preflight/seal lazy-import invariant for unrelated tests
    # that may execute later in the same pytest process.
    sys.modules.pop("src.benchmarks.crypto_oracles", None)


@pytest.fixture(scope="module")
def audit_bundle():
    assert PORTABLE_AUDIT_ROOT.is_dir()
    return PORTABLE_AUDIT_ROOT


def _resign_bundle(bundle: Path) -> None:
    manifest_path = bundle / "artifacts.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["artifacts"]:
        path = bundle / record["relative_path"]
        record["size_bytes"] = path.stat().st_size
        record["sha256"] = sha256_file(path)
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    names = [record["relative_path"] for record in manifest["artifacts"]]
    names.append("artifacts.manifest.json")
    (bundle / "checksums.sha256").write_text(
        "".join(f"{sha256_file(bundle / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def _audit_mutated_row(verifier, source_context, mutation):
    return _audit_selected_row(
        verifier,
        source_context,
        mutation,
        arm="v4_historical_greedy",
    )


def _audit_selected_row(verifier, source_context, mutation, *, arm):
    row = next(
        copy.deepcopy(item)
        for item in source_context["rows"]
        if item["family"] == "PRESENT"
        and item["output_bit"] == 1
        and item["solver_seed"] == 1
        and item["arm"] == arm
    )
    mutation(row)
    return verifier.audit_one_source_row_portable(
        row,
        ordinal=60,
        config=source_context["config"],
        weights=source_context["weights"],
        checkpoint=source_context["checkpoint"],
        coordinates=source_context["coordinates"],
    )


def _audit_selected_row_v3(verifier, source_context, mutation, *, arm):
    row = next(
        copy.deepcopy(item)
        for item in source_context["rows"]
        if item["family"] == "PRESENT"
        and item["output_bit"] == 1
        and item["solver_seed"] == 1
        and item["arm"] == arm
    )
    mutation(row)
    return verifier.audit_one_source_row_portable_v3(
        row,
        ordinal=60,
        config=source_context["config"],
        weights=source_context["weights"],
        checkpoint=source_context["checkpoint"],
        coordinates=source_context["coordinates"],
    )


def test_verifier_import_is_independent_of_producer() -> None:
    code = f"""
import importlib.util, os, sys
os.environ['XA_E5_PROJECT_ROOT'] = {str(PROJECT_ROOT)!r}
spec = importlib.util.spec_from_file_location('_independent_negative_audit', {str(VERIFIER_PATH)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert 'analysis.audit_e5_v11_negative_bundle' not in sys.modules
assert 'src.benchmarks.crypto_oracles' not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert completed.returncode == 0


def test_original_bundle_and_frozen_contract_are_hard_bound_and_unchanged(verifier) -> None:
    records = verifier._snapshot_records(SOURCE_ROOT)
    assert verifier._snapshot_sha(records) == verifier.SOURCE_SNAPSHOT_SHA256
    assert {name: digest for name, _size, digest in records} == verifier.SOURCE_FILE_SHA256
    assert sha256_file(PROJECT_ROOT / "scripts" / "verify_e5_external_crypto_holdout_bundle.py") == (
        verifier.FROZEN_VERIFIER_SHA256
    )
    assert sha256_file(
        PROJECT_ROOT / "configs" / "xa202609" / "e5_external_crypto_holdout_v1.protocol.lock.json"
    ) == verifier.STATIC_LOCK_FILE_SHA256


def test_legacy_v1_audit_bundle_bytes_remain_unchanged(verifier) -> None:
    assert {path.name for path in LEGACY_V1_AUDIT_ROOT.iterdir()} == verifier.EXPECTED_FILES
    assert {
        name: sha256_file(LEGACY_V1_AUDIT_ROOT / name)
        for name in sorted(LEGACY_V1_AUDIT_FILE_SHA256)
    } == LEGACY_V1_AUDIT_FILE_SHA256
    legacy_run = json.loads(
        (LEGACY_V1_AUDIT_ROOT / "run.json").read_text(encoding="utf-8")
    )
    assert legacy_run["producer_sources"] == verifier.LEGACY_V1_PRODUCER_SOURCE_BINDING


def test_legacy_v2_audit_bundle_bytes_and_historical_sources_remain_unchanged(
    audit_bundle, verifier
) -> None:
    assert {path.name for path in audit_bundle.iterdir()} == verifier.EXPECTED_FILES
    assert {
        name: sha256_file(audit_bundle / name)
        for name in sorted(LEGACY_V2_AUDIT_FILE_SHA256)
    } == LEGACY_V2_AUDIT_FILE_SHA256
    run = json.loads((audit_bundle / "run.json").read_text(encoding="utf-8"))
    assert run["producer_sources"] == verifier.LEGACY_V2_PRODUCER_SOURCE_BINDING
    report = verifier.verify_portable_audit_bundle(audit_bundle)
    assert report["ok"] is True, report["errors"]
    assert len(report["checks"]) == 20


def test_portable_recomputation_is_90_of_90_but_preserves_protocol_failure(verifier) -> None:
    result = verifier.recompute_source_portable_audit(SOURCE_ROOT)
    assert result["counts"] == {
        "row_count": 90,
        "portable_search_plan_scheduler_reconstructed": 90,
        "logical_semantics_native_endpoint_reconstructed": 90,
        "frozen_strict_search_passed": 60,
        "frozen_strict_search_failed": 30,
        "frozen_strict_native_passed": 0,
        "frozen_strict_native_failed": 90,
        "degenerate_rows": 60,
        "schedulable_rows": 30,
        "degenerate_groups": 12,
        "schedulable_groups": 6,
        "portable_float_path_count": 34,
        "portable_float_value_count": 1506,
        "derived_fingerprint_path_count": 4,
        "derived_fingerprint_value_count": 192,
    }
    assert result["elapsed_field_counts"] == verifier.EXPECTED_ELAPSED_COUNTS
    assert result["json_array_field_counts"] == verifier.EXPECTED_ARRAY_COUNTS
    assert result["family_schedulable_group_counts"] == {"ASCON": 0, "PRESENT": 6}
    assert result["each_family_has_schedulable_activity"] is False
    assert result["reference_runtime_build"] == verifier.REFERENCE_RUNTIME_BUILD
    assert result["runtime_build"]["torch_git_version"]
    assert isinstance(result["runtime_matches_reference"], bool)


def test_generated_bundle_is_exact_nine_files_and_independently_valid(
    audit_bundle, verifier
) -> None:
    assert {path.name for path in audit_bundle.iterdir()} == verifier.EXPECTED_FILES
    generic = verify_bundle(audit_bundle, required_roles=verifier.REQUIRED_ROLES)
    assert generic.ok, generic.errors
    report = verifier.verify_portable_audit_bundle(audit_bundle)
    assert report["ok"] is True, report["errors"]
    assert report["portable_audit_evidence_ok"] is True
    assert report["audit_completed"] is True
    assert report["protocol_acceptance"] is False
    assert report["experiment_completed"] is False
    assert report["reconstruction_counts"]["portable_search_plan_scheduler_reconstructed"] == 90
    assert report["reference_runtime_build"] == verifier.REFERENCE_RUNTIME_BUILD
    assert report["runtime_build"]["torch_git_version"]
    assert isinstance(report["runtime_matches_reference"], bool)
    summary = json.loads((audit_bundle / "summary.json").read_text(encoding="utf-8"))
    assert summary["row_reconstruction_complete"] is True
    assert summary["family_schedulable_group_counts"] == {"ASCON": 0, "PRESENT": 6}
    assert summary["each_family_has_schedulable_activity"] is False
    assert summary["protocol_acceptance"] is False
    assert summary["experiment_completed"] is False
    assert summary["performance_claim_supported"] is False
    assert summary["stored_historical_floats_resigned_by_replay"] is False


def test_portable_v3_producer_is_reference_only_but_verifier_is_cross_build(
    tmp_path, producer, verifier
) -> None:
    output = tmp_path / "portable-producer-probe-v3"
    runtime = verifier.runtime_build_fingerprint_v2()
    if verifier.runtime_matches_reference_v2(
        runtime, verifier.REFERENCE_RUNTIME_BUILD_V2
    ):
        built = producer.build_portable_audit_bundle_v3(SOURCE_ROOT, output)
        report = verifier.verify_portable_audit_bundle_v3(built)
        assert report["ok"] is True, report["errors"]
        assert report["runtime_matches_reference"] is True
        assert len(report["checks"]) == 20
    else:
        with pytest.raises(RuntimeError, match="reference"):
            producer.build_portable_audit_bundle_v3(SOURCE_ROOT, output)


def test_scheduler_allowlist_accepts_only_exact_fields_and_scopes(verifier) -> None:
    stored = {
        "method": "greedy",
        "diagnostics": {
            "selection_order": [0, 4, 3],
            "execution_feedback_elapsed_s": 1e-7,
            "total_elapsed_s": 2e-5,
            "utility_elapsed_s": 3e-5,
            "stable": [1, 2],
        },
    }
    rebuilt = {
        "method": "greedy",
        "diagnostics": {
            "selection_order": (0, 4, 3),
            "execution_feedback_elapsed_s": 8e-7,
            "total_elapsed_s": 9e-5,
            "utility_elapsed_s": 1e-4,
            "stable": [1, 2],
        },
    }
    projection, elapsed, arrays, strict = verifier._scheduler_projection(stored, rebuilt)
    assert strict is False
    assert elapsed == [
        "scheduler.diagnostics.execution_feedback_elapsed_s",
        "scheduler.diagnostics.total_elapsed_s",
        "scheduler.diagnostics.utility_elapsed_s",
    ]
    assert arrays == ["scheduler.diagnostics.selection_order"]
    assert projection["diagnostics"]["selection_order"] == [0, 4, 3]

    for bad in (
        lambda value: value["diagnostics"].__setitem__("total_elapsed_s", -1.0),
        lambda value: value["diagnostics"].__setitem__("total_elapsed_s", math.inf),
        lambda value: value["diagnostics"].__setitem__("total_elapsed_s", "0.1"),
        lambda value: value["diagnostics"].__setitem__("new_elapsed_s", 0.0),
        lambda value: value["diagnostics"].__setitem__("selection_order", [0, 3, 4]),
        lambda value: value["diagnostics"].pop("utility_elapsed_s"),
    ):
        tampered = copy.deepcopy(stored)
        bad(tampered)
        with pytest.raises(verifier.AuditMismatch):
            verifier._scheduler_projection(tampered, rebuilt)

    # A list/tuple relaxation at any unregistered path remains forbidden.
    rebuilt_extra_array = copy.deepcopy(rebuilt)
    rebuilt_extra_array["diagnostics"]["stable"] = (1, 2)
    with pytest.raises(verifier.AuditMismatch):
        verifier._scheduler_projection(stored, rebuilt_extra_array)


def test_portable_v2_contract_is_explicit_and_does_not_replace_v1(verifier) -> None:
    contract = verifier.portable_normalization_contract()
    assert contract["schema_version"] == "xa.e5-v11-portable-normalization.v2"
    assert contract["relative_tolerance"] == 1e-6
    assert contract["absolute_tolerance"] == 5e-6
    assert contract["historical_v1_contract_changed"] is False
    assert contract["portable_float_path_allowlist"] == sorted(
        verifier.PORTABLE_FLOAT_PATHS
    )
    assert verifier.normalization_contract()["schema_version"].endswith(".v1")


def test_portable_v3_contract_versions_nested_binding_without_rewriting_v2(
    verifier,
) -> None:
    v2 = verifier.portable_normalization_contract()
    v3 = verifier.portable_normalization_contract_v3()
    assert v2["schema_version"] == "xa.e5-v11-portable-normalization.v2"
    assert "nested_feedback_binding" not in v2
    assert v3["schema_version"] == "xa.e5-v11-portable-normalization.v3"
    assert "nested" in v3["derived_fingerprint_rule"]
    assert v3["relative_tolerance"] == v2["relative_tolerance"] == 1e-6
    assert v3["absolute_tolerance"] == v2["absolute_tolerance"] == 5e-6
    assert (
        verifier.PORTABLE_V3_NORMALIZATION_CONTRACT_SHA256
        != verifier.PORTABLE_NORMALIZATION_CONTRACT_SHA256
    )


def test_runtime_v2_fingerprint_freezes_complete_path_independent_subset(
    verifier,
) -> None:
    runtime = verifier.runtime_build_fingerprint_v2()
    assert verifier.runtime_build_fingerprint_valid_v2(runtime)
    subset = verifier.runtime_build_frozen_subset_v2(runtime)
    assert subset["python"]["cache_tag"]
    assert subset["python"]["soabi"]
    assert subset["torch"]["torch_c_sha256"]
    assert subset["torch"]["binary_inventory"]
    assert subset["numpy"]["build_config_sha256"]
    assert subset["scipy"]["build_config_sha256"]
    assert "package_root" not in subset["torch"]
    tampered = copy.deepcopy(runtime)
    tampered["torch"]["torch_c"]["sha256"] = "0" * 64
    differences = verifier.runtime_build_differences_v2(tampered, runtime)
    assert any(item["field"] == "torch.torch_c_sha256" for item in differences)
    assert verifier.runtime_matches_reference_v2(tampered, runtime) is False
    malformed = copy.deepcopy(runtime)
    malformed["python"].pop("cache_tag")
    assert verifier.runtime_build_fingerprint_valid_v2(malformed) is False


def test_portable_float_isclose_boundary_and_nonfinite_fail_closed(verifier) -> None:
    within = verifier._new_portable_stats()
    projection = verifier._portable_project_and_compare(
        0.5,
        0.500004,
        path="candidate_pool.utilities[0]",
        stats=within,
    )
    assert projection == {"portable_float_path": "candidate_pool.utilities[*]"}
    assert within["portable_float_value_count"] == 1

    for rebuilt in (0.51, math.nan, math.inf, -math.inf):
        with pytest.raises(verifier.AuditMismatch):
            verifier._portable_project_and_compare(
                0.5,
                rebuilt,
                path="candidate_pool.utilities[0]",
                stats=verifier._new_portable_stats(),
            )
    for stored in (math.nan, math.inf, -math.inf):
        with pytest.raises(verifier.AuditMismatch):
            verifier._portable_project_and_compare(
                stored,
                0.5,
                path="candidate_pool.utilities[0]",
                stats=verifier._new_portable_stats(),
            )

    # Unregistered floats and discrete QUBO index columns remain bit-exact.
    with pytest.raises(verifier.AuditMismatch):
        verifier._portable_project_and_compare(
            61.15,
            61.150000000001,
            path="scheduler.diagnostics.direct_score",
            stats=verifier._new_portable_stats(),
        )
    with pytest.raises(verifier.AuditMismatch):
        verifier._portable_project_and_compare(
            0,
            1,
            path="scheduler.diagnostics.qubo.quadratic[0][0]",
            stats=verifier._new_portable_stats(),
        )


def test_portable_row_accepts_only_within_tolerance_neural_prior(
    verifier, source_context
) -> None:
    def within(row):
        row["candidate_pool"]["action_signatures"][1]["prior"] += 1e-7
        row["candidate_pool_sha256"] = sha256_bytes(
            canonical_json_bytes(row["candidate_pool"])
        )

    record = _audit_mutated_row(verifier, source_context, within)
    assert record["search_plan_scheduler_reconstruction"]["ok"] is True

    def over(row):
        row["candidate_pool"]["action_signatures"][1]["prior"] += 1e-3
        row["candidate_pool_sha256"] = sha256_bytes(
            canonical_json_bytes(row["candidate_pool"])
        )

    record = _audit_mutated_row(verifier, source_context, over)
    assert record["search_plan_scheduler_reconstruction"]["ok"] is False
    assert "tolerance exceeded" in record["search_plan_scheduler_reconstruction"]["error"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row["candidate_pool"]["action_signatures"][0].__setitem__(
            "factor", row["candidate_pool"]["action_signatures"][0]["factor"] + 1
        ),
        lambda row: row["candidate_pool"].__setitem__(
            "action_signatures",
            list(reversed(row["candidate_pool"]["action_signatures"])),
        ),
    ],
)
def test_portable_candidate_core_and_order_tamper_fail(
    verifier, source_context, mutation
) -> None:
    def mutate_and_resign_pool(row):
        mutation(row)
        row["candidate_pool_sha256"] = sha256_bytes(
            canonical_json_bytes(row["candidate_pool"])
        )

    record = _audit_mutated_row(verifier, source_context, mutate_and_resign_pool)
    assert record["search_plan_scheduler_reconstruction"]["ok"] is False


def test_portable_stored_pool_and_derived_action_sha_tamper_fail(
    verifier, source_context
) -> None:
    pool_sha = _audit_mutated_row(
        verifier,
        source_context,
        lambda row: row.__setitem__("candidate_pool_sha256", "0" * 64),
    )
    assert pool_sha["search_plan_scheduler_reconstruction"]["ok"] is False
    assert "stored candidate pool SHA mismatch" in pool_sha[
        "search_plan_scheduler_reconstruction"
    ]["error"]

    action_sha = _audit_selected_row(
        verifier,
        source_context,
        lambda row: row["execution_feedback"]["diagnostics"][
            "candidate_action_sha256"
        ].__setitem__(0, "0" * 64),
        arm="v4_execution_aware_greedy",
    )
    assert action_sha["search_plan_scheduler_reconstruction"]["ok"] is False
    assert "candidate action SHA mismatch" in action_sha[
        "search_plan_scheduler_reconstruction"
    ]["error"]


@pytest.mark.parametrize("nested_field", ["candidate_list", "candidate_record"])
def test_portable_v3_nested_feedback_sha_tamper_fails_even_after_other_resigning(
    verifier, source_context, nested_field
) -> None:
    def attack(row):
        signature = row["candidate_pool"]["action_signatures"][0]
        signature["prior"] += 1e-7
        row["candidate_pool_sha256"] = sha256_bytes(
            canonical_json_bytes(row["candidate_pool"])
        )
        resigned = sha256_bytes(canonical_json_bytes(signature))
        top = row["execution_feedback"]["diagnostics"]
        top["candidate_action_sha256"][0] = resigned
        top["candidates"][0]["action_sha256"] = resigned
        nested = row["scheduler"]["diagnostics"]["execution_feedback"][
            "diagnostics"
        ]
        if nested_field == "candidate_list":
            nested["candidate_action_sha256"][0] = "0" * 64
        else:
            nested["candidates"][0]["action_sha256"] = "0" * 64

    historical = _audit_selected_row(
        verifier,
        source_context,
        attack,
        arm="v4_execution_aware_greedy",
    )
    assert historical["search_plan_scheduler_reconstruction"]["ok"] is True

    fail_closed = _audit_selected_row_v3(
        verifier,
        source_context,
        attack,
        arm="v4_execution_aware_greedy",
    )
    assert fail_closed["search_plan_scheduler_reconstruction"]["ok"] is False
    assert "candidate" in fail_closed["search_plan_scheduler_reconstruction"][
        "error"
    ]
    assert "SHA mismatch" in fail_closed["search_plan_scheduler_reconstruction"][
        "error"
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row["scheduler"]["diagnostics"]["qaoa"]["bitstring"].__setitem__(
            0, 1 - row["scheduler"]["diagnostics"]["qaoa"]["bitstring"][0]
        ),
        lambda row: row["scheduler"]["diagnostics"]["qaoa"]["counts"].__setitem__(
            "00000", row["scheduler"]["diagnostics"]["qaoa"]["counts"]["00000"] + 1
        ),
        lambda row: row["scheduler"]["diagnostics"].__setitem__(
            "qaoa_succeeded", False
        ),
    ],
)
def test_portable_selection_and_qaoa_discrete_tamper_fail(
    verifier, source_context, mutation
) -> None:
    record = _audit_selected_row(
        verifier,
        source_context,
        mutation,
        arm="v4_historical_qaoa_shot",
    )
    assert record["search_plan_scheduler_reconstruction"]["ok"] is False


def test_portable_greedy_selection_order_tamper_fails(
    verifier, source_context
) -> None:
    record = _audit_mutated_row(
        verifier,
        source_context,
        lambda row: row["scheduler"]["diagnostics"]["selection_order"].__setitem__(
            0, row["scheduler"]["diagnostics"]["selection_order"][1]
        ),
    )
    assert record["search_plan_scheduler_reconstruction"]["ok"] is False


@pytest.mark.parametrize(
    ("mutation", "failed_track"),
    [
        (
            lambda row: (
                row["candidate_pool"]["utilities"].__setitem__(
                    0, row["candidate_pool"]["utilities"][0] + 0.25
                ),
                row.__setitem__(
                    "candidate_pool_sha256",
                    sha256_bytes(canonical_json_bytes(row["candidate_pool"])),
                ),
            ),
            "search",
        ),
        (
            lambda row: row["raw_scheduler_utilities"].__setitem__(
                0, row["raw_scheduler_utilities"][0] + 0.125
            ),
            "search",
        ),
        (
            lambda row: row["scheduler"].__setitem__(
                "selected_indices", list(reversed(row["scheduler"]["selected_indices"]))
            ),
            "search",
        ),
        (lambda row: row.__setitem__("policy_cache_misses", row["policy_cache_misses"] + 1), "search"),
        (
            lambda row: row["learned_value_stats"].__setitem__(
                "value_calls", row["learned_value_stats"]["value_calls"] + 1
            ),
            "search",
        ),
        (lambda row: row.__setitem__("logical_resource_score", row["logical_resource_score"] + 1.0), "search"),
        (lambda row: row.__setitem__("plan_trace_sha256", "0" * 64), "search"),
        (
            lambda row: (
                row["native"]["initial_logical_to_physical"].__setitem__(
                    0, row["native"]["initial_logical_to_physical"][1]
                ),
                row.__setitem__(
                    "native_record_sha256",
                    sha256_bytes(canonical_json_bytes(row["native"])),
                ),
            ),
            "native",
        ),
        (
            lambda row: (
                row["primary_endpoint"].__setitem__(
                    "value", row["primary_endpoint"]["value"] + 1
                ),
                row.__setitem__(
                    "primary_endpoint_sha256",
                    sha256_bytes(canonical_json_bytes(row["primary_endpoint"])),
                ),
            ),
            "native",
        ),
    ],
)
def test_scientific_field_tampering_fails_reconstruction(
    verifier, source_context, mutation, failed_track
) -> None:
    record = _audit_mutated_row(verifier, source_context, mutation)
    if failed_track == "search":
        assert record["search_plan_scheduler_reconstruction"]["ok"] is False
    else:
        assert record["logical_semantics_native_endpoint_reconstruction"]["ok"] is False


def test_resigned_summary_tamper_cannot_fool_independent_verifier(
    tmp_path, audit_bundle, verifier
) -> None:
    tampered = tmp_path / audit_bundle.name
    shutil.copytree(audit_bundle, tampered)
    summary_path = tampered / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["protocol_acceptance"] = True
    summary["experiment_completed"] = True
    summary["counts"]["row_count"] += 1
    summary_path.write_bytes(canonical_json_bytes(summary))
    _resign_bundle(tampered)
    assert verify_bundle(tampered, required_roles=verifier.REQUIRED_ROLES).ok
    report = verifier.verify_portable_audit_bundle(tampered)
    assert report["ok"] is False
    assert report["checks"]["portable_audit_summary_independently_recomputed"] is False


def test_resigned_raw_tamper_cannot_fool_independent_verifier(
    tmp_path, audit_bundle, verifier
) -> None:
    tampered = tmp_path / audit_bundle.name
    shutil.copytree(audit_bundle, tampered)
    raw_path = tampered / "raw.jsonl"
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["source_row_sha256"] = "0" * 64
    raw_path.write_text(
        "".join(canonical_json_text(row) + "\n" for row in rows), encoding="utf-8"
    )
    _resign_bundle(tampered)
    assert verify_bundle(tampered, required_roles=verifier.REQUIRED_ROLES).ok
    report = verifier.verify_portable_audit_bundle(tampered)
    assert report["ok"] is False
    assert report["checks"]["portable_audit_raw_rows_independently_recomputed"] is False


def test_resigned_stored_source_sha_tamper_cannot_fool_portable_verifier(
    tmp_path, audit_bundle, verifier
) -> None:
    tampered = tmp_path / audit_bundle.name
    shutil.copytree(audit_bundle, tampered)
    run_path = tampered / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["source_bundle"]["raw_sha256"] = "0" * 64
    run_path.write_bytes(canonical_json_bytes(run))
    _resign_bundle(tampered)
    assert verify_bundle(tampered, required_roles=verifier.REQUIRED_ROLES).ok
    report = verifier.verify_portable_audit_bundle(tampered)
    assert report["ok"] is False
    assert report["checks"]["portable_audit_run_source_binding_recomputed"] is False


def _write_synthetic_fresh_validation_bundle(path, verifier):
    run_id = path.name
    runtime = copy.deepcopy(verifier.REFERENCE_RUNTIME_BUILD_V2)
    runtime["python"]["executable"]["sha256"] = "0" * 64
    assert verifier.runtime_build_fingerprint_valid_v2(runtime)
    science = {
        "run_id": verifier.PORTABLE_V3_RUN_ID,
        "snapshot_algorithm": "sha256(compact-json(sorted([name,size,sha256])))",
        "snapshot_sha256": "1" * 64,
        "snapshot_files": [
            {"path": "run.json", "size_bytes": 1, "sha256": "2" * 64}
        ],
    }
    requirements_path = PROJECT_ROOT / "environment" / "requirements" / "dev.txt"
    requirements = {
        "path": "environment/requirements/dev.txt",
        "sha256": sha256_file(requirements_path),
        "bytes": requirements_path.stat().st_size,
    }
    portable_report = {
        "schema_version": verifier.PORTABLE_V3_REPORT_SCHEMA,
        "ok": True,
        "checks": {f"check_{index}": True for index in range(20)},
        "runtime_build": runtime,
        "runtime_matches_reference": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
    }
    outputs = {
        "pip_freeze": (
            "numpy==2.4.6\nscipy==1.17.1\nPuLP==3.3.1\n"
            "torch==2.12.0\npytest==9.0.3\n"
        ),
        "pip_check": "No broken requirements found.\n",
        "targeted_e5": "40 passed in 1.00s\n",
        "full_pytest": "370 passed in 2.00s\n",
        "legacy_smoke": "smoke ok\n",
        "default_clean_install": json.dumps({"ok": True}, sort_keys=True) + "\n",
        "portable_v3_verifier": json.dumps(portable_report, sort_keys=True) + "\n",
    }

    def stream(text):
        payload = text.encode("utf-8")
        return {"text": text, "bytes": len(payload), "sha256": sha256_bytes(payload)}

    rows = []
    for ordinal, (command_id, argv) in enumerate(
        verifier.FRESH_VALIDATION_COMMAND_CONTRACT
    ):
        rows.append(
            {
                "schema_version": verifier.FRESH_VALIDATION_ROW_SCHEMA,
                "ordinal": ordinal,
                "command_id": command_id,
                "argv": list(argv),
                "exit_code": 0,
                "duration_seconds": 0.1 + ordinal * 0.01,
                "stdout": stream(outputs[command_id]),
                "stderr": stream(""),
                "success": True,
            }
        )
    command_contract = [
        {"command_id": command_id, "argv": list(argv)}
        for command_id, argv in verifier.FRESH_VALIDATION_COMMAND_CONTRACT
    ]
    run = {
        "schema_version": verifier.FRESH_VALIDATION_RUN_SCHEMA,
        "track": verifier.FRESH_VALIDATION_TRACK,
        "run_id": run_id,
        "status": "complete_fresh_validation",
        "created_at_utc": "2026-08-12T00:00:00Z",
        "software_validation_ok": True,
        "scientific_evidence": False,
        "hardware_execution": False,
        "performance_claim_supported": False,
        "protocol_acceptance": False,
        "experiment_completed": False,
        "requirements": requirements,
        "scientific_bundle": science,
        "fresh_runtime_build": runtime,
        "fresh_runtime_matches_reference": False,
        "producer_sources": verifier._producer_source_binding(),
        "command_contract": command_contract,
        "expected_artifacts": sorted(verifier.EXPECTED_FILES),
    }
    summary = verifier.expected_fresh_validation_summary(
        run_id,
        rows,
        requirements_binding=requirements,
        scientific_bundle_binding=science,
        fresh_runtime_build=runtime,
    )
    declared = verifier.expected_fresh_validation_declared_verifier(run_id)
    events = [
        {"event": "fresh_validation_started", "run_id": run_id},
        {"event": "portable_v3_scientific_bundle_bound", "run_id": run_id},
        {"event": "fresh_validation_completed", "run_id": run_id},
    ]
    writer = ArtifactBundleWriter(path)
    writer.add_json("run", "run.json", run)
    writer.add_text(
        "raw",
        "raw.jsonl",
        "".join(canonical_json_text(row) + "\n" for row in rows),
        "application/x-ndjson",
    )
    writer.add_json("summary", "summary.json", summary)
    writer.add_json("verifier", "verifier.json", declared)
    writer.add_text(
        "events",
        "events.jsonl",
        "".join(canonical_json_text(event) + "\n" for event in events),
        "application/x-ndjson",
    )
    writer.add_text(
        "stdout",
        "stdout.log",
        (
            "Fresh-validation command evidence authenticated: 7/7 historical "
            "commands exited 0; the v3 scientific bundle was independently "
            "recomputed.\n"
        ),
    )
    writer.add_text("stderr", "stderr.log", "")
    writer.finalize(bundle_metadata={"run_id": run_id})
    return science


def test_fresh_validation_bundle_verifier_and_tamper_boundaries(
    tmp_path, monkeypatch, verifier
) -> None:
    bundle = tmp_path / "synthetic-fresh-validation"
    science = _write_synthetic_fresh_validation_bundle(bundle, verifier)
    monkeypatch.setattr(verifier, "_directory_snapshot_binding", lambda _root: science)
    monkeypatch.setattr(
        verifier,
        "verify_portable_audit_bundle_v3",
        lambda _root: {
            "ok": True,
            "checks": {f"check_{index}": True for index in range(20)},
            "protocol_acceptance": False,
            "experiment_completed": False,
        },
    )
    baseline = verifier.verify_fresh_validation_bundle(bundle)
    assert baseline["ok"] is True, baseline["errors"]
    assert baseline["historical_commands_independently_rerun"] is False
    assert baseline["scientific_bundle_independently_recomputed"] is True

    runtime_tamper = tmp_path / "runtime-tamper"
    shutil.copytree(bundle, runtime_tamper)
    run_path = runtime_tamper / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["fresh_runtime_build"]["torch"]["torch_c"]["sha256"] = "f" * 64
    run_path.write_bytes(canonical_json_bytes(run))
    _resign_bundle(runtime_tamper)
    report = verifier.verify_fresh_validation_bundle(runtime_tamper)
    assert report["ok"] is False
    assert report["checks"][
        "fresh_validation_full_runtime_fingerprint_and_v3_stdout_bound"
    ] is False

    stream_tamper = tmp_path / "stream-tamper"
    shutil.copytree(bundle, stream_tamper)
    raw_path = stream_tamper / "raw.jsonl"
    rows = [json.loads(line) for line in raw_path.read_text().splitlines()]
    text = "attacker claims pip check passed\n"
    rows[1]["stdout"] = {
        "text": text,
        "bytes": len(text.encode()),
        "sha256": sha256_bytes(text.encode()),
    }
    raw_path.write_text(
        "".join(canonical_json_text(row) + "\n" for row in rows), encoding="utf-8"
    )
    _resign_bundle(stream_tamper)
    report = verifier.verify_fresh_validation_bundle(stream_tamper)
    assert report["ok"] is False
    assert report["checks"]["fresh_validation_recorded_command_semantics"] is False

    science_tamper = tmp_path / "science-tamper"
    shutil.copytree(bundle, science_tamper)
    run_path = science_tamper / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["scientific_bundle"]["snapshot_sha256"] = "0" * 64
    run_path.write_bytes(canonical_json_bytes(run))
    _resign_bundle(science_tamper)
    report = verifier.verify_fresh_validation_bundle(science_tamper)
    assert report["ok"] is False
    assert report["checks"][
        "fresh_validation_scientific_bundle_snapshot_bound"
    ] is False


def test_cli_unknown_schema_fails_closed(tmp_path, verifier) -> None:
    bundle = tmp_path / "unknown-schema"
    bundle.mkdir()
    (bundle / "run.json").write_text('{"schema_version":"attacker.v999"}')
    completed = subprocess.run(
        [sys.executable, str(VERIFIER_PATH), str(bundle)],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["ok"] is False
    assert report["checks"] == {"known_run_schema": False}


def test_original_bundle_snapshot_remains_unchanged_after_all_audits(verifier) -> None:
    records = verifier._snapshot_records(SOURCE_ROOT)
    assert verifier._snapshot_sha(records) == verifier.SOURCE_SNAPSHOT_SHA256
