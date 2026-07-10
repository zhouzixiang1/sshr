# Paired Statistical Evidence

Rows are recomputed from usable raw CSV rows matched by item name.
The sign test is two-sided and ignores ties. Negative relative changes favor the target method.

| comparison | scope | pairs | W/L/T | mean relative | median relative | log10 p |
|---|---:|---:|---:|---:|---:|---:|
| n<=6 Pareto vs direct ANF | n=3-6 | 177 | 172/1/4 | -67.80% | -71.37% | -49.54 |
| n<=6 Pareto vs ESOP beam | n=3-6 | 177 | 174/0/3 | -36.09% | -32.56% | -52.08 |
| n<=6 Pareto vs ESOP-MILP | n=3-6 | 177 | 167/3/7 | -29.84% | -23.69% | -44.96 |
| n<=6 Pareto vs SSHR-H | n=3-6 | 177 | 173/4/0 | -41.06% | -43.05% | -45.37 |
| n<=6 Pareto vs SSHR-I CNOT | n=3-6 | 177 | 173/4/0 | -31.89% | -33.91% | -45.37 |
| n<=6 Pareto vs ABC-XAG | n=3-6 | 177 | 177/0/0 | -65.58% | -65.25% | -52.98 |
| ROS-style LUT best-K | n=3-6,14-16,18 | 309 | 309/0/0 | -84.27% | -81.38% | -92.72 |
| mockturtle XAG n<=6 | n=3-6 | 177 | 166/11/0 | -31.50% | -32.43% | -35.96 |
| mockturtle XAG n=14 | n=14 | 64 | 64/0/0 | -91.49% | -95.50% | -18.96 |
| CirKit AIG/MC n<=6 | n=3-6 | 177 | 177/0/0 | -62.34% | -62.35% | -52.98 |
| CirKit AIG/MC n=14 | n=14 | 64 | 64/0/0 | -94.46% | -96.10% | -18.96 |
| RevKit CLI exact oracle | n=3-6 | 177 | 173/0/4 | -67.28% | -70.18% | -51.78 |
| n=14 Pareto vs root beam | n=14 | 64 | 60/0/4 | -6.31% | -4.68% | -17.76 |
| n=16 Resource vs root beam | n=16 | 24 | 23/0/1 | -4.36% | -3.36% | -6.62 |
| n=18 Resource vs fast pair | n=18 | 12 | 12/0/0 | -3.55% | -1.79% | -3.31 |
