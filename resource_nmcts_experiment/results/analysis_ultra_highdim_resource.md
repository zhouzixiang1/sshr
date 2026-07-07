# Ultra_Highdim_Resource Analysis

Rows: 240; usable: 240; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 24 | -45.29% | -49.95% | +0.00% |
| and_fprm_linear_pair | 24 | -62.08% | -69.83% | +0.00% |
| and_fprm_linear_pair_deep | 24 | -63.34% | -70.31% | +0.00% |
| and_fprm_linear_pair_deep_ai_guard | 24 | -63.36% | -70.33% | +0.00% |
| and_fprm_linear_pair_deep_root_neural | 24 | -63.32% | -70.33% | +0.00% |
| and_fprm_root_beam | 24 | -60.92% | -69.33% | +0.00% |
| and_pareto_resource_nmcts | 24 | -63.34% | -70.31% | +0.00% |
| and_profile_resource_nmcts | 24 | -63.36% | -70.33% | +0.00% |
| and_resource_nmcts | 24 | -63.36% | -70.33% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 23 | 0 | 1 | -63.36% |
| and_resource_nmcts | direct_anf | CNOT | 5 | 19 | 0 | +7.92% |
| and_resource_nmcts | direct_anf | depth | 5 | 19 | 0 | +7.92% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 23 | 1 | +145.83% |
| and_resource_nmcts | direct_anf | score | 23 | 1 | 0 | -60.83% |
| and_resource_nmcts | and_direct_anf | T | 23 | 0 | 1 | -34.50% |
| and_resource_nmcts | and_direct_anf | CNOT | 23 | 0 | 1 | -27.49% |
| and_resource_nmcts | and_direct_anf | depth | 23 | 0 | 1 | -27.49% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 23 | 1 | +56.25% |
| and_resource_nmcts | and_direct_anf | score | 23 | 0 | 1 | -33.56% |
| and_resource_nmcts | and_fprm_root_beam | T | 23 | 0 | 1 | -4.70% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 23 | 0 | 1 | -4.42% |
| and_resource_nmcts | and_fprm_root_beam | depth | 23 | 0 | 1 | -4.42% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 23 | 1 | +56.25% |
| and_resource_nmcts | and_fprm_root_beam | score | 23 | 0 | 1 | -4.36% |
| and_profile_resource_nmcts | direct_anf | T | 23 | 0 | 1 | -63.36% |
| and_profile_resource_nmcts | direct_anf | CNOT | 5 | 19 | 0 | +7.92% |
| and_profile_resource_nmcts | direct_anf | depth | 5 | 19 | 0 | +7.92% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 23 | 1 | +145.83% |
| and_profile_resource_nmcts | direct_anf | score | 23 | 1 | 0 | -60.83% |
| and_profile_resource_nmcts | and_direct_anf | T | 23 | 0 | 1 | -34.50% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 23 | 0 | 1 | -27.49% |
| and_profile_resource_nmcts | and_direct_anf | depth | 23 | 0 | 1 | -27.49% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 23 | 1 | +56.25% |
| and_profile_resource_nmcts | and_direct_anf | score | 23 | 0 | 1 | -33.56% |
| and_profile_resource_nmcts | and_fprm_root_beam | T | 23 | 0 | 1 | -4.70% |
| and_profile_resource_nmcts | and_fprm_root_beam | CNOT | 23 | 0 | 1 | -4.42% |
| and_profile_resource_nmcts | and_fprm_root_beam | depth | 23 | 0 | 1 | -4.42% |
| and_profile_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 23 | 1 | +56.25% |
| and_profile_resource_nmcts | and_fprm_root_beam | score | 23 | 0 | 1 | -4.36% |
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
| and_fprm_linear_pair_deep | and_fprm_linear_pair | T | 23 | 0 | 1 | -2.62% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | CNOT | 22 | 1 | 1 | -2.42% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | depth | 22 | 1 | 1 | -2.42% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | peak_ancilla | 0 | 4 | 20 | +5.90% |
| and_fprm_linear_pair_deep | and_fprm_linear_pair | score | 23 | 0 | 1 | -2.54% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | T | 23 | 0 | 1 | -4.64% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | CNOT | 23 | 0 | 1 | -4.42% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | depth | 23 | 0 | 1 | -4.42% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | peak_ancilla | 0 | 23 | 1 | +54.86% |
| and_fprm_linear_pair_deep | and_fprm_root_beam | score | 23 | 0 | 1 | -4.31% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair_deep | T | 6 | 6 | 12 | +0.07% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair_deep | CNOT | 3 | 9 | 12 | +0.12% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair_deep | depth | 3 | 9 | 12 | +0.12% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair_deep | peak_ancilla | 1 | 2 | 21 | +1.25% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair_deep | score | 6 | 7 | 11 | +0.08% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair | T | 23 | 0 | 1 | -2.55% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair | CNOT | 23 | 0 | 1 | -2.30% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair | depth | 23 | 0 | 1 | -2.30% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair | peak_ancilla | 0 | 5 | 19 | +6.94% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_linear_pair | score | 23 | 0 | 1 | -2.47% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_root_beam | T | 23 | 0 | 1 | -4.58% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_root_beam | CNOT | 23 | 0 | 1 | -4.31% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_root_beam | depth | 23 | 0 | 1 | -4.31% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_root_beam | peak_ancilla | 0 | 23 | 1 | +56.25% |
| and_fprm_linear_pair_deep_root_neural | and_fprm_root_beam | score | 23 | 0 | 1 | -4.24% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep | T | 6 | 0 | 18 | -0.06% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep | CNOT | 3 | 3 | 18 | +0.01% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep | depth | 3 | 3 | 18 | +0.01% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep | peak_ancilla | 0 | 1 | 23 | +1.04% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep | score | 6 | 0 | 18 | -0.05% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep_root_neural | T | 6 | 0 | 18 | -0.13% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep_root_neural | CNOT | 6 | 0 | 18 | -0.11% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep_root_neural | depth | 6 | 0 | 18 | -0.11% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep_root_neural | peak_ancilla | 1 | 1 | 22 | +0.21% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair_deep_root_neural | score | 7 | 0 | 17 | -0.13% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair | T | 23 | 0 | 1 | -2.68% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair | CNOT | 23 | 0 | 1 | -2.41% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair | depth | 23 | 0 | 1 | -2.41% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair | peak_ancilla | 0 | 5 | 19 | +6.94% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_linear_pair | score | 23 | 0 | 1 | -2.59% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_root_beam | T | 23 | 0 | 1 | -4.70% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_root_beam | CNOT | 23 | 0 | 1 | -4.42% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_root_beam | depth | 23 | 0 | 1 | -4.42% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_root_beam | peak_ancilla | 0 | 23 | 1 | +56.25% |
| and_fprm_linear_pair_deep_ai_guard | and_fprm_root_beam | score | 23 | 0 | 1 | -4.36% |
| and_resource_nmcts | and_fprm_linear_pair | T | 23 | 0 | 1 | -2.68% |
| and_resource_nmcts | and_fprm_linear_pair | CNOT | 23 | 0 | 1 | -2.41% |
| and_resource_nmcts | and_fprm_linear_pair | depth | 23 | 0 | 1 | -2.41% |
| and_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 0 | 5 | 19 | +6.94% |
| and_resource_nmcts | and_fprm_linear_pair | score | 23 | 0 | 1 | -2.59% |
| and_resource_nmcts | and_fprm_linear_pair_deep | T | 6 | 0 | 18 | -0.06% |
| and_resource_nmcts | and_fprm_linear_pair_deep | CNOT | 3 | 3 | 18 | +0.01% |
| and_resource_nmcts | and_fprm_linear_pair_deep | depth | 3 | 3 | 18 | +0.01% |
| and_resource_nmcts | and_fprm_linear_pair_deep | peak_ancilla | 0 | 1 | 23 | +1.04% |
| and_resource_nmcts | and_fprm_linear_pair_deep | score | 6 | 0 | 18 | -0.05% |
| and_profile_resource_nmcts | and_fprm_linear_pair | T | 23 | 0 | 1 | -2.68% |
| and_profile_resource_nmcts | and_fprm_linear_pair | CNOT | 23 | 0 | 1 | -2.41% |
| and_profile_resource_nmcts | and_fprm_linear_pair | depth | 23 | 0 | 1 | -2.41% |
| and_profile_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 0 | 5 | 19 | +6.94% |
| and_profile_resource_nmcts | and_fprm_linear_pair | score | 23 | 0 | 1 | -2.59% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | T | 6 | 0 | 18 | -0.06% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | CNOT | 3 | 3 | 18 | +0.01% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | depth | 3 | 3 | 18 | +0.01% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | peak_ancilla | 0 | 1 | 23 | +1.04% |
| and_profile_resource_nmcts | and_fprm_linear_pair_deep | score | 6 | 0 | 18 | -0.05% |
| and_pareto_resource_nmcts | direct_anf | T | 23 | 0 | 1 | -63.34% |
| and_pareto_resource_nmcts | direct_anf | CNOT | 5 | 19 | 0 | +7.91% |
| and_pareto_resource_nmcts | direct_anf | depth | 5 | 19 | 0 | +7.91% |
| and_pareto_resource_nmcts | direct_anf | peak_ancilla | 0 | 23 | 1 | +143.75% |
| and_pareto_resource_nmcts | direct_anf | score | 23 | 1 | 0 | -60.81% |
| and_pareto_resource_nmcts | and_direct_anf | T | 23 | 0 | 1 | -34.46% |
| and_pareto_resource_nmcts | and_direct_anf | CNOT | 23 | 0 | 1 | -27.49% |
| and_pareto_resource_nmcts | and_direct_anf | depth | 23 | 0 | 1 | -27.49% |
| and_pareto_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 23 | 1 | +54.86% |
| and_pareto_resource_nmcts | and_direct_anf | score | 23 | 0 | 1 | -33.53% |
| and_pareto_resource_nmcts | and_resource_nmcts | T | 1 | 5 | 18 | +0.06% |
| and_pareto_resource_nmcts | and_resource_nmcts | CNOT | 3 | 3 | 18 | -0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | depth | 3 | 3 | 18 | -0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | peak_ancilla | 1 | 0 | 23 | -0.83% |
| and_pareto_resource_nmcts | and_resource_nmcts | score | 1 | 5 | 18 | +0.05% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | T | 1 | 5 | 18 | +0.06% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | CNOT | 3 | 3 | 18 | -0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | depth | 3 | 3 | 18 | -0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | peak_ancilla | 1 | 0 | 23 | -0.83% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | score | 1 | 5 | 18 | +0.05% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | T | 23 | 0 | 1 | -2.62% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | CNOT | 22 | 1 | 1 | -2.41% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | depth | 22 | 1 | 1 | -2.41% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 0 | 4 | 20 | +5.90% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | score | 23 | 0 | 1 | -2.54% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_deep | T | 1 | 0 | 23 | -0.00% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_deep | CNOT | 0 | 1 | 23 | +0.01% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_deep | depth | 0 | 1 | 23 | +0.01% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_deep | peak_ancilla | 0 | 0 | 24 | +0.00% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_deep | score | 1 | 0 | 23 | -0.00% |
| and_pareto_resource_nmcts | and_fprm_root_beam | T | 23 | 0 | 1 | -4.65% |
| and_pareto_resource_nmcts | and_fprm_root_beam | CNOT | 23 | 0 | 1 | -4.42% |
| and_pareto_resource_nmcts | and_fprm_root_beam | depth | 23 | 0 | 1 | -4.42% |
| and_pareto_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 23 | 1 | +54.86% |
| and_pareto_resource_nmcts | and_fprm_root_beam | score | 23 | 0 | 1 | -4.31% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6656 | -70.33% |
| anf_n16_18 | 16 | 20988 | 6268 | -70.14% |
| anf_n16_9 | 16 | 17544 | 5260 | -70.02% |
| anf_n16_20 | 16 | 20828 | 6256 | -69.96% |
| anf_n16_2 | 16 | 18564 | 5592 | -69.88% |
| anf_n16_19 | 16 | 45620 | 13780 | -69.79% |
| anf_n16_5 | 16 | 25300 | 7716 | -69.50% |
| anf_n16_7 | 16 | 16464 | 5024 | -69.48% |
| anf_n16_15 | 16 | 34032 | 10416 | -69.39% |
| anf_n16_12 | 16 | 8240 | 2584 | -68.64% |
| anf_n16_17 | 16 | 18796 | 5896 | -68.63% |
| anf_n16_22 | 16 | 7856 | 2476 | -68.48% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6656 | -70.33% |
| anf_n16_18 | 16 | 20988 | 6268 | -70.14% |
| anf_n16_9 | 16 | 17544 | 5260 | -70.02% |
| anf_n16_20 | 16 | 20828 | 6256 | -69.96% |
| anf_n16_2 | 16 | 18564 | 5592 | -69.88% |
| anf_n16_19 | 16 | 45620 | 13780 | -69.79% |
| anf_n16_5 | 16 | 25300 | 7716 | -69.50% |
| anf_n16_7 | 16 | 16464 | 5024 | -69.48% |
| anf_n16_15 | 16 | 34032 | 10416 | -69.39% |
| anf_n16_12 | 16 | 8240 | 2584 | -68.64% |
| anf_n16_17 | 16 | 18796 | 5896 | -68.63% |
| anf_n16_22 | 16 | 7856 | 2476 | -68.48% |

## Largest and-pareto-resource-nmcts gains vs direct ANF

| function | n | direct T | and_pareto_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6660 | -70.31% |
| anf_n16_18 | 16 | 20988 | 6268 | -70.14% |
| anf_n16_9 | 16 | 17544 | 5260 | -70.02% |
| anf_n16_20 | 16 | 20828 | 6256 | -69.96% |
| anf_n16_2 | 16 | 18564 | 5592 | -69.88% |
| anf_n16_19 | 16 | 45620 | 13772 | -69.81% |
| anf_n16_5 | 16 | 25300 | 7716 | -69.50% |
| anf_n16_7 | 16 | 16464 | 5024 | -69.48% |
| anf_n16_15 | 16 | 34032 | 10416 | -69.39% |
| anf_n16_12 | 16 | 8240 | 2584 | -68.64% |
| anf_n16_17 | 16 | 18796 | 5896 | -68.63% |
| anf_n16_22 | 16 | 7856 | 2476 | -68.48% |

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

## Largest and-fprm-linear-pair-deep gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair_deep T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6660 | -70.31% |
| anf_n16_18 | 16 | 20988 | 6268 | -70.14% |
| anf_n16_9 | 16 | 17544 | 5260 | -70.02% |
| anf_n16_20 | 16 | 20828 | 6256 | -69.96% |
| anf_n16_2 | 16 | 18564 | 5592 | -69.88% |
| anf_n16_19 | 16 | 45620 | 13784 | -69.79% |
| anf_n16_5 | 16 | 25300 | 7716 | -69.50% |
| anf_n16_7 | 16 | 16464 | 5024 | -69.48% |
| anf_n16_15 | 16 | 34032 | 10416 | -69.39% |
| anf_n16_12 | 16 | 8240 | 2584 | -68.64% |
| anf_n16_17 | 16 | 18796 | 5896 | -68.63% |
| anf_n16_22 | 16 | 7856 | 2476 | -68.48% |

## Largest and-fprm-linear-pair-deep-root-neural gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair_deep_root_neural T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6656 | -70.33% |
| anf_n16_18 | 16 | 20988 | 6312 | -69.93% |
| anf_n16_9 | 16 | 17544 | 5284 | -69.88% |
| anf_n16_2 | 16 | 18564 | 5592 | -69.88% |
| anf_n16_20 | 16 | 20828 | 6288 | -69.81% |
| anf_n16_19 | 16 | 45620 | 13780 | -69.79% |
| anf_n16_5 | 16 | 25300 | 7716 | -69.50% |
| anf_n16_15 | 16 | 34032 | 10416 | -69.39% |
| anf_n16_7 | 16 | 16464 | 5052 | -69.31% |
| anf_n16_12 | 16 | 8240 | 2584 | -68.64% |
| anf_n16_17 | 16 | 18796 | 5912 | -68.55% |
| anf_n16_22 | 16 | 7856 | 2476 | -68.48% |

## Largest and-fprm-linear-pair-deep-ai-guard gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair_deep_ai_guard T | relative |
|---|---:|---:|---:|---:|
| anf_n16_21 | 16 | 22432 | 6656 | -70.33% |
| anf_n16_18 | 16 | 20988 | 6268 | -70.14% |
| anf_n16_9 | 16 | 17544 | 5260 | -70.02% |
| anf_n16_20 | 16 | 20828 | 6256 | -69.96% |
| anf_n16_2 | 16 | 18564 | 5592 | -69.88% |
| anf_n16_19 | 16 | 45620 | 13780 | -69.79% |
| anf_n16_5 | 16 | 25300 | 7716 | -69.50% |
| anf_n16_7 | 16 | 16464 | 5024 | -69.48% |
| anf_n16_15 | 16 | 34032 | 10416 | -69.39% |
| anf_n16_12 | 16 | 8240 | 2584 | -68.64% |
| anf_n16_17 | 16 | 18796 | 5896 | -68.63% |
| anf_n16_22 | 16 | 7856 | 2476 | -68.48% |
