# Phase-Parity Affine-FPRM Search

This run searches fixed-polarity phase-parity forms after a bounded set
of invertible linear input transforms.  The selected phase polynomial is
translated back to original input parity masks, so the transform is an
algebraic phase-polynomial rewrite rather than a hardware mapping step.

- rows: 531
- usable rows: 531
- verified up to global phase: 531/531
- rank metrics: score, score_rz1, score_synth_tperrz30
- transform budget per function: 32

## phase_parity_affine_fprm_opt_rz1

- rows: 177
- nonidentity transform selections: 81/177
- nonzero polarity selections: 40/177
- mean candidate affine forms: 1031.2
- mean lower-bound score: 8.66
- mean CNOT: 84.14
- mean depth: 110.06
- mean total Rz: 25.92
- mean non-Clifford Rz: 21.60
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 85/0/92 | -8.72% |
| phase_parity_anf | score_rz1 | 177 | 85/0/92 | -5.00% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 81/4/92 | -2.34% |
| phase_parity_anf | rz_non_clifford | 177 | 11/4/162 | -0.35% |
| phase_parity_anf | rz_total | 177 | 83/0/94 | -7.63% |
| phase_parity_anf | CNOT | 177 | 56/11/110 | -3.67% |
| phase_parity_anf | depth | 177 | 74/8/95 | -5.06% |
| phase_parity_fprm_opt_rz1 | score | 177 | 79/2/96 | -5.76% |
| phase_parity_fprm_opt_rz1 | score_rz1 | 177 | 81/0/96 | -3.46% |
| phase_parity_fprm_opt_rz1 | score_synth_tperrz30 | 177 | 76/5/96 | -2.02% |
| phase_parity_fprm_opt_rz1 | rz_non_clifford | 177 | 10/5/162 | -0.20% |
| phase_parity_fprm_opt_rz1 | rz_total | 177 | 70/3/104 | -5.78% |
| phase_parity_fprm_opt_rz1 | CNOT | 177 | 55/13/109 | -3.59% |
| phase_parity_fprm_opt_rz1 | depth | 177 | 66/13/98 | -4.34% |
| external_revkit_oracle_synth | score | 177 | 40/136/1 | +47.18% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -50.82% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -65.25% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.49% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -49.68% |
| external_revkit_oracle_synth | CNOT | 177 | 37/133/7 | +28.52% |
| external_revkit_oracle_synth | depth | 177 | 98/78/1 | -3.64% |

## phase_parity_affine_fprm_opt_score

- rows: 177
- nonidentity transform selections: 80/177
- nonzero polarity selections: 40/177
- mean candidate affine forms: 1031.2
- mean lower-bound score: 8.58
- mean CNOT: 84.37
- mean depth: 110.45
- mean total Rz: 26.07
- mean non-Clifford Rz: 21.88
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 85/0/92 | -9.13% |
| phase_parity_anf | score_rz1 | 177 | 85/0/92 | -4.66% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 74/11/92 | -1.58% |
| phase_parity_anf | rz_non_clifford | 177 | 2/11/164 | +0.44% |
| phase_parity_anf | rz_total | 177 | 82/0/95 | -7.11% |
| phase_parity_anf | CNOT | 177 | 55/13/109 | -3.43% |
| phase_parity_anf | depth | 177 | 72/10/95 | -4.74% |
| phase_parity_fprm_opt_score | score | 177 | 80/0/97 | -5.77% |
| phase_parity_fprm_opt_score | score_rz1 | 177 | 80/0/97 | -3.34% |
| phase_parity_fprm_opt_score | score_synth_tperrz30 | 177 | 75/5/97 | -1.91% |
| phase_parity_fprm_opt_score | rz_non_clifford | 177 | 7/5/165 | -0.09% |
| phase_parity_fprm_opt_score | rz_total | 177 | 70/1/106 | -5.36% |
| phase_parity_fprm_opt_score | CNOT | 177 | 53/13/111 | -3.40% |
| phase_parity_fprm_opt_score | depth | 177 | 65/13/99 | -4.09% |
| external_revkit_oracle_synth | score | 177 | 40/136/1 | +46.18% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -50.62% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -64.93% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.16% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -49.39% |
| external_revkit_oracle_synth | CNOT | 177 | 37/133/7 | +28.91% |
| external_revkit_oracle_synth | depth | 177 | 96/80/1 | -3.25% |

## phase_parity_affine_fprm_opt_tperrz30

- rows: 177
- nonidentity transform selections: 81/177
- nonzero polarity selections: 43/177
- mean candidate affine forms: 1031.2
- mean lower-bound score: 8.92
- mean CNOT: 85.32
- mean depth: 111.46
- mean total Rz: 26.14
- mean non-Clifford Rz: 21.45
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 82/3/92 | -7.10% |
| phase_parity_anf | score_rz1 | 177 | 84/1/92 | -4.75% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 85/0/92 | -2.98% |
| phase_parity_anf | rz_non_clifford | 177 | 24/0/153 | -1.04% |
| phase_parity_anf | rz_total | 177 | 82/1/94 | -7.06% |
| phase_parity_anf | CNOT | 177 | 53/14/110 | -2.63% |
| phase_parity_anf | depth | 177 | 71/11/95 | -4.14% |
| phase_parity_fprm_opt_tperrz30 | score | 177 | 69/12/96 | -4.31% |
| phase_parity_fprm_opt_tperrz30 | score_rz1 | 177 | 80/1/96 | -3.23% |
| phase_parity_fprm_opt_tperrz30 | score_synth_tperrz30 | 177 | 81/0/96 | -2.51% |
| phase_parity_fprm_opt_tperrz30 | rz_non_clifford | 177 | 20/0/157 | -0.73% |
| phase_parity_fprm_opt_tperrz30 | rz_total | 177 | 66/6/105 | -5.20% |
| phase_parity_fprm_opt_tperrz30 | CNOT | 177 | 51/16/110 | -2.55% |
| phase_parity_fprm_opt_tperrz30 | depth | 177 | 64/17/96 | -3.42% |
| external_revkit_oracle_synth | score | 177 | 40/136/1 | +51.43% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -50.68% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -65.50% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.75% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -49.32% |
| external_revkit_oracle_synth | CNOT | 177 | 37/133/7 | +30.25% |
| external_revkit_oracle_synth | depth | 177 | 96/81/0 | -2.44% |

## Interpretation

- The identity transform is included, so affine-FPRM is score-nondegrading relative to fixed-polarity FPRM under the same rank metric.
- Nonidentity transform selections indicate that linear preconditioning changes parity-gadget cancellation, not only tie-breaking.
- This remains a logic-layer phase-oracle emitter; it does not output approximate rotation sequences or perform hardware mapping.
