# Phase-Parity FPRM Polarity Search

This run exhaustively searches fixed-polarity Reed-Muller forms for
each benchmark function and translates shifted parity phases back to
the original variables.  Verification is exact up to global phase.

- rows: 531
- usable rows: 531
- verified up to global phase: 531/531
- rank metrics: score, score_rz1, score_synth_tperrz30

## phase_parity_fprm_opt_rz1

- rows: 177
- nonzero polarity selections: 59/177
- mean polarity weight: 0.58
- mean lower-bound score: 9.47
- mean CNOT: 87.21
- mean depth: 114.40
- mean total Rz: 27.19
- mean non-Clifford Rz: 21.68
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 57/2/118 | -3.44% |
| phase_parity_anf | score_rz1 | 177 | 59/0/118 | -1.65% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 58/1/118 | -0.31% |
| phase_parity_anf | rz_non_clifford | 177 | 3/1/173 | -0.14% |
| phase_parity_anf | rz_total | 177 | 46/2/129 | -2.00% |
| phase_parity_anf | CNOT | 177 | 10/0/167 | -0.09% |
| phase_parity_anf | depth | 177 | 46/2/129 | -0.79% |
| external_revkit_oracle_synth | score | 177 | 40/137/0 | +59.67% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -49.14% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -65.09% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.40% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -46.29% |
| external_revkit_oracle_synth | CNOT | 177 | 34/140/3 | +34.17% |
| external_revkit_oracle_synth | depth | 177 | 79/96/2 | +1.63% |

## phase_parity_fprm_opt_score

- rows: 177
- nonzero polarity selections: 59/177
- mean polarity weight: 0.55
- mean lower-bound score: 9.34
- mean CNOT: 87.36
- mean depth: 114.62
- mean total Rz: 27.26
- mean non-Clifford Rz: 21.99
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 59/0/118 | -3.98% |
| phase_parity_anf | score_rz1 | 177 | 56/2/119 | -1.39% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 51/8/118 | +0.37% |
| phase_parity_anf | rz_non_clifford | 177 | 0/8/169 | +0.56% |
| phase_parity_anf | rz_total | 177 | 43/3/131 | -1.88% |
| phase_parity_anf | CNOT | 177 | 5/1/171 | -0.03% |
| phase_parity_anf | depth | 177 | 43/3/131 | -0.71% |
| external_revkit_oracle_synth | score | 177 | 40/137/0 | +58.24% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -48.98% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -64.78% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.09% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -46.22% |
| external_revkit_oracle_synth | CNOT | 177 | 34/140/3 | +34.30% |
| external_revkit_oracle_synth | depth | 177 | 79/96/2 | +1.74% |

## phase_parity_fprm_opt_tperrz30

- rows: 177
- nonzero polarity selections: 59/177
- mean polarity weight: 0.57
- mean lower-bound score: 9.57
- mean CNOT: 87.22
- mean depth: 114.42
- mean total Rz: 27.20
- mean non-Clifford Rz: 21.60
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 56/3/118 | -3.08% |
| phase_parity_anf | score_rz1 | 177 | 59/0/118 | -1.63% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 59/0/118 | -0.47% |
| phase_parity_anf | rz_non_clifford | 177 | 4/0/173 | -0.31% |
| phase_parity_anf | rz_total | 177 | 46/2/129 | -1.99% |
| phase_parity_anf | CNOT | 177 | 11/0/166 | -0.09% |
| phase_parity_anf | depth | 177 | 47/2/128 | -0.78% |
| external_revkit_oracle_synth | score | 177 | 40/137/0 | +60.70% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -49.12% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -65.16% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.48% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -46.28% |
| external_revkit_oracle_synth | CNOT | 177 | 34/140/3 | +34.18% |
| external_revkit_oracle_synth | depth | 177 | 79/96/2 | +1.64% |

## Interpretation

- Fixed-polarity search changes the phase polynomial itself, not only the reported cost model.
- The selected polarity is rank-metric dependent, so lower-bound and synthesized-Rz objectives should be reported separately.
- This remains a logic-layer phase-oracle emitter; it does not yet output approximate rotation sequences or perform hardware mapping.
