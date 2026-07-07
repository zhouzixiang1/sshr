# Score-Weight Robustness Analysis

This post-hoc analysis recomputes the candidate scores from already verified raw CSV rows. It does not rerun synthesis; it tests whether the reported comparisons survive alternative logical resource weights.

## Weight profiles

| profile | T | CNOT | depth | gates | ancilla |
|---|---:|---:|---:|---:|---:|
| Paper score | 1 | 0.04 | 0.015 | 0.01 | 2 |
| T-only | 1 | 0 | 0 | 0 | 0 |
| T-heavy | 1 | 0.015 | 0.005 | 0.005 | 1 |
| CNOT-depth | 0.65 | 0.18 | 0.08 | 0.01 | 2 |
| Ancilla-tight | 1 | 0.04 | 0.015 | 0.01 | 8 |

## Compact view

| dataset | target vs baseline | Paper score | T-only | CNOT-depth | Ancilla-tight |
|---|---|---:|---:|---:|---:|
| n<=6 traditional | pareto-resource-nmcts vs ESOP cube beam | 174/0/3, -36.09% | 174/0/3, -38.95% | 174/0/3, -32.08% | 174/0/3, -32.75% |
| n<=6 traditional | pareto-resource-nmcts vs ESOP-MILP | 167/3/7, -29.84% | 166/0/11, -32.77% | 165/4/8, -25.44% | 167/3/7, -26.68% |
| n<=6 traditional | pareto-resource-nmcts vs SSHR-H | 173/4/0, -41.06% | 173/0/4, -47.93% | 168/9/0, -27.87% | 172/5/0, -31.95% |
| n=14 random ANF | pareto-resource-nmcts vs FPRM root beam | 60/0/4, -6.31% | 60/0/4, -7.65% | 60/0/4, -5.35% | 56/4/4, -3.28% |
| n=16 random ANF | resource-nmcts vs FPRM root beam | 23/0/1, -4.36% | 23/0/1, -4.70% | 23/0/1, -4.28% | 23/0/1, -3.43% |
| n=18 random ANF | resource-nmcts vs FPRM root beam | 12/0/0, -5.29% | 12/0/0, -6.19% | 12/0/0, -4.54% | 11/1/0, -3.33% |
| n=18 random ANF | resource-nmcts vs fast pair guard | 12/0/0, -3.55% | 12/0/0, -3.75% | 12/0/0, -3.23% | 12/0/0, -3.33% |

## Full comparison rows

| dataset | profile | target | baseline | pairs | score W/L/T | mean relative |
|---|---|---|---|---:|---:|---:|
| n<=6 traditional | Paper score | and_pareto_resource_nmcts | Direct ANF | 177 | 172/1/4 | -67.80% |
| n<=6 traditional | T-only | and_pareto_resource_nmcts | Direct ANF | 177 | 172/0/5 | -72.25% |
| n<=6 traditional | T-heavy | and_pareto_resource_nmcts | Direct ANF | 177 | 172/1/4 | -70.16% |
| n<=6 traditional | CNOT-depth | and_pareto_resource_nmcts | Direct ANF | 177 | 172/1/4 | -59.55% |
| n<=6 traditional | Ancilla-tight | and_pareto_resource_nmcts | Direct ANF | 177 | 172/1/4 | -61.04% |
| n<=6 traditional | Paper score | and_pareto_resource_nmcts | AND-direct ANF | 177 | 172/0/5 | -51.19% |
| n<=6 traditional | T-only | and_pareto_resource_nmcts | AND-direct ANF | 177 | 172/0/5 | -54.84% |
| n<=6 traditional | T-heavy | and_pareto_resource_nmcts | AND-direct ANF | 177 | 172/0/5 | -52.99% |
| n<=6 traditional | CNOT-depth | and_pareto_resource_nmcts | AND-direct ANF | 177 | 172/0/5 | -47.67% |
| n<=6 traditional | Ancilla-tight | and_pareto_resource_nmcts | AND-direct ANF | 177 | 172/0/5 | -45.25% |
| n<=6 traditional | Paper score | and_pareto_resource_nmcts | ESOP cube beam | 177 | 174/0/3 | -36.09% |
| n<=6 traditional | T-only | and_pareto_resource_nmcts | ESOP cube beam | 177 | 174/0/3 | -38.95% |
| n<=6 traditional | T-heavy | and_pareto_resource_nmcts | ESOP cube beam | 177 | 174/0/3 | -37.52% |
| n<=6 traditional | CNOT-depth | and_pareto_resource_nmcts | ESOP cube beam | 177 | 174/0/3 | -32.08% |
| n<=6 traditional | Ancilla-tight | and_pareto_resource_nmcts | ESOP cube beam | 177 | 174/0/3 | -32.75% |
| n<=6 traditional | Paper score | and_pareto_resource_nmcts | ESOP-MILP | 177 | 167/3/7 | -29.84% |
| n<=6 traditional | T-only | and_pareto_resource_nmcts | ESOP-MILP | 177 | 166/0/11 | -32.77% |
| n<=6 traditional | T-heavy | and_pareto_resource_nmcts | ESOP-MILP | 177 | 167/3/7 | -31.32% |
| n<=6 traditional | CNOT-depth | and_pareto_resource_nmcts | ESOP-MILP | 177 | 165/4/8 | -25.44% |
| n<=6 traditional | Ancilla-tight | and_pareto_resource_nmcts | ESOP-MILP | 177 | 167/3/7 | -26.68% |
| n<=6 traditional | Paper score | and_pareto_resource_nmcts | SSHR-H | 177 | 173/4/0 | -41.06% |
| n<=6 traditional | T-only | and_pareto_resource_nmcts | SSHR-H | 177 | 173/0/4 | -47.93% |
| n<=6 traditional | T-heavy | and_pareto_resource_nmcts | SSHR-H | 177 | 173/4/0 | -44.70% |
| n<=6 traditional | CNOT-depth | and_pareto_resource_nmcts | SSHR-H | 177 | 168/9/0 | -27.87% |
| n<=6 traditional | Ancilla-tight | and_pareto_resource_nmcts | SSHR-H | 177 | 172/5/0 | -31.95% |
| n<=6 traditional | Paper score | and_pareto_resource_nmcts | Resource-NMCTS | 177 | 68/0/109 | -3.26% |
| n<=6 traditional | T-only | and_pareto_resource_nmcts | Resource-NMCTS | 177 | 53/0/124 | -3.72% |
| n<=6 traditional | T-heavy | and_pareto_resource_nmcts | Resource-NMCTS | 177 | 68/0/109 | -3.46% |
| n<=6 traditional | CNOT-depth | and_pareto_resource_nmcts | Resource-NMCTS | 177 | 68/0/109 | -3.31% |
| n<=6 traditional | Ancilla-tight | and_pareto_resource_nmcts | Resource-NMCTS | 177 | 60/8/109 | -2.13% |
| n=14 random ANF | Paper score | and_pareto_resource_nmcts | Direct ANF | 64 | 61/3/0 | -54.55% |
| n=14 random ANF | T-only | and_pareto_resource_nmcts | Direct ANF | 64 | 61/0/3 | -57.94% |
| n=14 random ANF | T-heavy | and_pareto_resource_nmcts | Direct ANF | 64 | 61/3/0 | -56.48% |
| n=14 random ANF | CNOT-depth | and_pareto_resource_nmcts | Direct ANF | 64 | 60/4/0 | -44.26% |
| n=14 random ANF | Ancilla-tight | and_pareto_resource_nmcts | Direct ANF | 64 | 53/11/0 | -51.62% |
| n=14 random ANF | Paper score | and_pareto_resource_nmcts | AND-direct ANF | 64 | 61/0/3 | -31.40% |
| n=14 random ANF | T-only | and_pareto_resource_nmcts | AND-direct ANF | 64 | 61/0/3 | -33.30% |
| n=14 random ANF | T-heavy | and_pareto_resource_nmcts | AND-direct ANF | 64 | 61/0/3 | -32.40% |
| n=14 random ANF | CNOT-depth | and_pareto_resource_nmcts | AND-direct ANF | 64 | 61/0/3 | -28.53% |
| n=14 random ANF | Ancilla-tight | and_pareto_resource_nmcts | AND-direct ANF | 64 | 57/4/3 | -28.37% |
| n=14 random ANF | Paper score | and_pareto_resource_nmcts | FPRM root beam | 64 | 60/0/4 | -6.31% |
| n=14 random ANF | T-only | and_pareto_resource_nmcts | FPRM root beam | 64 | 60/0/4 | -7.65% |
| n=14 random ANF | T-heavy | and_pareto_resource_nmcts | FPRM root beam | 64 | 60/0/4 | -6.98% |
| n=14 random ANF | CNOT-depth | and_pareto_resource_nmcts | FPRM root beam | 64 | 60/0/4 | -5.35% |
| n=14 random ANF | Ancilla-tight | and_pareto_resource_nmcts | FPRM root beam | 64 | 56/4/4 | -3.28% |
| n=14 random ANF | Paper score | and_pareto_resource_nmcts | FPRM linear pair | 64 | 59/0/5 | -3.49% |
| n=14 random ANF | T-only | and_pareto_resource_nmcts | FPRM linear pair | 64 | 58/0/6 | -3.83% |
| n=14 random ANF | T-heavy | and_pareto_resource_nmcts | FPRM linear pair | 64 | 59/0/5 | -3.66% |
| n=14 random ANF | CNOT-depth | and_pareto_resource_nmcts | FPRM linear pair | 64 | 59/0/5 | -2.94% |
| n=14 random ANF | Ancilla-tight | and_pareto_resource_nmcts | FPRM linear pair | 64 | 59/0/5 | -3.16% |
| n=14 random ANF | Paper score | and_pareto_resource_nmcts | Resource-NMCTS | 64 | 16/0/48 | -0.59% |
| n=14 random ANF | T-only | and_pareto_resource_nmcts | Resource-NMCTS | 64 | 10/0/54 | -0.64% |
| n=14 random ANF | T-heavy | and_pareto_resource_nmcts | Resource-NMCTS | 64 | 16/0/48 | -0.61% |
| n=14 random ANF | CNOT-depth | and_pareto_resource_nmcts | Resource-NMCTS | 64 | 15/1/48 | -0.60% |
| n=14 random ANF | Ancilla-tight | and_pareto_resource_nmcts | Resource-NMCTS | 64 | 16/0/48 | -0.48% |
| n=15 random ANF | Paper score | and_resource_nmcts | Direct ANF | 32 | 30/2/0 | -53.41% |
| n=15 random ANF | T-only | and_resource_nmcts | Direct ANF | 32 | 30/0/2 | -56.64% |
| n=15 random ANF | T-heavy | and_resource_nmcts | Direct ANF | 32 | 30/2/0 | -55.26% |
| n=15 random ANF | CNOT-depth | and_resource_nmcts | Direct ANF | 32 | 29/3/0 | -43.28% |
| n=15 random ANF | Ancilla-tight | and_resource_nmcts | Direct ANF | 32 | 29/3/0 | -50.83% |
| n=15 random ANF | Paper score | and_resource_nmcts | AND-direct ANF | 32 | 30/0/2 | -30.78% |
| n=15 random ANF | T-only | and_resource_nmcts | AND-direct ANF | 32 | 30/0/2 | -32.44% |
| n=15 random ANF | T-heavy | and_resource_nmcts | AND-direct ANF | 32 | 30/0/2 | -31.65% |
| n=15 random ANF | CNOT-depth | and_resource_nmcts | AND-direct ANF | 32 | 29/1/2 | -28.26% |
| n=15 random ANF | Ancilla-tight | and_resource_nmcts | AND-direct ANF | 32 | 29/1/2 | -28.14% |
| n=15 random ANF | Paper score | and_resource_nmcts | FPRM root beam | 32 | 30/0/2 | -5.28% |
| n=15 random ANF | T-only | and_resource_nmcts | FPRM root beam | 32 | 30/0/2 | -6.43% |
| n=15 random ANF | T-heavy | and_resource_nmcts | FPRM root beam | 32 | 30/0/2 | -5.85% |
| n=15 random ANF | CNOT-depth | and_resource_nmcts | FPRM root beam | 32 | 29/1/2 | -4.55% |
| n=15 random ANF | Ancilla-tight | and_resource_nmcts | FPRM root beam | 32 | 28/2/2 | -2.63% |
| n=15 random ANF | Paper score | and_resource_nmcts | Recursive linear pair | 32 | 0/0/32 | +0.00% |
| n=15 random ANF | T-only | and_resource_nmcts | Recursive linear pair | 32 | 0/0/32 | +0.00% |
| n=15 random ANF | T-heavy | and_resource_nmcts | Recursive linear pair | 32 | 0/0/32 | +0.00% |
| n=15 random ANF | CNOT-depth | and_resource_nmcts | Recursive linear pair | 32 | 0/0/32 | +0.00% |
| n=15 random ANF | Ancilla-tight | and_resource_nmcts | Recursive linear pair | 32 | 0/0/32 | +0.00% |
| n=16 random ANF | Paper score | and_resource_nmcts | Direct ANF | 24 | 23/1/0 | -60.83% |
| n=16 random ANF | T-only | and_resource_nmcts | Direct ANF | 24 | 23/0/1 | -63.36% |
| n=16 random ANF | T-heavy | and_resource_nmcts | Direct ANF | 24 | 23/1/0 | -62.35% |
| n=16 random ANF | CNOT-depth | and_resource_nmcts | Direct ANF | 24 | 23/1/0 | -50.40% |
| n=16 random ANF | Ancilla-tight | and_resource_nmcts | Direct ANF | 24 | 23/1/0 | -60.02% |
| n=16 random ANF | Paper score | and_resource_nmcts | AND-direct ANF | 24 | 23/0/1 | -33.56% |
| n=16 random ANF | T-only | and_resource_nmcts | AND-direct ANF | 24 | 23/0/1 | -34.50% |
| n=16 random ANF | T-heavy | and_resource_nmcts | AND-direct ANF | 24 | 23/0/1 | -34.08% |
| n=16 random ANF | CNOT-depth | and_resource_nmcts | AND-direct ANF | 24 | 23/0/1 | -31.40% |
| n=16 random ANF | Ancilla-tight | and_resource_nmcts | AND-direct ANF | 24 | 23/0/1 | -32.64% |
| n=16 random ANF | Paper score | and_resource_nmcts | FPRM root beam | 24 | 23/0/1 | -4.36% |
| n=16 random ANF | T-only | and_resource_nmcts | FPRM root beam | 24 | 23/0/1 | -4.70% |
| n=16 random ANF | T-heavy | and_resource_nmcts | FPRM root beam | 24 | 23/0/1 | -4.52% |
| n=16 random ANF | CNOT-depth | and_resource_nmcts | FPRM root beam | 24 | 23/0/1 | -4.28% |
| n=16 random ANF | Ancilla-tight | and_resource_nmcts | FPRM root beam | 24 | 23/0/1 | -3.43% |
| n=16 random ANF | Paper score | and_resource_nmcts | Recursive linear pair | 24 | 6/0/18 | -0.05% |
| n=16 random ANF | T-only | and_resource_nmcts | Recursive linear pair | 24 | 6/0/18 | -0.06% |
| n=16 random ANF | T-heavy | and_resource_nmcts | Recursive linear pair | 24 | 6/0/18 | -0.06% |
| n=16 random ANF | CNOT-depth | and_resource_nmcts | Recursive linear pair | 24 | 4/2/18 | -0.03% |
| n=16 random ANF | Ancilla-tight | and_resource_nmcts | Recursive linear pair | 24 | 5/1/18 | -0.05% |
| n=18 random ANF | Paper score | and_resource_nmcts | Direct ANF | 12 | 12/0/0 | -56.99% |
| n=18 random ANF | T-only | and_resource_nmcts | Direct ANF | 12 | 12/0/0 | -60.05% |
| n=18 random ANF | T-heavy | and_resource_nmcts | Direct ANF | 12 | 12/0/0 | -58.77% |
| n=18 random ANF | CNOT-depth | and_resource_nmcts | Direct ANF | 12 | 11/1/0 | -46.19% |
| n=18 random ANF | Ancilla-tight | and_resource_nmcts | Direct ANF | 12 | 11/1/0 | -55.08% |
| n=18 random ANF | Paper score | and_resource_nmcts | AND-direct ANF | 12 | 12/0/0 | -32.01% |
| n=18 random ANF | T-only | and_resource_nmcts | AND-direct ANF | 12 | 12/0/0 | -33.39% |
| n=18 random ANF | T-heavy | and_resource_nmcts | AND-direct ANF | 12 | 12/0/0 | -32.75% |
| n=18 random ANF | CNOT-depth | and_resource_nmcts | AND-direct ANF | 12 | 12/0/0 | -29.64% |
| n=18 random ANF | Ancilla-tight | and_resource_nmcts | AND-direct ANF | 12 | 11/1/0 | -30.06% |
| n=18 random ANF | Paper score | and_resource_nmcts | FPRM root beam | 12 | 12/0/0 | -5.29% |
| n=18 random ANF | T-only | and_resource_nmcts | FPRM root beam | 12 | 12/0/0 | -6.19% |
| n=18 random ANF | T-heavy | and_resource_nmcts | FPRM root beam | 12 | 12/0/0 | -5.74% |
| n=18 random ANF | CNOT-depth | and_resource_nmcts | FPRM root beam | 12 | 12/0/0 | -4.54% |
| n=18 random ANF | Ancilla-tight | and_resource_nmcts | FPRM root beam | 12 | 11/1/0 | -3.33% |
| n=18 random ANF | Paper score | and_resource_nmcts | fast pair guard | 12 | 12/0/0 | -3.55% |
| n=18 random ANF | T-only | and_resource_nmcts | fast pair guard | 12 | 12/0/0 | -3.75% |
| n=18 random ANF | T-heavy | and_resource_nmcts | fast pair guard | 12 | 12/0/0 | -3.65% |
| n=18 random ANF | CNOT-depth | and_resource_nmcts | fast pair guard | 12 | 12/0/0 | -3.23% |
| n=18 random ANF | Ancilla-tight | and_resource_nmcts | fast pair guard | 12 | 12/0/0 | -3.33% |

## Interpretation

- The traditional-function result is robust across all tested weights against ESOP cube beam and ESOP-MILP.
- The SSHR-H comparison remains favorable in weighted score, but the CNOT-depth profile narrows the margin and keeps the CNOT-only limitation visible.
- The high-dimensional claims survive T-only, T-heavy, CNOT-depth, and ancilla-tight rescoring against root-beam baselines; direct-ANF comparisons remain much larger but still trade CNOT/depth/ancilla.
- The n=16 AI guard remains a small no-score-loss improvement under the paper, T-only, and T-heavy weights, and becomes near-tie under CNOT-depth and ancilla-tight weights.
