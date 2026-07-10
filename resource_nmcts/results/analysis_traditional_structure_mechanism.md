# Traditional Structure Mechanism Audit

This audit stratifies the verified n<=6 traditional truth-table slice by Boolean-function structure.
Negative score deltas favor Pareto-Resource-NMCTS.  The audit is post-hoc over existing verified rows and does not rerun synthesis.

## Status counts

- pass: 11

| feature | bucket | functions | mean degree | mean ANF terms | vs direct ANF | vs ESOP-MILP | vs SSHR-H | vs ABC-XAG | vs Caterpillar API | interpretation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| family | arithmetic/mux | 5 | 3.20 | 5.00 | 4/1/0, -43.06% | 3/1/1, -19.53% | 5/0/0, -46.75% | 5/0/0, -65.48% | 5/0/0, -38.54% | moderate or mixed mechanism slice |
| family | parity | 4 | 1.00 | 4.50 | 0/0/4, +0.00% | 0/0/4, +0.00% | 4/0/0, -98.59% | 4/0/0, -99.21% | 4/0/0, -12.50% | trivial/affine guard: no algebraic score gain expected |
| family | random truth-table | 160 | 4.29 | 16.20 | 160/0/0, -70.23% | 156/2/2, -30.04% | 158/2/0, -40.07% | 160/0/0, -64.73% | 160/0/0, -48.81% | main mechanism slice: dense high-degree ANF benefits from factor/Pareto search |
| family | threshold/majority | 8 | 3.50 | 12.25 | 8/0/0, -68.47% | 8/0/0, -47.17% | 6/2/0, -28.50% | 8/0/0, -65.74% | 8/0/0, -54.12% | clear score-reduction slice |
| degree | degree 0-1 | 4 | 1.00 | 4.50 | 0/0/4, +0.00% | 0/0/4, +0.00% | 4/0/0, -98.59% | 4/0/0, -99.21% | 4/0/0, -12.50% | trivial/affine guard: no algebraic score gain expected |
| degree | degree 2 | 3 | 2.00 | 2.67 | 2/1/0, -41.82% | 2/0/1, -42.81% | 1/2/0, -25.00% | 3/0/0, -85.35% | 3/0/0, -58.70% | low-degree boundary: SSHR can remain competitive on some rows |
| degree | degree 3 | 38 | 3.00 | 7.84 | 38/0/0, -63.35% | 34/2/2, -23.46% | 36/2/0, -30.60% | 38/0/0, -71.29% | 38/0/0, -51.53% | clear score-reduction slice |
| degree | degree >=4 | 132 | 4.63 | 18.25 | 132/0/0, -71.72% | 131/1/0, -32.29% | 132/0/0, -42.69% | 132/0/0, -62.46% | 132/0/0, -47.74% | main mechanism slice: dense high-degree ANF benefits from factor/Pareto search |
| ANF terms | ANF <= n | 12 | 2.25 | 3.75 | 7/1/4, -30.71% | 7/0/5, -18.42% | 10/2/0, -53.71% | 12/0/0, -80.09% | 12/0/0, -31.50% | low-degree boundary: SSHR can remain competitive on some rows |
| ANF terms | ANF > 2n | 124 | 4.56 | 19.23 | 124/0/0, -73.38% | 123/1/0, -33.36% | 123/1/0, -41.71% | 124/0/0, -63.81% | 124/0/0, -49.97% | main mechanism slice: dense high-degree ANF benefits from factor/Pareto search |
| ANF terms | ANF n..2n | 41 | 3.46 | 7.39 | 41/0/0, -61.77% | 37/2/2, -22.55% | 40/1/0, -35.40% | 41/0/0, -66.67% | 41/0/0, -46.62% | clear score-reduction slice |

## Mechanism Reading

- Affine/parity rows are a guard sanity check: the method should not claim a score gain over direct algebraic synthesis there.
- The largest score reductions appear on high-degree or ANF-dense buckets, consistent with the paper's factor/Pareto search mechanism.
- Low-degree structured rows preserve an SSHR boundary, which prevents the mechanism claim from becoming universal dominance.
