# Phase-Parity Affine-FPRM Search

This run searches fixed-polarity phase-parity forms after a bounded set
of invertible linear input transforms.  The selected phase polynomial is
translated back to original input parity masks, so the transform is an
algebraic phase-polynomial rewrite rather than a hardware mapping step.

- rows: 531
- usable rows: 531
- verified up to global phase: 531/531
- rank metrics: score, score_rz1, score_synth_tperrz30
- transform budget per function: 128

## phase_parity_affine_fprm_opt_rz1

- rows: 177
- nonidentity transform selections: 82/177
- nonzero polarity selections: 35/177
- mean candidate affine forms: 4124.9
- mean lower-bound score: 8.47
- mean CNOT: 82.53
- mean depth: 107.88
- mean total Rz: 25.34
- mean non-Clifford Rz: 21.45
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 85/0/92 | -9.58% |
| phase_parity_anf | score_rz1 | 177 | 85/0/92 | -5.80% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 84/1/92 | -3.13% |
| phase_parity_anf | rz_non_clifford | 177 | 16/1/160 | -0.88% |
| phase_parity_anf | rz_total | 177 | 85/0/92 | -9.32% |
| phase_parity_anf | CNOT | 177 | 62/10/105 | -5.00% |
| phase_parity_anf | depth | 177 | 76/6/95 | -6.51% |
| phase_parity_fprm_opt_rz1 | score | 177 | 80/2/95 | -6.74% |
| phase_parity_fprm_opt_rz1 | score_rz1 | 177 | 82/0/95 | -4.32% |
| phase_parity_fprm_opt_rz1 | score_synth_tperrz30 | 177 | 80/2/95 | -2.82% |
| phase_parity_fprm_opt_rz1 | rz_non_clifford | 177 | 15/2/160 | -0.73% |
| phase_parity_fprm_opt_rz1 | rz_total | 177 | 79/0/98 | -7.53% |
| phase_parity_fprm_opt_rz1 | CNOT | 177 | 61/10/106 | -4.92% |
| phase_parity_fprm_opt_rz1 | depth | 177 | 73/9/95 | -5.80% |
| external_revkit_oracle_synth | score | 177 | 42/134/1 | +44.42% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -51.25% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -65.44% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.67% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -50.58% |
| external_revkit_oracle_synth | CNOT | 177 | 36/133/8 | +26.47% |
| external_revkit_oracle_synth | depth | 177 | 104/72/1 | -5.24% |

## phase_parity_affine_fprm_opt_score

- rows: 177
- nonidentity transform selections: 81/177
- nonzero polarity selections: 43/177
- mean candidate affine forms: 4124.9
- mean lower-bound score: 8.36
- mean CNOT: 83.19
- mean depth: 108.79
- mean total Rz: 25.60
- mean non-Clifford Rz: 21.81
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 85/0/92 | -10.23% |
| phase_parity_anf | score_rz1 | 177 | 85/0/92 | -5.36% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 74/11/92 | -2.03% |
| phase_parity_anf | rz_non_clifford | 177 | 3/11/163 | +0.26% |
| phase_parity_anf | rz_total | 177 | 85/0/92 | -8.61% |
| phase_parity_anf | CNOT | 177 | 59/11/107 | -4.32% |
| phase_parity_anf | depth | 177 | 76/6/95 | -5.82% |
| phase_parity_fprm_opt_score | score | 177 | 81/0/96 | -7.08% |
| phase_parity_fprm_opt_score | score_rz1 | 177 | 81/0/96 | -4.09% |
| phase_parity_fprm_opt_score | score_synth_tperrz30 | 177 | 75/6/96 | -2.37% |
| phase_parity_fprm_opt_score | rz_non_clifford | 177 | 7/6/164 | -0.26% |
| phase_parity_fprm_opt_score | rz_total | 177 | 77/0/100 | -6.90% |
| phase_parity_fprm_opt_score | CNOT | 177 | 58/11/108 | -4.29% |
| phase_parity_fprm_opt_score | depth | 177 | 71/9/97 | -5.18% |
| external_revkit_oracle_synth | score | 177 | 42/134/1 | +42.73% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -50.98% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -64.99% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.21% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -50.17% |
| external_revkit_oracle_synth | CNOT | 177 | 36/133/8 | +27.53% |
| external_revkit_oracle_synth | depth | 177 | 99/75/3 | -4.41% |

## phase_parity_affine_fprm_opt_tperrz30

- rows: 177
- nonidentity transform selections: 82/177
- nonzero polarity selections: 30/177
- mean candidate affine forms: 4124.9
- mean lower-bound score: 8.62
- mean CNOT: 83.23
- mean depth: 108.62
- mean total Rz: 25.39
- mean non-Clifford Rz: 21.36
- max angle denominator: 32

| baseline | metric | items | W/L/T | mean relative |
|---|---|---:|---:|---:|
| phase_parity_anf | score | 177 | 84/1/92 | -8.69% |
| phase_parity_anf | score_rz1 | 177 | 85/0/92 | -5.67% |
| phase_parity_anf | score_synth_tperrz30 | 177 | 85/0/92 | -3.56% |
| phase_parity_anf | rz_non_clifford | 177 | 27/0/150 | -1.33% |
| phase_parity_anf | rz_total | 177 | 85/0/92 | -9.28% |
| phase_parity_anf | CNOT | 177 | 61/11/105 | -4.40% |
| phase_parity_anf | depth | 177 | 75/7/95 | -6.05% |
| phase_parity_fprm_opt_tperrz30 | score | 177 | 75/7/95 | -5.98% |
| phase_parity_fprm_opt_tperrz30 | score_rz1 | 177 | 81/1/95 | -4.20% |
| phase_parity_fprm_opt_tperrz30 | score_synth_tperrz30 | 177 | 82/0/95 | -3.10% |
| phase_parity_fprm_opt_tperrz30 | rz_non_clifford | 177 | 23/0/154 | -1.03% |
| phase_parity_fprm_opt_tperrz30 | rz_total | 177 | 80/0/97 | -7.50% |
| phase_parity_fprm_opt_tperrz30 | CNOT | 177 | 60/11/106 | -4.31% |
| phase_parity_fprm_opt_tperrz30 | depth | 177 | 72/10/95 | -5.34% |
| external_revkit_oracle_synth | score | 177 | 40/136/1 | +46.73% |
| external_revkit_oracle_synth | score_rz1 | 177 | 177/0/0 | -51.16% |
| external_revkit_oracle_synth | score_synth_tperrz30 | 177 | 177/0/0 | -65.60% |
| external_revkit_oracle_synth | rz_non_clifford | 177 | 171/0/6 | -63.83% |
| external_revkit_oracle_synth | rz_total | 177 | 173/3/1 | -50.55% |
| external_revkit_oracle_synth | CNOT | 177 | 36/133/8 | +27.57% |
| external_revkit_oracle_synth | depth | 177 | 102/75/0 | -4.57% |

## Interpretation

- The identity transform is included, so affine-FPRM is score-nondegrading relative to fixed-polarity FPRM under the same rank metric.
- Nonidentity transform selections indicate that linear preconditioning changes parity-gadget cancellation, not only tie-breaking.
- This remains a logic-layer phase-oracle emitter; it does not output approximate rotation sequences or perform hardware mapping.
