from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


DRAFT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(os.environ.get("XA_E5_PROJECT_ROOT", DRAFT_ROOT)).resolve()
RUNNER_PATH = DRAFT_ROOT / "scripts" / "run_e5_external_crypto_holdout.py"
VERIFIER_PATH = DRAFT_ROOT / "scripts" / "verify_e5_external_crypto_holdout_bundle.py"
CONFIG_PATH = DRAFT_ROOT / "configs" / "xa202609" / "e5_external_crypto_holdout_v1.json"
LOCK_PATH = (
    DRAFT_ROOT
    / "configs"
    / "xa202609"
    / "e5_external_crypto_holdout_v1.protocol.lock.json"
)


def _load_module(name: str, path: Path):
    os.environ["XA_E5_PROJECT_ROOT"] = str(PROJECT_ROOT)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner():
    return _load_module("_e5_runner_contract_test", RUNNER_PATH)


@pytest.fixture(scope="module")
def verifier():
    return _load_module("_e5_verifier_compute_contract_test", VERIFIER_PATH)


def _config(runner):
    return runner.load_config(CONFIG_PATH)


def test_import_and_config_validation_do_not_release_holdouts() -> None:
    code = f"""
import importlib.util, os, sys
os.environ['XA_E5_PROJECT_ROOT'] = {str(PROJECT_ROOT)!r}
spec = importlib.util.spec_from_file_location('_e5_isolated', {str(RUNNER_PATH)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert module.CRYPTO_MODULE not in sys.modules
config = module.load_config({str(CONFIG_PATH)!r})
assert config['evaluation']['family_order'] == ['ASCON', 'PRESENT']
module._preflight_cases(config)
assert module.CRYPTO_MODULE not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert completed.returncode == 0


def test_config_freezes_model_families_arms_profile_and_endpoint(runner) -> None:
    config = _config(runner)
    assert config["status"] == "post_release_pre_endpoint_amendment_pre_registered_unrun"
    assert config["amendment"]["classification"] == (
        "post_release_pre_endpoint_protocol_amendment"
    )
    assert config["amendment"]["parent_v1"]["static_lock_canonical_sha256"] == (
        "029eb6d3ceb5afdf12fd1a2e406d96919a1ae7fa8f0359d510060d8e44cbde19"
    )
    assert config["amendment"]["parent_v1"]["seal"]["evaluation_lock_sha256"] == (
        "dd05ab6a3370dd64252e36d429b4a12507d4d99309c176f1dce443b988adceba"
    )
    assert config["foundation_v4"]["required_profile"] == "formal"
    assert config["foundation_v4"]["required_crypto_training_examples"] == 0
    assert config["holdout_access"]["families"]["ASCON"]["role"] == "primary"
    assert config["holdout_access"]["families"]["PRESENT"]["role"] == "secondary"
    assert [item["name"] for item in config["evaluation"]["arms"]] == list(runner.ARMS)
    assert all(item["learned_value"] for item in config["evaluation"]["arms"][1:])
    assert config["search"]["policy_term_threshold"] == 0
    assert config["native_profile"]["frozen_n_qubits"] == 10
    assert config["compute_contract"] == {
        "device": "cpu",
        "torch_intraop_threads": 1,
        "torch_interop_threads": 1,
        "torch_deterministic_algorithms": True,
    }
    assert config["primary_endpoint"]["cluster_unit"] == ["family", "output_bit"]
    assert config["noisy_diagnostic"]["enabled"] is False


def test_static_lock_binds_compute_contract_and_all_contract_sources(runner) -> None:
    config = _config(runner)
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    assert lock["config"]["file_sha256"] == runner.sha256_file(CONFIG_PATH)
    assert lock["config"]["canonical_sha256"] == runner._sha_payload(config)
    assert lock["amendment"] == config["amendment"]
    assert lock["amendment_sha256"] == runner._sha_payload(config["amendment"])
    assert lock["parent_v1_static_lock_canonical_sha256"] == (
        config["amendment"]["parent_v1"]["static_lock_canonical_sha256"]
    )
    assert lock["compute_contract"] == config["compute_contract"]
    assert lock["compute_contract_sha256"] == runner.compute_contract_sha256(config)
    contract_sources = {
        "runner": RUNNER_PATH,
        "verifier": VERIFIER_PATH,
        "contract_test": Path(__file__).resolve(),
    }
    for role, path in contract_sources.items():
        assert lock["sources"][role]["sha256"] == runner.sha256_file(path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["evaluation"].update(family_order=["PRESENT", "ASCON"]), "family order"),
        (lambda value: value["search"].update(policy_term_threshold=1), "policy and value"),
        (lambda value: value["native_profile"].update(frozen_n_qubits=9), "10q"),
        (
            lambda value: value["compute_contract"].update(torch_intraop_threads=2),
            "compute contract",
        ),
        (lambda value: value["noisy_diagnostic"].update(enabled=True), "noisy"),
        (
            lambda value: value["amendment"]["exposure_ledger"].update(
                endpoint_results_observed=True
            ),
            "pre-endpoint",
        ),
        (lambda value: value["search"].update(simulations=9), "frozen scientific"),
    ],
)
def test_config_tampering_fails_closed(runner, tmp_path: Path, mutation, message: str) -> None:
    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    mutation(value)
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        runner.load_config(path)


def test_cli_has_no_combined_or_all_phase(runner) -> None:
    with pytest.raises(SystemExit):
        runner._args(["--phase", "all"])
    assert runner._args(["--phase", "preflight"]).phase == "preflight"
    assert runner._args(["--phase", "seal"]).phase == "seal"
    assert runner._args(["--phase", "evaluate"]).phase == "evaluate"


@pytest.mark.parametrize(
    ("module_path", "helper_name", "matcher_name"),
    [
        (RUNNER_PATH, "establish_compute_contract", "compute_runtime_matches"),
        (VERIFIER_PATH, "_establish_compute_contract", "_compute_runtime_matches"),
    ],
)
def test_default_thread_mismatch_is_reset_before_checkpoint_inference(
    module_path: Path, helper_name: str, matcher_name: str
) -> None:
    code = f"""
import importlib.util, json, os, sys, torch
os.environ['XA_E5_PROJECT_ROOT'] = {str(PROJECT_ROOT)!r}
spec = importlib.util.spec_from_file_location('_e5_compute_reset', {str(module_path)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
config = json.loads(open({str(CONFIG_PATH)!r}, encoding='utf-8').read())
before = {{
    'torch_intraop_threads': torch.get_num_threads(),
    'torch_interop_threads': torch.get_num_interop_threads(),
}}
assert before != {{'torch_intraop_threads': 1, 'torch_interop_threads': 1}}
runtime = getattr(module, {helper_name!r})(
    config, context='contract-test-before-checkpoint-inference'
)
assert getattr(module, {matcher_name!r})(runtime, config)
assert runtime['reset_applied'] is True
assert torch.get_num_threads() == 1
assert torch.get_num_interop_threads() == 1
assert torch.are_deterministic_algorithms_enabled() is True
assert str(torch.get_default_device()) == 'cpu'
print(json.dumps(runtime, sort_keys=True))
"""
    environment = dict(os.environ)
    environment.update({"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"})
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    runtime = json.loads(completed.stdout)
    assert runtime["observed_before"] != runtime["observed_after"]


@pytest.mark.parametrize("module_fixture", ["runner", "verifier"])
def test_compute_contract_refuses_when_postconditions_cannot_be_established(
    module_fixture: str,
    runner,
    verifier,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = runner if module_fixture == "runner" else verifier
    config = _config(runner)

    def locked_interop(_value):
        raise RuntimeError("interop runtime already locked")

    monkeypatch.setattr(module.torch, "set_num_interop_threads", locked_interop)
    monkeypatch.setattr(module.torch, "get_num_interop_threads", lambda: 2)
    helper = getattr(module, "establish_compute_contract", None)
    if helper is None:
        helper = module._establish_compute_contract
    with pytest.raises(RuntimeError, match="cannot establish"):
        helper(config, context="contract-test-must-fail-closed")


def test_verifier_v4_gate_never_touches_checkpoint_when_compute_setup_fails(
    runner, verifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    touched_checkpoint = False

    def fail_compute(*_args, **_kwargs):
        raise RuntimeError("compute setup unavailable")

    def mark_checkpoint(*_args, **_kwargs):
        nonlocal touched_checkpoint
        touched_checkpoint = True
        raise AssertionError("checkpoint verifier must not be reached")

    monkeypatch.setattr(verifier, "_establish_compute_contract", fail_compute)
    monkeypatch.setattr(verifier, "verify_foundation_v4_bundle", mark_checkpoint)
    ok, details = verifier._verify_v4_gate(_config(runner))
    assert ok is False
    assert details == {}
    assert touched_checkpoint is False


def test_preflight_cases_are_unique_n6_n7_and_non_crypto(runner) -> None:
    cases = runner._preflight_cases(_config(runner))
    assert len(cases) == 12
    assert [case["n"] for case in cases] == [6] * 6 + [7] * 6
    assert len({case["truth_table_sha256"] for case in cases}) == 12
    denylist = {
        digest
        for family in _config(runner)["holdout_access"]["families"].values()
        for digest in (
            family["vector_truth_table_sha256"],
            *family["coordinate_truth_table_sha256"],
        )
    }
    assert not ({case["truth_table_sha256"] for case in cases} & denylist)


def test_weight_rule_is_fixed_compile_only_median_scaling(runner) -> None:
    config = _config(runner)
    records = []
    for twoq, depth in ((10.0, 4.0), (20.0, 8.0), (30.0, 12.0)):
        records.append(
            {
                "resource_components": {
                    "native_one_qubit": 100.0,
                    "native_two_qubit": twoq,
                    "inserted_swap": 2.0,
                    "native_depth": depth,
                    "duration_ns": 1000.0,
                    "model_risk": 0.0,
                }
            }
        )
    weights, rule = runner.select_frozen_weights(
        rows=[{"compile_time_candidates": records}],
        config=config,
        calibration_sha256="a" * 64,
        profile_sha256="b" * 64,
    )
    assert weights.native_two_qubit == pytest.approx(0.15 * 0.8 / 20.0)
    assert weights.native_depth == pytest.approx(0.15 * 0.2 / 8.0)
    assert weights.native_one_qubit == weights.inserted_swap == 0.0
    assert weights.duration_ns == weights.model_risk == 0.0
    assert rule["model_fit"] is False
    assert rule["holdout_used"] is False
    assert rule["noisy_outcome_used"] is False


def test_v11_binds_parent_v1_preflight_and_exact_frozen_weight_identity(runner) -> None:
    config = _config(runner)
    summary, rows, bundle = runner._parent_v1_preflight_evidence(config)
    parent = config["amendment"]["parent_v1"]["preflight"]
    assert bundle.name == Path(parent["bundle"]).name
    assert len(rows) == 12
    assert summary["calibration_sha256"] == parent["calibration_sha256"]
    assert summary["weights_sha256"] == parent["weights_sha256"]
    weights = runner._weights_from_payload(summary["frozen_penalty_weights"])
    assert weights.weights_sha256 == (
        "b5e832cae44ff4660192a8f4c9800ad19b87299084fc172de79f6ea481f1da5e"
    )


def _comparison_rows(runner, *, repaired_bit: int | None = None):
    rows = []
    for bit in range(5):
        for seed in (1, 2):
            for arm, value in (
                ("v4_historical_qaoa_shot", 10 + bit),
                ("v4_execution_aware_qaoa_shot", 9 + bit),
            ):
                qaoa = "direct_unrepaired"
                if repaired_bit == bit and arm == "v4_execution_aware_qaoa_shot" and seed == 1:
                    qaoa = "direct_repaired"
                rows.append(
                    {
                        "family": "ASCON",
                        "output_bit": bit,
                        "solver_seed": seed,
                        "arm": arm,
                        "execution_status": qaoa,
                        "qaoa_execution": qaoa,
                        "root_eligibility": "schedulable",
                        "primary_endpoint": {"value": value},
                    }
                )
    return rows


def test_cluster_statistics_treat_seeds_as_repeats_and_exact_p_floor(runner) -> None:
    config = _config(runner)
    config = copy.deepcopy(config)
    config["statistics"]["bootstrap_resamples"] = 200
    result = runner.cluster_paired_comparison(
        _comparison_rows(runner),
        family="ASCON",
        historical_arm="v4_historical_qaoa_shot",
        execution_arm="v4_execution_aware_qaoa_shot",
        config=config,
    )
    assert result["cluster_count"] == 5
    assert result["paired_seed_observation_count"] == 10
    assert result["mean_difference"] == -1.0
    assert result["exact_sign_flip_permutations"] == 32
    assert result["exact_two_sided_sign_flip_p"] == 0.0625
    assert result["claim_rule"] == (
        "effect_estimate_only_no_binary_superiority_due_five_clusters"
    )
    assert result["wins_losses_ties"] == {"wins": 5, "losses": 0, "ties": 0}
    assert result["nonzero_cluster_count"] == 5
    assert result["zero_cluster_count"] == 0


def test_direct_only_filter_excludes_whole_cluster_not_one_seed(runner) -> None:
    config = copy.deepcopy(_config(runner))
    config["statistics"]["bootstrap_resamples"] = 200
    result = runner.cluster_paired_comparison(
        _comparison_rows(runner, repaired_bit=2),
        family="ASCON",
        historical_arm="v4_historical_qaoa_shot",
        execution_arm="v4_execution_aware_qaoa_shot",
        config=config,
        direct_unrepaired_only=True,
    )
    assert result["eligible_clusters"] == [0, 1, 3, 4]
    assert result["excluded_clusters"] == [2]
    assert result["cluster_count"] == 4
    assert result["paired_seed_observation_count"] == 8
    assert result["excluded_cluster_reasons"] == [
        {
            "output_bit": 2,
            "reasons": [
                "not_both_arms_direct_unrepaired_all_seeds:direct_repaired,direct_unrepaired"
            ],
        }
    ]
    assert result["direct_filter_rule"] == (
        "retain_family_bit_only_if_both_arms_direct_unrepaired_for_all_solver_seeds"
    )


def test_schedulable_only_filter_is_secondary_and_records_reason(runner) -> None:
    config = copy.deepcopy(_config(runner))
    config["statistics"]["bootstrap_resamples"] = 200
    rows = _comparison_rows(runner)
    for row in rows:
        if row["output_bit"] == 0:
            row["root_eligibility"] = "degenerate_direct_root"
            row["execution_status"] = "not_invoked_degenerate"
            row["qaoa_execution"] = "not_invoked_degenerate"
            row["primary_endpoint"]["value"] = 10
    result = runner.cluster_paired_comparison(
        rows,
        family="ASCON",
        historical_arm="v4_historical_qaoa_shot",
        execution_arm="v4_execution_aware_qaoa_shot",
        config=config,
        schedulable_only=True,
    )
    assert result["estimand"] == "schedulable_only_secondary"
    assert result["eligible_clusters"] == [1, 2, 3, 4]
    assert result["excluded_cluster_reasons"] == [
        {
            "output_bit": 0,
            "reasons": ["excluded_from_schedulable_only_secondary"],
        }
    ]


def test_four_v4_arms_same_pool_raw_utility_and_budget_contract(runner) -> None:
    rows = []
    for family, width in (("ASCON", 5), ("PRESENT", 4)):
        for bit in range(width):
            for seed in (1, 2):
                for arm in runner.V4_FOUR_ARMS:
                    rows.append(
                        {
                            "family": family,
                            "output_bit": bit,
                            "solver_seed": seed,
                            "arm": arm,
                            "root_eligibility": "schedulable",
                            "candidate_pool_sha256": f"{family}-{bit}-{seed}",
                            "raw_scheduler_utilities": [0.4, 0.2, 0.1],
                            "simulations": 8,
                            "search_config": {"candidate_top_k": 8},
                            "scheduler": {
                                "budget_requested": 3,
                                "budget_effective": 3,
                                "candidate_count": 6,
                            },
                        }
                    )
    result = runner._v4_pool_fairness(rows)
    assert result["group_count"] == 18
    assert result["all"] is True
    rows[-1]["raw_scheduler_utilities"] = [0.5, 0.2, 0.1]
    assert runner._v4_pool_fairness(rows)["all"] is False


def test_four_arm_fairness_excludes_degenerate_groups_but_requires_each_family(runner) -> None:
    rows = []
    for family, width in (("ASCON", 5), ("PRESENT", 4)):
        for bit in range(width):
            for seed in (1, 2):
                eligibility = (
                    "degenerate_direct_root"
                    if (family, bit, seed) == ("ASCON", 0, 1)
                    else "schedulable"
                )
                for arm in runner.V4_FOUR_ARMS:
                    rows.append(
                        {
                            "family": family,
                            "output_bit": bit,
                            "solver_seed": seed,
                            "arm": arm,
                            "root_eligibility": eligibility,
                            "candidate_pool_sha256": f"{family}-{bit}-{seed}",
                            "raw_scheduler_utilities": [0.4, 0.2, 0.1],
                            "simulations": 8,
                            "search_config": {"candidate_top_k": 8},
                            "scheduler": {
                                "budget_requested": 3,
                                "budget_effective": 3,
                                "candidate_count": 6,
                            },
                        }
                    )
    result = runner._v4_pool_fairness(rows)
    assert result["group_count"] == 17
    assert result["degenerate_group_count"] == 1
    assert result["each_family_has_schedulable_activity"] is True
    assert result["all"] is True


def test_zero_clusters_reduce_effective_sign_flip_space(runner) -> None:
    config = copy.deepcopy(_config(runner))
    config["statistics"]["bootstrap_resamples"] = 200
    rows = _comparison_rows(runner)
    for row in rows:
        if row["output_bit"] in {3, 4}:
            row["primary_endpoint"]["value"] = 10 + row["output_bit"]
    result = runner.cluster_paired_comparison(
        rows,
        family="ASCON",
        historical_arm="v4_historical_qaoa_shot",
        execution_arm="v4_execution_aware_qaoa_shot",
        config=config,
    )
    assert result["cluster_count"] == 5
    assert result["nonzero_cluster_count"] == 3
    assert result["zero_cluster_count"] == 2
    assert result["effective_exact_sign_flip_permutations"] == 8
    assert result["minimum_attainable_two_sided_sign_flip_p"] == 0.25
    assert result["wins_losses_ties"] == {"wins": 3, "losses": 0, "ties": 2}


@pytest.mark.parametrize(
    ("diagnostics", "arm", "expected"),
    [
        ({"root_eligibility": "degenerate_direct_root"}, "v4_historical_qaoa_shot", "not_invoked_degenerate"),
        ({"root_eligibility": "schedulable"}, "v4_historical_greedy", "classical_invoked"),
        (
            {"root_eligibility": "schedulable", "status": "qaoa_not_invoked"},
            "v4_historical_qaoa_shot",
            "not_invoked_small_pool",
        ),
        (
            {"root_eligibility": "schedulable", "qaoa_succeeded": True},
            "v4_historical_qaoa_shot",
            "direct_unrepaired",
        ),
        (
            {"root_eligibility": "schedulable", "qaoa_repaired": True},
            "v4_historical_qaoa_shot",
            "direct_repaired",
        ),
        (
            {"root_eligibility": "schedulable", "qaoa_fallback": True},
            "v4_historical_qaoa_shot",
            "fallback",
        ),
        ({"root_eligibility": "schedulable"}, "v4_historical_qaoa_shot", "invalid"),
    ],
)
def test_execution_status_taxonomy_is_closed(runner, diagnostics, arm, expected) -> None:
    assert runner._qaoa_execution_class(diagnostics, arm) == expected
    assert expected in runner.EXECUTION_STATUSES


def test_failed_attempt_writer_creates_non_overwriting_nine_file_evidence(
    runner, tmp_path: Path
) -> None:
    config = _config(runner)
    runner._FAILURE_CONTEXT = {
        "rows": [],
        "events": [],
        "holdout_released": False,
        "release_record": None,
    }
    bundle = runner._write_failed_attempt_bundle(
        out_dir=tmp_path,
        run_id="e5-contract-failure",
        phase="preflight",
        config_path=CONFIG_PATH,
        config=config,
        exception=RuntimeError("contract test failure"),
        traceback_text="Traceback: contract test failure\n",
        terminal_capture_available=False,
    )
    assert {path.name for path in bundle.iterdir()} == set(runner.EXPECTED_ARTIFACTS)
    summary = json.loads((bundle / "summary.json").read_text(encoding="utf-8"))
    assert summary["evidence_ok"] is True
    assert summary["experiment_completed"] is False
    assert summary["terminal_transcript_fabricated"] is False
    with pytest.raises(FileExistsError):
        runner.ArtifactBundleWriter(bundle)


def test_failure_path_never_steals_an_existing_run_reservation(
    runner, tmp_path: Path
) -> None:
    reservation = runner._reserve_run_id(tmp_path, "reserved-attempt")
    try:
        failure = runner._failure_bundle_path(
            tmp_path, "reserved-attempt", "RuntimeError: test"
        )
        assert failure.name.startswith("reserved-attempt-failed-attempt-")
        assert failure != tmp_path / "reserved-attempt"
    finally:
        reservation.unlink()


def test_degenerate_direct_root_runs_all_five_arms_and_produces_identical_artifacts(
    runner,
) -> None:
    config = _config(runner)
    bf = runner.BooleanFunction(3, 0x96)  # x0 xor x1 xor x2: no repeated factor.
    truth_sha = runner._truth_table_sha256(bf)
    coordinate = SimpleNamespace(
        family="ASCON",
        operation="forward",
        output_bit=0,
        input_width=3,
        output_width=1,
        bit_order="lsb0",
        source={"contract_test": True},
        provenance={"contract_test": True},
        benchmark_partition="contract_test_only",
        training_access_allowed=False,
        family_exclusion_label="contract_test_only",
        vector_truth_table_sha256=truth_sha,
        truth_table_sha256=truth_sha,
        boolean_function=bf,
        evaluate=lambda x: bf.evaluate(x),
    )

    class NoInferenceScorer:
        cache_hits = 0
        cache_misses = 0

        def clear_cache(self):
            self.cache_hits = 0
            self.cache_misses = 0

    profile_spec = runner._profile_spec(config)
    frozen_profile, profile_sha = runner._frozen_concrete_profile(config, profile_spec)
    weights = runner.FrozenExecutionPenaltyWeights(
        calibration_sha256="a" * 64,
        profile_sha256=profile_spec.profile_sha256,
    )
    rows = [
        runner._evaluation_trial(
            coordinate=coordinate,
            arm_spec=arm,
            solver_seed=1,
            config=config,
            scorer=NoInferenceScorer(),
            checkpoint_sha256=config["foundation_v4"]["checkpoint_sha256"],
            weights=weights,
            profile_spec=profile_spec,
            frozen_profile=frozen_profile,
            frozen_profile_sha256=profile_sha,
            run_id="degenerate-contract-test",
        )
        for arm in config["evaluation"]["arms"]
    ]
    assert {row["root_action_count"] for row in rows} == {0}
    assert {row["root_eligibility"] for row in rows} == {"degenerate_direct_root"}
    assert {row["execution_status"] for row in rows} == {"not_invoked_degenerate"}
    for field in (
        "plan_trace_sha256",
        "logical_qasm3_sha256",
        "native_record_sha256",
        "primary_endpoint_sha256",
    ):
        assert len({row[field] for row in rows}) == 1
    assert len({row["native"]["native_qasm3_sha256"] for row in rows}) == 1
    assert all(row["plan_anf_ok"] and row["oracle_ok"] for row in rows)
    assert all(row["native"]["native_gate_set_ok"] for row in rows)
    identity = runner._eligibility_and_degenerate_identity(rows)
    assert identity["groups"][0][
        "degenerate_five_arm_plan_qasm_native_endpoint_identical"
    ] is True


def test_evaluate_never_releases_tables_when_an_earlier_gate_fails(
    runner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    released = False

    def mark_release(_config):
        nonlocal released
        released = True
        raise AssertionError("release must not be reached")

    monkeypatch.setattr(runner, "_release_holdout_families_after_all_gates", mark_release)
    monkeypatch.setattr(
        runner,
        "load_static_protocol_lock",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("gate failed")),
    )
    with pytest.raises(ValueError, match="gate failed"):
        runner.run_evaluate(
            config_path=CONFIG_PATH,
            config=_config(runner),
            preflight_bundle=tmp_path / "preflight",
            seal_bundle=tmp_path / "seal",
            out_dir=tmp_path,
            run_id="must-not-release",
        )
    assert released is False


def test_verifier_has_no_top_level_crypto_import_and_exposes_public_entrypoint() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    prefix = source.split("def _load_and_verify_holdouts", 1)[0]
    assert "from src.benchmarks.crypto_oracles import" not in prefix
    verifier = _load_module("_e5_verifier_contract_test", VERIFIER_PATH)
    assert callable(verifier.verify_e5_external_crypto_holdout_bundle)
