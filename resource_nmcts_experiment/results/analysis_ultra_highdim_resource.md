# Ultra_Highdim_Resource Analysis

Rows: 144; usable: 144; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 24 | -45.29% | -49.95% | +0.00% |
| and_fprm_linear_pair | 24 | -62.08% | -69.83% | +0.00% |
| and_fprm_root_beam | 24 | -60.92% | -69.33% | +0.00% |
| and_profile_resource_nmcts | 24 | -62.08% | -69.83% | +0.00% |
| and_resource_nmcts | 24 | -62.08% | -69.83% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 23 | 0 | 1 | -62.08% |
| and_resource_nmcts | direct_anf | CNOT | 4 | 20 | 0 | +10.43% |
| and_resource_nmcts | direct_anf | depth | 4 | 20 | 0 | +10.43% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 23 | 1 | +129.17% |
| and_resource_nmcts | direct_anf | score | 23 | 1 | 0 | -59.52% |
| and_resource_nmcts | and_direct_anf | T | 23 | 0 | 1 | -32.60% |
| and_resource_nmcts | and_direct_anf | CNOT | 23 | 0 | 1 | -25.63% |
| and_resource_nmcts | and_direct_anf | depth | 23 | 0 | 1 | -25.63% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 22 | 2 | +47.22% |
| and_resource_nmcts | and_direct_anf | score | 23 | 0 | 1 | -31.68% |
| and_resource_nmcts | and_fprm_root_beam | T | 22 | 0 | 2 | -2.18% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 22 | 0 | 2 | -2.10% |
| and_resource_nmcts | and_fprm_root_beam | depth | 22 | 0 | 2 | -2.10% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 22 | 2 | +47.22% |
| and_resource_nmcts | and_fprm_root_beam | score | 22 | 0 | 2 | -1.88% |
| and_profile_resource_nmcts | direct_anf | T | 23 | 0 | 1 | -62.08% |
| and_profile_resource_nmcts | direct_anf | CNOT | 4 | 20 | 0 | +10.43% |
| and_profile_resource_nmcts | direct_anf | depth | 4 | 20 | 0 | +10.43% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 23 | 1 | +129.17% |
| and_profile_resource_nmcts | direct_anf | score | 23 | 1 | 0 | -59.52% |
| and_profile_resource_nmcts | and_direct_anf | T | 23 | 0 | 1 | -32.60% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 23 | 0 | 1 | -25.63% |
| and_profile_resource_nmcts | and_direct_anf | depth | 23 | 0 | 1 | -25.63% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 22 | 2 | +47.22% |
| and_profile_resource_nmcts | and_direct_anf | score | 23 | 0 | 1 | -31.68% |
| and_profile_resource_nmcts | and_fprm_root_beam | T | 22 | 0 | 2 | -2.18% |
| and_profile_resource_nmcts | and_fprm_root_beam | CNOT | 22 | 0 | 2 | -2.10% |
| and_profile_resource_nmcts | and_fprm_root_beam | depth | 22 | 0 | 2 | -2.10% |
| and_profile_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 22 | 2 | +47.22% |
| and_profile_resource_nmcts | and_fprm_root_beam | score | 22 | 0 | 2 | -1.88% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 24 | +0.00% |
| and_fprm_linear_pair | and_fprm_root_beam | T | 22 | 0 | 2 | -2.18% |
| and_fprm_linear_pair | and_fprm_root_beam | CNOT | 22 | 0 | 2 | -2.10% |
| and_fprm_linear_pair | and_fprm_root_beam | depth | 22 | 0 | 2 | -2.10% |
| and_fprm_linear_pair | and_fprm_root_beam | peak_ancilla | 0 | 22 | 2 | +47.22% |
| and_fprm_linear_pair | and_fprm_root_beam | score | 22 | 0 | 2 | -1.88% |
| and_resource_nmcts | and_fprm_linear_pair | T | 0 | 0 | 24 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair | CNOT | 0 | 0 | 24 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair | depth | 0 | 0 | 24 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 0 | 0 | 24 | +0.00% |
| and_resource_nmcts | and_fprm_linear_pair | score | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair | T | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair | CNOT | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair | depth | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 0 | 0 | 24 | +0.00% |
| and_profile_resource_nmcts | and_fprm_linear_pair | score | 0 | 0 | 24 | +0.00% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6768 | -69.83% |
| anf_n16_19 | 16 | 45620 | 13796 | -69.76% |
| anf_n16_18 | 16 | 20988 | 6420 | -69.41% |
| anf_n16_15 | 16 | 34032 | 10428 | -69.36% |
| anf_n16_20 | 16 | 20828 | 6384 | -69.35% |
| anf_n16_2 | 16 | 18564 | 5692 | -69.34% |
| anf_n16_9 | 16 | 17544 | 5400 | -69.22% |
| anf_n16_5 | 16 | 25300 | 7864 | -68.92% |
| anf_n16_7 | 16 | 16464 | 5136 | -68.80% |
| anf_n16_17 | 16 | 18796 | 5956 | -68.31% |
| anf_n16_22 | 16 | 7856 | 2568 | -67.31% |
| anf_n16_12 | 16 | 8240 | 2700 | -67.23% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6768 | -69.83% |
| anf_n16_19 | 16 | 45620 | 13796 | -69.76% |
| anf_n16_18 | 16 | 20988 | 6420 | -69.41% |
| anf_n16_15 | 16 | 34032 | 10428 | -69.36% |
| anf_n16_20 | 16 | 20828 | 6384 | -69.35% |
| anf_n16_2 | 16 | 18564 | 5692 | -69.34% |
| anf_n16_9 | 16 | 17544 | 5400 | -69.22% |
| anf_n16_5 | 16 | 25300 | 7864 | -68.92% |
| anf_n16_7 | 16 | 16464 | 5136 | -68.80% |
| anf_n16_17 | 16 | 18796 | 5956 | -68.31% |
| anf_n16_22 | 16 | 7856 | 2568 | -67.31% |
| anf_n16_12 | 16 | 8240 | 2700 | -67.23% |

## Largest and-fprm-root-beam gains vs direct ANF

| function | n | direct T | and_fprm_root_beam T | relative |
|---|---:|---:|---:|---:|
| anf_n16_19 | 16 | 45620 | 13992 | -69.33% |
| anf_n16_21 | 16 | 22432 | 6884 | -69.31% |
| anf_n16_18 | 16 | 20988 | 6516 | -68.95% |
| anf_n16_15 | 16 | 34032 | 10588 | -68.89% |
| anf_n16_20 | 16 | 20828 | 6508 | -68.75% |
| anf_n16_2 | 16 | 18564 | 5820 | -68.65% |
| anf_n16_9 | 16 | 17544 | 5512 | -68.58% |
| anf_n16_5 | 16 | 25300 | 7960 | -68.54% |
| anf_n16_7 | 16 | 16464 | 5204 | -68.39% |
| anf_n16_17 | 16 | 18796 | 6020 | -67.97% |
| anf_n16_1 | 16 | 9064 | 3016 | -66.73% |
| anf_n16_12 | 16 | 8240 | 2776 | -66.31% |

## Largest and-fprm-linear-pair gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6768 | -69.83% |
| anf_n16_19 | 16 | 45620 | 13796 | -69.76% |
| anf_n16_18 | 16 | 20988 | 6420 | -69.41% |
| anf_n16_15 | 16 | 34032 | 10428 | -69.36% |
| anf_n16_20 | 16 | 20828 | 6384 | -69.35% |
| anf_n16_2 | 16 | 18564 | 5692 | -69.34% |
| anf_n16_9 | 16 | 17544 | 5400 | -69.22% |
| anf_n16_5 | 16 | 25300 | 7864 | -68.92% |
| anf_n16_7 | 16 | 16464 | 5136 | -68.80% |
| anf_n16_17 | 16 | 18796 | 5956 | -68.31% |
| anf_n16_22 | 16 | 7856 | 2568 | -67.31% |
| anf_n16_12 | 16 | 8240 | 2700 | -67.23% |
