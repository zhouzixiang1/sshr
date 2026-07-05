# Resource Sweep Analysis

Rows: 1128; usable: 1128; errors: 0; skipped: 0.

## Mean resources by profile and method

| profile | method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| T-heavy | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 91.92 | 0.000 |
| T-heavy | Fixed MCTS | 47 | 54.81 | 109.49 | 109.77 | 1.55 | 58.79 | 0.144 |
| T-heavy | Affine-NMCTS | 47 | 41.62 | 85.02 | 89.21 | 1.62 | 45.17 | 1.259 |
| T-heavy | Resource-NMCTS | 47 | 41.36 | 84.45 | 88.60 | 1.62 | 44.90 | 1.410 |
| T-heavy | ESOP cube beam | 47 | 83.91 | 134.23 | 161.68 | 2.45 | 89.57 | 0.017 |
| T-heavy | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 76.47 | 0.075 |
| Balanced | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 99.02 | 0.000 |
| Balanced | Fixed MCTS | 47 | 54.64 | 109.15 | 109.43 | 1.55 | 64.22 | 0.146 |
| Balanced | Affine-NMCTS | 47 | 41.62 | 84.89 | 89.09 | 1.62 | 50.00 | 1.260 |
| Balanced | Resource-NMCTS | 47 | 41.28 | 84.32 | 88.47 | 1.62 | 49.63 | 1.420 |
| Balanced | ESOP cube beam | 47 | 83.23 | 133.17 | 160.60 | 2.45 | 96.64 | 0.019 |
| Balanced | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 80.30 | 0.027 |
| CNOT-depth | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 98.00 | 0.000 |
| CNOT-depth | Fixed MCTS | 47 | 54.89 | 109.21 | 109.49 | 1.55 | 67.68 | 0.142 |
| CNOT-depth | Affine-NMCTS | 47 | 41.96 | 85.45 | 89.55 | 1.64 | 53.52 | 1.232 |
| CNOT-depth | Resource-NMCTS | 47 | 41.70 | 84.13 | 88.32 | 1.64 | 53.01 | 1.388 |
| CNOT-depth | ESOP cube beam | 47 | 83.49 | 133.64 | 160.87 | 2.45 | 96.86 | 0.019 |
| CNOT-depth | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 68.96 | 0.016 |
| Ancilla-tight | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 109.74 | 0.000 |
| Ancilla-tight | Fixed MCTS | 47 | 55.06 | 109.30 | 109.57 | 1.55 | 73.98 | 0.138 |
| Ancilla-tight | Affine-NMCTS | 47 | 43.32 | 86.43 | 90.23 | 1.66 | 61.83 | 1.271 |
| Ancilla-tight | Resource-NMCTS | 47 | 43.06 | 85.57 | 89.32 | 1.64 | 61.35 | 1.407 |
| Ancilla-tight | ESOP cube beam | 47 | 83.32 | 133.30 | 160.85 | 2.45 | 111.41 | 0.018 |
| Ancilla-tight | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 87.45 | 0.008 |

## Objective best-or-tied counts by profile

| profile | best-or-tied method | functions |
|---|---|---:|
| T-heavy | Resource-NMCTS | 42 |
| T-heavy | Affine-NMCTS | 40 |
| T-heavy | Fixed MCTS | 10 |
| T-heavy | AND-direct ANF | 5 |
| T-heavy | SSHR-H | 5 |
| T-heavy | ESOP cube beam | 1 |
| Balanced | Resource-NMCTS | 42 |
| Balanced | Affine-NMCTS | 40 |
| Balanced | Fixed MCTS | 10 |
| Balanced | AND-direct ANF | 5 |
| Balanced | SSHR-H | 5 |
| Balanced | ESOP cube beam | 1 |
| CNOT-depth | Resource-NMCTS | 40 |
| CNOT-depth | Affine-NMCTS | 37 |
| CNOT-depth | Fixed MCTS | 10 |
| CNOT-depth | SSHR-H | 7 |
| CNOT-depth | AND-direct ANF | 5 |
| CNOT-depth | ESOP cube beam | 2 |
| Ancilla-tight | Resource-NMCTS | 42 |
| Ancilla-tight | Affine-NMCTS | 39 |
| Ancilla-tight | Fixed MCTS | 11 |
| Ancilla-tight | AND-direct ANF | 5 |
| Ancilla-tight | SSHR-H | 5 |
| Ancilla-tight | ESOP cube beam | 1 |

## Focused Resource-NMCTS comparisons

| profile | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| T-heavy | Affine-NMCTS | score | 2 | 0 | 45 | -0.19% |
| T-heavy | Affine-NMCTS | T | 2 | 0 | 45 | -0.19% |
| T-heavy | Affine-NMCTS | CNOT | 2 | 0 | 45 | -0.21% |
| T-heavy | Affine-NMCTS | depth | 2 | 0 | 45 | -0.22% |
| T-heavy | Affine-NMCTS | peak_ancilla | 0 | 0 | 47 | +0.00% |
| T-heavy | Fixed MCTS | score | 35 | 0 | 12 | -22.96% |
| T-heavy | Fixed MCTS | T | 35 | 0 | 12 | -23.96% |
| T-heavy | Fixed MCTS | CNOT | 34 | 1 | 12 | -20.92% |
| T-heavy | Fixed MCTS | depth | 34 | 1 | 12 | -17.27% |
| T-heavy | Fixed MCTS | peak_ancilla | 0 | 3 | 44 | +3.19% |
| T-heavy | ESOP cube beam | score | 46 | 0 | 1 | -39.63% |
| T-heavy | ESOP cube beam | T | 45 | 0 | 2 | -40.57% |
| T-heavy | ESOP cube beam | CNOT | 37 | 7 | 3 | -23.90% |
| T-heavy | ESOP cube beam | depth | 44 | 2 | 1 | -32.24% |
| T-heavy | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -31.38% |
| T-heavy | SSHR-H | score | 42 | 5 | 0 | -40.27% |
| T-heavy | SSHR-H | T | 42 | 0 | 5 | -43.01% |
| T-heavy | SSHR-H | CNOT | 10 | 37 | 0 | +22.62% |
| T-heavy | SSHR-H | depth | 20 | 26 | 1 | +2.35% |
| T-heavy | SSHR-H | peak_ancilla | 3 | 23 | 21 | +37.23% |
| Balanced | Affine-NMCTS | score | 2 | 0 | 45 | -0.23% |
| Balanced | Affine-NMCTS | T | 2 | 0 | 45 | -0.24% |
| Balanced | Affine-NMCTS | CNOT | 2 | 0 | 45 | -0.21% |
| Balanced | Affine-NMCTS | depth | 2 | 0 | 45 | -0.22% |
| Balanced | Affine-NMCTS | peak_ancilla | 0 | 0 | 47 | +0.00% |
| Balanced | Fixed MCTS | score | 35 | 0 | 12 | -21.99% |
| Balanced | Fixed MCTS | T | 35 | 0 | 12 | -23.91% |
| Balanced | Fixed MCTS | CNOT | 34 | 1 | 12 | -20.87% |
| Balanced | Fixed MCTS | depth | 34 | 1 | 12 | -17.22% |
| Balanced | Fixed MCTS | peak_ancilla | 0 | 3 | 44 | +3.19% |
| Balanced | ESOP cube beam | score | 46 | 0 | 1 | -37.85% |
| Balanced | ESOP cube beam | T | 45 | 0 | 2 | -39.81% |
| Balanced | ESOP cube beam | CNOT | 37 | 7 | 3 | -22.98% |
| Balanced | ESOP cube beam | depth | 44 | 2 | 1 | -31.59% |
| Balanced | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -31.38% |
| Balanced | SSHR-H | score | 42 | 5 | 0 | -37.10% |
| Balanced | SSHR-H | T | 42 | 0 | 5 | -43.05% |
| Balanced | SSHR-H | CNOT | 10 | 37 | 0 | +22.52% |
| Balanced | SSHR-H | depth | 20 | 26 | 1 | +2.27% |
| Balanced | SSHR-H | peak_ancilla | 3 | 23 | 21 | +37.23% |
| CNOT-depth | Affine-NMCTS | score | 3 | 0 | 44 | -0.41% |
| CNOT-depth | Affine-NMCTS | T | 2 | 0 | 45 | -0.18% |
| CNOT-depth | Affine-NMCTS | CNOT | 3 | 0 | 44 | -0.81% |
| CNOT-depth | Affine-NMCTS | depth | 3 | 0 | 44 | -0.70% |
| CNOT-depth | Affine-NMCTS | peak_ancilla | 1 | 1 | 45 | +0.35% |
| CNOT-depth | Fixed MCTS | score | 35 | 0 | 12 | -20.75% |
| CNOT-depth | Fixed MCTS | T | 35 | 0 | 12 | -23.76% |
| CNOT-depth | Fixed MCTS | CNOT | 34 | 1 | 12 | -21.24% |
| CNOT-depth | Fixed MCTS | depth | 34 | 1 | 12 | -17.49% |
| CNOT-depth | Fixed MCTS | peak_ancilla | 0 | 4 | 43 | +4.26% |
| CNOT-depth | ESOP cube beam | score | 45 | 0 | 2 | -33.86% |
| CNOT-depth | ESOP cube beam | T | 45 | 0 | 2 | -39.62% |
| CNOT-depth | ESOP cube beam | CNOT | 37 | 7 | 3 | -23.67% |
| CNOT-depth | ESOP cube beam | depth | 44 | 1 | 2 | -32.02% |
| CNOT-depth | ESOP cube beam | peak_ancilla | 28 | 0 | 19 | -30.67% |
| CNOT-depth | SSHR-H | score | 40 | 7 | 0 | -23.89% |
| CNOT-depth | SSHR-H | T | 42 | 0 | 5 | -42.81% |
| CNOT-depth | SSHR-H | CNOT | 11 | 36 | 0 | +22.17% |
| CNOT-depth | SSHR-H | depth | 21 | 25 | 1 | +2.09% |
| CNOT-depth | SSHR-H | peak_ancilla | 3 | 24 | 20 | +38.30% |
| Ancilla-tight | Affine-NMCTS | score | 3 | 0 | 44 | -0.26% |
| Ancilla-tight | Affine-NMCTS | T | 1 | 0 | 46 | -0.18% |
| Ancilla-tight | Affine-NMCTS | CNOT | 3 | 0 | 44 | -0.32% |
| Ancilla-tight | Affine-NMCTS | depth | 3 | 0 | 44 | -0.34% |
| Ancilla-tight | Affine-NMCTS | peak_ancilla | 1 | 0 | 46 | -0.71% |
| Ancilla-tight | Fixed MCTS | score | 34 | 0 | 13 | -17.85% |
| Ancilla-tight | Fixed MCTS | T | 33 | 0 | 14 | -22.84% |
| Ancilla-tight | Fixed MCTS | CNOT | 34 | 0 | 13 | -20.65% |
| Ancilla-tight | Fixed MCTS | depth | 34 | 0 | 13 | -17.25% |
| Ancilla-tight | Fixed MCTS | peak_ancilla | 0 | 4 | 43 | +3.90% |
| Ancilla-tight | ESOP cube beam | score | 46 | 0 | 1 | -35.43% |
| Ancilla-tight | ESOP cube beam | T | 45 | 0 | 2 | -38.58% |
| Ancilla-tight | ESOP cube beam | CNOT | 36 | 9 | 2 | -22.70% |
| Ancilla-tight | ESOP cube beam | depth | 45 | 1 | 1 | -31.71% |
| Ancilla-tight | ESOP cube beam | peak_ancilla | 28 | 0 | 19 | -30.85% |
| Ancilla-tight | SSHR-H | score | 42 | 5 | 0 | -29.35% |
| Ancilla-tight | SSHR-H | T | 42 | 0 | 5 | -42.09% |
| Ancilla-tight | SSHR-H | CNOT | 11 | 36 | 0 | +23.39% |
| Ancilla-tight | SSHR-H | depth | 21 | 25 | 1 | +2.63% |
| Ancilla-tight | SSHR-H | peak_ancilla | 3 | 23 | 21 | +38.30% |
