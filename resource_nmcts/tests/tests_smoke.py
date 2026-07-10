#!/usr/bin/env python3
"""Smoke tests for resource-constrained neural MCTS synthesis."""
from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Allow tests/ to import from src/, scripts/, submission/ at project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("", "src", "scripts", "submission"):
    _p = _PROJECT_ROOT / _sub if _sub else _PROJECT_ROOT
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from src.anf_utils import anf_monomials, boolean_from_anf, majority_function, parity_function
from submission.export_benchmarks import export_suite, selected_formats
from src.factor_plan import (
    SearchConfig,
    direct_plan,
    emit_plan_to_circuit,
    expand_plan_anf_terms,
    linear_pair_screen_plan,
    verify_circuit_anf,
    verify_plan_anf,
)
from src.resource_model import ResourceWeights
from scripts.run_external_baselines import (
    EsopCube,
    bdd_cost,
    blif_lut_network_cost,
    build_robdd_for_order,
    candidate_bdd_orders,
    blif_truth_table,
    eval_blif,
    parse_blif,
    verify_bdd,
    verify_blif,
    verify_esop,
)
from src.synthesizers import synthesize


def check_roundtrip() -> None:
    for n in range(1, 5):
        for tt in range(1 << (1 << n)):
            if n == 4 and tt > 512:
                break
            bf = boolean_from_anf(n, anf_monomials(boolean_from_anf(n, anf_monomials(boolean_from_anf(n, [])))))
            del bf
            from src.sshr_lib.bool_func import BooleanFunction

            original = BooleanFunction(n, tt)
            rebuilt = boolean_from_anf(n, anf_monomials(original))
            assert rebuilt.truth_table == original.truth_table


def check_external_truth_verifiers() -> None:
    from src.sshr_lib.bool_func import BooleanFunction

    with TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        and_blif = out_dir / "and2.blif"
        and_blif.write_text(
            "\n".join(
                [
                    ".model and2",
                    ".inputs x0 x1",
                    ".outputs f",
                    ".names x0 x1 f",
                    "11 1",
                    ".end",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        or_blif = out_dir / "or2.blif"
        or_blif.write_text(
            "\n".join(
                [
                    ".model or2",
                    ".inputs x0 x1",
                    ".outputs f",
                    ".names x0 x1 f",
                    "00 0",
                    ".end",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        pi_xor_blif = out_dir / "pi_xor2.blif"
        pi_xor_blif.write_text(
            "\n".join(
                [
                    ".model pi_xor2",
                    ".inputs pi00 \\",
                    " pi01",
                    ".outputs po0",
                    ".names pi00 pi01 po0",
                    "01 1",
                    "10 1",
                    ".end",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        assert verify_blif(and_blif, BooleanFunction(2, 0b1000))
        assert verify_blif(or_blif, BooleanFunction(2, 0b1110))
        assert verify_blif(pi_xor_blif, BooleanFunction(2, 0b0110))

        inputs, output, nodes = parse_blif(or_blif)
        truth = blif_truth_table(inputs, output, nodes, 2)
        slow_truth = sum(eval_blif(inputs, output, nodes, x) << x for x in range(4))
        assert truth == slow_truth == 0b1110
        lut_cost = blif_lut_network_cost(inputs, output, nodes, BooleanFunction(2, 0b1110))
        assert lut_cost.T > 0
        assert lut_cost.peak_ancilla >= 1

    xor_cubes = [EsopCube("1-"), EsopCube("-1")]
    assert verify_esop(xor_cubes, BooleanFunction(2, 0b0110))

    xor_bdd = build_robdd_for_order(BooleanFunction(2, 0b0110), (0, 1))
    assert verify_bdd(xor_bdd, BooleanFunction(2, 0b0110))
    assert len(xor_bdd.nodes) >= 2
    assert bdd_cost(xor_bdd, BooleanFunction(2, 0b0110)).CNOT > 0
    assert candidate_bdd_orders(BooleanFunction(1, 0b10), seed=1, max_orders=8) == [(0,)]


def check_plan_anf_verifier() -> None:
    terms = frozenset([0b0011, 0b0101, 0b1001, 0b0111, 0b1011])
    config = SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=3,
        max_factor_size=4,
        candidate_top_k=12,
        gate_mode="logical_and",
    )
    plans = [
        direct_plan(terms, 0, 0, config),
        linear_pair_screen_plan(terms, config=config, action_width=4, recursive_depth=2, boolean_ring=True),
    ]
    for plan in plans:
        verification = verify_plan_anf(plan)
        assert verification.ok
        assert verification.mismatches == 0
        assert expand_plan_anf_terms(plan) == terms
        circuit = emit_plan_to_circuit(plan, 5, config.max_factor_ancilla)
        circuit_verification = verify_circuit_anf(circuit, 5, terms)
        assert circuit_verification.ok
        assert circuit_verification.output_mismatch == 0
        assert circuit_verification.ancilla_mismatches == 0


def main() -> int:
    check_roundtrip()
    check_external_truth_verifiers()
    check_plan_anf_verifier()
    with TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        summary = export_suite("smoke", 42, out_dir, selected_formats("pla,blif,truth"), limit=2)
        assert summary["functions"] == 2
        for rel in ["manifest.csv", "manifest.json"]:
            assert (out_dir / rel).exists(), rel
        assert list((out_dir / "pla").glob("*.pla"))
        assert list((out_dir / "blif").glob("*.blif"))
        assert list((out_dir / "truth").glob("*.json"))
    config = SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=3,
        max_factor_size=4,
        candidate_top_k=12,
    )
    functions = [
        parity_function(4),
        majority_function(4),
        boolean_from_anf(5, [0b00111, 0b01111, 0b10111, 0b11111, 0b00011]),
        boolean_from_anf(5, [0b001, 0b010, 0b1101, 0b1110, 0b10101, 0b10110]),
    ]
    for bf in functions:
        direct = synthesize("direct_anf", bf, config)
        greedy = synthesize("greedy_factor", bf, config)
        mcts = synthesize("mcts_factor", bf, config, seed=7)
        fprm = synthesize("fprm_mcts", bf, config, seed=7)
        cube_greedy = synthesize("cube_greedy", bf, config, seed=7)
        cube_beam = synthesize("cube_beam", bf, config, seed=7)
        and_fprm = synthesize("and_fprm_mcts", bf, config, seed=7)
        and_fprm_neural = synthesize("and_fprm_neural_mcts", bf, config, seed=7)
        and_fprm_linear = synthesize("and_fprm_linear_pair", bf, config, seed=7)
        and_fprm_linear_fast = synthesize("and_fprm_linear_pair_fast", bf, config, seed=7)
        and_fprm_linear_deep = synthesize("and_fprm_linear_pair_deep", bf, config, seed=7)
        and_fprm_linear_parity = synthesize("and_fprm_linear_parity", bf, config, seed=7)
        and_fprm_affine_linear = synthesize("and_fprm_affine_linear_pair", bf, config, seed=7)
        and_fprm_affine_linear_deep = synthesize("and_fprm_affine_linear_pair_deep", bf, config, seed=7)
        and_fprm_polarity_archive = synthesize("and_fprm_polarity_archive", bf, config, seed=7)
        and_affine = synthesize("and_affine_nmcts", bf, config, seed=7)
        rc_nmcts = synthesize("and_rc_nmcts", bf, config, seed=7)
        resource_nmcts = synthesize("and_resource_nmcts", bf, config, seed=7)
        pareto_resource_nmcts = synthesize("and_pareto_resource_nmcts", bf, config, seed=7)
        for result in [direct, greedy, mcts, fprm, cube_greedy, cube_beam, and_fprm, and_fprm_neural, and_fprm_linear, and_fprm_linear_fast, and_fprm_linear_deep, and_fprm_linear_parity, and_fprm_affine_linear, and_fprm_affine_linear_deep, and_fprm_polarity_archive, and_affine, rc_nmcts, resource_nmcts, pareto_resource_nmcts]:
            assert result.correct, (result.method, bf.n, bf.truth_table)
        assert greedy.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert mcts.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert fprm.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_fprm.cost.T <= direct.cost.T
        assert and_fprm_neural.cost.T <= direct.cost.T
        assert and_fprm_linear.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_fprm_linear_fast.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_fprm_linear_deep.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_fprm_linear_parity.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_fprm_affine_linear.cost.score(config.weights) <= and_fprm_linear.cost.score(config.weights) + 1e-9
        assert and_fprm_affine_linear_deep.cost.score(config.weights) <= and_fprm_linear.cost.score(config.weights) + 1e-9
        assert and_fprm_polarity_archive.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_affine.cost.T <= direct.cost.T
        assert rc_nmcts.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert resource_nmcts.cost.score(config.weights) <= and_affine.cost.score(config.weights) + 1e-9
        assert pareto_resource_nmcts.cost.score(config.weights) <= resource_nmcts.cost.score(config.weights) + 1e-9
    highdim_bf = boolean_from_anf(
        13,
        [
            0b111,
            0b1101,
            0b10101,
            0b100011,
            0b1000011,
            0b10000011,
            0b100000011,
            0b1000000011,
        ],
    )
    highdim_config = SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=3,
        max_factor_size=4,
        candidate_top_k=8,
        mcts_simulations=8,
        neural_mcts_simulations=8,
        max_polarities=4,
    )
    highdim_resource = synthesize("and_resource_nmcts", highdim_bf, highdim_config, seed=7)
    highdim_pareto = synthesize("and_pareto_resource_nmcts", highdim_bf, highdim_config, seed=7)
    assert highdim_resource.correct
    assert highdim_pareto.correct
    assert highdim_pareto.cost.score(highdim_config.weights) <= highdim_resource.cost.score(highdim_config.weights) + 1e-9
    affine_bf = boolean_from_anf(
        6,
        [
            0b001100,
            0b001101,
            0b011000,
            0b011001,
            0b101100,
            0b101101,
            0b110000,
            0b110001,
            0b111000,
        ],
    )
    affine_linear = synthesize("and_fprm_affine_linear_pair", affine_bf, config, seed=7)
    ordinary_linear = synthesize("and_fprm_linear_pair", affine_bf, config, seed=7)
    assert affine_linear.correct
    assert affine_linear.cost.score(config.weights) <= ordinary_linear.cost.score(config.weights) + 1e-9
    print("smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
