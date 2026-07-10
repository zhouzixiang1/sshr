# ESOP Baseline Analysis

This analysis uses Pareto-Resource-NMCTS as the reported method and compares it with ESOP baselines on exactly matched benchmark functions. The internal ESOP-MILP rows come from `raw_traditional_resource.csv`; the external ABC-ESOP rows come from `raw_external_traditional_resource_n6.csv`.

The SSHR-paper ESOP table is not directly comparable unless the same function set and cost model are used.  The tables below are same-benchmark comparisons and are therefore the evidence used in the manuscript.

## Aggregate by baseline

| baseline | functions | T ours/base/change | CNOT ours/base/change | ancilla ours/base/change | score ours/base/change | score W/L/T |
|---|---:|---:|---:|---:|---:|---:|
| Internal ESOP-MILP | 177 | 7156/14796/-51.64% | 14698/23631/-37.80% | 359/411/-12.65% | 8771.50/17121.33/-48.77% | 167/3/7 |
| ABC-ESOP export | 177 | 7156/9644/-25.80% | 14698/15537/-5.40% | 359/406/-11.58% | 8771.50/11453.97/-23.42% | 170/1/6 |

## Aggregate by n

| n | baseline | functions | ESOP T/CNOT/ancilla | ours T/CNOT/ancilla | T change | CNOT change | ancilla change | score W/L/T |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | Internal ESOP-MILP | 3 | 24/45/0 | 8/27/0 | -66.67% | -40.00% | +0.00% | 2/0/1 |
| 4 | Internal ESOP-MILP | 69 | 1456/2466/102 | 1028/2217/100 | -29.40% | -10.10% | -1.96% | 64/1/4 |
| 5 | Internal ESOP-MILP | 67 | 3392/5558/169 | 2580/5461/139 | -23.94% | -1.75% | -17.75% | 65/1/1 |
| 6 | Internal ESOP-MILP | 38 | 9924/15562/140 | 3540/6993/120 | -64.33% | -55.06% | -14.29% | 36/1/1 |
| 3 | ABC-ESOP export | 3 | 24/45/0 | 8/27/0 | -66.67% | -40.00% | +0.00% | 2/0/1 |
| 4 | ABC-ESOP export | 69 | 1576/2622/104 | 1028/2217/100 | -34.77% | -15.45% | -3.85% | 66/0/3 |
| 5 | ABC-ESOP export | 67 | 3592/5802/170 | 2580/5461/139 | -28.17% | -5.88% | -18.24% | 66/0/1 |
| 6 | ABC-ESOP export | 38 | 4452/7068/132 | 3540/6993/120 | -20.49% | -1.06% | -9.09% | 36/1/1 |

## Interpretation

Against the internal ESOP-MILP baseline, Pareto-Resource-NMCTS has lower aggregate T-count and CNOT count for every n=3..6 group; aggregate peak ancilla is tied at n=3 and lower for n=4..6.
Against external ABC-ESOP, Pareto-Resource-NMCTS has lower aggregate T-count, CNOT count, and peak ancilla for every n=3..6 group after the Resource-NMCTS portfolio adds the cheap no-MCTS linear/root-beam candidates.  This supports a matched-benchmark ESOP superiority claim, while still not implying CNOT dominance over SSHR or hardware-mapped flows.
