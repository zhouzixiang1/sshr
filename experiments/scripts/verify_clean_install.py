#!/usr/bin/env python3
"""Verify the minimal XA-202609 install and offline execution contract.

The default run includes the legacy smoke suite and the competition demo in a
temporary directory.  ``--quick`` keeps only deterministic in-process probes
plus a demo CLI check; it is useful for diagnosis but is not clean-install
acceptance evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORE_REQUIREMENTS = PROJECT_ROOT / "environment" / "requirements" / "core.txt"
MODEL_PATH = PROJECT_ROOT / "models" / "boolean_oracle_fm_v3.pt"
MODEL_SHA256 = "87904409966e6d9d18aae3711dff54d696608e6eefcf0e5cb5bb98ae96d4f57d"
MODEL_PARAMETER_COUNT = 60_450
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _exact_requirements(path: Path) -> dict[str, str]:
    """Read the exact pins used by the frozen core contract."""

    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-r"):
            continue
        if "==" not in line:
            raise ValueError(f"core requirement is not exactly pinned: {line}")
        distribution, version = (part.strip() for part in line.split("==", 1))
        pins[distribution] = version
    return pins


def _dependency_probe() -> dict[str, Any]:
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError(
            "the frozen XA environment requires CPython 3.11; "
            f"found {sys.version.split()[0]}"
        )
    pins = _exact_requirements(CORE_REQUIREMENTS)
    modules = {"numpy": "numpy", "scipy": "scipy", "PuLP": "pulp", "torch": "torch"}
    installed: dict[str, str] = {}
    for distribution, expected in pins.items():
        module_name = modules[distribution]
        importlib.import_module(module_name)
        actual = importlib.metadata.version(distribution)
        if actual != expected:
            raise RuntimeError(
                f"{distribution} version mismatch: expected {expected}, found {actual}"
            )
        installed[distribution] = actual

    # Exercise both optimization APIs rather than treating import alone as the
    # contract.  The current synthesizer uses SciPy MILP; PuLP is retained for
    # compatibility with the frozen experiment environment.
    import numpy as np
    import pulp
    from scipy.optimize import Bounds, LinearConstraint, milp

    scipy_result = milp(
        c=np.array([1.0]),
        integrality=np.array([1]),
        bounds=Bounds([0.0], [1.0]),
        constraints=LinearConstraint([[1.0]], [1.0], [1.0]),
    )
    if not scipy_result.success or not np.allclose(scipy_result.x, [1.0]):
        raise RuntimeError("SciPy MILP one-variable probe did not solve exactly")
    problem = pulp.LpProblem("xa_install_probe", pulp.LpMinimize)
    variable = pulp.LpVariable("x", lowBound=0, upBound=1, cat="Binary")
    problem += variable
    if problem.name != "xa_install_probe" or len(problem.variables()) != 1:
        raise RuntimeError("PuLP model-construction probe failed")

    return {
        "python": sys.version.split()[0],
        "pins": installed,
        "imports_ok": sorted(modules.values()),
        "scipy_milp_probe": True,
        "pulp_model_probe": True,
    }


def _model_probe() -> dict[str, Any]:
    from src.foundation.adapter import FoundationScorer
    from src.synthesizers import FOUNDATION_MODEL, synthesize

    if FOUNDATION_MODEL.resolve() != MODEL_PATH.resolve():
        raise RuntimeError("public synthesizer model path drifted from the install contract")
    digest = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    if digest != MODEL_SHA256:
        raise RuntimeError(
            f"foundation checkpoint SHA-256 mismatch: expected {MODEL_SHA256}, "
            f"found {digest}"
        )
    scorer = FoundationScorer.from_checkpoint(MODEL_PATH)
    parameters = sum(parameter.numel() for parameter in scorer.model.parameters())
    if parameters != MODEL_PARAMETER_COUNT or not callable(synthesize):
        raise RuntimeError("foundation checkpoint or public synthesize entry point is invalid")
    return {
        "checkpoint": MODEL_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "checkpoint_sha256": digest,
        "checkpoint_bytes": MODEL_PATH.stat().st_size,
        "parameters": parameters,
        "device": str(scorer.device),
        "public_entrypoint": "src.synthesizers.synthesize",
    }


def _qaoa_probe() -> dict[str, Any]:
    from src.search.qaoa_scheduler import run_qaoa

    result = run_qaoa(
        linear={0: -1.0, 1: -1.0, 2: -1.0},
        p=1,
        seed=7,
        shots=128,
    )
    if result.bitstring != (1, 1, 1) or result.repaired or not result.is_feasible:
        raise RuntimeError("direct QAOA mini-case returned an invalid selection")
    if result.diagnostics.get("execution_mode") != "direct_qaoa_statevector":
        raise RuntimeError("QAOA mini-case did not use the direct statevector path")
    return {
        "backend": result.diagnostics["backend"],
        "execution_mode": result.diagnostics["execution_mode"],
        "bitstring": list(result.bitstring),
        "energy": result.energy,
        "repaired": result.repaired,
        "hardware_execution": False,
    }


def _native_noise_probe() -> dict[str, Any]:
    from src.hardware.noise import PauliNoiseModel, simulate_noisy_shots
    from src.hardware.superconducting import compile_superconducting, linear_profile
    from src.sshr_lib.bool_func import QuantumCircuit

    circuit = QuantumCircuit(2)
    circuit.add_x(0)
    circuit.add_cnot(0, 1)
    compiled = compile_superconducting(circuit, linear_profile(2))
    executed = simulate_noisy_shots(
        compiled,
        (0, 0),
        shots=16,
        seed=202609,
        noise_model=PauliNoiseModel(parameter_source="clean-install-zero"),
    )
    native_names = sorted({gate.name for gate in compiled.native_gates})
    if not set(native_names) <= {"rz", "sx", "x", "cx"}:
        raise RuntimeError(f"unexpected native gate set: {native_names}")
    if executed.counts != {"11": 16} or not executed.actual_noisy_simulation:
        raise RuntimeError("native/noise mini-case failed deterministic zero-noise execution")
    if executed.hardware_execution:
        raise RuntimeError("offline simulator incorrectly reported hardware execution")
    return {
        "profile": compiled.profile.name,
        "profile_synthetic": compiled.profile.synthetic,
        "native_gate_set": native_names,
        "actual_noisy_simulation": executed.actual_noisy_simulation,
        "shots": executed.shots,
        "success_rate": executed.success_rate,
        "hardware_execution": executed.hardware_execution,
    }


def _run_checked(command: list[str], *, expected: str) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or expected not in completed.stdout:
        tail = "\n".join(completed.stdout.splitlines()[-20:])
        raise RuntimeError(
            f"command failed or omitted {expected!r} (exit={completed.returncode}):\n{tail}"
        )
    return {"exit_code": completed.returncode, "expected_marker": expected}


def _demo_cli_probe() -> dict[str, Any]:
    result = _run_checked(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "demo_competition.py"), "--help"],
        expected="--synthesizer",
    )
    result["executed"] = False
    return result


def _smoke_probe() -> dict[str, Any]:
    return _run_checked(
        [sys.executable, str(PROJECT_ROOT / "tests" / "tests_smoke.py")],
        expected="smoke ok",
    )


def _demo_probe() -> dict[str, Any]:
    with TemporaryDirectory(prefix="xa-clean-install-demo-") as tmp:
        output = Path(tmp) / "output"
        result = _run_checked(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "demo_competition.py"),
                "--case",
                "aes_sbox_bit0",
                "--synthesizer",
                "foundation_nmcts",
                "--scheduler",
                "qaoa_diversity",
                "--hardware",
                "superconducting_noise",
                "--output",
                str(output),
                "--workers",
                "2",
            ],
            expected="verification_ok=true",
        )
        verification = json.loads(
            (output / "verification.json").read_text(encoding="utf-8")
        )
        report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        if not verification.get("ok"):
            raise RuntimeError("competition demo verifier returned ok=false")
        if not report["quantum_for_ai"]["direct_non_fallback"]:
            raise RuntimeError("competition demo did not return direct non-fallback QAOA")
        if report["native_and_noise"]["hardware_execution"]:
            raise RuntimeError("competition demo incorrectly reported hardware execution")
        result.update(
            {
                "executed": True,
                "verification_ok": True,
                "direct_non_fallback": True,
                "hardware_execution": False,
                "performance_evidence": report["scope"]["performance_evidence"],
            }
        )
        return result


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="skip legacy smoke and full competition demo execution",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    checks: list[tuple[str, Callable[[], dict[str, Any]]]] = [
        ("dependencies", _dependency_probe),
        ("foundation_model", _model_probe),
        ("qaoa_direct_mini", _qaoa_probe),
        ("native_noise_mini", _native_noise_probe),
    ]
    if args.quick:
        checks.append(("competition_demo", _demo_cli_probe))
    else:
        checks.extend((("legacy_smoke", _smoke_probe), ("competition_demo", _demo_probe)))

    report: dict[str, Any] = {
        "schema_version": "xa.clean-install-verification.v1",
        "mode": "quick" if args.quick else "full",
        "project_root_is_relative_contract": True,
        "checks": {},
        "ok": False,
        "claim_boundary": (
            "Offline software verification only: no Gurobi licence, Qiskit stack, "
            "real calibration, quantum hardware, speedup, or quantum advantage is validated."
        ),
    }
    try:
        for name, check in checks:
            report["checks"][name] = {"ok": True, **check()}
    except Exception as exc:  # emit a machine-readable failure before exiting
        report["checks"][name] = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    report["ok"] = True
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
