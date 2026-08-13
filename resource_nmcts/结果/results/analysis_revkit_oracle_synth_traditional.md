# RevKit Oracle Synth Baseline

This run uses the installed RevKit Python API (`oracle_synth`) on
complete truth-table benchmark rows and estimates the returned
Rz-phase netlist at the logic layer.  It is a real RevKit API
baseline, not the ABC-only ROS-style LUT proxy, but it is still not
hardware mapping and not the legacy CirKit CLI flow.

Rows: 177; usable: 177.
Exact Clifford+T-supported rows under this audit: 6; rows with non-Clifford Rz rotations: 171.
Total non-Clifford Rz rotations: 9242; maximum observed denominator in angle/pi: 64.

The pairwise `score` and `T` comparisons below are lower-bound comparisons
for RevKit whenever `rz_non_clifford > 0`, because the cost of synthesizing
non-Clifford Rz rotations into Clifford+T is not included.
`score_rz1`, `score_rz2`, `score_rz4`, and `score_rz10` add a symbolic
cost of 1, 2, 4, or 10 score units per non-Clifford Rz rotation.

## Rotation Spectrum

- total exact T-like gates: 168 (mean 0.95)
- total non-Clifford Rz rotations: 9242 (mean 52.21, median 43.00, max 127)
- total Rz rotations: 9453

| n | rows | mean exact T-like | mean non-Clifford Rz | mean total Rz |
|---:|---:|---:|---:|---:|
| 3 | 3 | 5.33 | 0.00 | 7.00 |
| 4 | 69 | 1.88 | 22.67 | 24.80 |
| 5 | 67 | 0.27 | 52.91 | 53.39 |
| 6 | 38 | 0.11 | 108.76 | 109.05 |

## Break-even Rz Proxy

Break-even is the per-Rz score charge needed for the target method's
ordinary score to match the RevKit lower-bound score on each row.

| target | items | already wins | finite thresholds | impossible without Rz cost | median break-even | mean break-even | covered by Rz=1/2/4/10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| and_resource_nmcts | 177 | 6 | 177 | 0 | 0.83 | 0.82 | 140/177/177/177 |
| and_pareto_resource_nmcts | 177 | 6 | 177 | 0 | 0.80 | 0.78 | 157/177/177/177 |
| and_fprm_polarity_archive | 177 | 4 | 175 | 2 | 0.90 | 0.88 | 136/174/175/175 |
| direct_anf | 177 | 4 | 175 | 2 | 3.15 | 3.20 | 6/25/128/175 |

## Pairwise Comparisons

| target | baseline | metric | items | W/L/T | mean relative |
|---|---|---|---:|---:|---:|
| and_resource_nmcts | external_revkit_oracle_synth | T | 177 | 2/171/4 | +4060.08% |
| and_resource_nmcts | external_revkit_oracle_synth | phase_ops | 177 | 148/18/11 | -23.88% |
| and_resource_nmcts | external_revkit_oracle_synth | CNOT | 177 | 11/166/0 | +48.17% |
| and_resource_nmcts | external_revkit_oracle_synth | depth | 177 | 122/52/3 | -11.24% |
| and_resource_nmcts | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -59.83% |
| and_resource_nmcts | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +192.09% |
| and_resource_nmcts | external_revkit_oracle_synth | score | 177 | 6/171/0 | +751.69% |
| and_resource_nmcts | external_revkit_oracle_synth | score_rz1 | 177 | 140/37/0 | -14.52% |
| and_resource_nmcts | external_revkit_oracle_synth | score_rz2 | 177 | 177/0/0 | -53.48% |
| and_resource_nmcts | external_revkit_oracle_synth | score_rz4 | 177 | 177/0/0 | -74.94% |
| and_resource_nmcts | external_revkit_oracle_synth | score_rz10 | 177 | 177/0/0 | -88.57% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | T | 177 | 2/171/4 | +3714.88% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | phase_ops | 177 | 162/6/9 | -27.44% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | CNOT | 177 | 11/165/1 | +41.12% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | depth | 177 | 141/31/5 | -14.78% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -60.97% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +202.82% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | score | 177 | 6/171/0 | +711.60% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | score_rz1 | 177 | 157/20/0 | -17.89% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | score_rz2 | 177 | 177/0/0 | -55.24% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | score_rz4 | 177 | 177/0/0 | -75.84% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | score_rz10 | 177 | 177/0/0 | -88.94% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | T | 177 | 0/171/6 | +3928.63% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | phase_ops | 177 | 144/21/12 | -20.13% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | CNOT | 177 | 9/167/1 | +51.67% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | depth | 177 | 118/52/7 | -8.76% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -59.68% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | peak_ancilla | 177 | 0/172/5 | +210.73% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | score | 177 | 4/173/0 | +774.83% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | score_rz1 | 177 | 136/41/0 | -9.76% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | score_rz2 | 177 | 174/3/0 | -50.44% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | score_rz4 | 177 | 175/2/0 | -72.93% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | score_rz10 | 177 | 175/2/0 | -87.25% |
| and_cube_beam | external_revkit_oracle_synth | T | 177 | 0/177/0 | +6539.17% |
| and_cube_beam | external_revkit_oracle_synth | phase_ops | 177 | 57/119/1 | +600.08% |
| and_cube_beam | external_revkit_oracle_synth | CNOT | 177 | 4/173/0 | +168.77% |
| and_cube_beam | external_revkit_oracle_synth | depth | 177 | 43/132/2 | +104.64% |
| and_cube_beam | external_revkit_oracle_synth | gates | 177 | 171/6/0 | -12.70% |
| and_cube_beam | external_revkit_oracle_synth | peak_ancilla | 177 | 0/176/1 | +255.37% |
| and_cube_beam | external_revkit_oracle_synth | score | 177 | 0/177/0 | +1831.60% |
| and_cube_beam | external_revkit_oracle_synth | score_rz1 | 177 | 38/139/0 | +678.45% |
| and_cube_beam | external_revkit_oracle_synth | score_rz2 | 177 | 155/22/0 | +618.78% |
| and_cube_beam | external_revkit_oracle_synth | score_rz4 | 177 | 170/7/0 | +585.84% |
| and_cube_beam | external_revkit_oracle_synth | score_rz10 | 177 | 171/6/0 | +564.89% |
| and_esop_milp | external_revkit_oracle_synth | T | 177 | 0/173/4 | +7887.57% |
| and_esop_milp | external_revkit_oracle_synth | phase_ops | 177 | 85/81/11 | +24.73% |
| and_esop_milp | external_revkit_oracle_synth | CNOT | 177 | 10/167/0 | +90.57% |
| and_esop_milp | external_revkit_oracle_synth | depth | 177 | 79/95/3 | +26.32% |
| and_esop_milp | external_revkit_oracle_synth | gates | 177 | 154/23/0 | -44.48% |
| and_esop_milp | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +232.20% |
| and_esop_milp | external_revkit_oracle_synth | score | 177 | 4/173/0 | +1266.26% |
| and_esop_milp | external_revkit_oracle_synth | score_rz1 | 177 | 78/99/0 | +33.95% |
| and_esop_milp | external_revkit_oracle_synth | score_rz2 | 177 | 142/35/0 | -27.33% |
| and_esop_milp | external_revkit_oracle_synth | score_rz4 | 177 | 175/2/0 | -60.93% |
| and_esop_milp | external_revkit_oracle_synth | score_rz10 | 177 | 175/2/0 | -82.21% |
| sshr_h | external_revkit_oracle_synth | T | 177 | 2/175/0 | +7575.33% |
| sshr_h | external_revkit_oracle_synth | phase_ops | 177 | 10/154/13 | +156.43% |
| sshr_h | external_revkit_oracle_synth | CNOT | 177 | 34/141/2 | +34.23% |
| sshr_h | external_revkit_oracle_synth | depth | 177 | 128/46/3 | +1.30% |
| sshr_h | external_revkit_oracle_synth | gates | 177 | 174/3/0 | -59.36% |
| sshr_h | external_revkit_oracle_synth | peak_ancilla | 177 | 0/173/4 | +135.59% |
| sshr_h | external_revkit_oracle_synth | score | 177 | 2/175/0 | +1458.91% |
| sshr_h | external_revkit_oracle_synth | score_rz1 | 177 | 10/167/0 | +168.29% |
| sshr_h | external_revkit_oracle_synth | score_rz2 | 177 | 162/15/0 | +103.86% |
| sshr_h | external_revkit_oracle_synth | score_rz4 | 177 | 173/4/0 | +68.50% |
| sshr_h | external_revkit_oracle_synth | score_rz10 | 177 | 173/4/0 | +46.08% |
| direct_anf | external_revkit_oracle_synth | T | 177 | 0/173/4 | +17281.17% |
| direct_anf | external_revkit_oracle_synth | phase_ops | 177 | 2/171/4 | +201.80% |
| direct_anf | external_revkit_oracle_synth | CNOT | 177 | 7/170/0 | +129.42% |
| direct_anf | external_revkit_oracle_synth | depth | 177 | 37/137/3 | +29.40% |
| direct_anf | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -84.97% |
| direct_anf | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +132.77% |
| direct_anf | external_revkit_oracle_synth | score | 177 | 4/173/0 | +2940.07% |
| direct_anf | external_revkit_oracle_synth | score_rz1 | 177 | 6/171/0 | +193.64% |
| direct_anf | external_revkit_oracle_synth | score_rz2 | 177 | 25/152/0 | +57.48% |
| direct_anf | external_revkit_oracle_synth | score_rz4 | 177 | 128/49/0 | -17.12% |
| direct_anf | external_revkit_oracle_synth | score_rz10 | 177 | 175/2/0 | -64.34% |

## Boundary

- Correctness is delegated to RevKit `oracle_synth` accepting the exact truth table.
- RevKit `oracle_synth` returns Rz-phase netlists that often contain rotations outside Clifford+T, such as pi/8 or pi/16 multiples.
- The reported `score` is therefore a lower-bound netlist proxy when `rz_non_clifford > 0`; it must not be described as an exact Clifford+T T-count.
- The rotation-aware scores are not hardware mapping results; they are sensitivity checks for non-Clifford phase cost.
- These results should be presented as an external RevKit API / phase-rotation boundary, not as a claim about hardware mapping.
