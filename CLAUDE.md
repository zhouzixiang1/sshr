# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reproduction and extension of the SSHR algorithm from "CNOT Oriented Synthesis for Small-Scale Boolean Functions Using Spatial Structures of Parallelotopes" (Zheng et al., 2025). The project synthesizes quantum circuit oracles for small Boolean functions (n=3–8 variables) using geometric parallelotope structures, minimizing CNOT/T gate counts.

## Environment

All code runs in the `mcts-qoracle` conda environment. Use the direct interpreter path (conda run has permission issues on this machine):

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python <script>.py
```

Key dependency: **Gurobi** (`gurobipy`) is required for ILP solvers (SSHR-I, ESOP ILP). Not needed for SSHR-H or enumeration.

## Main Code Areas

### `src/` — Main project directory

This directory is the Git repository and contains the SSHR implementation, AI-SSHR experiments, GNN-SSHR project, paper assets, and project-level guidance files.

### `src/sshr/` — Core SSHR implementation

Contains the core SSHR algorithms and extensive experiment scripts. See `src/sshr/CLAUDE.md` for full documentation.

Key additions beyond `src/`:
- **SSHR-MCTS v2** (`sshr_mcts_v2.py`) — Numpy-accelerated UCT Monte Carlo tree search, 4–5x faster than v1
- **SSHR-Beam** (`sshr_beam.py`) — Beam search synthesis, outperforms MCTS at n≤6
- **SSHR-H variant** (`sshr_h_paper.py`) — Faithful paper implementation (enumerates from current onset, not full hypercube)
- **ESOP ILP** (`esop_ilp.py`) — Exact ESOP solver for comparison
- NPN representative constants for n=4 (`npn_reps_n4.py`)

```bash
cd src/sshr && /opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ -v
/opt/anaconda3/envs/mcts-qoracle/bin/python src/sshr/experiments/run_tables.py --tables 8
```

### `src/ai_sshr_experiment/` — AI-SSHR prototype

Early AI-guided search and pruning experiments using rule rankers, LightGBM rankers, XOR-Beam, and pruned ILP utilities.

### `src/gnn-sshr/` — GNN-SSHR project

Self-contained GNN/LightGBM candidate-pruning project. It copies the SSHR core into `src/gnn-sshr/src/sshr_core/` so experiments remain isolated from changes in `src/sshr/`.

### `src/tex/` — LaTeX paper source

Chinese paper source, bibliography, journal styles, and figures.

## Algorithm Summary

| Algorithm | File | Method | Update Semantics | Scalability |
|-----------|------|--------|-----------------|-------------|
| SSHR-H | `sshr_h.py` | Greedy, R=3/4 threshold | XOR (allows off-set contamination) | n≤8 |
| SSHR-I | `sshr_i.py` | ILP parity cover (Gurobi) | XOR | n≤6 (timeout beyond) |
| ESOP | `esop.py` | ILP over product terms {0,1,*}^n | XOR | n≤6 |
| SSHR-MCTS v2 | `sshr_mcts_v2.py` | UCT with numpy rollout | Set subtract (monotone) | n≤7 |
| SSHR-Beam | `sshr_beam.py` | Beam search + greedy lower bound | Set subtract (monotone) | n≤6 |

XOR semantics (`src/` and `src/sshr/`) match the paper but cause cascading pollution at n≥7. Monotone semantics (MCTS/Beam) avoid this at the cost of restricted candidate set.

## Key Domain Concepts

- **Bitmask convention**: Sets of minterms are represented as Python integers throughout. Bit k set = minterm k is in the set.
- **Parallelotope**: A geometric block in {0,1}^n defined by a base pattern and disjoint basis vectors. Equivalent to a grouped-flipping-variable structure. Dimension = number of basis vectors; size = 2^dimension.
- **Parity cover (WP-SCP)**: Each minterm in on-set must be covered by an odd number of blocks; off-set by an even number. This is the ILP formulation.
- **Candidate counts** (Table VIII): n=3→49, n=4→257, n=5→1539, n=6→10299, n=7→75905, n=8→609441. Enumeration is the performance bottleneck for large n.

## Other Directories

- `ECC/` — Elliptic curve discrete logarithm quantum resource papers (5 PDFs)
- `lunwen/` — Logic synthesis / quantum compilation papers (11 PDFs)
- `src1/` — Reference paper copy (1 PDF)
- `榜题方案汇总材料/` — Competition proposal materials across multiple regions and domains
