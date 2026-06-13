# AI-SSHR Experiment Prototype

This folder contains a standalone prototype for AI-SSHR experiments.
It does not modify the existing `sshr/` implementation. Instead, it imports
the current SSHR modules and adds a thin experimental layer for:

- candidate parallelotope feature extraction;
- rule-based ranker interface;
- AI-guided beam search;
- candidate pruning for WP-SCP / ILP experiments.

The first implementation uses a deterministic `RuleRanker` so the search
pipeline can be tested before replacing it with a trained model.

## Files

- `feature_extractor.py`: candidate cache and feature extraction.
- `rankers.py`: ranker interface and baseline rule ranker.
- `ai_guided_beam.py`: monotone AI-guided beam search.
- `pruned_candidates.py`: candidate pruning helper for future ILP experiments.
- `run_demo.py`: small CLI demo comparing SSHR-H, Beam, and AI-Guided Beam.

## Quick Demo

Run from the repository root:

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python ai_sshr_experiment/run_demo.py --n 4 --hex 46B9
```

Random sample:

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python ai_sshr_experiment/run_demo.py --n 5 --random --seed 42 --width 30 --branch 8
```

## Current Scope

This prototype intentionally ignores hardware mapping. It optimizes logical
circuit metrics only:

- CNOT count;
- T-count;
- ancilla;
- runtime;
- correctness.

The beam backend currently uses monotone semantics:

```text
vertices(P) subset A
A <- A - vertices(P)
```

The parity/XOR backend is represented by candidate pruning utilities and is
intended to be connected to the existing SSHR-I WP-SCP code next.

