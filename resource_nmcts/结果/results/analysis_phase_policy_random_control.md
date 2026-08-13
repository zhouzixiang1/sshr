# Phase Policy Random-Control Audit

This audit compares learned Affine-FPRM phase shortlists with eight same-budget random shortlists.
The independent unit is the held-out n=6 function; random repeats are averaged per function before the sign test.

| policy | top-k | functions | W/L/T vs random mean | sign p | target mean | random mean | mean delta | seed means beaten | target <= best random |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rank | 64 | 38 | 16/3/19 | 0.0044 | 1482.48 | 1482.80 | -0.318 (-0.021%) | 8/8 | 29/38 |
| diverse | 64 | 38 | 16/3/19 | 0.0044 | 1482.40 | 1482.80 | -0.405 (-0.027%) | 8/8 | 29/38 |
| rank | 128 | 38 | 14/5/19 | 0.0636 | 1482.29 | 1482.52 | -0.227 (-0.015%) | 8/8 | 28/38 |
| diverse | 128 | 38 | 14/5/19 | 0.0636 | 1482.15 | 1482.52 | -0.368 (-0.025%) | 8/8 | 29/38 |
| rank | 256 | 38 | 12/6/20 | 0.2379 | 1482.14 | 1482.32 | -0.181 (-0.012%) | 8/8 | 27/38 |
| diverse | 256 | 38 | 15/3/20 | 0.0075 | 1482.06 | 1482.32 | -0.260 (-0.018%) | 8/8 | 31/38 |
| rank | 512 | 38 | 14/3/21 | 0.0127 | 1482.03 | 1482.13 | -0.098 (-0.007%) | 8/8 | 30/38 |
| diverse | 512 | 38 | 17/0/21 | 1.53e-05 | 1481.95 | 1482.13 | -0.180 (-0.012%) | 8/8 | 32/38 |

## Interpretation

- Diverse top-512 is the strongest random-control row: it is never worse than the per-function random mean on non-tie functions and beats all eight random seed means.
- Random repeats are dense in this candidate space, so the margins are small in absolute score units; the claim is reliable pruning, not global phase/Rz optimality.
- Rows compare only the logic-layer T/Rz=30 synthesis proxy and do not synthesize approximate rotation sequences.
