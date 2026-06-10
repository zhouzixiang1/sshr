# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two independent quantum-circuit-synthesis research projects:

1. **SSHR oracle synthesis (`sshr/`)** — reproduction and extension of Zheng et al. (2025), "CNOT Oriented Synthesis for Small-Scale Boolean Functions Using Spatial Structures of Parallelotopes." The code synthesizes Boolean-function oracle circuits for small `n` using parallelotope covers, ILP, MCTS, and beam search.
2. **Sparse quantum state preparation paper (`tex/`)** — Chinese LaTeX paper source for "针对稀疏量子态制备的最优线路研究", using CjC journal style and GB/T 7714 bibliography.

The reference SSHR paper PDF is in `papers/`.

## Environments

Use direct interpreter paths; `conda run` has permission issues on this machine.

| Environment | Path | Use |
|---|---|---|
| `mcts-qoracle` | `/opt/anaconda3/envs/mcts-qoracle/bin/python` | SSHR-H, MCTS, Beam, enumeration, pytest tests |
| `sshr` | `/opt/anaconda3/envs/sshr/bin/python` | Gurobi-backed ILP scripts (`sshr_i.py`, `esop_ilp.py`) |

`gurobipy` is not installed in `mcts-qoracle`; use the `sshr` interpreter when you need Gurobi. No root-level `requirements.txt`, `pyproject.toml`, or setup file exists; dependencies are provided by these conda environments.

## Common Commands

### SSHR tests

```bash
cd /Users/zhouzixiang/Desktop/tzb/claude/sshr

# Main pytest suite
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ -v

# Run one pytest test
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/test_correctness.py::test_sshr_h_3majority -v

# Collect tests without running them
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ --collect-only -q

# MCTS correctness script; pytest collects 0 tests from this file
/opt/anaconda3/envs/mcts-qoracle/bin/python tests/test_mcts_correctness.py
```

`tests/test_correctness.py` currently collects 15 pytest tests. The SSHR-I pytest gracefully skips if `gurobipy` is unavailable, so run ILP-specific checks with `/opt/anaconda3/envs/sshr/bin/python` when you need real Gurobi coverage.

### SSHR paper-table and comparison experiments

```bash
cd /Users/zhouzixiang/Desktop/tzb/claude/sshr

# Table VIII: parallelotope search-space counts
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 8

# Tables IV/V: SSHR-H raw gates and cost totals
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 4 5 --n 3 4 5 6 --seed 42

# Tables VI/VII: SSHR-I ILP; use Gurobi environment
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_tables.py --n 3 4 --timeout 30
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_tables.py --n 5 --timeout 120 --cnot-only --fns 2000 --seed 42

# Resumable ILP sweep; checkpoint defaults to resume
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py --n 5 --objective cnot --fns 2000 --seed 42
/opt/anaconda3/envs/sshr/bin/python experiments/run_ilp_checkpoint.py --n 6 --objective cnot --fns 200 --timeout 600 --no-resume

# MCTS/Beam/SSHR-H comparison
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/mcts_beam_compare.py --n 3 4 5 6 7 8 --fns 2000 --workers 14
```

`run_ilp_tables.py` and `run_ilp_checkpoint.py` auto-select timeout when `--timeout` is omitted: 30s for `n<=4`, 120s for `n=5`, and the current `sshr_i.py` default is 7200s for `n>=6` when called directly.

### LaTeX paper build

```bash
cd /Users/zhouzixiang/Desktop/tzb/claude/tex
mkdir -p build
xelatex -interaction=nonstopmode -output-directory=build main_template.tex
cd build && BIBINPUTS=..: BSTINPUTS=..: bibtex main_template
cd ..
xelatex -interaction=nonstopmode -output-directory=build main_template.tex
xelatex -interaction=nonstopmode -output-directory=build main_template.tex

# Alternative if latexmk is preferred
latexmk -xelatex -outdir=build main_template.tex
```

Use XeLaTeX, not pdfLaTeX: `main_template.tex` loads `xeCJK` and local CjC/GB-T style assets. Build artifacts and generated PDFs are ignored by git.

## Repository Structure

```text
claude/
├── AGENTS.md                 # Existing agent context; root CLAUDE.md should stay consistent with it
├── papers/                   # Zheng2025 reference PDF
├── sshr/                     # SSHR implementation, experiments, tests, results
│   ├── *.py                  # Core algorithm modules, intentionally flat imports
│   ├── experiments/          # Reproducible experiment entrypoints and ILP checkpoints
│   ├── results/              # CSV/TXT result outputs
│   ├── tests/                # pytest suite plus direct MCTS script
│   ├── viz/                  # Circuit visualization utilities; generated images ignored
│   └── _archive/             # Historical debug/analysis/old experiment scripts
└── tex/                      # Monolithic Chinese LaTeX paper source and figures
```

There are no Cursor rules, `.cursorrules`, `.github/copilot-instructions.md`, root README, Makefile, or Python package metadata in this repository.

## SSHR Architecture

The `sshr/` code intentionally uses flat root-level modules rather than a Python package. Avoid adding subpackages unless you also update all bare imports.

### Data and geometry layer

- `bool_func.py` defines `BooleanFunction`, `QuantumCircuit`, `mct_cost()`, and `mct_cost_rp()`. Truth tables are integers; bit `x` stores `f(x)`. `QuantumCircuit.cost()` uses the standard MCT cost model, not RP-Toffoli.
- `parallelotope.py` defines `Parallelotope(v0, basis)`. Equality/hash are by vertex set. The constructor does not validate basis disjointness; callers/enumerators must supply valid bases.
- `parallelotope_enum.py` enumerates valid parallelotopes inside a universe. It omits dim-0 singletons unless `include_singletons=True`; several algorithms append singletons manually.
- `block_synth.py` implements Algorithm 1: parallelotope block to `QuantumCircuit`, with block cost helpers.

### Synthesis algorithms

| File | Role | Important semantics |
|---|---|---|
| `sshr_h.py` | SSHR-H greedy heuristic | Enumerates candidates from the full hypercube with `lru_cache(maxsize=8)`; updates active set with XOR/symmetric difference, so off-set vertices can be introduced. |
| `sshr_h_paper.py` | Strict paper-style SSHR-H | Re-enumerates from the current active set each loop; effectively monotone because candidates are subsets of active minterms. |
| `sshr_i.py` | SSHR-I ILP | Current code is Gurobi-only. CNOT objective uses SSHR-H as upper-bound/fallback. T objective is two-stage: minimize RP-T, then minimize CNOT under the optimal RP-T budget. |
| `sshr_mcts_v2.py` | Numpy-accelerated UCT MCTS | Monotone subset-removal semantics only (`vertices(P) ⊆ A`), with greedy incumbent and bitmask acceleration. Prefer v2 over `sshr_mcts.py`. |
| `sshr_beam.py` | Beam search | Monotone subset-removal semantics with greedy lower bound; often stronger than MCTS for `n<=6`. |
| `esop_ilp.py` | Exact ESOP ILP baseline | Gurobi over all `3^n` product-term cubes; no RP two-stage optimization. |
| `baselines.py` | Lightweight baselines | `xag_synthesize()` is a stub; `esop_exact()` is canonical minterm ESOP, not a minimum exact ESOP. |

Do not mix XOR semantics (`sshr_h.py`, `sshr_i.py`) with monotone semantics (`sshr_mcts_v2.py`, `sshr_beam.py`) when comparing algorithms or modifying state transitions.

### Reference data and reproduction sets

- `paper_data.py` encodes Zheng et al. Tables IV, V, VI, VII, and VIII plus this repo's reproduction results.
- `npn_reps_n4.py` provides `NPN_REPS_N4`, 222 NPN representatives including zero, with the optimal-complement convention needed to reproduce Table VI CNOT=4696 for `n=4`.
- ILP scripts use different test sets than `run_tables.py`:
  - `run_ilp_tables.py` / `run_ilp_checkpoint.py`: `n=3` uses 255 non-zero functions; `n=4` uses `NPN_REPS_N4` minus zero; `n>=5` uses random functions.
  - `run_tables.py`: `n<=4` uses all truth tables; `n>=5` uses 2000 random functions and does not expose a `--fns` flag.

## SSHR Experiment Output Notes

- `experiments/run_ilp_checkpoint.py` writes JSON checkpoints to `experiments/checkpoints/ilp_n{n}_{objective}_fns{fns}_seed{seed}.json` and resumes by default. Changing `--fns` or `--seed` creates a different checkpoint file.
- `experiments/mcts_beam_compare.py` appends to per-n CSVs, so repeated runs can duplicate rows. Its aggregate `comparison_all.csv` is overwritten for the current invocation only.
- `results/comparison/*.csv` columns are `n, method, n_functions, T, CNOT, ancilla, time_s`; `compare_n4.csv` has space-padded headers, so use `skipinitialspace=True` when parsing with pandas.
- `_archive/` is historical/debug material. Do not edit archived files; create new scripts in the appropriate live location or delete temporary scratch scripts after use.

## Layout Rules for `sshr/`

1. Keep core algorithms as root-level `sshr/*.py` files with bare imports.
2. Put formal reproducible experiment entrypoints in `sshr/experiments/`, named `run_<purpose>.py` when applicable.
3. Put generated experiment outputs under `sshr/results/`, not under `experiments/`.
4. Treat `sshr/experiments/checkpoints/` as generated/resumable state; do not hand-edit unless explicitly repairing a checkpoint.
5. Keep scratch/debug scripts out of the live paths; either delete them or archive them under `_archive/`.

## LaTeX Architecture

`tex/main_template.tex` is monolithic; there are no `\input`/`\include` child files. It uses local `CjC.cls`, `gbt7714-numerical.bst`, `captionhack.sty`, `picins.sty`, `ref.bib`, and images under `tex/figure/`. One referenced figure path contains a literal space: `figure/CCCG_D/all_D_CCCX _1.png`; do not rename it casually.
