# sshr/ — Core Implementation

This directory contains the core Python implementation for **"CNOT Oriented Synthesis for Small-Scale Boolean Functions Using Spatial Structures of Parallelotopes"** (Zheng et al., 2025).

## File Organization

### Core Primitives
- `bool_func.py` — `BooleanFunction` and `QuantumCircuit` data structures
- `parallelotope.py` — `Parallelotope` geometry data structure
- `parallelotope_enum.py` — Bottom-up BFS enumeration of valid parallelotopes
- `block_synth.py` — Algorithm 1: parallelotope → quantum circuit block

### Synthesis Algorithms
- `sshr_h.py` — Algorithm 2: SSHR-H (greedy heuristic)
- `sshr_h_paper.py` — Strict paper version of SSHR-H (enumerates from current onset)
- `sshr_i.py` — Algorithm 3: SSHR-I (ILP exact/optimal, **Gurobi only**)
- `sshr_mcts.py` — SSHR-MCTS v1 (UCT with Python loops)
- `sshr_mcts_v2.py` — SSHR-MCTS v2 (numpy-accelerated, recommended)
- `sshr_beam.py` — SSHR-Beam (beam search)

### Baselines & Data
- `baselines.py` — ESOP and XAG baseline synthesis
- `esop_ilp.py` — Exact ESOP formulation (WP-SCP with Gurobi)
- `npn_reps_n4.py` — Pre-computed 222 NPN canonical representatives for n=4
- `paper_data.py` — Hard-coded reference data from the paper (Tables IV–VIII)

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `analysis/` | One-off diagnostic and tuning scripts |
| `debug/` | Historical debugging scripts (read-only, not maintained) |
| `experiments/` | Paper reproduction and comparison experiments |
| `experiments/greedy/` | SSHR-H specific experiment scripts |
| `experiments/ilp/` | ILP-specific reproduction scripts (Table VI/VII) |
| `experiments/mcts/` | MCTS and Beam search experiment scripts |
| `results/` | CSV result files from benchmark runs |
| `results/comparison/` | Multi-method comparison CSVs |
| `results/mcts/` | MCTS-specific result files |
| `tests/` | pytest correctness tests |
| `viz/` | Circuit visualization scripts |

## Running Tests

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pytest tests/ -v
```

## Reproducing Paper Tables

```bash
# Table VIII (optimization space sizes)
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 8

# Tables IV/V (SSHR-H)
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 4 5 --n 3 4 5 6

# Table VI/VII (SSHR-I, requires Gurobi)
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/ilp/run_ilp_tables.py
```
