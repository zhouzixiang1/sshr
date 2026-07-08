# Multi-Metric Pareto Tradeoff Analysis

Dominance is computed on raw logical resources: T, CNOT, depth, and peak ancilla.
Weighted score is not part of the dominance predicate.

## Pairwise dominance against Pareto-Resource-NMCTS

| baseline | pairs | Pareto dominates | baseline dominates | incomparable | equal | score W/L/T |
|---|---:|---:|---:|---:|---:|---:|
| Direct ANF | 177 | 69 | 1 | 103 | 4 | 172/1/4 |
| ESOP beam | 177 | 165 | 0 | 9 | 3 | 174/0/3 |
| ESOP-MILP | 177 | 123 | 2 | 45 | 7 | 167/3/7 |
| SSHR-H | 177 | 33 | 4 | 140 | 0 | 173/4/0 |
| SSHR-I CNOT | 177 | 9 | 3 | 165 | 0 | 173/4/0 |
| ABC-XAG | 177 | 33 | 0 | 144 | 0 | 177/0/0 |
| mockturtle XAG | 177 | 11 | 0 | 166 | 0 | 166/11/0 |
| CirKit AIG/MC | 177 | 21 | 0 | 156 | 0 | 177/0/0 |
| RevKit CLI exact oracle | 177 | 3 | 0 | 170 | 4 | 173/0/4 |

## Nondominated membership in the n<=6 method pool

| method | rows | nondominated | dominated | nondominated share |
|---|---:|---:|---:|---:|
| Pareto-Resource-NMCTS | 177 | 170 | 7 | 96.0% |
| SSHR-I CNOT | 177 | 162 | 15 | 91.5% |
| mockturtle XAG | 177 | 159 | 18 | 89.8% |
| RevKit CLI exact oracle | 177 | 141 | 36 | 79.7% |
| Resource-NMCTS | 177 | 124 | 53 | 70.1% |
| CirKit AIG/MC | 177 | 56 | 121 | 31.6% |
| SSHR-H | 177 | 46 | 131 | 26.0% |
| ESOP-MILP | 177 | 44 | 133 | 24.9% |
| ABC-XAG | 177 | 15 | 162 | 8.5% |
| Direct ANF | 177 | 7 | 170 | 4.0% |
| ESOP beam | 177 | 6 | 171 | 3.4% |
| AND-direct ANF | 177 | 4 | 173 | 2.3% |
