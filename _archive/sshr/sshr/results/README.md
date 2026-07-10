# Results Directory

This directory stores CSV result files and text summaries from benchmark runs.

## Subdirectories

- `comparison/` — Multi-method comparison CSVs produced by `mcts_beam_compare.py`
  - `compare_n<N>.csv` — Per-n comparison of SSHR-H, SSHR-H-Paper, MCTS, and Beam
  - `comparison_all.csv` — Aggregated summary across all n
- `mcts/` — MCTS-specific result files
  - `mcts_greedy_result.txt` — MCTS vs Greedy heuristic comparison

## Generating Results

Run the corresponding experiment script from `sshr/experiments/`:
```bash
cd sshr
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/mcts/mcts_beam_compare.py
```

## Note

Do not commit large result files (>1MB) to git. Use `.gitignore` if necessary.
