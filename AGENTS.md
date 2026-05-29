# AGENTS.md

This file provides context for AI coding agents working on this repository.

## Project Overview

This repository contains the implementation and paper materials for **"CNOT Oriented Synthesis for Small-Scale Boolean Functions Using Spatial Structures of Parallelotopes"** (Zheng et al., 2025).

The core codebase lives in `sshr/` and implements several quantum circuit synthesis algorithms that translate small-scale Boolean functions (n ≤ 8 variables) into reversible quantum oracles using multi-controlled Toffoli (MCT) gates. The key idea is to exploit geometric structures called *parallelotopes* in the Boolean hypercube to cover multiple minterms with a single circuit block, reducing T-count and CNOT count compared to traditional ESOP or XAG baselines.

The `tex/` directory contains LaTeX source files, figures, and bibliography for the paper.

## Technology Stack

- **Language**: Python 3.8+
- **Numerical computing**: `numpy` (required for MCTS and Beam search acceleration)
- **ILP solver**: `gurobipy` — commercial, required for SSHR-I and ESOP-ILP; needs a Gurobi license
- **Testing**: `pytest`
- **Visualization**: `matplotlib` (for circuit diagrams)
- **Environment**: The project is developed and run inside a Conda environment named `mcts-qoracle` located at `/opt/anaconda3/envs/mcts-qoracle/`. Direct path invocation is preferred over `conda run` due to local permission issues.

No `pyproject.toml`, `setup.py`, `requirements.txt`, or `Makefile` exists. Dependencies are managed manually inside the Conda environment.

## Directory Structure

```
<root>
├── sshr/                  # Core Python implementation
│   ├── bool_func.py       # BooleanFunction and QuantumCircuit primitives
│   ├── parallelotope.py   # Parallelotope geometry data structure
│   ├── parallelotope_enum.py  # Bottom-up BFS enumeration of valid parallelotopes
│   ├── block_synth.py     # Algorithm 1: parallelotope → quantum circuit block
│   ├── sshr_h.py          # Algorithm 2: SSHR-H (greedy heuristic)
│   ├── sshr_i.py          # Algorithm 3: SSHR-I (ILP exact/optimal)
│   ├── sshr_mcts.py       # SSHR-MCTS v1 (UCT with Python loops)
│   ├── sshr_mcts_v2.py    # SSHR-MCTS v2 (numpy-accelerated, recommended)
│   ├── sshr_beam.py       # SSHR-Beam (beam search, newest method)
│   ├── baselines.py       # ESOP and XAG baseline synthesis
│   ├── esop_ilp.py        # ESOP ILP exact formulation for comparison
│   ├── npn_reps_n4.py     # Pre-computed NPN canonical representatives for n=4
│   ├── paper_data.py      # Reference data from the paper (Tables IV–VIII)
│   ├── analysis/          # One-off diagnostic / tuning scripts
│   ├── experiments/       # Paper reproduction and comparison experiments
│   │   └── ilp/           # ILP-specific reproduction scripts (Table VI/VII)
│   ├── tests/             # pytest correctness tests
│   ├── viz/               # Circuit visualization scripts and PNG outputs
│   ├── results/           # CSV result files from prior runs
│   └── debug/             # Historical debugging scripts (not maintained)
├── tex/                   # LaTeX paper source
└── papers/                # Paper PDFs and related documents
```

## Build and Run Commands

Because there is no formal build system, scripts are run directly with the Conda interpreter:

```bash
# Run any script
cd sshr
/opt/anaconda3/envs/mcts-qoracle/bin/python <script>.py

# Run the full test suite
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ -v

# Reproduce paper tables (example: Table VIII — optimization space sizes)
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 8

# Reproduce Tables IV/V for n=3,4,5,6 with SSHR-H
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 4 5 --n 3 4 5 6

# Reproduce Table VI (SSHR-I CNOT objective) — requires an ILP solver
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 6 --n 3 4 5

# Reproduce Table VII (SSHR-I T objective) — requires an ILP solver
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 7 --n 3 4 5
```

## Code Organization and Module Divisions

### Core Pipeline (dependency order)

1. **`bool_func.py`** — Primitives
   - `BooleanFunction(n, truth_table_int)` represents an n-variable Boolean function.
   - `QuantumCircuit(n_qubits)` stores a gate list and supports `add_cnot`, `add_x`, `add_mct`, `add_block`, `simulate`, and `cost`.
   - `mct_cost(k)` and `mct_cost_rp(k)` return decomposition costs (T-count, CNOT, ancilla) for a k-control MCT gate. Relative-phase Toffoli (`rp`) uses T=4 for k=2 instead of T=7.

2. **`parallelotope.py`** — Geometry
   - `Parallelotope(v0, basis)` defines a k-dimensional parallelotope in the n-dimensional Boolean hypercube.
   - Lemma 1 invariant: basis vectors must have pairwise disjoint bit-supports (`alpha_i & alpha_j == 0`).
   - `vertices()` lazily computes the 2^k vertices as a `frozenset` via XOR closure.

3. **`parallelotope_enum.py`** — Enumeration
   - `enumerate_parallelotopes(universe, n)` performs bottom-up BFS: dim-1 segments first, then extend to higher dimensions while preserving Lemma 1 and ensuring all vertices stay inside `universe`.
   - Returns a list sorted by **descending dimension**.
   - Complexity grows quickly: n=5 → ~1.5K, n=6 → ~10K, n=7 → ~76K, n=8 → ~609K parallelotopes.

4. **`block_synth.py`** — Algorithm 1
   - `synth_block(p, n)` converts a single parallelotope into a circuit block: CNOT chain → X gates → (n−m)-MCT → undo X gates → undo CNOT chain.
   - `block_cnot_cost(p, n)` and `block_t_cost(p, n)` estimate costs without building the circuit.

5. **`sshr_h.py`** — Algorithm 2 (Greedy Heuristic)
   - `sshr_h(bf, R=3/4)` enumerates candidates **once** from the full hypercube, then iteratively picks the highest-dim parallelotope with `|A ∩ P| / |P| ≥ R`.
   - Updates the residual set `A` via **XOR** (`A ^= vertices(P)`), which means off-set points can enter `A`.
   - Remaining points after the loop are handled as dim-0 singletons (n-MCT gates).
   - Uses `@lru_cache(maxsize=8)` on `_full_hypercube_parallelotopes(n)` so that repeated calls for the same `n` reuse the candidate set.

6. **`sshr_i.py`** — Algorithm 3 (ILP Exact)
   - `sshr_i(bf, objective="cnot"|"t", timeout=120)` formulates synthesis as a **Weighted Parity Set Covering Problem (WP-SCP)**.
   - Constraints: on-set minterms must be covered an **odd** number of times; off-set minterms must be covered an **even** number of times.
   - Solver: **Gurobi only**. Falls back to `sshr_h` if the solver produces no solution.
   - T-objective uses a two-stage optimization (minimize T first, then minimize CNOT at that optimal T) with relative-phase Toffoli costs.
   - Only feasible for n ≤ 5 in practice; n ≥ 6 typically times out.

7. **`sshr_mcts.py` / `sshr_mcts_v2.py`** — Monte Carlo Tree Search
   - Both implement UCT with domain-informed greedy rollout.
   - **Critical semantic difference from SSHR-H**: MCTS requires `vertices(P) ⊆ A` (monotone subset removal), so off-set contamination is impossible.
   - `sshr_mcts_v2.py` is the recommended version. It pre-computes numpy arrays for all parallelotopes and uses bitwise vectorized validity checks `(P & A) == P`, yielding a ~4–5× overall speedup over v1.
   - Supports ε-greedy rollouts (`epsilon > 0`) and progressive widening for large action spaces.

8. **`sshr_beam.py`** — Beam Search
   - `sshr_beam(bf, width=50, branch=10, objective="cnot")` maintains `width` partial paths and expands each with the top `branch` actions.
   - Scores states by `cost_so_far + greedy_lb(A)` and keeps the best `width` candidates.
   - Uses the same numpy engine design as `sshr_mcts_v2`.
   - Recommended parameters: n≤6 → `width=50, branch=10`; n=7 → `width=20, branch=5`.

### Supporting Modules

- **`baselines.py`** — `esop_synthesize` (greedy cube-cover ESOP) and XAG stubs.
- **`esop_ilp.py`** — Exact ESOP formulation for baseline comparison.
- **`npn_reps_n4.py`** — Pre-computed 222 NPN canonical representatives for n=4.
- **`paper_data.py`** — Hard-coded reference values from the paper for validation.

### Experiments and Analysis

- **`experiments/run_tables.py`** — Main reproduction entry point for Tables IV–VIII.
- **`experiments/evaluate.py`** — Generic evaluation harness with per-table logic.
- **`experiments/run_sshrh_n56.py`, `run_npn_n4.py`, `run_table6_n5.py`, etc.** — Individual table scripts.
- **`experiments/quick_*.py`** — Fast smoke-test scripts that run a small sample instead of the full 2000-function benchmark.
- **`analysis/`** — Development-time diagnostic scripts (e.g., `approach_paper.py`, `tiebreak_study.py`). These are not maintained as primary entry points.

## Testing Strategy

Tests are located in `sshr/tests/` and run with pytest.

- **`tests/test_correctness.py`**:
  - Verifies MCT cost table against paper Table II.
  - Verifies parallelotope geometry and enumeration invariants.
  - Verifies `synth_block` simulation correctness on individual blocks.
  - Verifies `sshr_h` correctness on:
    - 3-Majority function
    - Paper example `0x46B9`
    - **All 256** 3-bit Boolean functions
    - A random sample of 200 4-bit functions
  - Conditionally tests `sshr_i` on the paper example if PuLP/Gurobi is available.

- **`tests/test_mcts_correctness.py`**:
  - Runs `sshr_mcts` (v1) on all 255 non-zero 3-bit functions and checks simulation correctness.
  - Also spot-checks 10 random 4-bit functions.

### Running Tests

```bash
cd sshr
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ -v
```

No CI configuration files (GitHub Actions, etc.) are present. Testing is local and manual.

## Code Style Guidelines

- **Docstrings**: All modules and public functions have docstrings in **English**.
- **Comments**: Mixed English inline comments; no Chinese in source files (only in `sshr/CLAUDE.md`).
- **Typing**: Use `from __future__ import annotations` at the top of every file. Type hints are present on function signatures.
- **Naming**: `snake_case` for functions and variables, `PascalCase` for classes.
- **Imports**: Standard library first, then third-party (`numpy`), then local modules.
- **Data structures**: Prefer `frozenset` for deduplication of parallelotope vertices. Use `List`, `Tuple`, `Dict`, `Optional`, `FrozenSet` from `typing`.
- **Performance-sensitive paths** (MCTS/Beam):
  - Pre-compute Python lists (`costs_list`, `bitmasks_list`, `sizes_list`) alongside numpy arrays for circuit reconstruction.
  - Use `np.uint64` bitmasks for n ≤ 6, split `lo`/`hi` uint64 arrays for n = 7, and fall back to Python `int` object arrays for n = 8.

## Important Algorithmic Conventions

### Update Semantics

| Algorithm | Update Rule | Meaning |
|-----------|-------------|---------|
| SSHR-H / SSHR-I | `A ← A ⊕ vertices(P)` | XOR / symmetric difference; off-set points may re-enter `A` |
| SSHR-MCTS / SSHR-Beam | `A ← A − vertices(P)`, requiring `vertices(P) ⊆ A` | Monotone shrinking; no off-set contamination |

When modifying any synthesis algorithm, preserve the update semantics specific to that algorithm. Do not mix XOR semantics into MCTS/Beam or vice versa.

### MCT Cost Model (Table II)

| Controls k | T-count | CNOT | Ancilla |
|-----------|---------|------|---------|
| 1 (CNOT) | 0 | 1 | 0 |
| 2 (Toffoli) | 7 (standard) / 4 (relative-phase) | 6 | 0 |
| 3 | 16 | 14 | 1 |
| ≥4 | 8k − 8 | 4k − 6 | ⌈(k−2)/2⌉ |

`mct_cost_rp` switches k=2 to T=4; all other k use standard costs.

### Circuit Convention

- All synthesized circuits use **n + 1 qubits**.
- The **last qubit** (index `n`) is the output / target qubit.
- `QuantumCircuit.simulate(input_bits)` performs classical bit-wise simulation and is the ground-truth for correctness verification.

## Security Considerations

- This is a **pure research / offline computation** project. There are no network services, user inputs, or credential stores.
- `gurobi.log` may appear in the working directory; it contains solver timestamps and model statistics but no sensitive data.
- `.gitignore` already excludes `__pycache__`, `*.pyc`, `.pytest_cache/`, and `.DS_Store`.
- No external API keys or secrets are required. The only optional commercial dependency is Gurobi, which must be licensed separately by the user.

## Tips for Agents

- When adding a new synthesis algorithm, place it as a new top-level file in `sshr/` and follow the existing pattern: accept `BooleanFunction`, return `QuantumCircuit(n+1)`.
- When adding experiments, place them in `sshr/experiments/` and import `make_test_set` from `run_tables.py` or `evaluate.py` to ensure consistent test-set generation (seed=42, 2000 random functions for n≥5).
- If you need to optimize hot paths, replicate the numpy bitmask engine pattern from `sshr_mcts_v2.py` or `sshr_beam.py`.
- Before claiming a result matches the paper, compare against the hard-coded reference data in `sshr/paper_data.py`.
- The `sshr/debug/` directory contains many historical scripts; treat them as read-only references rather than code to refactor or extend.
