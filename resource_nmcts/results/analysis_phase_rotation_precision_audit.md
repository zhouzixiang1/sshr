# Phase Rotation-Precision Sensitivity Audit

This audit freezes the verified phase/Rz candidates and recomputes logical resource scores
under multiple approximation precisions.  Each non-Clifford Rz is charged
`ceil(3 log2(1/epsilon))` T gates, with the same count added to logical depth and
gate count.  The estimate follows the common Ross--Selinger asymptotic scaling for
ancilla-free Clifford+T Z-rotation approximation.

This is a precision-sensitive logical cost model, not exact rotation-sequence synthesis,
not hardware mapping, and not a routed Clifford+T implementation.

| scope | comparison | epsilon | T/Rz | items | W/L/T | mean delta | target non-Clifford Rz | baseline non-Clifford Rz |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| traditional | Affine-128 vs RevKit oracle_synth | 0.001 | 30 | 177 | 177/0/0 | -65.795% | 21.36 | 52.21 |
| traditional | Affine-128 vs RevKit oracle_synth | 1e-06 | 60 | 177 | 177/0/0 | -66.118% | 21.36 | 52.21 |
| traditional | Affine-128 vs Affine-32 | 1e-06 | 60 | 177 | 43/0/134 | -0.583% | 21.36 | 21.45 |
| policy | Diverse-512 vs Budget-32 | 1e-06 | 60 | 38 | 17/0/21 | -2.381% | 47.68 | 48.13 |
| policy | Diverse-512 vs Wide-128 | 1e-06 | 60 | 38 | 0/7/31 | +0.002% | 47.68 | 47.68 |
| policy | Diverse-256 vs Wide-128 | 1e-06 | 60 | 38 | 0/9/29 | +0.007% | 47.68 | 47.68 |
| traditional | Affine-128 vs RevKit oracle_synth | 1e-09 | 90 | 177 | 177/0/0 | -66.226% | 21.36 | 52.21 |
| policy | Diverse-512 vs Wide-128 | 1e-09 | 90 | 38 | 0/7/31 | +0.001% | 47.68 | 47.68 |

## Interpretation

- At epsilon=1e-6, Affine-128 vs RevKit oracle_synth is 177/0/0 with -66.118% mean score change under the precision model.
- At epsilon=1e-6, Diverse-512 vs Budget-32 is 17/0/21 with -2.381% mean score change.
- At epsilon=1e-6, Diverse-512 vs Wide-128 is 0/7/31 with +0.002% mean score gap, so the learned shortlist remains a pruning result rather than a better-than-wide-search claim.
- The audit strengthens the phase/Rz boundary: results no longer depend on one hard-coded T/Rz=30 proxy, but they still do not claim synthesized rotation sequences.
