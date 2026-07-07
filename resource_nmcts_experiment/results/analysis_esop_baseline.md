# ESOP Baseline Analysis

This analysis uses Pareto-Resource-NMCTS as the reported method and compares it with ESOP baselines on exactly matched benchmark functions. The internal ESOP-MILP rows come from `raw_traditional_resource.csv`; the external ABC-ESOP rows come from `raw_external_traditional_resource_n6.csv`.

The SSHR-paper ESOP table is not directly comparable unless the same function set and cost model are used.  The tables below are same-benchmark comparisons and are therefore the evidence used in the manuscript.

## Aggregate by baseline

| baseline | functions | T ours/base/change | CNOT ours/base/change | ancilla ours/base/change | score ours/base/change | score W/L/T |
|---|---:|---:|---:|---:|---:|---:|
| Internal ESOP-MILP | 177 | 7216/14796/-51.23% | 14856/23631/-37.13% | 349/411/-15.09% | 8820.00/17121.33/-48.49% | 167/3/7 |
| ABC-ESOP export | 177 | 7216/9644/-25.18% | 14856/15537/-4.38% | 349/406/-14.04% | 8820.00/11453.97/-23.00% | 170/1/6 |

## Aggregate by n

| n | baseline | functions | ESOP T/CNOT/ancilla | ours T/CNOT/ancilla | T change | CNOT change | ancilla change | score W/L/T |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | Internal ESOP-MILP | 3 | 24/45/0 | 8/27/0 | -66.67% | -40.00% | +0.00% | 2/0/1 |
| 4 | Internal ESOP-MILP | 69 | 1456/2466/102 | 1028/2217/100 | -29.40% | -10.10% | -1.96% | 64/1/4 |
| 5 | Internal ESOP-MILP | 67 | 3392/5558/169 | 2604/5515/136 | -23.23% | -0.77% | -19.53% | 65/1/1 |
| 6 | Internal ESOP-MILP | 38 | 9924/15562/140 | 3576/7097/113 | -63.97% | -54.40% | -19.29% | 36/1/1 |
| 3 | ABC-ESOP export | 3 | 24/45/0 | 8/27/0 | -66.67% | -40.00% | +0.00% | 2/0/1 |
| 4 | ABC-ESOP export | 69 | 1576/2622/104 | 1028/2217/100 | -34.77% | -15.45% | -3.85% | 66/0/3 |
| 5 | ABC-ESOP export | 67 | 3592/5802/170 | 2604/5515/136 | -27.51% | -4.95% | -20.00% | 66/0/1 |
| 6 | ABC-ESOP export | 38 | 4452/7068/132 | 3576/7097/113 | -19.68% | +0.41% | -14.39% | 36/1/1 |

## Interpretation

Against the internal ESOP-MILP baseline, Pareto-Resource-NMCTS has lower aggregate T-count and CNOT count for every n=3..6 group; aggregate peak ancilla is tied at n=3 and lower for n=4..6.
Against external ABC-ESOP, Pareto-Resource-NMCTS has lower aggregate T-count and peak ancilla for every n=3..6 group.  Aggregate CNOT is lower for n=3..5 and is 0.41% higher at n=6, so the correct claim is weighted-resource/low-T superiority, not strict CNOT dominance over every ESOP export group.
