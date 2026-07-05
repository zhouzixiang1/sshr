# Resource Sweep Analysis

Rows: 1316; usable: 1316; errors: 0; skipped: 0.

## Mean resources by profile and method

| profile | method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| T-heavy | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 91.92 | 0.000 |
| T-heavy | Fixed MCTS | 47 | 54.81 | 109.49 | 109.77 | 1.55 | 58.79 | 0.144 |
| T-heavy | Affine-NMCTS | 47 | 41.62 | 85.02 | 89.21 | 1.62 | 45.17 | 1.259 |
| T-heavy | Resource-NMCTS | 47 | 41.36 | 84.45 | 88.60 | 1.62 | 44.90 | 1.410 |
| T-heavy | Profile-Resource-NMCTS | 47 | 40.43 | 82.96 | 87.06 | 1.57 | 43.88 | 3.323 |
| T-heavy | ESOP cube beam | 47 | 83.91 | 134.23 | 161.68 | 2.45 | 89.57 | 0.017 |
| T-heavy | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 76.47 | 0.075 |
| Balanced | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 99.02 | 0.000 |
| Balanced | Fixed MCTS | 47 | 54.64 | 109.15 | 109.43 | 1.55 | 64.22 | 0.146 |
| Balanced | Affine-NMCTS | 47 | 41.62 | 84.89 | 89.09 | 1.62 | 50.00 | 1.260 |
| Balanced | Resource-NMCTS | 47 | 41.28 | 84.32 | 88.47 | 1.62 | 49.63 | 1.420 |
| Balanced | Profile-Resource-NMCTS | 47 | 40.34 | 82.91 | 87.02 | 1.57 | 48.52 | 3.215 |
| Balanced | ESOP cube beam | 47 | 83.23 | 133.17 | 160.60 | 2.45 | 96.64 | 0.019 |
| Balanced | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 80.30 | 0.027 |
| CNOT-depth | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 98.00 | 0.000 |
| CNOT-depth | Fixed MCTS | 47 | 54.89 | 109.21 | 109.49 | 1.55 | 67.68 | 0.142 |
| CNOT-depth | Affine-NMCTS | 47 | 41.96 | 85.45 | 89.55 | 1.64 | 53.52 | 1.232 |
| CNOT-depth | Resource-NMCTS | 47 | 41.70 | 84.13 | 88.32 | 1.64 | 53.01 | 1.388 |
| CNOT-depth | Profile-Resource-NMCTS | 47 | 40.51 | 82.43 | 86.72 | 1.60 | 51.71 | 3.151 |
| CNOT-depth | ESOP cube beam | 47 | 83.49 | 133.64 | 160.87 | 2.45 | 96.86 | 0.019 |
| CNOT-depth | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 68.96 | 0.016 |
| Ancilla-tight | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 109.74 | 0.000 |
| Ancilla-tight | Fixed MCTS | 47 | 55.06 | 109.30 | 109.57 | 1.55 | 73.98 | 0.138 |
| Ancilla-tight | Affine-NMCTS | 47 | 43.32 | 86.43 | 90.23 | 1.66 | 61.83 | 1.271 |
| Ancilla-tight | Resource-NMCTS | 47 | 43.06 | 85.57 | 89.32 | 1.64 | 61.35 | 1.407 |
| Ancilla-tight | Profile-Resource-NMCTS | 47 | 42.38 | 84.79 | 88.72 | 1.62 | 60.46 | 3.028 |
| Ancilla-tight | ESOP cube beam | 47 | 83.32 | 133.30 | 160.85 | 2.45 | 111.41 | 0.018 |
| Ancilla-tight | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 87.45 | 0.008 |

## Objective best-or-tied counts by profile

| profile | best-or-tied method | functions |
|---|---|---:|
| T-heavy | Profile-Resource-NMCTS | 42 |
| T-heavy | Affine-NMCTS | 37 |
| T-heavy | Resource-NMCTS | 37 |
| T-heavy | Fixed MCTS | 10 |
| T-heavy | AND-direct ANF | 5 |
| T-heavy | SSHR-H | 5 |
| T-heavy | ESOP cube beam | 1 |
| Balanced | Profile-Resource-NMCTS | 42 |
| Balanced | Affine-NMCTS | 36 |
| Balanced | Resource-NMCTS | 36 |
| Balanced | Fixed MCTS | 10 |
| Balanced | AND-direct ANF | 5 |
| Balanced | SSHR-H | 5 |
| Balanced | ESOP cube beam | 1 |
| CNOT-depth | Profile-Resource-NMCTS | 41 |
| CNOT-depth | Resource-NMCTS | 34 |
| CNOT-depth | Affine-NMCTS | 33 |
| CNOT-depth | Fixed MCTS | 10 |
| CNOT-depth | SSHR-H | 6 |
| CNOT-depth | AND-direct ANF | 5 |
| CNOT-depth | ESOP cube beam | 2 |
| Ancilla-tight | Profile-Resource-NMCTS | 42 |
| Ancilla-tight | Resource-NMCTS | 38 |
| Ancilla-tight | Affine-NMCTS | 35 |
| Ancilla-tight | Fixed MCTS | 10 |
| Ancilla-tight | AND-direct ANF | 5 |
| Ancilla-tight | SSHR-H | 5 |
| Ancilla-tight | ESOP cube beam | 1 |

## Focused Profile-Resource-NMCTS comparisons

| profile | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| T-heavy | Resource-NMCTS | score | 5 | 0 | 42 | -0.73% |
| T-heavy | Resource-NMCTS | T | 3 | 0 | 44 | -0.72% |
| T-heavy | Resource-NMCTS | CNOT | 4 | 1 | 42 | -0.66% |
| T-heavy | Resource-NMCTS | depth | 4 | 1 | 42 | -0.67% |
| T-heavy | Resource-NMCTS | peak_ancilla | 2 | 0 | 45 | -1.42% |
| T-heavy | Affine-NMCTS | score | 5 | 0 | 42 | -0.90% |
| T-heavy | Affine-NMCTS | T | 3 | 0 | 44 | -0.88% |
| T-heavy | Affine-NMCTS | CNOT | 4 | 1 | 42 | -0.86% |
| T-heavy | Affine-NMCTS | depth | 4 | 1 | 42 | -0.87% |
| T-heavy | Affine-NMCTS | peak_ancilla | 2 | 0 | 45 | -1.42% |
| T-heavy | Fixed MCTS | score | 35 | 0 | 12 | -23.56% |
| T-heavy | Fixed MCTS | T | 35 | 0 | 12 | -24.54% |
| T-heavy | Fixed MCTS | CNOT | 35 | 0 | 12 | -21.49% |
| T-heavy | Fixed MCTS | depth | 34 | 1 | 12 | -17.85% |
| T-heavy | Fixed MCTS | peak_ancilla | 0 | 1 | 46 | +1.06% |
| T-heavy | ESOP cube beam | score | 46 | 0 | 1 | -40.27% |
| T-heavy | ESOP cube beam | T | 45 | 0 | 2 | -41.18% |
| T-heavy | ESOP cube beam | CNOT | 39 | 5 | 3 | -24.63% |
| T-heavy | ESOP cube beam | depth | 45 | 1 | 1 | -32.88% |
| T-heavy | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -32.45% |
| T-heavy | SSHR-H | score | 42 | 5 | 0 | -40.75% |
| T-heavy | SSHR-H | T | 42 | 0 | 5 | -43.46% |
| T-heavy | SSHR-H | CNOT | 11 | 36 | 0 | +21.59% |
| T-heavy | SSHR-H | depth | 20 | 26 | 1 | +1.56% |
| T-heavy | SSHR-H | peak_ancilla | 3 | 21 | 23 | +35.11% |
| Balanced | Resource-NMCTS | score | 6 | 0 | 41 | -0.74% |
| Balanced | Resource-NMCTS | T | 4 | 0 | 43 | -0.72% |
| Balanced | Resource-NMCTS | CNOT | 4 | 2 | 41 | -0.63% |
| Balanced | Resource-NMCTS | depth | 4 | 2 | 41 | -0.63% |
| Balanced | Resource-NMCTS | peak_ancilla | 2 | 0 | 45 | -1.42% |
| Balanced | Affine-NMCTS | score | 6 | 0 | 41 | -0.96% |
| Balanced | Affine-NMCTS | T | 4 | 0 | 43 | -0.94% |
| Balanced | Affine-NMCTS | CNOT | 4 | 2 | 41 | -0.82% |
| Balanced | Affine-NMCTS | depth | 4 | 2 | 41 | -0.84% |
| Balanced | Affine-NMCTS | peak_ancilla | 2 | 0 | 45 | -1.42% |
| Balanced | Fixed MCTS | score | 35 | 0 | 12 | -22.60% |
| Balanced | Fixed MCTS | T | 35 | 0 | 12 | -24.48% |
| Balanced | Fixed MCTS | CNOT | 35 | 0 | 12 | -21.41% |
| Balanced | Fixed MCTS | depth | 34 | 1 | 12 | -17.78% |
| Balanced | Fixed MCTS | peak_ancilla | 0 | 1 | 46 | +1.06% |
| Balanced | ESOP cube beam | score | 46 | 0 | 1 | -38.48% |
| Balanced | ESOP cube beam | T | 45 | 0 | 2 | -40.41% |
| Balanced | ESOP cube beam | CNOT | 39 | 5 | 3 | -23.68% |
| Balanced | ESOP cube beam | depth | 45 | 1 | 1 | -32.21% |
| Balanced | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -32.45% |
| Balanced | SSHR-H | score | 42 | 5 | 0 | -37.61% |
| Balanced | SSHR-H | T | 42 | 0 | 5 | -43.51% |
| Balanced | SSHR-H | CNOT | 11 | 36 | 0 | +21.55% |
| Balanced | SSHR-H | depth | 20 | 26 | 1 | +1.52% |
| Balanced | SSHR-H | peak_ancilla | 3 | 21 | 23 | +35.11% |
| CNOT-depth | Resource-NMCTS | score | 7 | 0 | 40 | -0.88% |
| CNOT-depth | Resource-NMCTS | T | 5 | 0 | 42 | -0.92% |
| CNOT-depth | Resource-NMCTS | CNOT | 5 | 2 | 40 | -0.76% |
| CNOT-depth | Resource-NMCTS | depth | 5 | 2 | 40 | -0.70% |
| CNOT-depth | Resource-NMCTS | peak_ancilla | 2 | 0 | 45 | -1.42% |
| CNOT-depth | Affine-NMCTS | score | 8 | 0 | 39 | -1.26% |
| CNOT-depth | Affine-NMCTS | T | 5 | 0 | 42 | -1.08% |
| CNOT-depth | Affine-NMCTS | CNOT | 6 | 2 | 39 | -1.56% |
| CNOT-depth | Affine-NMCTS | depth | 6 | 2 | 39 | -1.38% |
| CNOT-depth | Affine-NMCTS | peak_ancilla | 3 | 1 | 43 | -1.06% |
| CNOT-depth | Fixed MCTS | score | 35 | 0 | 12 | -21.49% |
| CNOT-depth | Fixed MCTS | T | 35 | 0 | 12 | -24.51% |
| CNOT-depth | Fixed MCTS | CNOT | 35 | 0 | 12 | -21.90% |
| CNOT-depth | Fixed MCTS | depth | 34 | 1 | 12 | -18.12% |
| CNOT-depth | Fixed MCTS | peak_ancilla | 0 | 2 | 45 | +2.13% |
| CNOT-depth | ESOP cube beam | score | 45 | 0 | 2 | -34.66% |
| CNOT-depth | ESOP cube beam | T | 45 | 0 | 2 | -40.40% |
| CNOT-depth | ESOP cube beam | CNOT | 39 | 4 | 4 | -24.52% |
| CNOT-depth | ESOP cube beam | depth | 45 | 0 | 2 | -32.69% |
| CNOT-depth | ESOP cube beam | peak_ancilla | 28 | 0 | 19 | -31.74% |
| CNOT-depth | SSHR-H | score | 41 | 6 | 0 | -24.67% |
| CNOT-depth | SSHR-H | T | 42 | 0 | 5 | -43.42% |
| CNOT-depth | SSHR-H | CNOT | 12 | 35 | 0 | +20.95% |
| CNOT-depth | SSHR-H | depth | 21 | 25 | 1 | +1.25% |
| CNOT-depth | SSHR-H | peak_ancilla | 3 | 22 | 22 | +36.17% |
| Ancilla-tight | Resource-NMCTS | score | 4 | 0 | 43 | -0.52% |
| Ancilla-tight | Resource-NMCTS | T | 3 | 0 | 44 | -0.51% |
| Ancilla-tight | Resource-NMCTS | CNOT | 2 | 2 | 43 | -0.30% |
| Ancilla-tight | Resource-NMCTS | depth | 2 | 2 | 43 | -0.22% |
| Ancilla-tight | Resource-NMCTS | peak_ancilla | 2 | 1 | 44 | -0.53% |
| Ancilla-tight | Affine-NMCTS | score | 7 | 0 | 40 | -0.78% |
| Ancilla-tight | Affine-NMCTS | T | 4 | 0 | 43 | -0.69% |
| Ancilla-tight | Affine-NMCTS | CNOT | 5 | 2 | 40 | -0.62% |
| Ancilla-tight | Affine-NMCTS | depth | 5 | 2 | 40 | -0.56% |
| Ancilla-tight | Affine-NMCTS | peak_ancilla | 3 | 1 | 43 | -1.24% |
| Ancilla-tight | Fixed MCTS | score | 35 | 0 | 12 | -18.35% |
| Ancilla-tight | Fixed MCTS | T | 34 | 0 | 13 | -23.31% |
| Ancilla-tight | Fixed MCTS | CNOT | 35 | 0 | 12 | -20.96% |
| Ancilla-tight | Fixed MCTS | depth | 35 | 0 | 12 | -17.49% |
| Ancilla-tight | Fixed MCTS | peak_ancilla | 0 | 3 | 44 | +2.84% |
| Ancilla-tight | ESOP cube beam | score | 46 | 0 | 1 | -35.90% |
| Ancilla-tight | ESOP cube beam | T | 45 | 0 | 2 | -39.06% |
| Ancilla-tight | ESOP cube beam | CNOT | 36 | 8 | 3 | -23.09% |
| Ancilla-tight | ESOP cube beam | depth | 45 | 1 | 1 | -31.95% |
| Ancilla-tight | ESOP cube beam | peak_ancilla | 28 | 0 | 19 | -31.38% |
| Ancilla-tight | SSHR-H | score | 42 | 5 | 0 | -29.81% |
| Ancilla-tight | SSHR-H | T | 42 | 0 | 5 | -42.47% |
| Ancilla-tight | SSHR-H | CNOT | 11 | 36 | 0 | +22.82% |
| Ancilla-tight | SSHR-H | depth | 21 | 25 | 1 | +2.32% |
| Ancilla-tight | SSHR-H | peak_ancilla | 3 | 22 | 22 | +37.23% |
