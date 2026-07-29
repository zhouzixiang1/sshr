#!/usr/bin/env python3
"""Invariant tests for the topology-aware Qiskit compilation layer."""
from __future__ import annotations

import math
import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import torch  # noqa: F401  (must load before qiskit_aer on Windows)
from qiskit import QuantumCircuit as QiskitCircuit

from src.anf_utils import anf_monomials, majority_function
from src.hardware_map import (
    CompileConfig,
    compile_for_target,
    make_cx_full_target,
    make_cx_line_target,
    make_cz_grid_target,
    make_ecr_heavy_hex_target,
    validate_target_support,
    verify_mapped_oracle,
)
from src.sshr_lib.bool_func import BooleanFunction
from src.sshr_lib.bool_func import QuantumCircuit as EngineCircuit


def _majority3_oracle() -> tuple[BooleanFunction, EngineCircuit]:
    bf = majority_function(3)
    circ = EngineCircuit(4)
    circ.add_mct([0, 1], 3)
    circ.add_mct([0, 2], 3)
    circ.add_mct([1, 2], 3)
    return bf, circ


class TargetFactoryTests(unittest.TestCase):
    def test_factory_widths_bases_and_hashes(self) -> None:
        specs = (
            (make_cx_full_target(5), 5, "cx"),
            (make_cx_line_target(5), 5, "cx"),
            (make_cz_grid_target(2, 3), 6, "cz"),
            (make_ecr_heavy_hex_target(3), 19, "ecr"),
        )
        for spec, width, entangler in specs:
            with self.subTest(target=spec.target_id):
                self.assertEqual(spec.num_qubits, width)
                self.assertIn(entangler, spec.basis_gates)
                self.assertIn(entangler, spec.to_target().operation_names)
                self.assertEqual(len(spec.config_hash()), 64)
                self.assertTrue(spec.normalized_edges)

    def test_illegal_coupling_is_detected(self) -> None:
        spec = make_cx_line_target(5)
        illegal = QiskitCircuit(5)
        illegal.cx(0, 4)
        violations = validate_target_support(illegal, spec.to_target())
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].reason, "unsupported_coupling_or_direction")

    def test_all_native_proxy_targets_compile_without_violations(self) -> None:
        bf = BooleanFunction(2, 1 << 3)
        circ = EngineCircuit(3)
        circ.add_mct([0, 1], 2)
        specs = (
            make_cx_full_target(5),
            make_cx_line_target(5),
            make_cz_grid_target(2, 3),
            make_ecr_heavy_hex_target(3),
        )
        for spec in specs:
            with self.subTest(target=spec.target_id):
                artifact = compile_for_target(
                    circ,
                    spec,
                    CompileConfig(optimization_level=1, seed_transpiler=5),
                    bf=bf,
                )
                self.assertEqual(artifact.metrics.unsupported_instructions, 0)
                self.assertEqual(artifact.metrics.coupling_violations, 0)
                self.assertEqual(artifact.metrics.highq_count, 0)
                self.assertTrue(set(spec.twoq_gates) & set(artifact.metrics.gate_counts))
                self.assertIsNotNone(artifact.verification)
                assert artifact.verification is not None
                self.assertTrue(artifact.verification.ok)
                self.assertEqual(artifact.verification.evaluated, 8)


class TopologyCompileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bf, cls.engine = _majority3_oracle()
        cls.artifact = compile_for_target(
            cls.engine,
            make_cx_line_target(7),
            CompileConfig(optimization_level=1, seed_transpiler=7),
            bf=cls.bf,
        )

    def test_mapped_majority_is_target_valid_and_exact(self) -> None:
        artifact = self.artifact
        self.assertEqual(artifact.metrics.unsupported_instructions, 0)
        self.assertEqual(artifact.metrics.coupling_violations, 0)
        self.assertEqual(artifact.metrics.highq_count, 0)
        self.assertEqual(len(artifact.initial_layout), artifact.work.num_qubits)
        self.assertEqual(len(artifact.final_layout), artifact.work.num_qubits)
        self.assertIsNotNone(artifact.verification)
        assert artifact.verification is not None
        self.assertTrue(artifact.verification.ok)
        self.assertEqual(artifact.verification.mode, "exact_xy_phase")
        self.assertEqual(artifact.verification.evaluated, 16)
        self.assertEqual(artifact.verification.mismatches, 0)
        self.assertLess(artifact.verification.max_leakage, 1e-8)
        self.assertLess(artifact.verification.max_phase_error, 1e-8)

    def test_phase_sensitive_verifier_rejects_probability_equivalent_error(self) -> None:
        corrupted = replace(
            self.artifact,
            mapped=self.artifact.mapped.copy(),
            verification=None,
        )
        # A terminal Rz on a data qubit preserves every truth-table probability
        # but adds an input-dependent relative phase.
        corrupted.mapped.rz(math.pi / 2, corrupted.final_layout[0])
        verification = verify_mapped_oracle(self.bf, corrupted)
        self.assertFalse(verification.ok)
        self.assertLess(verification.max_leakage, 1e-8)
        self.assertGreater(verification.max_phase_error, 0.5)

    def test_fixed_trivial_layout_exposes_routing_overhead(self) -> None:
        circ = EngineCircuit(5)
        circ.add_cnot(0, 4)
        artifact = compile_for_target(
            circ,
            make_cx_line_target(5),
            CompileConfig(
                optimization_level=1,
                layout_method="trivial",
                routing_method="sabre",
                seed_transpiler=11,
            ),
            verify=False,
        )
        self.assertEqual(artifact.metrics.basis_reference_twoq_count, 1)
        self.assertGreater(artifact.metrics.twoq_count, 1)
        self.assertGreater(artifact.metrics.routing_twoq_delta, 0)
        self.assertEqual(artifact.metrics.coupling_violations, 0)

    def test_same_seed_is_metric_and_layout_deterministic(self) -> None:
        repeated = compile_for_target(
            self.engine,
            make_cx_line_target(7),
            CompileConfig(optimization_level=1, seed_transpiler=7),
            bf=self.bf,
        )
        self.assertEqual(repeated.initial_layout, self.artifact.initial_layout)
        self.assertEqual(repeated.final_layout, self.artifact.final_layout)
        self.assertEqual(repeated.metrics.gate_counts, self.artifact.metrics.gate_counts)
        self.assertEqual(repeated.metrics.depth, self.artifact.metrics.depth)

    def test_clean_hls_ancillas_are_verified(self) -> None:
        bf = BooleanFunction(4, 1 << 15)
        circ = EngineCircuit(5)
        circ.add_mct([0, 1, 2, 3], 4)
        artifact = compile_for_target(
            circ,
            make_cx_line_target(7),
            CompileConfig(
                optimization_level=1,
                seed_transpiler=13,
                hls_ancilla_budget=2,
            ),
            bf=bf,
        )
        self.assertEqual(artifact.metrics.compiler_ancillas, 2)
        self.assertIsNotNone(artifact.verification)
        assert artifact.verification is not None
        self.assertTrue(artifact.verification.ok)
        self.assertEqual(artifact.verification.evaluated, 32)
        self.assertLess(artifact.verification.max_leakage, 1e-8)

    def test_arbitrary_oracle_inputs_are_never_borrowed_as_clean_hls_ancillas(self) -> None:
        """Regression for unsafe ``qubits_initially_zero=True`` MCX lowering."""
        bf = majority_function(5)
        circ = EngineCircuit(6)
        for mask in anf_monomials(bf):
            controls = [bit for bit in range(bf.n) if (mask >> bit) & 1]
            if not controls:
                circ.add_x(5)
            elif len(controls) == 1:
                circ.add_cnot(controls[0], 5)
            else:
                circ.add_mct(controls, 5)
        artifact = compile_for_target(
            circ,
            make_cx_full_target(12),
            CompileConfig(
                optimization_level=1,
                seed_transpiler=3,
                hls_ancilla_budget=0,
            ),
            bf=bf,
        )
        self.assertEqual(artifact.metrics.compiler_ancillas, 0)
        self.assertIsNotNone(artifact.verification)
        assert artifact.verification is not None
        self.assertTrue(artifact.verification.ok)
        self.assertEqual(artifact.verification.evaluated, 64)
        self.assertEqual(artifact.verification.mismatches, 0)

    def test_target_width_is_enforced(self) -> None:
        circ = EngineCircuit(6)
        with self.assertRaisesRegex(ValueError, "logical circuit needs 6"):
            compile_for_target(circ, make_cx_line_target(5), verify=False)


if __name__ == "__main__":
    unittest.main()
