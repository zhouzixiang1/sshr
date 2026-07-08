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

## Pairwise Comparisons

| target | baseline | metric | items | W/L/T | mean relative |
|---|---|---|---:|---:|---:|
| and_resource_nmcts | external_revkit_oracle_synth | T | 177 | 2/171/4 | +4060.08% |
| and_resource_nmcts | external_revkit_oracle_synth | CNOT | 177 | 11/166/0 | +48.17% |
| and_resource_nmcts | external_revkit_oracle_synth | depth | 177 | 122/52/3 | -11.24% |
| and_resource_nmcts | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -59.83% |
| and_resource_nmcts | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +192.09% |
| and_resource_nmcts | external_revkit_oracle_synth | score | 177 | 6/171/0 | +751.69% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | T | 177 | 2/171/4 | +3714.88% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | CNOT | 177 | 11/165/1 | +41.12% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | depth | 177 | 141/31/5 | -14.78% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -60.97% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +202.82% |
| and_pareto_resource_nmcts | external_revkit_oracle_synth | score | 177 | 6/171/0 | +711.60% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | T | 177 | 0/171/6 | +3928.63% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | CNOT | 177 | 9/167/1 | +51.67% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | depth | 177 | 118/52/7 | -8.76% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -59.68% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | peak_ancilla | 177 | 0/172/5 | +210.73% |
| and_fprm_polarity_archive | external_revkit_oracle_synth | score | 177 | 4/173/0 | +774.83% |
| and_cube_beam | external_revkit_oracle_synth | T | 177 | 0/177/0 | +6539.17% |
| and_cube_beam | external_revkit_oracle_synth | CNOT | 177 | 4/173/0 | +168.77% |
| and_cube_beam | external_revkit_oracle_synth | depth | 177 | 43/132/2 | +104.64% |
| and_cube_beam | external_revkit_oracle_synth | gates | 177 | 171/6/0 | -12.70% |
| and_cube_beam | external_revkit_oracle_synth | peak_ancilla | 177 | 0/176/1 | +255.37% |
| and_cube_beam | external_revkit_oracle_synth | score | 177 | 0/177/0 | +1831.60% |
| and_esop_milp | external_revkit_oracle_synth | T | 177 | 0/173/4 | +7887.57% |
| and_esop_milp | external_revkit_oracle_synth | CNOT | 177 | 10/167/0 | +90.57% |
| and_esop_milp | external_revkit_oracle_synth | depth | 177 | 79/95/3 | +26.32% |
| and_esop_milp | external_revkit_oracle_synth | gates | 177 | 154/23/0 | -44.48% |
| and_esop_milp | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +232.20% |
| and_esop_milp | external_revkit_oracle_synth | score | 177 | 4/173/0 | +1266.26% |
| sshr_h | external_revkit_oracle_synth | T | 177 | 2/175/0 | +7575.33% |
| sshr_h | external_revkit_oracle_synth | CNOT | 177 | 34/141/2 | +34.23% |
| sshr_h | external_revkit_oracle_synth | depth | 177 | 128/46/3 | +1.30% |
| sshr_h | external_revkit_oracle_synth | gates | 177 | 174/3/0 | -59.36% |
| sshr_h | external_revkit_oracle_synth | peak_ancilla | 177 | 0/173/4 | +135.59% |
| sshr_h | external_revkit_oracle_synth | score | 177 | 2/175/0 | +1458.91% |
| direct_anf | external_revkit_oracle_synth | T | 177 | 0/173/4 | +17281.17% |
| direct_anf | external_revkit_oracle_synth | CNOT | 177 | 7/170/0 | +129.42% |
| direct_anf | external_revkit_oracle_synth | depth | 177 | 37/137/3 | +29.40% |
| direct_anf | external_revkit_oracle_synth | gates | 177 | 177/0/0 | -84.97% |
| direct_anf | external_revkit_oracle_synth | peak_ancilla | 177 | 0/170/7 | +132.77% |
| direct_anf | external_revkit_oracle_synth | score | 177 | 4/173/0 | +2940.07% |

## Boundary

- Correctness is delegated to RevKit `oracle_synth` accepting the exact truth table.
- RevKit `oracle_synth` returns Rz-phase netlists that often contain rotations outside Clifford+T, such as pi/8 or pi/16 multiples.
- The reported `score` is therefore a lower-bound netlist proxy when `rz_non_clifford > 0`; it must not be described as an exact Clifford+T T-count.
- These results should be presented as an external RevKit API / phase-rotation boundary, not as a claim about hardware mapping.
