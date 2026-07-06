#!/usr/bin/env python3
"""Smoke tests for resource-constrained neural MCTS synthesis."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from anf_utils import anf_monomials, boolean_from_anf, majority_function, parity_function
from export_benchmarks import export_suite, selected_formats
from factor_plan import SearchConfig
from resource_model import ResourceWeights
from synthesizers import synthesize


def check_roundtrip() -> None:
    for n in range(1, 5):
        for tt in range(1 << (1 << n)):
            if n == 4 and tt > 512:
                break
            bf = boolean_from_anf(n, anf_monomials(boolean_from_anf(n, anf_monomials(boolean_from_anf(n, [])))))
            del bf
            from bool_func import BooleanFunction

            original = BooleanFunction(n, tt)
            rebuilt = boolean_from_anf(n, anf_monomials(original))
            assert rebuilt.truth_table == original.truth_table


def main() -> int:
    check_roundtrip()
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
        and_fprm_linear_deep = synthesize("and_fprm_linear_pair_deep", bf, config, seed=7)
        and_affine = synthesize("and_affine_nmcts", bf, config, seed=7)
        rc_nmcts = synthesize("and_rc_nmcts", bf, config, seed=7)
        resource_nmcts = synthesize("and_resource_nmcts", bf, config, seed=7)
        for result in [direct, greedy, mcts, fprm, cube_greedy, cube_beam, and_fprm, and_fprm_neural, and_fprm_linear, and_fprm_linear_deep, and_affine, rc_nmcts, resource_nmcts]:
            assert result.correct, (result.method, bf.n, bf.truth_table)
        assert greedy.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert mcts.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert fprm.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_fprm.cost.T <= direct.cost.T
        assert and_fprm_neural.cost.T <= direct.cost.T
        assert and_fprm_linear.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_fprm_linear_deep.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert and_affine.cost.T <= direct.cost.T
        assert rc_nmcts.cost.score(config.weights) <= direct.cost.score(config.weights) + 1e-9
        assert resource_nmcts.cost.score(config.weights) <= and_affine.cost.score(config.weights) + 1e-9
    print("smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
