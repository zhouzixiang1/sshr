# Visualization Directory

Scripts and generated outputs for circuit diagrams and figures.

## Scripts

- `draw_circuits.py` — General circuit drawing utilities
- `draw_circuit_fig5b.py` — Specific figure generator for Fig. 5(b) in the paper

## Generated Outputs

PNG files in this directory are **generated artifacts** and are excluded from git via `.gitignore`.
To regenerate:
```bash
cd sshr
/opt/anaconda3/envs/mcts-qoracle/bin/python viz/draw_circuits.py
```
