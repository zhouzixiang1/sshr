# Search Contribution Decomposition

This report reuses already verified experiment CSV files and converts the scattered
ablation evidence into a single contribution table.  Every row is a matched
function-level comparison; negative relative values favor the target method.

## Compact score view

| category | comparison | dataset | pairs | score W/L/T | mean score change | mean T change |
|---|---|---|---:|---:|---:|---:|
| affine search | Affine greedy vs fixed-coordinate MCTS | ablation_affine | 321 | 165/88/68 | -12.12% | -13.49% |
| neural refine | Neural refine over affine greedy | ablation_affine | 322 | 65/0/257 | -1.08% | -1.00% |
| guarded MCTS | Guarded Affine-NMCTS over no-guard | ablation_affine | 322 | 88/0/234 | -1.74% | -1.81% |
| full affine | Full Affine-NMCTS vs fixed-coordinate MCTS | ablation_affine | 321 | 165/0/156 | -14.82% | -16.18% |
| portfolio | Resource-NMCTS over Affine-NMCTS | traditional_resource | 177 | 44/0/133 | -1.91% | -2.12% |
| pareto archive | Pareto archive over Resource-NMCTS | traditional_resource | 177 | 68/0/109 | -3.26% | -3.72% |
| dedicated ablation | No-MCTS portfolio over heuristic-only | search_ablation_traditional | 177 | 54/0/123 | -2.51% | -2.68% |
| dedicated ablation | No-MCTS portfolio over beam-only | search_ablation_traditional | 177 | 106/1/70 | -8.36% | -8.99% |
| dedicated ablation | Resource-NMCTS over heuristic-only | search_ablation_traditional | 177 | 98/0/79 | -3.93% | -4.03% |
| dedicated ablation | Resource-NMCTS over no-MCTS portfolio | search_ablation_traditional | 177 | 54/0/123 | -1.44% | -1.36% |
| dedicated ablation | Pareto Resource-NMCTS over no-MCTS portfolio | search_ablation_traditional | 177 | 106/0/71 | -4.69% | -5.07% |
| highdim ablation | Highdim no-MCTS portfolio over heuristic-only | search_ablation_highdim | 16 | 14/0/2 | -6.50% | -7.66% |
| highdim ablation | Highdim no-MCTS portfolio over beam-only | search_ablation_highdim | 16 | 14/0/2 | -3.08% | -3.45% |
| highdim ablation | Highdim no-MCTS portfolio over root beam | search_ablation_highdim | 16 | 14/0/2 | -6.25% | -7.39% |
| highdim ablation | Highdim no-MCTS portfolio over linear-pair | search_ablation_highdim | 16 | 14/0/2 | -3.08% | -3.45% |
| esop boundary | Pareto Resource-NMCTS vs ESOP-MILP | traditional_resource | 177 | 167/3/7 | -29.84% | -32.77% |
| n14 guard | Linear-pair guard vs root beam at n=14 | highdim_resource | 64 | 60/0/4 | -3.00% | -4.19% |
| n14 portfolio | Pareto Resource-NMCTS vs linear-pair at n=14 | highdim_resource | 64 | 59/0/5 | -3.49% | -3.83% |
| n15 guard | Recursive linear-pair guard vs root beam at n=15 | highdim_scale_resource | 32 | 30/0/2 | -5.28% | -6.43% |
| n15 portfolio | Pareto Resource-NMCTS vs recursive linear-pair at n=15 | highdim_scale_resource | 32 | 5/0/27 | -0.03% | -0.03% |
| n16 guard | Linear-pair guard vs root beam at n=16 | ultra_highdim_resource | 24 | 22/0/2 | -1.88% | -2.18% |
| n16 portfolio | Pareto Resource-NMCTS vs linear-pair at n=16 | ultra_highdim_resource | 24 | 9/0/15 | -0.09% | -0.11% |
| n18 guard | Fast linear-pair guard vs root beam at n=18 | mega_highdim_resource | 12 | 6/0/6 | -1.91% | -2.72% |
| n18 portfolio | Resource-NMCTS vs fast linear-pair at n=18 | mega_highdim_resource | 12 | 12/0/0 | -3.55% | -3.75% |
| learned prior | Learned prior for Affine-NMCTS | traditional_resource | 177 | 42/0/135 | -1.47% | -1.62% |
| learned prior | Learned prior for Resource-NMCTS | traditional_resource | 177 | 39/0/138 | -1.10% | -1.16% |
| learned prior | Learned prior for Pareto Resource-NMCTS | traditional_resource | 177 | 29/0/148 | -0.78% | -0.77% |

## Detailed metric view

| comparison | metric | W/L/T | target mean | baseline mean | mean relative |
|---|---|---:|---:|---:|---:|
| Affine greedy vs fixed-coordinate MCTS | T | 161/77/83 | 153.76 | 155.17 | -13.49% |
| Affine greedy vs fixed-coordinate MCTS | CNOT | 174/77/70 | 280.10 | 291.43 | -13.22% |
| Affine greedy vs fixed-coordinate MCTS | depth | 165/86/70 | 282.88 | 291.71 | -10.77% |
| Affine greedy vs fixed-coordinate MCTS | peak_ancilla | 1/46/274 | 1.99 | 1.85 | +6.60% |
| Affine greedy vs fixed-coordinate MCTS | score | 165/88/68 | 174.35 | 176.09 | -12.12% |
| Neural refine over affine greedy | T | 25/0/297 | 153.75 | 154.09 | -1.00% |
| Neural refine over affine greedy | CNOT | 44/16/262 | 280.26 | 280.80 | -0.95% |
| Neural refine over affine greedy | depth | 47/15/260 | 282.95 | 283.58 | -1.01% |
| Neural refine over affine greedy | peak_ancilla | 18/0/304 | 1.93 | 1.99 | -1.86% |
| Neural refine over affine greedy | score | 65/0/257 | 174.24 | 174.72 | -1.08% |
| Guarded Affine-NMCTS over no-guard | T | 77/0/245 | 145.39 | 153.75 | -1.81% |
| Guarded Affine-NMCTS over no-guard | CNOT | 77/10/235 | 272.73 | 280.26 | -0.87% |
| Guarded Affine-NMCTS over no-guard | depth | 78/10/234 | 275.39 | 282.95 | -0.89% |
| Guarded Affine-NMCTS over no-guard | peak_ancilla | 15/0/307 | 1.89 | 1.93 | -1.42% |
| Guarded Affine-NMCTS over no-guard | score | 88/0/234 | 165.34 | 174.24 | -1.74% |
| Full Affine-NMCTS vs fixed-coordinate MCTS | T | 161/0/160 | 145.03 | 155.17 | -16.18% |
| Full Affine-NMCTS vs fixed-coordinate MCTS | CNOT | 164/1/156 | 272.01 | 291.43 | -14.87% |
| Full Affine-NMCTS vs fixed-coordinate MCTS | depth | 161/3/157 | 274.67 | 291.71 | -12.52% |
| Full Affine-NMCTS vs fixed-coordinate MCTS | peak_ancilla | 1/13/307 | 1.89 | 1.85 | +1.72% |
| Full Affine-NMCTS vs fixed-coordinate MCTS | score | 165/0/156 | 164.95 | 176.09 | -14.82% |
| Resource-NMCTS over Affine-NMCTS | T | 33/0/144 | 43.91 | 45.88 | -2.12% |
| Resource-NMCTS over Affine-NMCTS | CNOT | 42/0/135 | 89.85 | 94.36 | -2.46% |
| Resource-NMCTS over Affine-NMCTS | depth | 42/2/133 | 94.51 | 98.92 | -2.24% |
| Resource-NMCTS over Affine-NMCTS | peak_ancilla | 1/8/168 | 1.92 | 1.88 | +2.31% |
| Resource-NMCTS over Affine-NMCTS | score | 44/0/133 | 53.22 | 55.37 | -1.91% |
| Pareto archive over Resource-NMCTS | T | 53/0/124 | 40.43 | 43.91 | -3.72% |
| Pareto archive over Resource-NMCTS | CNOT | 66/0/111 | 83.04 | 89.85 | -3.90% |
| Pareto archive over Resource-NMCTS | depth | 65/2/110 | 88.00 | 94.51 | -3.48% |
| Pareto archive over Resource-NMCTS | peak_ancilla | 2/20/155 | 2.03 | 1.92 | +4.80% |
| Pareto archive over Resource-NMCTS | score | 68/0/109 | 49.56 | 53.22 | -3.26% |
| No-MCTS portfolio over heuristic-only | T | 40/0/137 | 44.41 | 46.69 | -2.68% |
| No-MCTS portfolio over heuristic-only | CNOT | 52/0/125 | 90.38 | 95.28 | -2.96% |
| No-MCTS portfolio over heuristic-only | depth | 52/2/123 | 95.34 | 100.30 | -2.69% |
| No-MCTS portfolio over heuristic-only | peak_ancilla | 5/6/166 | 1.99 | 1.99 | +0.99% |
| No-MCTS portfolio over heuristic-only | score | 54/0/123 | 53.90 | 56.46 | -2.51% |
| No-MCTS portfolio over beam-only | T | 81/0/96 | 44.41 | 47.41 | -8.99% |
| No-MCTS portfolio over beam-only | CNOT | 86/15/76 | 90.38 | 94.04 | -5.88% |
| No-MCTS portfolio over beam-only | depth | 86/16/75 | 95.34 | 99.00 | -5.62% |
| No-MCTS portfolio over beam-only | peak_ancilla | 23/10/144 | 1.99 | 2.07 | -2.92% |
| No-MCTS portfolio over beam-only | score | 106/1/70 | 53.90 | 57.26 | -8.36% |
| Resource-NMCTS over heuristic-only | T | 59/0/118 | 43.91 | 46.69 | -4.03% |
| Resource-NMCTS over heuristic-only | CNOT | 76/12/89 | 89.85 | 95.28 | -3.84% |
| Resource-NMCTS over heuristic-only | depth | 82/12/83 | 94.51 | 100.30 | -3.93% |
| Resource-NMCTS over heuristic-only | peak_ancilla | 18/6/153 | 1.92 | 1.99 | -1.46% |
| Resource-NMCTS over heuristic-only | score | 98/0/79 | 53.22 | 56.46 | -3.93% |
| Resource-NMCTS over no-MCTS portfolio | T | 21/0/156 | 43.91 | 44.41 | -1.36% |
| Resource-NMCTS over no-MCTS portfolio | CNOT | 30/16/131 | 89.85 | 90.38 | -0.87% |
| Resource-NMCTS over no-MCTS portfolio | depth | 38/12/127 | 94.51 | 95.34 | -1.25% |
| Resource-NMCTS over no-MCTS portfolio | peak_ancilla | 13/0/164 | 1.92 | 1.99 | -2.45% |
| Resource-NMCTS over no-MCTS portfolio | score | 54/0/123 | 53.22 | 53.90 | -1.44% |
| Pareto Resource-NMCTS over no-MCTS portfolio | T | 73/0/104 | 40.43 | 44.41 | -5.07% |
| Pareto Resource-NMCTS over no-MCTS portfolio | CNOT | 88/9/80 | 83.04 | 90.38 | -4.77% |
| Pareto Resource-NMCTS over no-MCTS portfolio | depth | 93/9/75 | 88.00 | 95.34 | -4.73% |
| Pareto Resource-NMCTS over no-MCTS portfolio | peak_ancilla | 14/19/144 | 2.03 | 1.99 | +2.26% |
| Pareto Resource-NMCTS over no-MCTS portfolio | score | 106/0/71 | 49.56 | 53.90 | -4.69% |
| Highdim no-MCTS portfolio over heuristic-only | T | 14/0/2 | 3081.75 | 3231.00 | -7.66% |
| Highdim no-MCTS portfolio over heuristic-only | CNOT | 14/0/2 | 5312.56 | 5541.19 | -5.28% |
| Highdim no-MCTS portfolio over heuristic-only | depth | 12/2/2 | 5314.62 | 5541.31 | -2.83% |
| Highdim no-MCTS portfolio over heuristic-only | peak_ancilla | 0/14/2 | 3.25 | 2.25 | +45.83% |
| Highdim no-MCTS portfolio over heuristic-only | score | 14/0/2 | 3400.92 | 3561.57 | -6.50% |
| Highdim no-MCTS portfolio over beam-only | T | 14/0/2 | 3081.75 | 3135.75 | -3.45% |
| Highdim no-MCTS portfolio over beam-only | CNOT | 14/0/2 | 5312.56 | 5395.50 | -1.77% |
| Highdim no-MCTS portfolio over beam-only | depth | 11/3/2 | 5314.62 | 5396.00 | +0.32% |
| Highdim no-MCTS portfolio over beam-only | peak_ancilla | 0/2/14 | 3.25 | 3.12 | +3.65% |
| Highdim no-MCTS portfolio over beam-only | score | 14/0/2 | 3400.92 | 3459.50 | -3.08% |
| Highdim no-MCTS portfolio over root beam | T | 14/0/2 | 3081.75 | 3220.00 | -7.39% |
| Highdim no-MCTS portfolio over root beam | CNOT | 14/0/2 | 5312.56 | 5537.75 | -5.20% |
| Highdim no-MCTS portfolio over root beam | depth | 12/2/2 | 5314.62 | 5537.88 | -2.76% |
| Highdim no-MCTS portfolio over root beam | peak_ancilla | 0/14/2 | 3.25 | 2.25 | +45.83% |
| Highdim no-MCTS portfolio over root beam | score | 14/0/2 | 3400.92 | 3550.39 | -6.25% |
| Highdim no-MCTS portfolio over linear-pair | T | 14/0/2 | 3081.75 | 3135.75 | -3.45% |
| Highdim no-MCTS portfolio over linear-pair | CNOT | 14/0/2 | 5312.56 | 5395.50 | -1.77% |
| Highdim no-MCTS portfolio over linear-pair | depth | 11/3/2 | 5314.62 | 5396.00 | +0.32% |
| Highdim no-MCTS portfolio over linear-pair | peak_ancilla | 0/2/14 | 3.25 | 3.12 | +3.65% |
| Highdim no-MCTS portfolio over linear-pair | score | 14/0/2 | 3400.92 | 3459.50 | -3.08% |
| Pareto Resource-NMCTS vs ESOP-MILP | T | 166/0/11 | 40.43 | 83.59 | -32.77% |
| Pareto Resource-NMCTS vs ESOP-MILP | CNOT | 123/41/13 | 83.04 | 133.51 | -14.97% |
| Pareto Resource-NMCTS vs ESOP-MILP | depth | 156/12/9 | 88.00 | 159.56 | -22.54% |
| Pareto Resource-NMCTS vs ESOP-MILP | peak_ancilla | 58/7/112 | 2.03 | 2.32 | -8.00% |
| Pareto Resource-NMCTS vs ESOP-MILP | score | 167/3/7 | 49.56 | 96.73 | -29.84% |
| Linear-pair guard vs root beam at n=14 | T | 60/0/4 | 2193.50 | 2248.81 | -4.19% |
| Linear-pair guard vs root beam at n=14 | CNOT | 57/1/6 | 3790.83 | 3886.62 | -3.03% |
| Linear-pair guard vs root beam at n=14 | depth | 54/6/4 | 3791.78 | 3886.77 | -1.51% |
| Linear-pair guard vs root beam at n=14 | peak_ancilla | 0/58/6 | 2.94 | 2.03 | +54.30% |
| Linear-pair guard vs root beam at n=14 | score | 60/0/4 | 2422.51 | 2481.64 | -3.00% |
| Pareto Resource-NMCTS vs linear-pair at n=14 | T | 58/0/6 | 2148.81 | 2193.50 | -3.83% |
| Pareto Resource-NMCTS vs linear-pair at n=14 | CNOT | 59/0/5 | 3724.98 | 3790.83 | -2.54% |
| Pareto Resource-NMCTS vs linear-pair at n=14 | depth | 54/5/5 | 3726.72 | 3791.78 | -1.26% |
| Pareto Resource-NMCTS vs linear-pair at n=14 | peak_ancilla | 1/9/54 | 3.06 | 2.94 | +3.23% |
| Pareto Resource-NMCTS vs linear-pair at n=14 | score | 59/0/5 | 2374.22 | 2422.51 | -3.49% |
| Recursive linear-pair guard vs root beam at n=15 | T | 30/0/2 | 3200.25 | 3302.50 | -6.43% |
| Recursive linear-pair guard vs root beam at n=15 | CNOT | 29/0/3 | 5492.38 | 5670.19 | -4.89% |
| Recursive linear-pair guard vs root beam at n=15 | depth | 28/2/2 | 5493.59 | 5670.25 | -2.41% |
| Recursive linear-pair guard vs root beam at n=15 | peak_ancilla | 0/30/2 | 3.06 | 1.94 | +60.16% |
| Recursive linear-pair guard vs root beam at n=15 | score | 30/0/2 | 3529.63 | 3640.08 | -5.28% |
| Pareto Resource-NMCTS vs recursive linear-pair at n=15 | T | 5/0/27 | 3199.62 | 3200.25 | -0.03% |
| Pareto Resource-NMCTS vs recursive linear-pair at n=15 | CNOT | 1/4/27 | 5492.75 | 5492.38 | +0.02% |
| Pareto Resource-NMCTS vs recursive linear-pair at n=15 | depth | 1/4/27 | 5493.97 | 5493.59 | +0.02% |
| Pareto Resource-NMCTS vs recursive linear-pair at n=15 | peak_ancilla | 0/0/32 | 3.06 | 3.06 | +0.00% |
| Pareto Resource-NMCTS vs recursive linear-pair at n=15 | score | 5/0/27 | 3529.02 | 3529.63 | -0.03% |
| Linear-pair guard vs root beam at n=16 | T | 22/0/2 | 3759.67 | 3822.33 | -2.18% |
| Linear-pair guard vs root beam at n=16 | CNOT | 22/0/2 | 6501.33 | 6613.50 | -2.10% |
| Linear-pair guard vs root beam at n=16 | depth | 22/0/2 | 6501.46 | 6613.62 | -2.10% |
| Linear-pair guard vs root beam at n=16 | peak_ancilla | 0/22/2 | 3.21 | 2.29 | +47.22% |
| Linear-pair guard vs root beam at n=16 | score | 22/0/2 | 4148.75 | 4216.21 | -1.88% |
| Pareto Resource-NMCTS vs linear-pair at n=16 | T | 8/0/16 | 3756.33 | 3759.67 | -0.11% |
| Pareto Resource-NMCTS vs linear-pair at n=16 | CNOT | 2/6/16 | 6504.17 | 6501.33 | +0.03% |
| Pareto Resource-NMCTS vs linear-pair at n=16 | depth | 2/6/16 | 6504.29 | 6501.46 | +0.03% |
| Pareto Resource-NMCTS vs linear-pair at n=16 | peak_ancilla | 0/0/24 | 3.21 | 3.21 | +0.00% |
| Pareto Resource-NMCTS vs linear-pair at n=16 | score | 9/0/15 | 4145.59 | 4148.75 | -0.09% |
| Fast linear-pair guard vs root beam at n=18 | T | 6/0/6 | 6754.00 | 6765.33 | -2.72% |
| Fast linear-pair guard vs root beam at n=18 | CNOT | 5/0/7 | 11566.83 | 11585.17 | -1.79% |
| Fast linear-pair guard vs root beam at n=18 | depth | 5/1/6 | 11568.42 | 11585.25 | +0.14% |
| Fast linear-pair guard vs root beam at n=18 | peak_ancilla | 0/6/6 | 2.67 | 2.17 | +37.50% |
| Fast linear-pair guard vs root beam at n=18 | score | 6/0/6 | 7439.93 | 7451.30 | -1.91% |
| Resource-NMCTS vs fast linear-pair at n=18 | T | 12/0/0 | 6641.67 | 6754.00 | -3.75% |
| Resource-NMCTS vs fast linear-pair at n=18 | CNOT | 12/0/0 | 11382.42 | 11566.83 | -2.65% |
| Resource-NMCTS vs fast linear-pair at n=18 | depth | 12/0/0 | 11383.67 | 11568.42 | -2.96% |
| Resource-NMCTS vs fast linear-pair at n=18 | peak_ancilla | 0/6/6 | 3.25 | 2.67 | +20.83% |
| Resource-NMCTS vs fast linear-pair at n=18 | score | 12/0/0 | 7317.88 | 7439.93 | -3.55% |
| Learned prior for Affine-NMCTS | T | 22/0/155 | 45.88 | 46.42 | -1.62% |
| Learned prior for Affine-NMCTS | CNOT | 33/2/142 | 94.36 | 95.48 | -1.61% |
| Learned prior for Affine-NMCTS | depth | 33/5/139 | 98.92 | 100.13 | -1.64% |
| Learned prior for Affine-NMCTS | peak_ancilla | 1/0/176 | 1.88 | 1.89 | -0.19% |
| Learned prior for Affine-NMCTS | score | 42/0/135 | 55.37 | 55.99 | -1.47% |
| Learned prior for Resource-NMCTS | T | 17/0/160 | 43.91 | 44.32 | -1.16% |
| Learned prior for Resource-NMCTS | CNOT | 27/5/145 | 89.85 | 90.46 | -0.95% |
| Learned prior for Resource-NMCTS | depth | 31/4/142 | 94.51 | 95.32 | -1.21% |
| Learned prior for Resource-NMCTS | peak_ancilla | 3/0/174 | 1.92 | 1.94 | -0.56% |
| Learned prior for Resource-NMCTS | score | 39/0/138 | 53.22 | 53.70 | -1.10% |
| Learned prior for Pareto Resource-NMCTS | T | 9/0/168 | 40.43 | 40.66 | -0.77% |
| Learned prior for Pareto Resource-NMCTS | CNOT | 19/3/155 | 83.04 | 83.29 | -0.47% |
| Learned prior for Pareto Resource-NMCTS | depth | 21/5/151 | 88.00 | 88.49 | -0.81% |
| Learned prior for Pareto Resource-NMCTS | peak_ancilla | 5/0/172 | 2.03 | 2.06 | -0.94% |
| Learned prior for Pareto Resource-NMCTS | score | 29/0/148 | 49.56 | 49.86 | -0.78% |

## Interpretation

- The affine-coordinate search is the largest algorithmic jump before the full portfolio: affine greedy already improves over fixed-coordinate MCTS in score on the matched completed rows.
- Neural refinement and the fixed-coordinate guard are smaller but monotone in score on this benchmark: both add score wins without score losses in the matched ablation rows.
- The learned action prior is a positive but modest quality signal on the n<=6 rerun; it improves score with no losses, while earlier runtime evidence shows it is not yet the fastest configuration.
- The Pareto archive gives the clearest small-function portfolio gain over single-score Resource-NMCTS, again with no score losses.
- In the high-dimensional suites, the measurable scale contribution is mostly the bounded linear-pair guard.  Resource/Profile/Pareto sometimes reduce to the same guarded candidate, so these rows should be written as scalability/guard evidence rather than as independent Pareto superiority evidence.
