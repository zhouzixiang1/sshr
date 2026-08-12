"""Public detailed-result contract without legacy-entrypoint regressions."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.anf_utils import majority_function
from src.factor_plan import SearchConfig
from src.foundation.adapter import FoundationScorer
from src.synthesizers import (
    DetailedResultUnavailable,
    synthesize,
    synthesize_detailed,
)


def _small_config() -> SearchConfig:
    return SearchConfig(
        candidate_top_k=8,
        mcts_simulations=4,
        neural_mcts_simulations=4,
        max_polarities=4,
    )


def test_detailed_direct_preserves_legacy_summary_and_verification() -> None:
    bf = majority_function(4)
    config = _small_config()
    legacy = synthesize("direct_anf", bf, config, seed=17)
    detailed = synthesize_detailed("direct_anf", bf, config, seed=17)

    assert detailed.requested_method == "direct_anf"
    assert detailed.effective_method == "direct_anf"
    assert detailed.summary["method"] == legacy.method
    assert detailed.summary["cost"] == {
        "T": legacy.cost.T,
        "CNOT": legacy.cost.CNOT,
        "gates": legacy.cost.gates,
        "depth": legacy.cost.depth,
        "explicit_ancilla": legacy.cost.explicit_ancilla,
        "peak_ancilla": legacy.cost.peak_ancilla,
    }
    assert detailed.summary["correct"] == legacy.correct
    assert detailed.summary["terms"] == legacy.terms
    assert detailed.summary["gates"] == legacy.gates
    assert detailed.summary["n_qubits"] == legacy.n_qubits
    assert detailed.input["n_declared"] == 4
    assert detailed.input["truth_table_hex"].startswith("0x")
    assert detailed.plan_trace is not None
    assert detailed.plan_unavailable_reason is None
    assert detailed.verification["oracle_truth_table"]["ok"]
    assert detailed.verification["plan_anf"]["ok"]
    assert detailed.verification["circuit_anf"]["ok"]
    assert detailed.logical_qasm3.startswith("OPENQASM 3.0;")
    assert detailed.qasm_metadata["claim_boundary"] in detailed.to_dict()["qasm_metadata"]["claim_boundary"]


def test_detailed_records_effective_and_cost_domain() -> None:
    detailed = synthesize_detailed(
        "and_direct_anf",
        majority_function(4),
        _small_config(),
        seed=3,
    )

    assert detailed.requested_method == "and_direct_anf"
    assert detailed.effective_method == "direct_anf"
    assert detailed.effective_config["gate_mode"] == "logical_and"
    assert detailed.cost_semantics == "logical-resource-proxy-v1"
    assert "not a native-gate" in detailed.claim_boundary


def test_detailed_model_record_hashes_without_leaking_absolute_path(tmp_path: Path) -> None:
    checkpoint = tmp_path / "outside-workspace.pt"
    FoundationScorer.untrained(hidden=16, layers=1, seed=7).save(checkpoint)

    detailed = synthesize_detailed(
        "foundation_nmcts",
        majority_function(4),
        _small_config(),
        seed=5,
        model_path=str(checkpoint),
    )

    assert detailed.model is not None
    assert detailed.model["path_hint"] == checkpoint.name
    assert len(detailed.model["sha256"]) == 64
    assert str(tmp_path) not in str(detailed.to_dict())


def test_detailed_portfolio_fails_explicitly_while_legacy_still_runs() -> None:
    bf = majority_function(3)
    legacy = synthesize("resource_heuristic", bf, _small_config(), seed=1)
    assert legacy.correct

    with pytest.raises(DetailedResultUnavailable, match="portfolio/wrapper"):
        synthesize_detailed("resource_heuristic", bf, _small_config(), seed=1)
