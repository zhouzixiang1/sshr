# Dependency groups

- `core.txt`: XA logical synthesis, learned policy/value checkpoint loading,
  NumPy QAOA, SciPy MILP, synthetic native mapping/noise, and the competition
  demo.  `PuLP` remains in this frozen core contract for compatibility with the
  recorded experiment environment and is exercised by the installation
  self-check; the current built-in ESOP MILP implementation uses SciPy.
- `dev.txt`: core plus the checked-in pytest suite.
- `optional-sshr-gurobi.txt`: SSHR-I only.  `gurobipy` and a separately managed
  Gurobi licence are both required; neither is a condition for the XA demo.
- `quantum.txt`: optional Qiskit/Aer/QNN interoperability.  The checked-in QAOA,
  native mapper, and Pauli-trajectory simulator do not depend on Qiskit.
- `research.txt`: optional GFlowNet and model-comparison work.
- `server.txt`: planned FastAPI experiment control plane.

The frozen environment is CPython 3.11.15 with the exact versions in
`core.txt`; `dev.txt` adds the verified pytest version.  These pins describe the
reproduction environment, not support for every Python, operating-system, or
accelerator combination.

The repository also provides `../environment.yml` as the single-file Conda
entry point.  Its Python and pip-package versions mirror `core.txt` and
`dev.txt`; when either requirements file changes, the environment file must be
updated in the same revision.

From the `experiments/` directory, the Conda route is:

```bash
conda env create -f environment/environment.yml
conda run -n xa202609 python scripts/verify_clean_install.py
```

From the `experiments/` directory, install and verify the CPU/local runtime:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r environment/requirements/dev.txt
.venv/bin/python scripts/verify_clean_install.py
```

The verifier uses only repository-relative paths.  Its default mode checks
dependency versions and imports, loads the frozen foundation checkpoint, runs
small SciPy/PuLP API probes, a direct QAOA mini-case, a synthetic native/noise
mini-case, the legacy smoke suite, and the complete competition demo in a
temporary directory.  For a fast diagnostic that skips the two subprocess
workloads:

```bash
python scripts/verify_clean_install.py --quick
```

`--quick` is not a clean-install acceptance result.  It still checks the demo
CLI, but it does not execute the full AES demo or legacy smoke suite.

For an NVIDIA server, install the CUDA-compatible PyTorch wheel selected for
that server before installing the remaining requirements.  Do not copy the
macOS MPS environment or a local Conda prefix to Linux.  A passing verifier
establishes this offline software contract only; it does not validate Gurobi,
Qiskit, real calibration data, or quantum hardware.
