"""Tiny end-to-end evidence bundles for prior and value diagnostics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.contracts.artifacts import verify_bundle
from src.anf_utils import anf_monomials, majority_function
from src.factor_plan import SearchConfig
from src.foundation.adapter import FoundationScorer
from src.nmcts_solver import NeuralMCTSSolver, StateKey
from scripts.run_prior_ablation import OraclePrior


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _checkpoint(path: Path) -> Path:
    FoundationScorer.untrained(hidden=16, layers=1, seed=7).save(path)
    return path


def _run(script: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / script), *args],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_prior_tiny_pilot_writes_complete_three_variant_bundle(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path / "model.pt")
    out_dir = tmp_path / "results"
    completed = _run(
        "run_prior_ablation.py",
        [
            "--checkpoint",
            str(checkpoint),
            "--sizes",
            "4",
            "--per-size",
            "1",
            "--simulations",
            "1",
            "--out-dir",
            str(out_dir),
            "--run-id",
            "prior-tiny",
        ],
    )
    bundle = out_dir / "prior-tiny"
    verification = verify_bundle(bundle)
    assert verification.ok, verification.errors
    rows = [json.loads(line) for line in (bundle / "raw.jsonl").read_text().splitlines()]
    assert {row["variant"] for row in rows} == {"shuffled", "model", "oracle"}
    assert all(row["plan_anf_ok"] and row["circuit_anf_ok"] and row["oracle_ok"] for row in rows)
    assert "bundle_ok=True" in completed.stdout


def test_qaoa_scheduler_tiny_pilot_closes_the_full_evidence_contract(
    tmp_path: Path,
) -> None:
    checkpoint = _checkpoint(tmp_path / "model.pt")
    out_dir = tmp_path / "results"
    completed = _run(
        "run_qaoa_scheduler_pilot.py",
        [
            "--checkpoint",
            str(checkpoint),
            "--tiny",
            "--out-dir",
            str(out_dir),
            "--run-id",
            "qaoa-scheduler-tiny",
        ],
    )
    bundle = out_dir / "qaoa-scheduler-tiny"
    verification = verify_bundle(bundle)
    assert verification.ok, verification.errors
    verifier = json.loads((bundle / "verifier.json").read_text())
    summary = json.loads((bundle / "summary.json").read_text())
    records = [
        json.loads(line) for line in (bundle / "raw.jsonl").read_text().splitlines()
    ]
    trials = [record for record in records if record["record_type"] == "scheduler_trial"]

    assert verifier["ok"]
    assert summary["trial_count"] == 7
    assert {row["variant"] for row in trials} == {
        "random",
        "top_b",
        "greedy",
        "exact",
        "qaoa_ideal",
        "qaoa_shot",
        "qaoa_noisy",
    }
    assert all(
        row["plan_anf_ok"] and row["circuit_anf_ok"] and row["oracle_ok"]
        for row in trials
    )
    assert {record["record_type"] for record in records} == {
        "pool_instance",
        "qubo_audit",
        "boundary_audit",
        "scheduler_trial",
    }
    assert "bundle_ok=True" in completed.stdout


def test_value_tiny_pilot_summary_is_recomputable_and_no_absolute_model_path(
    tmp_path: Path,
) -> None:
    checkpoint = _checkpoint(tmp_path / "model.pt")
    out_dir = tmp_path / "results"
    _run(
        "run_value_diagnostic.py",
        [
            "--checkpoint",
            str(checkpoint),
            "--sizes",
            "4",
            "--per-size",
            "1",
            "--simulations",
            "2",
            "--out-dir",
            str(out_dir),
            "--run-id",
            "value-tiny",
        ],
    )
    bundle = out_dir / "value-tiny"
    verification = verify_bundle(bundle)
    assert verification.ok, verification.errors
    verifier = json.loads((bundle / "verifier.json").read_text())
    summary = json.loads((bundle / "summary.json").read_text())
    assert verifier["ok"]
    assert summary["state_count"] > 0
    assert str(tmp_path) not in (bundle / "run.json").read_text()


def test_prior_without_out_dir_remains_stdout_only(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path / "model.pt")
    before = {path.name for path in tmp_path.iterdir()}
    completed = _run(
        "run_prior_ablation.py",
        [
            "--checkpoint",
            str(checkpoint),
            "--sizes",
            "4",
            "--per-size",
            "1",
            "--simulations",
            "1",
        ],
    )
    after = {path.name for path in tmp_path.iterdir()}
    assert before == after
    assert "bundle:" not in completed.stdout


def test_oracle_prior_uses_classical_rollout_not_learned_value() -> None:
    class BombValue:
        def estimate(self, *args, **kwargs):
            raise AssertionError("learned value must not define the rollout-oracle ordering")

    terms = frozenset(anf_monomials(majority_function(4)))
    solver = OraclePrior(
        SearchConfig(candidate_top_k=8),
        simulations=1,
        seed=1,
        value_estimator=BombValue(),
    )
    node = solver._node(StateKey(terms, 0, 0))
    solver._expand(node)
    costs = [solver._classical_rollout_action_cost(node.key, action) for action in node.actions]
    assert costs == sorted(costs)


def test_c0c7_tiny_pilot_wires_all_causal_variants(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path / "model.pt")
    out_dir = tmp_path / "results"
    _run(
        "run_c0c7_pilot.py",
        [
            "--checkpoint",
            str(checkpoint),
            "--sizes",
            "4",
            "--per-size",
            "1",
            "--simulations",
            "2",
            "--solver-seeds",
            "1",
            "--out-dir",
            str(out_dir),
            "--run-id",
            "c0c7-tiny",
        ],
    )
    bundle = out_dir / "c0c7-tiny"
    verification = verify_bundle(bundle)
    assert verification.ok, verification.errors
    rows = [json.loads(line) for line in (bundle / "raw.jsonl").read_text().splitlines()]
    assert {row["variant"] for row in rows} == {f"C{i}" for i in range(8)}
    specs = {row["variant"]: (row["policy"], row["value"], row["width"]) for row in rows}
    assert specs["C0"] == ("heuristic", "greedy", "exhaustive")
    assert specs["C5"] == ("learned", "learned", "progressive")
    assert specs["C6"] == ("shuffled_learned", "learned", "progressive")
    assert specs["C7"] == ("conditional_classical_rollout", "learned", "progressive")
    assert all(row["plan_anf_ok"] and row["circuit_anf_ok"] and row["oracle_ok"] for row in rows)


def test_rollout_scorer_can_be_frozen_without_changing_legacy_default() -> None:
    scorer = FoundationScorer.untrained(hidden=8, layers=1, seed=5)
    legacy = NeuralMCTSSolver(SearchConfig(), simulations=1, neural_scorer=scorer)
    controlled = NeuralMCTSSolver(
        SearchConfig(),
        simulations=1,
        neural_scorer=scorer,
        rollout_scorer=None,
    )
    assert legacy.rollout_scorer is scorer
    assert controlled.rollout_scorer is None
