# Results Directory

This directory stores CSV result files from benchmark runs.

## File Naming Convention

- `compare_n<N>.csv` — Comparison of SSHR-H, SSHR-H-Paper, MCTS, and Beam search for n variables
- `comparison_all.csv` — Aggregated comparison summary
- `mcts_greedy_result.txt` — MCTS vs Greedy heuristic comparison results

## Generating Results

Results are produced by scripts in `sshr/experiments/`.
Example:
```bash
cd sshr
/opt/anaconda3/envs/mcts-qoracle/bin/python experiments/run_tables.py --tables 5 --n 3 4 5 6
```

## Note

Do not commit large result files (>1MB) to git. Use `.gitignore` if necessary.
