# Resource Sweep Analysis

Rows: 2115; usable: 2115; errors: 0; skipped: 0.

## Mean resources by profile and method

| profile | method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| T-heavy | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 91.92 | 0.000 |
| T-heavy | Fixed MCTS | 47 | 54.81 | 109.49 | 109.77 | 1.55 | 58.79 | 0.144 |
| T-heavy | Affine-NMCTS | 47 | 41.62 | 85.02 | 89.21 | 1.62 | 45.17 | 1.259 |
| T-heavy | Resource-NMCTS | 47 | 41.36 | 84.45 | 88.60 | 1.62 | 44.90 | 1.410 |
| T-heavy | Profile-Resource-NMCTS | 47 | 40.43 | 82.96 | 87.06 | 1.57 | 43.88 | 3.323 |
| T-heavy | Polarity archive | 47 | 37.36 | 76.45 | 80.55 | 2.09 | 41.19 | 0.138 |
| T-heavy | Pareto-Resource-NMCTS | 47 | 35.91 | 74.26 | 78.72 | 1.87 | 39.49 | 1.707 |
| T-heavy | ESOP cube beam | 47 | 83.91 | 134.23 | 161.68 | 2.45 | 89.57 | 0.017 |
| T-heavy | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 76.47 | 0.075 |
| Balanced | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 99.02 | 0.000 |
| Balanced | Fixed MCTS | 47 | 54.64 | 109.15 | 109.43 | 1.55 | 64.22 | 0.146 |
| Balanced | Affine-NMCTS | 47 | 41.62 | 84.89 | 89.09 | 1.62 | 50.00 | 1.260 |
| Balanced | Resource-NMCTS | 47 | 41.28 | 84.32 | 88.47 | 1.62 | 49.63 | 1.420 |
| Balanced | Profile-Resource-NMCTS | 47 | 40.34 | 82.91 | 87.02 | 1.57 | 48.52 | 3.215 |
| Balanced | Polarity archive | 47 | 37.36 | 76.32 | 80.43 | 2.11 | 46.22 | 0.134 |
| Balanced | Pareto-Resource-NMCTS | 47 | 35.91 | 74.26 | 78.72 | 1.87 | 44.19 | 1.691 |
| Balanced | ESOP cube beam | 47 | 83.23 | 133.17 | 160.60 | 2.45 | 96.64 | 0.019 |
| Balanced | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 80.30 | 0.027 |
| CNOT-depth | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 98.00 | 0.000 |
| CNOT-depth | Fixed MCTS | 47 | 54.89 | 109.21 | 109.49 | 1.55 | 67.68 | 0.142 |
| CNOT-depth | Affine-NMCTS | 47 | 41.96 | 85.45 | 89.55 | 1.64 | 53.52 | 1.232 |
| CNOT-depth | Resource-NMCTS | 47 | 41.70 | 84.13 | 88.32 | 1.64 | 53.01 | 1.388 |
| CNOT-depth | Profile-Resource-NMCTS | 47 | 40.51 | 82.43 | 86.72 | 1.60 | 51.71 | 3.151 |
| CNOT-depth | Polarity archive | 47 | 37.62 | 76.28 | 80.49 | 2.11 | 49.22 | 0.136 |
| CNOT-depth | Pareto-Resource-NMCTS | 47 | 35.91 | 73.55 | 77.79 | 1.94 | 47.06 | 1.688 |
| CNOT-depth | ESOP cube beam | 47 | 83.49 | 133.64 | 160.87 | 2.45 | 96.86 | 0.019 |
| CNOT-depth | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 68.96 | 0.016 |
| CNOT-only | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 143.47 | 0.000 |
| CNOT-only | Fixed MCTS | 47 | 55.74 | 108.60 | 108.87 | 1.57 | 108.60 | 0.012 |
| CNOT-only | Affine-NMCTS | 47 | 42.30 | 84.06 | 88.28 | 1.68 | 84.06 | 0.135 |
| CNOT-only | Resource-NMCTS | 47 | 41.11 | 76.98 | 85.38 | 1.98 | 76.98 | 0.211 |
| CNOT-only | Profile-Resource-NMCTS | 47 | 41.11 | 76.23 | 85.45 | 2.00 | 76.23 | 0.444 |
| CNOT-only | Polarity archive | 47 | 37.70 | 73.62 | 78.83 | 2.34 | 73.62 | 0.239 |
| CNOT-only | Pareto-Resource-NMCTS | 47 | 36.68 | 71.38 | 76.68 | 2.17 | 71.38 | 2.195 |
| CNOT-only | ESOP cube beam | 47 | 83.40 | 133.23 | 161.17 | 2.51 | 133.23 | 0.008 |
| CNOT-only | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 64.60 | 0.034 |
| Ancilla-tight | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 109.74 | 0.000 |
| Ancilla-tight | Fixed MCTS | 47 | 55.06 | 109.30 | 109.57 | 1.55 | 73.98 | 0.138 |
| Ancilla-tight | Affine-NMCTS | 47 | 43.32 | 86.43 | 90.23 | 1.66 | 61.83 | 1.271 |
| Ancilla-tight | Resource-NMCTS | 47 | 43.06 | 85.57 | 89.32 | 1.64 | 61.35 | 1.407 |
| Ancilla-tight | Profile-Resource-NMCTS | 47 | 42.38 | 84.79 | 88.72 | 1.62 | 60.46 | 3.028 |
| Ancilla-tight | Polarity archive | 47 | 42.47 | 82.55 | 86.49 | 1.70 | 61.08 | 0.067 |
| Ancilla-tight | Pareto-Resource-NMCTS | 47 | 39.74 | 80.47 | 84.81 | 1.62 | 57.57 | 1.405 |
| Ancilla-tight | ESOP cube beam | 47 | 83.32 | 133.30 | 160.85 | 2.45 | 111.41 | 0.018 |
| Ancilla-tight | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 87.45 | 0.008 |

## Objective best-or-tied counts by profile

| profile | best-or-tied method | functions |
|---|---|---:|
| T-heavy | Pareto-Resource-NMCTS | 44 |
| T-heavy | Affine-NMCTS | 25 |
| T-heavy | Resource-NMCTS | 25 |
| T-heavy | Profile-Resource-NMCTS | 25 |
| T-heavy | Polarity archive | 24 |
| T-heavy | Fixed MCTS | 6 |
| T-heavy | AND-direct ANF | 5 |
| T-heavy | SSHR-H | 3 |
| T-heavy | ESOP cube beam | 1 |
| Balanced | Pareto-Resource-NMCTS | 44 |
| Balanced | Affine-NMCTS | 25 |
| Balanced | Resource-NMCTS | 25 |
| Balanced | Profile-Resource-NMCTS | 25 |
| Balanced | Polarity archive | 24 |
| Balanced | Fixed MCTS | 6 |
| Balanced | AND-direct ANF | 5 |
| Balanced | SSHR-H | 3 |
| Balanced | ESOP cube beam | 1 |
| CNOT-depth | Pareto-Resource-NMCTS | 42 |
| CNOT-depth | Polarity archive | 26 |
| CNOT-depth | Affine-NMCTS | 22 |
| CNOT-depth | Resource-NMCTS | 22 |
| CNOT-depth | Profile-Resource-NMCTS | 22 |
| CNOT-depth | Fixed MCTS | 6 |
| CNOT-depth | AND-direct ANF | 5 |
| CNOT-depth | SSHR-H | 5 |
| CNOT-depth | ESOP cube beam | 1 |
| CNOT-only | SSHR-H | 33 |
| CNOT-only | Pareto-Resource-NMCTS | 14 |
| CNOT-only | Resource-NMCTS | 11 |
| CNOT-only | Profile-Resource-NMCTS | 11 |
| CNOT-only | Polarity archive | 10 |
| CNOT-only | Affine-NMCTS | 9 |
| CNOT-only | Fixed MCTS | 6 |
| CNOT-only | AND-direct ANF | 5 |
| CNOT-only | ESOP cube beam | 2 |
| Ancilla-tight | Pareto-Resource-NMCTS | 43 |
| Ancilla-tight | Profile-Resource-NMCTS | 29 |
| Ancilla-tight | Resource-NMCTS | 28 |
| Ancilla-tight | Affine-NMCTS | 27 |
| Ancilla-tight | Polarity archive | 19 |
| Ancilla-tight | Fixed MCTS | 7 |
| Ancilla-tight | AND-direct ANF | 5 |
| Ancilla-tight | SSHR-H | 4 |
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
| CNOT-only | Resource-NMCTS | score | 3 | 0 | 44 | -0.32% |
| CNOT-only | Resource-NMCTS | T | 2 | 1 | 44 | +0.13% |
| CNOT-only | Resource-NMCTS | CNOT | 3 | 0 | 44 | -0.32% |
| CNOT-only | Resource-NMCTS | depth | 2 | 1 | 44 | +0.16% |
| CNOT-only | Resource-NMCTS | peak_ancilla | 0 | 1 | 46 | +0.71% |
| CNOT-only | Affine-NMCTS | score | 20 | 0 | 27 | -5.59% |
| CNOT-only | Affine-NMCTS | T | 12 | 6 | 29 | -2.02% |
| CNOT-only | Affine-NMCTS | CNOT | 20 | 0 | 27 | -5.59% |
| CNOT-only | Affine-NMCTS | depth | 15 | 5 | 27 | -2.45% |
| CNOT-only | Affine-NMCTS | peak_ancilla | 0 | 14 | 33 | +20.21% |
| CNOT-only | Fixed MCTS | score | 41 | 0 | 6 | -25.93% |
| CNOT-only | Fixed MCTS | T | 39 | 2 | 6 | -25.58% |
| CNOT-only | Fixed MCTS | CNOT | 41 | 0 | 6 | -25.93% |
| CNOT-only | Fixed MCTS | depth | 38 | 2 | 7 | -19.51% |
| CNOT-only | Fixed MCTS | peak_ancilla | 0 | 18 | 29 | +25.89% |
| CNOT-only | ESOP cube beam | score | 41 | 0 | 6 | -28.53% |
| CNOT-only | ESOP cube beam | T | 41 | 0 | 6 | -39.81% |
| CNOT-only | ESOP cube beam | CNOT | 41 | 0 | 6 | -28.53% |
| CNOT-only | ESOP cube beam | depth | 41 | 0 | 6 | -34.22% |
| CNOT-only | ESOP cube beam | peak_ancilla | 21 | 3 | 23 | -17.20% |
| CNOT-only | SSHR-H | score | 12 | 35 | 0 | +13.21% |
| CNOT-only | SSHR-H | T | 43 | 0 | 4 | -43.83% |
| CNOT-only | SSHR-H | CNOT | 12 | 35 | 0 | +13.21% |
| CNOT-only | SSHR-H | depth | 20 | 27 | 0 | -1.31% |
| CNOT-only | SSHR-H | peak_ancilla | 3 | 35 | 9 | +63.83% |
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

## Focused Pareto-Resource-NMCTS comparisons

| profile | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| T-heavy | Profile-Resource-NMCTS | score | 19 | 0 | 28 | -5.56% |
| T-heavy | Profile-Resource-NMCTS | T | 17 | 0 | 30 | -6.24% |
| T-heavy | Profile-Resource-NMCTS | CNOT | 18 | 0 | 29 | -5.78% |
| T-heavy | Profile-Resource-NMCTS | depth | 17 | 2 | 28 | -4.96% |
| T-heavy | Profile-Resource-NMCTS | peak_ancilla | 0 | 11 | 36 | +15.25% |
| T-heavy | Resource-NMCTS | score | 19 | 0 | 28 | -6.23% |
| T-heavy | Resource-NMCTS | T | 17 | 0 | 30 | -6.89% |
| T-heavy | Resource-NMCTS | CNOT | 18 | 0 | 29 | -6.36% |
| T-heavy | Resource-NMCTS | depth | 17 | 2 | 28 | -5.55% |
| T-heavy | Resource-NMCTS | peak_ancilla | 0 | 11 | 36 | +12.41% |
| T-heavy | Affine-NMCTS | score | 19 | 0 | 28 | -6.38% |
| T-heavy | Affine-NMCTS | T | 17 | 0 | 30 | -7.04% |
| T-heavy | Affine-NMCTS | CNOT | 18 | 0 | 29 | -6.53% |
| T-heavy | Affine-NMCTS | depth | 17 | 2 | 28 | -5.73% |
| T-heavy | Affine-NMCTS | peak_ancilla | 0 | 11 | 36 | +12.41% |
| T-heavy | Fixed MCTS | score | 41 | 0 | 6 | -28.42% |
| T-heavy | Fixed MCTS | T | 41 | 0 | 6 | -30.00% |
| T-heavy | Fixed MCTS | CNOT | 41 | 0 | 6 | -26.54% |
| T-heavy | Fixed MCTS | depth | 39 | 2 | 6 | -22.24% |
| T-heavy | Fixed MCTS | peak_ancilla | 0 | 11 | 36 | +16.67% |
| T-heavy | ESOP cube beam | score | 46 | 0 | 1 | -44.07% |
| T-heavy | ESOP cube beam | T | 46 | 0 | 1 | -45.44% |
| T-heavy | ESOP cube beam | CNOT | 42 | 3 | 2 | -29.61% |
| T-heavy | ESOP cube beam | depth | 46 | 0 | 1 | -36.66% |
| T-heavy | ESOP cube beam | peak_ancilla | 22 | 1 | 24 | -23.05% |
| T-heavy | SSHR-H | score | 44 | 3 | 0 | -44.74% |
| T-heavy | SSHR-H | T | 44 | 0 | 3 | -47.80% |
| T-heavy | SSHR-H | CNOT | 12 | 35 | 0 | +12.52% |
| T-heavy | SSHR-H | depth | 23 | 23 | 1 | -5.02% |
| T-heavy | SSHR-H | peak_ancilla | 3 | 29 | 15 | +53.19% |
| Balanced | Profile-Resource-NMCTS | score | 19 | 0 | 28 | -4.93% |
| Balanced | Profile-Resource-NMCTS | T | 17 | 0 | 30 | -6.18% |
| Balanced | Profile-Resource-NMCTS | CNOT | 18 | 0 | 29 | -5.76% |
| Balanced | Profile-Resource-NMCTS | depth | 17 | 2 | 28 | -4.94% |
| Balanced | Profile-Resource-NMCTS | peak_ancilla | 0 | 11 | 36 | +15.25% |
| Balanced | Resource-NMCTS | score | 19 | 0 | 28 | -5.60% |
| Balanced | Resource-NMCTS | T | 17 | 0 | 30 | -6.80% |
| Balanced | Resource-NMCTS | CNOT | 18 | 0 | 29 | -6.32% |
| Balanced | Resource-NMCTS | depth | 17 | 2 | 28 | -5.50% |
| Balanced | Resource-NMCTS | peak_ancilla | 0 | 11 | 36 | +12.41% |
| Balanced | Affine-NMCTS | score | 19 | 0 | 28 | -5.79% |
| Balanced | Affine-NMCTS | T | 17 | 0 | 30 | -7.00% |
| Balanced | Affine-NMCTS | CNOT | 18 | 0 | 29 | -6.49% |
| Balanced | Affine-NMCTS | depth | 17 | 2 | 28 | -5.68% |
| Balanced | Affine-NMCTS | peak_ancilla | 0 | 11 | 36 | +12.41% |
| Balanced | Fixed MCTS | score | 41 | 0 | 6 | -26.88% |
| Balanced | Fixed MCTS | T | 41 | 0 | 6 | -29.84% |
| Balanced | Fixed MCTS | CNOT | 41 | 0 | 6 | -26.45% |
| Balanced | Fixed MCTS | depth | 39 | 2 | 6 | -22.14% |
| Balanced | Fixed MCTS | peak_ancilla | 0 | 11 | 36 | +16.67% |
| Balanced | ESOP cube beam | score | 46 | 0 | 1 | -41.89% |
| Balanced | ESOP cube beam | T | 46 | 0 | 1 | -44.64% |
| Balanced | ESOP cube beam | CNOT | 42 | 3 | 2 | -28.66% |
| Balanced | ESOP cube beam | depth | 46 | 0 | 1 | -36.01% |
| Balanced | ESOP cube beam | peak_ancilla | 22 | 1 | 24 | -23.05% |
| Balanced | SSHR-H | score | 44 | 3 | 0 | -41.30% |
| Balanced | SSHR-H | T | 44 | 0 | 3 | -47.80% |
| Balanced | SSHR-H | CNOT | 12 | 35 | 0 | +12.52% |
| Balanced | SSHR-H | depth | 23 | 23 | 1 | -5.02% |
| Balanced | SSHR-H | peak_ancilla | 3 | 29 | 15 | +53.19% |
| CNOT-depth | Profile-Resource-NMCTS | score | 21 | 0 | 26 | -4.85% |
| CNOT-depth | Profile-Resource-NMCTS | T | 17 | 0 | 30 | -6.30% |
| CNOT-depth | Profile-Resource-NMCTS | CNOT | 19 | 1 | 27 | -5.83% |
| CNOT-depth | Profile-Resource-NMCTS | depth | 19 | 2 | 26 | -5.43% |
| CNOT-depth | Profile-Resource-NMCTS | peak_ancilla | 1 | 14 | 32 | +17.38% |
| CNOT-depth | Resource-NMCTS | score | 21 | 0 | 26 | -5.63% |
| CNOT-depth | Resource-NMCTS | T | 17 | 0 | 30 | -7.10% |
| CNOT-depth | Resource-NMCTS | CNOT | 19 | 1 | 27 | -6.50% |
| CNOT-depth | Resource-NMCTS | depth | 19 | 2 | 26 | -6.05% |
| CNOT-depth | Resource-NMCTS | peak_ancilla | 1 | 13 | 33 | +14.89% |
| CNOT-depth | Affine-NMCTS | score | 21 | 0 | 26 | -5.98% |
| CNOT-depth | Affine-NMCTS | T | 17 | 0 | 30 | -7.24% |
| CNOT-depth | Affine-NMCTS | CNOT | 20 | 0 | 27 | -7.31% |
| CNOT-depth | Affine-NMCTS | depth | 19 | 2 | 26 | -6.69% |
| CNOT-depth | Affine-NMCTS | peak_ancilla | 0 | 13 | 34 | +14.18% |
| CNOT-depth | Fixed MCTS | score | 41 | 0 | 6 | -25.67% |
| CNOT-depth | Fixed MCTS | T | 41 | 0 | 6 | -29.99% |
| CNOT-depth | Fixed MCTS | CNOT | 41 | 0 | 6 | -26.89% |
| CNOT-depth | Fixed MCTS | depth | 39 | 2 | 6 | -22.73% |
| CNOT-depth | Fixed MCTS | peak_ancilla | 0 | 14 | 33 | +19.50% |
| CNOT-depth | ESOP cube beam | score | 46 | 0 | 1 | -38.12% |
| CNOT-depth | ESOP cube beam | T | 46 | 0 | 1 | -44.69% |
| CNOT-depth | ESOP cube beam | CNOT | 43 | 2 | 2 | -29.34% |
| CNOT-depth | ESOP cube beam | depth | 46 | 0 | 1 | -36.68% |
| CNOT-depth | ESOP cube beam | peak_ancilla | 21 | 3 | 23 | -20.39% |
| CNOT-depth | SSHR-H | score | 42 | 5 | 0 | -29.08% |
| CNOT-depth | SSHR-H | T | 44 | 0 | 3 | -47.80% |
| CNOT-depth | SSHR-H | CNOT | 13 | 34 | 0 | +11.61% |
| CNOT-depth | SSHR-H | depth | 23 | 23 | 1 | -5.93% |
| CNOT-depth | SSHR-H | peak_ancilla | 3 | 29 | 15 | +58.51% |
| CNOT-only | Profile-Resource-NMCTS | score | 17 | 0 | 30 | -3.34% |
| CNOT-only | Profile-Resource-NMCTS | T | 14 | 1 | 32 | -4.54% |
| CNOT-only | Profile-Resource-NMCTS | CNOT | 17 | 0 | 30 | -3.34% |
| CNOT-only | Profile-Resource-NMCTS | depth | 18 | 2 | 27 | -4.43% |
| CNOT-only | Profile-Resource-NMCTS | peak_ancilla | 2 | 9 | 36 | +8.69% |
| CNOT-only | Resource-NMCTS | score | 17 | 0 | 30 | -3.63% |
| CNOT-only | Resource-NMCTS | T | 14 | 1 | 32 | -4.43% |
| CNOT-only | Resource-NMCTS | CNOT | 17 | 0 | 30 | -3.63% |
| CNOT-only | Resource-NMCTS | depth | 18 | 2 | 27 | -4.32% |
| CNOT-only | Resource-NMCTS | peak_ancilla | 1 | 9 | 37 | +9.22% |
| CNOT-only | Affine-NMCTS | score | 26 | 0 | 21 | -8.62% |
| CNOT-only | Affine-NMCTS | T | 21 | 3 | 23 | -6.57% |
| CNOT-only | Affine-NMCTS | CNOT | 26 | 0 | 21 | -8.62% |
| CNOT-only | Affine-NMCTS | depth | 26 | 2 | 19 | -6.99% |
| CNOT-only | Affine-NMCTS | peak_ancilla | 0 | 20 | 27 | +28.72% |
| CNOT-only | Fixed MCTS | score | 41 | 0 | 6 | -28.43% |
| CNOT-only | Fixed MCTS | T | 41 | 0 | 6 | -29.49% |
| CNOT-only | Fixed MCTS | CNOT | 41 | 0 | 6 | -28.43% |
| CNOT-only | Fixed MCTS | depth | 40 | 0 | 7 | -23.39% |
| CNOT-only | Fixed MCTS | peak_ancilla | 0 | 23 | 24 | +35.11% |
| CNOT-only | ESOP cube beam | score | 44 | 0 | 3 | -31.22% |
| CNOT-only | ESOP cube beam | T | 44 | 0 | 3 | -43.30% |
| CNOT-only | ESOP cube beam | CNOT | 44 | 0 | 3 | -31.22% |
| CNOT-only | ESOP cube beam | depth | 45 | 0 | 2 | -37.89% |
| CNOT-only | ESOP cube beam | peak_ancilla | 15 | 5 | 27 | -11.70% |
| CNOT-only | SSHR-H | score | 14 | 33 | 0 | +8.60% |
| CNOT-only | SSHR-H | T | 43 | 0 | 4 | -46.85% |
| CNOT-only | SSHR-H | CNOT | 14 | 33 | 0 | +8.60% |
| CNOT-only | SSHR-H | depth | 22 | 24 | 1 | -6.99% |
| CNOT-only | SSHR-H | peak_ancilla | 3 | 37 | 7 | +77.66% |
| Ancilla-tight | Profile-Resource-NMCTS | score | 15 | 0 | 32 | -2.51% |
| Ancilla-tight | Profile-Resource-NMCTS | T | 12 | 0 | 35 | -3.41% |
| Ancilla-tight | Profile-Resource-NMCTS | CNOT | 14 | 0 | 33 | -2.95% |
| Ancilla-tight | Profile-Resource-NMCTS | depth | 12 | 3 | 32 | -2.44% |
| Ancilla-tight | Profile-Resource-NMCTS | peak_ancilla | 2 | 2 | 43 | +0.89% |
| Ancilla-tight | Resource-NMCTS | score | 16 | 0 | 31 | -3.02% |
| Ancilla-tight | Resource-NMCTS | T | 13 | 0 | 34 | -3.90% |
| Ancilla-tight | Resource-NMCTS | CNOT | 14 | 1 | 32 | -3.24% |
| Ancilla-tight | Resource-NMCTS | depth | 12 | 4 | 31 | -2.66% |
| Ancilla-tight | Resource-NMCTS | peak_ancilla | 3 | 2 | 42 | +0.18% |
| Ancilla-tight | Affine-NMCTS | score | 17 | 0 | 30 | -3.26% |
| Ancilla-tight | Affine-NMCTS | T | 13 | 0 | 34 | -4.06% |
| Ancilla-tight | Affine-NMCTS | CNOT | 15 | 1 | 31 | -3.55% |
| Ancilla-tight | Affine-NMCTS | depth | 13 | 4 | 30 | -2.98% |
| Ancilla-tight | Affine-NMCTS | peak_ancilla | 4 | 2 | 41 | -0.53% |
| Ancilla-tight | Fixed MCTS | score | 40 | 0 | 7 | -20.62% |
| Ancilla-tight | Fixed MCTS | T | 38 | 0 | 9 | -26.29% |
| Ancilla-tight | Fixed MCTS | CNOT | 40 | 0 | 7 | -23.48% |
| Ancilla-tight | Fixed MCTS | depth | 38 | 2 | 7 | -19.57% |
| Ancilla-tight | Fixed MCTS | peak_ancilla | 0 | 3 | 44 | +3.19% |
| Ancilla-tight | ESOP cube beam | score | 46 | 0 | 1 | -37.82% |
| Ancilla-tight | ESOP cube beam | T | 46 | 0 | 1 | -41.52% |
| Ancilla-tight | ESOP cube beam | CNOT | 39 | 5 | 3 | -25.55% |
| Ancilla-tight | ESOP cube beam | depth | 45 | 1 | 1 | -33.71% |
| Ancilla-tight | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -31.38% |
| Ancilla-tight | SSHR-H | score | 43 | 4 | 0 | -31.81% |
| Ancilla-tight | SSHR-H | T | 44 | 0 | 3 | -44.95% |
| Ancilla-tight | SSHR-H | CNOT | 11 | 36 | 0 | +18.00% |
| Ancilla-tight | SSHR-H | depth | 21 | 25 | 1 | -1.08% |
| Ancilla-tight | SSHR-H | peak_ancilla | 3 | 22 | 22 | +38.30% |
