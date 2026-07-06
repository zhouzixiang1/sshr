# Highdim_Scale_Resource Analysis

Rows: 256; usable: 256; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 32 | -38.36% | -49.96% | +0.00% |
| and_fprm_greedy | 32 | -51.90% | -69.80% | +0.00% |
| and_fprm_linear_pair | 32 | -55.20% | -70.74% | +0.00% |
| and_fprm_linear_pair_deep | 32 | -55.21% | -70.82% | +0.00% |
| and_fprm_root_beam | 32 | -52.06% | -69.84% | +0.00% |
| and_profile_resource_nmcts | 32 | -55.21% | -70.82% | +0.00% |
| and_resource_nmcts | 32 | -55.21% | -70.82% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 30 | 0 | 2 | -55.21% |
| and_resource_nmcts | direct_anf | CNOT | 5 | 27 | 0 | +7.63% |
| and_resource_nmcts | direct_anf | depth | 5 | 27 | 0 | +9.72% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 29 | 3 | +131.25% |
| and_resource_nmcts | direct_anf | score | 30 | 2 | 0 | -52.01% |
| and_resource_nmcts | and_direct_anf | T | 30 | 0 | 2 | -30.59% |
| and_resource_nmcts | and_direct_anf | CNOT | 29 | 0 | 3 | -23.57% |
| and_resource_nmcts | and_direct_anf | depth | 29 | 1 | 2 | -21.79% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_resource_nmcts | and_direct_anf | score | 30 | 0 | 2 | -29.00% |
| and_resource_nmcts | and_fprm_greedy | T | 30 | 0 | 2 | -4.63% |
| and_resource_nmcts | and_fprm_greedy | CNOT | 29 | 0 | 3 | -3.21% |
| and_resource_nmcts | and_fprm_greedy | depth | 29 | 1 | 2 | -1.43% |
| and_resource_nmcts | and_fprm_greedy | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_resource_nmcts | and_fprm_greedy | score | 30 | 0 | 2 | -3.55% |
| and_resource_nmcts | and_fprm_root_beam | T | 29 | 0 | 3 | -4.16% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 28 | 0 | 4 | -2.96% |
| and_resource_nmcts | and_fprm_root_beam | depth | 28 | 1 | 3 | -1.17% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_resource_nmcts | and_fprm_root_beam | score | 29 | 0 | 3 | -3.09% |
| and_profile_resource_nmcts | direct_anf | T | 30 | 0 | 2 | -55.21% |
| and_profile_resource_nmcts | direct_anf | CNOT | 5 | 27 | 0 | +7.63% |
| and_profile_resource_nmcts | direct_anf | depth | 5 | 27 | 0 | +9.72% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 29 | 3 | +131.25% |
| and_profile_resource_nmcts | direct_anf | score | 30 | 2 | 0 | -52.01% |
| and_profile_resource_nmcts | and_direct_anf | T | 30 | 0 | 2 | -30.59% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 29 | 0 | 3 | -23.57% |
| and_profile_resource_nmcts | and_direct_anf | depth | 29 | 1 | 2 | -21.79% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_profile_resource_nmcts | and_direct_anf | score | 30 | 0 | 2 | -29.00% |
| and_profile_resource_nmcts | and_fprm_greedy | T | 30 | 0 | 2 | -4.63% |
| and_profile_resource_nmcts | and_fprm_greedy | CNOT | 29 | 0 | 3 | -3.21% |
| and_profile_resource_nmcts | and_fprm_greedy | depth | 29 | 1 | 2 | -1.43% |
| and_profile_resource_nmcts | and_fprm_greedy | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_profile_resource_nmcts | and_fprm_greedy | score | 30 | 0 | 2 | -3.55% |
| and_profile_resource_nmcts | and_fprm_root_beam | T | 29 | 0 | 3 | -4.16% |
| and_profile_resource_nmcts | and_fprm_root_beam | CNOT | 28 | 0 | 4 | -2.96% |
| and_profile_resource_nmcts | and_fprm_root_beam | depth | 28 | 1 | 3 | -1.17% |
| and_profile_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_profile_resource_nmcts | and_fprm_root_beam | score | 29 | 0 | 3 | -3.09% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 32 | +0.00% |
| and_fprm_linear_pair | and_fprm_root_beam | T | 29 | 0 | 3 | -4.12% |
| and_fprm_linear_pair | and_fprm_root_beam | CNOT | 28 | 0 | 4 | -2.93% |
| and_fprm_linear_pair | and_fprm_root_beam | depth | 28 | 1 | 3 | -1.14% |
| and_fprm_linear_pair | and_fprm_root_beam | peak_ancilla | 0 | 29 | 3 | +51.82% |
| and_fprm_linear_pair | and_fprm_root_beam | score | 29 | 0 | 3 | -3.06% |
| and_fprm_linear_pair | and_fprm_greedy | T | 30 | 0 | 2 | -4.60% |
| and_fprm_linear_pair | and_fprm_greedy | CNOT | 29 | 0 | 3 | -3.18% |
| and_fprm_linear_pair | and_fprm_greedy | depth | 29 | 1 | 2 | -1.39% |
| and_fprm_linear_pair | and_fprm_greedy | peak_ancilla | 0 | 29 | 3 | +51.82% |
| and_fprm_linear_pair | and_fprm_greedy | score | 30 | 0 | 2 | -3.52% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | T | 7 | 0 | 25 | -0.04% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | CNOT | 7 | 1 | 24 | -0.03% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | depth | 7 | 1 | 24 | -0.03% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | peak_ancilla | 0 | 5 | 27 | +3.28% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | score | 9 | 0 | 23 | -0.03% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | T | 29 | 0 | 3 | -4.16% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | CNOT | 28 | 0 | 4 | -2.96% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | depth | 28 | 1 | 3 | -1.17% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | score | 29 | 0 | 3 | -3.09% |
| and_fprm_linear_pair_deep | and_fprm_greedy | T | 30 | 0 | 2 | -4.63% |
| and_fprm_linear_pair_deep | and_fprm_greedy | CNOT | 29 | 0 | 3 | -3.21% |
| and_fprm_linear_pair_deep | and_fprm_greedy | depth | 29 | 1 | 2 | -1.43% |
| and_fprm_linear_pair_deep | and_fprm_greedy | peak_ancilla | 0 | 29 | 3 | +55.99% |
| and_fprm_linear_pair_deep | and_fprm_greedy | score | 30 | 0 | 2 | -3.55% |
| and_resource_nmcts | and_fprm_linear_pair | T | 7 | 0 | 25 | -0.04% |
| and_resource_nmcts | and_fprm_linear_pair | CNOT | 7 | 1 | 24 | -0.03% |
| and_resource_nmcts | and_fprm_linear_pair | depth | 7 | 1 | 24 | -0.03% |
| and_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 0 | 5 | 27 | +3.28% |
| and_resource_nmcts | and_fprm_linear_pair | score | 9 | 0 | 23 | -0.03% |
| and_resource_nmcts | and_fprm_linear_pair_deep | T | 0 | 0 | 32 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair_deep | CNOT | 0 | 0 | 32 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair_deep | depth | 0 | 0 | 32 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair_deep | peak_ancilla | 0 | 0 | 32 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair_deep | score | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair | T | 7 | 0 | 25 | -0.04% |
| and_profile_resource_nmcts | and_fprm_linear_pair | CNOT | 7 | 1 | 24 | -0.03% |
| and_profile_resource_nmcts | and_fprm_linear_pair | depth | 7 | 1 | 24 | -0.03% |
| and_profile_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 0 | 5 | 27 | +3.28% |
| and_profile_resource_nmcts | and_fprm_linear_pair | score | 9 | 0 | 23 | -0.03% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | T | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | CNOT | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | depth | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | peak_ancilla | 0 | 0 | 32 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | score | 0 | 0 | 32 | +0.00% |
| and_fprm_root_beam | and_fprm_greedy | T | 23 | 0 | 9 | -0.48% |
| and_fprm_root_beam | and_fprm_greedy | CNOT | 16 | 7 | 9 | -0.26% |
| and_fprm_root_beam | and_fprm_greedy | depth | 16 | 7 | 9 | -0.26% |
| and_fprm_root_beam | and_fprm_greedy | peak_ancilla | 0 | 0 | 32 | +0.00% |
| and_fprm_root_beam | and_fprm_greedy | score | 23 | 0 | 9 | -0.46% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n15_14 | 15 | 51040 | 14892 | -70.82% |
| anf_n15_31 | 15 | 45016 | 13232 | -70.61% |
| anf_n15_25 | 15 | 47292 | 13984 | -70.43% |
| anf_n15_16 | 15 | 19744 | 5868 | -70.28% |
| anf_n15_18 | 15 | 33708 | 10060 | -70.16% |
| anf_n15_10 | 15 | 37180 | 11120 | -70.09% |
| anf_n15_11 | 15 | 15016 | 4608 | -69.31% |
| anf_n15_23 | 15 | 12436 | 3872 | -68.86% |
| anf_n15_22 | 15 | 12520 | 3948 | -68.47% |
| anf_n15_26 | 15 | 10484 | 3316 | -68.37% |
| anf_n15_27 | 15 | 11172 | 3560 | -68.13% |
| anf_n15_30 | 15 | 8400 | 2716 | -67.67% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n15_14 | 15 | 51040 | 14892 | -70.82% |
| anf_n15_31 | 15 | 45016 | 13232 | -70.61% |
| anf_n15_25 | 15 | 47292 | 13984 | -70.43% |
| anf_n15_16 | 15 | 19744 | 5868 | -70.28% |
| anf_n15_18 | 15 | 33708 | 10060 | -70.16% |
| anf_n15_10 | 15 | 37180 | 11120 | -70.09% |
| anf_n15_11 | 15 | 15016 | 4608 | -69.31% |
| anf_n15_23 | 15 | 12436 | 3872 | -68.86% |
| anf_n15_22 | 15 | 12520 | 3948 | -68.47% |
| anf_n15_26 | 15 | 10484 | 3316 | -68.37% |
| anf_n15_27 | 15 | 11172 | 3560 | -68.13% |
| anf_n15_30 | 15 | 8400 | 2716 | -67.67% |

## Largest and-fprm-greedy gains vs direct ANF

| function | n | direct T | and_fprm_greedy T | relative |
|---|---:|---:|---:|---:|
| anf_n15_14 | 15 | 51040 | 15412 | -69.80% |
| anf_n15_31 | 15 | 45016 | 13644 | -69.69% |
| anf_n15_25 | 15 | 47292 | 14384 | -69.58% |
| anf_n15_10 | 15 | 37180 | 11388 | -69.37% |
| anf_n15_18 | 15 | 33708 | 10356 | -69.28% |
| anf_n15_16 | 15 | 19744 | 6076 | -69.23% |
| anf_n15_11 | 15 | 15016 | 4740 | -68.43% |
| anf_n15_23 | 15 | 12436 | 3928 | -68.41% |
| anf_n15_22 | 15 | 12520 | 4008 | -67.99% |
| anf_n15_27 | 15 | 11172 | 3588 | -67.88% |
| anf_n15_26 | 15 | 10484 | 3372 | -67.84% |
| anf_n15_30 | 15 | 8400 | 2776 | -66.95% |

## Largest and-fprm-root-beam gains vs direct ANF

| function | n | direct T | and_fprm_root_beam T | relative |
|---|---:|---:|---:|---:|
| anf_n15_14 | 15 | 51040 | 15396 | -69.84% |
| anf_n15_31 | 15 | 45016 | 13640 | -69.70% |
| anf_n15_25 | 15 | 47292 | 14340 | -69.68% |
| anf_n15_10 | 15 | 37180 | 11352 | -69.47% |
| anf_n15_18 | 15 | 33708 | 10312 | -69.41% |
| anf_n15_16 | 15 | 19744 | 6048 | -69.37% |
| anf_n15_11 | 15 | 15016 | 4696 | -68.73% |
| anf_n15_23 | 15 | 12436 | 3920 | -68.48% |
| anf_n15_22 | 15 | 12520 | 3980 | -68.21% |
| anf_n15_26 | 15 | 10484 | 3344 | -68.10% |
| anf_n15_27 | 15 | 11172 | 3580 | -67.96% |
| anf_n15_30 | 15 | 8400 | 2744 | -67.33% |

## Largest and-fprm-linear-pair gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair T | relative |
|---|---:|---:|---:|---:|
| anf_n15_14 | 15 | 51040 | 14932 | -70.74% |
| anf_n15_31 | 15 | 45016 | 13260 | -70.54% |
| anf_n15_25 | 15 | 47292 | 14008 | -70.38% |
| anf_n15_16 | 15 | 19744 | 5880 | -70.22% |
| anf_n15_18 | 15 | 33708 | 10076 | -70.11% |
| anf_n15_10 | 15 | 37180 | 11124 | -70.08% |
| anf_n15_11 | 15 | 15016 | 4612 | -69.29% |
| anf_n15_23 | 15 | 12436 | 3872 | -68.86% |
| anf_n15_22 | 15 | 12520 | 3948 | -68.47% |
| anf_n15_26 | 15 | 10484 | 3316 | -68.37% |
| anf_n15_27 | 15 | 11172 | 3560 | -68.13% |
| anf_n15_30 | 15 | 8400 | 2716 | -67.67% |

## Largest and-fprm-linear-pair-deep gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair_deep T | relative |
|---|---:|---:|---:|---:|
| anf_n15_14 | 15 | 51040 | 14892 | -70.82% |
| anf_n15_31 | 15 | 45016 | 13232 | -70.61% |
| anf_n15_25 | 15 | 47292 | 13984 | -70.43% |
| anf_n15_16 | 15 | 19744 | 5868 | -70.28% |
| anf_n15_18 | 15 | 33708 | 10060 | -70.16% |
| anf_n15_10 | 15 | 37180 | 11120 | -70.09% |
| anf_n15_11 | 15 | 15016 | 4608 | -69.31% |
| anf_n15_23 | 15 | 12436 | 3872 | -68.86% |
| anf_n15_22 | 15 | 12520 | 3948 | -68.47% |
| anf_n15_26 | 15 | 10484 | 3316 | -68.37% |
| anf_n15_27 | 15 | 11172 | 3560 | -68.13% |
| anf_n15_30 | 15 | 8400 | 2716 | -67.67% |
