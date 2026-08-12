#!/usr/bin/env python3
"""Mechanism-only tests for isolated E6 multi-output shared emission."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from e6.shared_oracle import (
    MonomialSharedAction,
    SemiAffineSharedAction,
    VectorANF,
    actions_conflict,
    emit_shared_oracle,
    enumerate_monomial_shared_actions,
    enumerate_semi_affine_shared_actions,
    expand_semi_affine,
    permute_action_outputs,
    target_mask_to_targets,
    targets_to_mask,
    verify_vector_oracle_semantics,
)
from src.benchmarks.crypto_oracles import (
    CRYPTO_HOLDOUT_EXCLUSION_LABEL,
    get_crypto_holdout_oracle_coordinates,
)


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def synthetic_monomial_vector() -> VectorANF:
    # x0*x1 is shared by all outputs; the other monomials remain direct.
    return VectorANF(
        3,
        (
            frozenset({0b011, 0b100}),
            frozenset({0b011, 0b001}),
            frozenset({0b011, 0b010}),
        ),
    )


@pytest.fixture
def synthetic_semi_affine_vector() -> VectorANF:
    # x0 * (1 xor x1 xor x2) = x0 xor x0*x1 xor x0*x2.
    shared_terms = frozenset({0b001, 0b011, 0b101})
    return VectorANF(
        3,
        (
            shared_terms | {0b010},
            shared_terms | {0b100},
            frozenset({0, 0b110}),
        ),
    )


def test_vector_anf_truth_table_roundtrip_and_gf2_overlap_cancellation() -> None:
    values = (0, 3, 1, 2, 2, 1, 3, 0)
    vector = VectorANF.from_value_table(3, 2, values)

    assert [vector.evaluate_value(x) for x in range(8)] == list(values)
    assert vector.output_count == 2

    # x0 * (1 xor x0) cancels in the Boolean ring: x0 xor x0 == 0.
    assert expand_semi_affine(0b001, 0b001, True) == frozenset()
    # This expression has three distinct ANF terms.
    assert expand_semi_affine(0b001, 0b110, True) == frozenset(
        {0b001, 0b011, 0b101}
    )


def test_monomial_compute_fanout_uncompute_is_correct_for_every_x_and_y(
    synthetic_monomial_vector: VectorANF,
) -> None:
    action = MonomialSharedAction(0b011, (0, 1, 2))
    program = emit_shared_oracle(synthetic_monomial_vector, (action,))
    verification = verify_vector_oracle_semantics(program)

    assert verification.ok
    assert verification.assignments_checked == 1 << (3 + 3)
    assert verification.arbitrary_y_covered
    assert verification.ancilla_reset
    assert verification.max_ancilla_observed == program.ancilla_count == 1
    assert program.covered_footprint == frozenset(
        {(0, 0b011), (1, 0b011), (2, 0b011)}
    )
    # MCT compute, three CNOT fanouts, MCT uncompute, then three residual gates.
    assert [gate.type for gate in program.circuit.gates[:5]] == [
        "MCT",
        "CNOT",
        "CNOT",
        "CNOT",
        "MCT",
    ]
    assert all(0b011 not in terms for terms in program.residual_outputs)


def test_semi_affine_uses_two_reusable_ancillas_and_resets_both(
    synthetic_semi_affine_vector: VectorANF,
) -> None:
    action = SemiAffineSharedAction(
        base_monomial=0b001,
        affine_mask=0b110,
        affine_const=True,
        targets=(0, 1),
    )
    program = emit_shared_oracle(synthetic_semi_affine_vector, (action,))
    verification = verify_vector_oracle_semantics(program)

    assert action.polynomial_terms == frozenset({0b001, 0b011, 0b101})
    assert program.ancilla_count == 2
    assert verification.ok
    assert verification.assignments_checked == 64
    assert verification.ancilla_mismatches == 0
    assert verification.ancilla_reset
    assert verification.max_ancilla_observed <= 2
    assert all(
        not (action.polynomial_terms & residual)
        for residual in program.residual_outputs[:2]
    )


def test_footprint_conflicts_are_rejected_before_emission(
    synthetic_semi_affine_vector: VectorANF,
) -> None:
    monomial = MonomialSharedAction(0b011, (0, 1))
    semi_affine = SemiAffineSharedAction(0b001, 0b110, True, (0, 1))

    assert actions_conflict(monomial, semi_affine)
    with pytest.raises(ValueError, match="footprint conflict"):
        emit_shared_oracle(synthetic_semi_affine_vector, (monomial, semi_affine))


def test_action_enumeration_is_bounded_and_actions_are_semantically_applicable(
    synthetic_semi_affine_vector: VectorANF,
) -> None:
    monomials = enumerate_monomial_shared_actions(synthetic_semi_affine_vector)
    semi_affine = enumerate_semi_affine_shared_actions(
        synthetic_semi_affine_vector, max_affine_weight=3
    )

    assert MonomialSharedAction(0b001, (0, 1)) in monomials
    assert any(
        action.polynomial_terms == frozenset({0b001, 0b011, 0b101})
        and action.targets == (0, 1)
        for action in semi_affine
    )
    for action in monomials + semi_affine:
        for target, term in action.footprint:
            assert term in synthetic_semi_affine_vector.outputs[target]


def test_target_mask_enumerates_every_partial_fanout_in_deterministic_order(
    synthetic_monomial_vector: VectorANF,
) -> None:
    actions = [
        action
        for action in enumerate_monomial_shared_actions(synthetic_monomial_vector)
        if action.monomial == 0b011
    ]

    assert [action.target_mask for action in actions] == [0b011, 0b101, 0b110, 0b111]
    assert [action.targets for action in actions] == [
        (0, 1),
        (0, 2),
        (1, 2),
        (0, 1, 2),
    ]
    assert targets_to_mask((0, 2)) == 0b101
    assert target_mask_to_targets(0b101) == (0, 2)
    assert MonomialSharedAction.from_target_mask(0b011, 0b101) == actions[1]
    assert actions[1].to_dict()["target_mask"] == 0b101


def test_output_permutation_maps_vector_and_all_target_mask_candidates() -> None:
    shared_terms = frozenset({0b001, 0b011, 0b101})
    vector = VectorANF(
        3,
        (
            shared_terms | {0b110},
            shared_terms | {0b010},
            shared_terms | {0b100},
        ),
    )
    permutation = (2, 0, 1)  # old output -> new output
    permuted_vector = vector.permute_outputs(permutation)

    original = (
        enumerate_monomial_shared_actions(vector)
        + enumerate_semi_affine_shared_actions(vector, max_affine_weight=3)
    )
    shared_semi_masks = [
        action.target_mask
        for action in original
        if action.kind == "semi_affine"
        and action.polynomial_terms == shared_terms
    ]
    assert shared_semi_masks == [0b011, 0b101, 0b110, 0b111]
    mapped = {
        (
            action.kind,
            tuple(sorted(action.polynomial_terms)),
            action.target_mask,
        )
        for action in (
            permute_action_outputs(
                action, permutation, output_count=vector.output_count
            )
            for action in original
        )
    }
    reenumerated = (
        enumerate_monomial_shared_actions(permuted_vector)
        + enumerate_semi_affine_shared_actions(
            permuted_vector, max_affine_weight=3
        )
    )
    actual = {
        (
            action.kind,
            tuple(sorted(action.polynomial_terms)),
            action.target_mask,
        )
        for action in reenumerated
    }

    assert actual == mapped
    for x in range(1 << vector.input_count):
        original_bits = vector.evaluate_bits(x)
        expected = [0] * vector.output_count
        for old, new in enumerate(permutation):
            expected[new] = original_bits[old]
        assert permuted_vector.evaluate_bits(x) == tuple(expected)


def test_constant_monomial_is_shared_and_uncomputed_for_arbitrary_y() -> None:
    vector = VectorANF(2, (frozenset({0, 0b01}), frozenset({0, 0b10})))
    action = MonomialSharedAction(0, (0, 1))
    program = emit_shared_oracle(vector, (action,))
    verification = verify_vector_oracle_semantics(program)

    assert verification.ok
    assert verification.ancilla_reset
    assert program.ancilla_count == 1
    assert [gate.type for gate in program.circuit.gates[:4]] == [
        "X",
        "CNOT",
        "CNOT",
        "X",
    ]


def test_base_affine_overlap_cancels_symbolically_and_emits_correctly() -> None:
    # x0 * (1 xor x0 xor x1) = x0*x1 because x0 xor x0 cancels.
    action = SemiAffineSharedAction(0b01, 0b11, True, (0, 1))
    vector = VectorANF(2, (frozenset({0b11}), frozenset({0b11})))
    program = emit_shared_oracle(vector, (action,))

    assert action.polynomial_terms == frozenset({0b11})
    assert verify_vector_oracle_semantics(program).ok
    assert program.explicit_workspace_peak == 2


def test_mixed_action_program_preserves_residuals_and_reports_whole_program_peak() -> None:
    semi_terms = frozenset({0b001, 0b011, 0b101})
    vector = VectorANF(
        3,
        (
            semi_terms | {0},
            semi_terms | {0b110, 0b010},
            frozenset({0b110, 0b100}),
        ),
    )
    actions = (
        SemiAffineSharedAction(0b001, 0b110, True, (0, 1)),
        MonomialSharedAction(0b110, (1, 2)),
    )
    program = emit_shared_oracle(vector, actions)
    verification = verify_vector_oracle_semantics(program)

    assert verification.ok
    assert program.residual_outputs == (
        frozenset({0}),
        frozenset({0b010}),
        frozenset({0b100}),
    )
    assert program.ancilla_count == program.explicit_workspace_peak == 2
    payload = program.to_dict()
    assert payload["explicit_workspace_peak"] == 2
    assert payload["resource_contract"]["mct_decomposition_implicit_ancillas_included"] is False
    assert payload["resource_contract"]["exact_hardware_resource_claim"] is False


def test_two_ancilla_cap_and_action_containment_fail_closed(
    synthetic_monomial_vector: VectorANF,
    synthetic_semi_affine_vector: VectorANF,
) -> None:
    semi_affine = SemiAffineSharedAction(0b001, 0b110, True, (0, 1))
    with pytest.raises(ValueError, match="require 2 ancillas"):
        emit_shared_oracle(
            synthetic_semi_affine_vector, (semi_affine,), max_ancilla=1
        )
    with pytest.raises(ValueError, match="no more than 2"):
        emit_shared_oracle(synthetic_monomial_vector, (), max_ancilla=3)
    with pytest.raises(ValueError, match="missing ANF term"):
        emit_shared_oracle(
            synthetic_monomial_vector,
            (MonomialSharedAction(0b111, (0, 1)),),
        )


@pytest.mark.parametrize("family", ["ASCON", "PRESENT"])
def test_observed_crypto_families_are_development_semantic_regressions_only(
    family: str,
) -> None:
    """These families were already observed in E5; this is not holdout evidence."""

    coordinates = get_crypto_holdout_oracle_coordinates(
        family,
        family_exclusion_label=CRYPTO_HOLDOUT_EXCLUSION_LABEL,
    )
    vector = VectorANF.from_boolean_functions(
        [coordinate.boolean_function for coordinate in coordinates]
    )
    enumerated = enumerate_monomial_shared_actions(vector)
    # Enumeration now contains every partial fanout.  Use one maximal fanout
    # action per monomial so this semantic regression remains conflict-free.
    actions = tuple(
        max(
            (action for action in enumerated if action.monomial == monomial),
            key=lambda action: (action.target_mask.bit_count(), action.target_mask),
        )
        for monomial in sorted({action.monomial for action in enumerated})
    )
    program = emit_shared_oracle(vector, actions)
    verification = verify_vector_oracle_semantics(program)

    assert actions
    assert verification.ok
    assert verification.assignments_checked == 1 << (
        vector.input_count + vector.output_count
    )
    assert verification.ancilla_reset
    assert program.ancilla_count == 1


def test_config_declares_mechanism_only_and_no_private_prototype_evidence() -> None:
    config = json.loads(
        (ROOT / "configs/xa202609/e6_multioutput_shared_mvp_v1.json").read_text()
    )

    assert config["scope"]["isolated_from_src"] is True
    assert config["scope"]["scalar_synthesize_modified"] is False
    assert config["scope"]["formal_result_bundle_present"] is False
    assert config["vector_oracle_contract"]["max_reusable_explicit_ancilla"] == 2
    assert config["development_regression"]["not_new_holdout"] is True
    assert config["development_regression"]["private_tmp_prototype_is_evidence"] is False
    assert config["vector_oracle_contract"]["action_target_feature"] == "LSB-indexed target_mask"
    assert config["shared_utility"]["exact_hardware_resource_claim"] is False
    assert config["shared_utility"]["mct_decomposition_implicit_ancillas_included"] is False
    assert config["shared_utility"]["weights"]["whole_program_explicit_workspace_peak_weight"] == 2.0
    assert config["ai_quantum_boundary"]["shared_model_architecture_implemented"] is True
    assert config["ai_quantum_boundary"]["shared_model_schema"] == (
        "xa.e6-shared-policy-value-model.v1"
    )
    assert config["ai_quantum_boundary"]["learned_multioutput_head_connected"] is False
    assert config["ai_quantum_boundary"]["qaoa_trajectory_replay_update_connected"] is False
