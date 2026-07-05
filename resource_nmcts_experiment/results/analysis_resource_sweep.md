# Resource Sweep Analysis

Rows: 940; usable: 940; errors: 0; skipped: 0.

## Mean resources by profile and method

| profile | method | completed | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| T-heavy | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 91.92 | 0.000 |
| T-heavy | Fixed MCTS | 47 | 54.81 | 109.49 | 109.77 | 1.55 | 58.79 | 0.143 |
| T-heavy | Affine-NMCTS | 47 | 41.62 | 85.02 | 89.21 | 1.62 | 45.17 | 1.297 |
| T-heavy | ESOP cube beam | 47 | 83.91 | 134.23 | 161.68 | 2.45 | 89.57 | 0.017 |
| T-heavy | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 76.47 | 0.065 |
| Balanced | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 99.02 | 0.000 |
| Balanced | Fixed MCTS | 47 | 54.64 | 109.15 | 109.43 | 1.55 | 64.22 | 0.138 |
| Balanced | Affine-NMCTS | 47 | 41.62 | 84.89 | 89.09 | 1.62 | 50.00 | 1.221 |
| Balanced | ESOP cube beam | 47 | 83.23 | 133.17 | 160.60 | 2.45 | 96.64 | 0.018 |
| Balanced | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 80.30 | 0.019 |
| CNOT-depth | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 98.00 | 0.000 |
| CNOT-depth | Fixed MCTS | 47 | 54.89 | 109.21 | 109.49 | 1.55 | 67.68 | 0.137 |
| CNOT-depth | Affine-NMCTS | 47 | 41.96 | 85.45 | 89.55 | 1.64 | 53.52 | 1.187 |
| CNOT-depth | ESOP cube beam | 47 | 83.49 | 133.64 | 160.87 | 2.45 | 96.86 | 0.018 |
| CNOT-depth | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 68.96 | 0.017 |
| Ancilla-tight | AND-direct ANF | 47 | 86.98 | 143.47 | 143.74 | 1.79 | 109.74 | 0.000 |
| Ancilla-tight | Fixed MCTS | 47 | 55.06 | 109.30 | 109.57 | 1.55 | 73.98 | 0.135 |
| Ancilla-tight | Affine-NMCTS | 47 | 43.32 | 86.43 | 90.23 | 1.66 | 61.83 | 1.242 |
| Ancilla-tight | ESOP cube beam | 47 | 83.32 | 133.30 | 160.85 | 2.45 | 111.41 | 0.018 |
| Ancilla-tight | SSHR-H | 47 | 73.70 | 64.60 | 83.30 | 1.19 | 87.45 | 0.017 |

## Objective winners by profile

| profile | winner method | functions |
|---|---|---:|
| T-heavy | Affine-NMCTS | 32 |
| T-heavy | AND-direct ANF | 5 |
| T-heavy | SSHR-H | 5 |
| T-heavy | Fixed MCTS | 5 |
| Balanced | Affine-NMCTS | 32 |
| Balanced | AND-direct ANF | 5 |
| Balanced | SSHR-H | 5 |
| Balanced | Fixed MCTS | 5 |
| CNOT-depth | Affine-NMCTS | 29 |
| CNOT-depth | SSHR-H | 7 |
| CNOT-depth | AND-direct ANF | 5 |
| CNOT-depth | Fixed MCTS | 5 |
| CNOT-depth | ESOP cube beam | 1 |
| Ancilla-tight | Affine-NMCTS | 30 |
| Ancilla-tight | Fixed MCTS | 7 |
| Ancilla-tight | AND-direct ANF | 5 |
| Ancilla-tight | SSHR-H | 5 |

## Focused Affine-NMCTS comparisons

| profile | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| T-heavy | Fixed MCTS | score | 35 | 0 | 12 | -22.80% |
| T-heavy | Fixed MCTS | T | 35 | 0 | 12 | -23.81% |
| T-heavy | Fixed MCTS | CNOT | 34 | 1 | 12 | -20.74% |
| T-heavy | Fixed MCTS | depth | 34 | 1 | 12 | -17.07% |
| T-heavy | Fixed MCTS | peak_ancilla | 0 | 3 | 44 | +3.19% |
| T-heavy | ESOP cube beam | score | 46 | 0 | 1 | -39.47% |
| T-heavy | ESOP cube beam | T | 45 | 0 | 2 | -40.40% |
| T-heavy | ESOP cube beam | CNOT | 37 | 7 | 3 | -23.67% |
| T-heavy | ESOP cube beam | depth | 44 | 2 | 1 | -32.03% |
| T-heavy | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -31.38% |
| T-heavy | SSHR-H | score | 42 | 5 | 0 | -40.14% |
| T-heavy | SSHR-H | T | 42 | 0 | 5 | -42.88% |
| T-heavy | SSHR-H | CNOT | 10 | 37 | 0 | +23.02% |
| T-heavy | SSHR-H | depth | 20 | 26 | 1 | +2.67% |
| T-heavy | SSHR-H | peak_ancilla | 3 | 23 | 21 | +37.23% |
| Balanced | Fixed MCTS | score | 35 | 0 | 12 | -21.79% |
| Balanced | Fixed MCTS | T | 35 | 0 | 12 | -23.69% |
| Balanced | Fixed MCTS | CNOT | 34 | 1 | 12 | -20.69% |
| Balanced | Fixed MCTS | depth | 34 | 1 | 12 | -17.02% |
| Balanced | Fixed MCTS | peak_ancilla | 0 | 3 | 44 | +3.19% |
| Balanced | ESOP cube beam | score | 46 | 0 | 1 | -37.63% |
| Balanced | ESOP cube beam | T | 45 | 0 | 2 | -39.58% |
| Balanced | ESOP cube beam | CNOT | 37 | 7 | 3 | -22.75% |
| Balanced | ESOP cube beam | depth | 44 | 2 | 1 | -31.38% |
| Balanced | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -31.38% |
| Balanced | SSHR-H | score | 42 | 5 | 0 | -36.92% |
| Balanced | SSHR-H | T | 42 | 0 | 5 | -42.89% |
| Balanced | SSHR-H | CNOT | 10 | 37 | 0 | +22.92% |
| Balanced | SSHR-H | depth | 20 | 26 | 1 | +2.59% |
| Balanced | SSHR-H | peak_ancilla | 3 | 23 | 21 | +37.23% |
| CNOT-depth | Fixed MCTS | score | 35 | 0 | 12 | -20.40% |
| CNOT-depth | Fixed MCTS | T | 35 | 0 | 12 | -23.60% |
| CNOT-depth | Fixed MCTS | CNOT | 34 | 1 | 12 | -20.55% |
| CNOT-depth | Fixed MCTS | depth | 34 | 1 | 12 | -16.86% |
| CNOT-depth | Fixed MCTS | peak_ancilla | 0 | 4 | 43 | +4.26% |
| CNOT-depth | ESOP cube beam | score | 45 | 1 | 1 | -33.45% |
| CNOT-depth | ESOP cube beam | T | 45 | 0 | 2 | -39.45% |
| CNOT-depth | ESOP cube beam | CNOT | 37 | 8 | 2 | -22.63% |
| CNOT-depth | ESOP cube beam | depth | 44 | 2 | 1 | -31.21% |
| CNOT-depth | ESOP cube beam | peak_ancilla | 29 | 0 | 18 | -30.85% |
| CNOT-depth | SSHR-H | score | 40 | 7 | 0 | -23.55% |
| CNOT-depth | SSHR-H | T | 42 | 0 | 5 | -42.68% |
| CNOT-depth | SSHR-H | CNOT | 10 | 37 | 0 | +23.34% |
| CNOT-depth | SSHR-H | depth | 20 | 26 | 1 | +2.91% |
| CNOT-depth | SSHR-H | peak_ancilla | 3 | 24 | 20 | +38.30% |
| Ancilla-tight | Fixed MCTS | score | 33 | 0 | 14 | -17.60% |
| Ancilla-tight | Fixed MCTS | T | 33 | 0 | 14 | -22.68% |
| Ancilla-tight | Fixed MCTS | CNOT | 33 | 0 | 14 | -20.36% |
| Ancilla-tight | Fixed MCTS | depth | 33 | 0 | 14 | -16.94% |
| Ancilla-tight | Fixed MCTS | peak_ancilla | 0 | 5 | 42 | +4.96% |
| Ancilla-tight | ESOP cube beam | score | 46 | 0 | 1 | -35.19% |
| Ancilla-tight | ESOP cube beam | T | 45 | 0 | 2 | -38.42% |
| Ancilla-tight | ESOP cube beam | CNOT | 36 | 9 | 2 | -22.37% |
| Ancilla-tight | ESOP cube beam | depth | 45 | 1 | 1 | -31.41% |
| Ancilla-tight | ESOP cube beam | peak_ancilla | 28 | 0 | 19 | -30.32% |
| Ancilla-tight | SSHR-H | score | 42 | 5 | 0 | -29.14% |
| Ancilla-tight | SSHR-H | T | 42 | 0 | 5 | -41.96% |
| Ancilla-tight | SSHR-H | CNOT | 11 | 36 | 0 | +24.00% |
| Ancilla-tight | SSHR-H | depth | 21 | 25 | 1 | +3.12% |
| Ancilla-tight | SSHR-H | peak_ancilla | 3 | 24 | 20 | +39.36% |
