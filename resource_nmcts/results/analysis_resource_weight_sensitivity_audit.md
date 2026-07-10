# Resource-Weight Sensitivity Audit

This audit recomputes weighted logical-resource scores for matched internal and external baseline rows.
It is post-hoc over verified CSV artifacts; it does not rerun synthesis or change the emitted circuits.

## Status counts

- pass: 78

## Weight profiles

| profile | T | CNOT | depth | gates | peak ancilla |
|---|---:|---:|---:|---:|---:|
| Paper score | 1 | 0.04 | 0.015 | 0.01 | 2 |
| T-only | 1 | 0 | 0 | 0 | 0 |
| CNOT-only | 0 | 1 | 0 | 0 | 0 |
| CNOT-depth | 0.65 | 0.18 | 0.08 | 0.01 | 2 |
| Balanced | 1 | 0.1 | 0.05 | 0 | 2 |
| Ancilla-tight | 1 | 0.04 | 0.015 | 0.01 | 8 |

## Compact rows

| comparison | role | pairs | Paper | T-only | CNOT-only | CNOT-depth | Ancilla-tight | boundary |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Pareto vs Direct ANF | primary same-task baseline | 177 | 172/1/4, -67.80% | 172/0/5, -72.25% | 164/9/4, -34.20% | 172/1/4, -59.55% | 172/1/4, -61.04% | Direct algebraic expansion is a baseline, not a strong optimized compiler. |
| Pareto vs ESOP-MILP | primary exact/ILP counterpoint | 177 | 167/3/7, -29.84% | 166/0/11, -32.77% | 123/41/13, -14.97% | 165/4/8, -25.44% | 167/3/7, -26.68% | ILP is exact for its ESOP model but not a global quantum-circuit optimum. |
| Pareto vs SSHR-H | CNOT-oriented SSHR counterpoint | 177 | 173/4/0, -41.06% | 173/0/4, -47.93% | 43/128/6, +18.99% | 168/9/0, -27.87% | 172/5/0, -31.95% | CNOT-only rows are expected to expose SSHR's intended strength. |
| Pareto vs SSHR-I CNOT | ILP SSHR CNOT counterpoint | 177 | 173/4/0, -31.89% | 168/1/8, -39.49% | 0/168/9, +62.06% | 156/21/0, -14.92% | 168/9/0, -22.46% | SSHR-I is a CNOT-oriented external result; weighted rows are not CNOT dominance claims. |
| Pareto vs ABC-XAG | external logic synthesis | 177 | 177/0/0, -65.58% | 177/0/0, -55.68% | 175/2/0, -40.26% | 177/0/0, -60.94% | 177/0/0, -77.52% | ABC-XAG is a mature logic-synthesis probe under the same logical cost projection. |
| Pareto vs ROS LUT best-K | ROS-style LUT proxy | 309 | 309/0/0, -84.27% | 306/0/3, -84.22% | 309/0/0, -82.14% | 309/0/0, -83.23% | 309/0/0, -83.09% | This is a verified LUT proxy, not the official ROS SAT garbage optimizer. |
| Pareto vs ROS min-line budget | ROS-style garbage-budget proxy | 309 | 309/0/0, -87.93% | 306/0/3, -87.95% | 309/0/0, -86.30% | 309/0/0, -87.04% | 309/0/0, -86.43% | The min-line budget is a reversible-pebbling proxy over LUT DAGs, not full ROS reproduction. |
| Pareto vs RevKit CLI | exact reversible synthesis probe | 177 | 173/0/4, -67.28% | 173/0/4, -72.59% | 107/63/7, -9.32% | 173/0/4, -56.53% | 173/0/4, -58.54% | RevKit exact-oracle rows test a real reversible toolchain but not routed Clifford+T mapping. |
| Pareto vs mockturtle XAG | external logic synthesis | 177 | 166/11/0, -31.50% | 59/70/48, +5.72% | 37/139/1, +18.40% | 163/14/0, -26.31% | 177/0/0, -59.81% | mockturtle is a logic-network probe under the paper's logical resource projection. |
| Pareto vs Caterpillar API | external logic synthesis | 177 | 177/0/0, -47.94% | 169/0/8, -36.63% | 4/173/0, +195.18% | 174/3/0, -34.26% | 177/0/0, -64.84% | Caterpillar API rows are verified ANF-XAG implementation-family probes, not full ROS or hardware mapping. |
| Pareto vs CirKit AIG/MC | external logic synthesis | 177 | 177/0/0, -62.34% | 177/0/0, -52.94% | 167/9/1, -35.03% | 177/0/0, -56.99% | 177/0/0, -74.69% | CirKit AIG/multiplicative-complexity rows are projected to the same logical resource fields. |
| n=14 Pareto vs root beam | high-dimensional internal counterpoint | 64 | 60/0/4, -6.31% | 60/0/4, -7.65% | 60/0/4, -5.48% | 60/0/4, -5.35% | 56/4/4, -3.28% | Symbolic high-dimensional evidence, not exhaustive truth-table benchmarking. |
| n=16 Resource vs root beam | high-dimensional internal counterpoint | 24 | 23/0/1, -4.36% | 23/0/1, -4.70% | 23/0/1, -4.42% | 23/0/1, -4.28% | 23/0/1, -3.43% | Symbolic high-dimensional evidence, not exhaustive truth-table benchmarking. |

## Interpretation

- Paper-score and T-only profiles test the main non-Clifford-resource claim.
- CNOT-only is included as a deliberate non-dominance check; CNOT-oriented baselines can win there without contradicting the paper's stated claim.
- CNOT-depth and ancilla-tight profiles test whether weighted-score gains disappear when two common secondary resources are emphasized.
- ROS, Caterpillar, and RevKit rows remain proxy/external-toolchain stress tests rather than hardware-mapped or full ROS-reproduction results.

## Full summary rows

| comparison | profile | scope | pairs | W/L/T | mean relative | median relative | status |
|---|---|---|---:|---:|---:|---:|---|
| Pareto vs Direct ANF | Paper score | n=3-6 | 177 | 172/1/4 | -67.80% | -71.37% | pass |
| Pareto vs Direct ANF | T-only | n=3-6 | 177 | 172/0/5 | -72.25% | -75.56% | pass |
| Pareto vs Direct ANF | CNOT-only | n=3-6 | 177 | 164/9/4 | -34.20% | -37.50% | pass |
| Pareto vs Direct ANF | CNOT-depth | n=3-6 | 177 | 172/1/4 | -59.55% | -63.50% | pass |
| Pareto vs Direct ANF | Balanced | n=3-6 | 177 | 172/1/4 | -65.66% | -69.34% | pass |
| Pareto vs Direct ANF | Ancilla-tight | n=3-6 | 177 | 172/1/4 | -61.04% | -65.05% | pass |
| Pareto vs ESOP-MILP | Paper score | n=3-6 | 177 | 167/3/7 | -29.84% | -23.69% | pass |
| Pareto vs ESOP-MILP | T-only | n=3-6 | 177 | 166/0/11 | -32.77% | -26.67% | pass |
| Pareto vs ESOP-MILP | CNOT-only | n=3-6 | 177 | 123/41/13 | -14.97% | -6.52% | pass |
| Pareto vs ESOP-MILP | CNOT-depth | n=3-6 | 177 | 165/4/8 | -25.44% | -18.47% | pass |
| Pareto vs ESOP-MILP | Balanced | n=3-6 | 177 | 166/3/8 | -28.48% | -21.86% | pass |
| Pareto vs ESOP-MILP | Ancilla-tight | n=3-6 | 177 | 167/3/7 | -26.68% | -19.84% | pass |
| Pareto vs SSHR-H | Paper score | n=3-6 | 177 | 173/4/0 | -41.06% | -43.05% | pass |
| Pareto vs SSHR-H | T-only | n=3-6 | 177 | 173/0/4 | -47.93% | -50.00% | pass |
| Pareto vs SSHR-H | CNOT-only | n=3-6 | 177 | 43/128/6 | +18.99% | +20.00% | pass |
| Pareto vs SSHR-H | CNOT-depth | n=3-6 | 177 | 168/9/0 | -27.87% | -27.26% | pass |
| Pareto vs SSHR-H | Balanced | n=3-6 | 177 | 173/4/0 | -37.36% | -38.82% | pass |
| Pareto vs SSHR-H | Ancilla-tight | n=3-6 | 177 | 172/5/0 | -31.95% | -33.29% | pass |
| Pareto vs SSHR-I CNOT | Paper score | n=3-6 | 177 | 173/4/0 | -31.89% | -33.91% | pass |
| Pareto vs SSHR-I CNOT | T-only | n=3-6 | 177 | 168/1/8 | -39.49% | -42.11% | pass |
| Pareto vs SSHR-I CNOT | CNOT-only | n=3-6 | 177 | 0/168/9 | +62.06% | +63.16% | pass |
| Pareto vs SSHR-I CNOT | CNOT-depth | n=3-6 | 177 | 156/21/0 | -14.92% | -17.50% | pass |
| Pareto vs SSHR-I CNOT | Balanced | n=3-6 | 177 | 172/5/0 | -27.28% | -30.50% | pass |
| Pareto vs SSHR-I CNOT | Ancilla-tight | n=3-6 | 177 | 168/9/0 | -22.46% | -24.50% | pass |
| Pareto vs ABC-XAG | Paper score | n=3-6 | 177 | 177/0/0 | -65.58% | -65.25% | pass |
| Pareto vs ABC-XAG | T-only | n=3-6 | 177 | 177/0/0 | -55.68% | -55.00% | pass |
| Pareto vs ABC-XAG | CNOT-only | n=3-6 | 177 | 175/2/0 | -40.26% | -40.00% | pass |
| Pareto vs ABC-XAG | CNOT-depth | n=3-6 | 177 | 177/0/0 | -60.94% | -60.59% | pass |
| Pareto vs ABC-XAG | Balanced | n=3-6 | 177 | 177/0/0 | -62.83% | -62.41% | pass |
| Pareto vs ABC-XAG | Ancilla-tight | n=3-6 | 177 | 177/0/0 | -77.52% | -78.04% | pass |
| Pareto vs ROS LUT best-K | Paper score | n=3-6,14-16,18 | 309 | 309/0/0 | -84.27% | -81.38% | pass |
| Pareto vs ROS LUT best-K | T-only | n=3-6,14-16,18 | 309 | 306/0/3 | -84.22% | -81.82% | pass |
| Pareto vs ROS LUT best-K | CNOT-only | n=3-6,14-16,18 | 309 | 309/0/0 | -82.14% | -78.63% | pass |
| Pareto vs ROS LUT best-K | CNOT-depth | n=3-6,14-16,18 | 309 | 309/0/0 | -83.23% | -79.84% | pass |
| Pareto vs ROS LUT best-K | Balanced | n=3-6,14-16,18 | 309 | 309/0/0 | -83.95% | -80.97% | pass |
| Pareto vs ROS LUT best-K | Ancilla-tight | n=3-6,14-16,18 | 309 | 309/0/0 | -83.09% | -80.52% | pass |
| Pareto vs ROS min-line budget | Paper score | n=3-6,14-16,18 | 309 | 309/0/0 | -87.93% | -92.77% | pass |
| Pareto vs ROS min-line budget | T-only | n=3-6,14-16,18 | 309 | 306/0/3 | -87.95% | -93.44% | pass |
| Pareto vs ROS min-line budget | CNOT-only | n=3-6,14-16,18 | 309 | 309/0/0 | -86.30% | -92.52% | pass |
| Pareto vs ROS min-line budget | CNOT-depth | n=3-6,14-16,18 | 309 | 309/0/0 | -87.04% | -92.50% | pass |
| Pareto vs ROS min-line budget | Balanced | n=3-6,14-16,18 | 309 | 309/0/0 | -87.68% | -92.73% | pass |
| Pareto vs ROS min-line budget | Ancilla-tight | n=3-6,14-16,18 | 309 | 309/0/0 | -86.43% | -92.35% | pass |
| Pareto vs RevKit CLI | Paper score | n=3-6 | 177 | 173/0/4 | -67.28% | -70.18% | pass |
| Pareto vs RevKit CLI | T-only | n=3-6 | 177 | 173/0/4 | -72.59% | -74.60% | pass |
| Pareto vs RevKit CLI | CNOT-only | n=3-6 | 177 | 107/63/7 | -9.32% | -9.30% | pass |
| Pareto vs RevKit CLI | CNOT-depth | n=3-6 | 177 | 173/0/4 | -56.53% | -58.64% | pass |
| Pareto vs RevKit CLI | Balanced | n=3-6 | 177 | 173/0/4 | -64.56% | -67.13% | pass |
| Pareto vs RevKit CLI | Ancilla-tight | n=3-6 | 177 | 173/0/4 | -58.54% | -61.13% | pass |
| Pareto vs mockturtle XAG | Paper score | n=3-6 | 177 | 166/11/0 | -31.50% | -32.43% | pass |
| Pareto vs mockturtle XAG | T-only | n=3-6 | 177 | 59/70/48 | +5.72% | +0.00% | pass |
| Pareto vs mockturtle XAG | CNOT-only | n=3-6 | 177 | 37/139/1 | +18.40% | +16.56% | pass |
| Pareto vs mockturtle XAG | CNOT-depth | n=3-6 | 177 | 163/14/0 | -26.31% | -27.19% | pass |
| Pareto vs mockturtle XAG | Balanced | n=3-6 | 177 | 163/13/1 | -26.75% | -27.31% | pass |
| Pareto vs mockturtle XAG | Ancilla-tight | n=3-6 | 177 | 177/0/0 | -59.81% | -61.63% | pass |
| Pareto vs Caterpillar API | Paper score | n=3-6 | 177 | 177/0/0 | -47.94% | -48.92% | pass |
| Pareto vs Caterpillar API | T-only | n=3-6 | 177 | 169/0/8 | -36.63% | -37.50% | pass |
| Pareto vs Caterpillar API | CNOT-only | n=3-6 | 177 | 4/173/0 | +195.18% | +181.25% | pass |
| Pareto vs Caterpillar API | CNOT-depth | n=3-6 | 177 | 174/3/0 | -34.26% | -34.99% | pass |
| Pareto vs Caterpillar API | Balanced | n=3-6 | 177 | 177/0/0 | -41.85% | -42.59% | pass |
| Pareto vs Caterpillar API | Ancilla-tight | n=3-6 | 177 | 177/0/0 | -64.84% | -67.91% | pass |
| Pareto vs CirKit AIG/MC | Paper score | n=3-6 | 177 | 177/0/0 | -62.34% | -62.35% | pass |
| Pareto vs CirKit AIG/MC | T-only | n=3-6 | 177 | 177/0/0 | -52.94% | -52.38% | pass |
| Pareto vs CirKit AIG/MC | CNOT-only | n=3-6 | 177 | 167/9/1 | -35.03% | -34.86% | pass |
| Pareto vs CirKit AIG/MC | CNOT-depth | n=3-6 | 177 | 177/0/0 | -56.99% | -57.28% | pass |
| Pareto vs CirKit AIG/MC | Balanced | n=3-6 | 177 | 177/0/0 | -59.34% | -59.26% | pass |
| Pareto vs CirKit AIG/MC | Ancilla-tight | n=3-6 | 177 | 177/0/0 | -74.69% | -75.27% | pass |
| n=14 Pareto vs root beam | Paper score | n=14 | 64 | 60/0/4 | -6.31% | -4.68% | pass |
| n=14 Pareto vs root beam | T-only | n=14 | 64 | 60/0/4 | -7.65% | -5.00% | pass |
| n=14 Pareto vs root beam | CNOT-only | n=14 | 64 | 60/0/4 | -5.48% | -4.80% | pass |
| n=14 Pareto vs root beam | CNOT-depth | n=14 | 64 | 60/0/4 | -5.35% | -4.63% | pass |
| n=14 Pareto vs root beam | Balanced | n=14 | 64 | 60/0/4 | -6.13% | -4.71% | pass |
| n=14 Pareto vs root beam | Ancilla-tight | n=14 | 64 | 56/4/4 | -3.28% | -3.05% | pass |
| n=16 Resource vs root beam | Paper score | n=16 | 24 | 23/0/1 | -4.36% | -3.36% | pass |
| n=16 Resource vs root beam | T-only | n=16 | 24 | 23/0/1 | -4.70% | -3.58% | pass |
| n=16 Resource vs root beam | CNOT-only | n=16 | 24 | 23/0/1 | -4.42% | -3.68% | pass |
| n=16 Resource vs root beam | CNOT-depth | n=16 | 24 | 23/0/1 | -4.28% | -3.45% | pass |
| n=16 Resource vs root beam | Balanced | n=16 | 24 | 23/0/1 | -4.37% | -3.40% | pass |
| n=16 Resource vs root beam | Ancilla-tight | n=16 | 24 | 23/0/1 | -3.43% | -3.04% | pass |
