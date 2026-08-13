# Paired Effect Uncertainty

Rows reuse the matched pairs from the paired statistical evidence table.
Mean and median intervals are deterministic percentile bootstrap intervals with 4000 resamples per comparison.
Negative relative changes favor the target method.

| comparison | scope | pairs | mean relative [95% CI] | median relative [95% CI] | item p10/p90 |
|---|---:|---:|---:|---:|---:|
| n<=6 Pareto vs direct ANF | n=3-6 | 177 | -67.80% [-69.91%, -65.42%] | -71.37% [-73.09%, -69.62%] | -78.88%/-54.46% |
| n<=6 Pareto vs ESOP beam | n=3-6 | 177 | -36.09% [-38.67%, -33.69%] | -32.56% [-35.11%, -29.81%] | -55.01%/-19.65% |
| n<=6 Pareto vs ESOP-MILP | n=3-6 | 177 | -29.84% [-32.70%, -27.04%] | -23.69% [-26.68%, -21.47%] | -62.94%/-10.26% |
| n<=6 Pareto vs SSHR-H | n=3-6 | 177 | -41.06% [-43.38%, -38.77%] | -43.05% [-44.08%, -39.82%] | -55.50%/-22.11% |
| n<=6 Pareto vs SSHR-I CNOT | n=3-6 | 177 | -31.89% [-33.80%, -29.90%] | -33.91% [-36.68%, -33.23%] | -46.91%/-14.30% |
| n<=6 Pareto vs ABC-XAG | n=3-6 | 177 | -65.58% [-67.10%, -64.11%] | -65.25% [-66.60%, -63.34%] | -76.73%/-54.77% |
| ROS-style LUT best-K | n=3-6,14-16,18 | 309 | -84.27% [-85.73%, -82.79%] | -81.38% [-83.16%, -79.32%] | -99.62%/-68.49% |
| mockturtle XAG n<=6 | n=3-6 | 177 | -31.50% [-34.31%, -28.62%] | -32.43% [-33.58%, -29.70%] | -49.55%/-9.96% |
| mockturtle XAG n=14 | n=14 | 64 | -91.49% [-94.09%, -88.33%] | -95.50% [-97.12%, -93.60%] | -98.93%/-83.64% |
| CirKit AIG/MC n<=6 | n=3-6 | 177 | -62.34% [-64.10%, -60.59%] | -62.35% [-64.66%, -61.06%] | -76.91%/-47.69% |
| CirKit AIG/MC n=14 | n=14 | 64 | -94.46% [-95.72%, -93.16%] | -96.10% [-97.33%, -94.71%] | -98.96%/-87.43% |
| RevKit CLI exact oracle | n=3-6 | 177 | -67.28% [-69.11%, -65.23%] | -70.18% [-71.53%, -68.21%] | -78.57%/-57.54% |
| n=14 Pareto vs root beam | n=14 | 64 | -6.31% [-7.89%, -4.95%] | -4.68% [-5.21%, -3.76%] | -13.44%/-2.05% |
| n=16 Resource vs root beam | n=16 | 24 | -4.36% [-6.61%, -2.89%] | -3.36% [-4.22%, -2.46%] | -6.53%/-1.55% |
| n=18 Resource vs fast pair | n=18 | 12 | -3.55% [-5.66%, -1.81%] | -1.79% [-4.50%, -1.29%] | -8.59%/-1.24% |
