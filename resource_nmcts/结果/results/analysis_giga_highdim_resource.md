# Giga_Highdim_Resource Analysis

Rows: 48; usable: 36; errors: 12; skipped: 0.

## Timeout / error rows

| function | n | method | error |
|---|---:|---|---|
| anf_n20_0 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_1 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_2 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_3 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_4 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_5 | 20 | and_fprm_root_beam | TaskTimeout('synthesis task timed out') |
| anf_n20_0 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_1 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_2 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_3 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_4 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |
| anf_n20_5 | 20 | and_fprm_linear_pair_fast | TaskTimeout('synthesis task timed out') |

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_boolean_linear_pair_screen | 6 | -36.80% | -52.13% | +0.00% |
| and_direct_anf | 6 | -32.93% | -49.98% | +0.00% |
| and_pareto_resource_nmcts | 6 | -36.80% | -52.13% | +0.00% |
| and_profile_resource_nmcts | 6 | -36.80% | -52.13% | +0.00% |
| and_resource_nmcts | 6 | -36.80% | -52.13% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 5 | 0 | 1 | -36.80% |
| and_resource_nmcts | direct_anf | CNOT | 1 | 5 | 0 | +33.82% |
| and_resource_nmcts | direct_anf | depth | 1 | 5 | 0 | +33.82% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 5 | 1 | +108.33% |
| and_resource_nmcts | direct_anf | score | 5 | 1 | 0 | -34.00% |
| and_resource_nmcts | and_direct_anf | T | 5 | 0 | 1 | -5.24% |
| and_resource_nmcts | and_direct_anf | CNOT | 5 | 0 | 1 | -4.82% |
| and_resource_nmcts | and_direct_anf | depth | 5 | 0 | 1 | -4.82% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 5 | 1 | +51.39% |
| and_resource_nmcts | and_direct_anf | score | 5 | 0 | 1 | -4.89% |
| and_resource_nmcts | and_boolean_linear_pair_screen | T | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_boolean_linear_pair_screen | CNOT | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_boolean_linear_pair_screen | depth | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_boolean_linear_pair_screen | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_boolean_linear_pair_screen | score | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | direct_anf | T | 5 | 0 | 1 | -36.80% |
| and_profile_resource_nmcts | direct_anf | CNOT | 1 | 5 | 0 | +33.82% |
| and_profile_resource_nmcts | direct_anf | depth | 1 | 5 | 0 | +33.82% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 5 | 1 | +108.33% |
| and_profile_resource_nmcts | direct_anf | score | 5 | 1 | 0 | -34.00% |
| and_profile_resource_nmcts | and_direct_anf | T | 5 | 0 | 1 | -5.24% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 5 | 0 | 1 | -4.82% |
| and_profile_resource_nmcts | and_direct_anf | depth | 5 | 0 | 1 | -4.82% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 5 | 1 | +51.39% |
| and_profile_resource_nmcts | and_direct_anf | score | 5 | 0 | 1 | -4.89% |
| and_profile_resource_nmcts | and_boolean_linear_pair_screen | T | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_boolean_linear_pair_screen | CNOT | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_boolean_linear_pair_screen | depth | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_boolean_linear_pair_screen | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_boolean_linear_pair_screen | score | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 6 | +0.00% |
| and_boolean_linear_pair_screen | and_direct_anf | T | 5 | 0 | 1 | -5.24% |
| and_boolean_linear_pair_screen | and_direct_anf | CNOT | 5 | 0 | 1 | -4.82% |
| and_boolean_linear_pair_screen | and_direct_anf | depth | 5 | 0 | 1 | -4.82% |
| and_boolean_linear_pair_screen | and_direct_anf | peak_ancilla | 0 | 5 | 1 | +51.39% |
| and_boolean_linear_pair_screen | and_direct_anf | score | 5 | 0 | 1 | -4.89% |
| and_pareto_resource_nmcts | direct_anf | T | 5 | 0 | 1 | -36.80% |
| and_pareto_resource_nmcts | direct_anf | CNOT | 1 | 5 | 0 | +33.82% |
| and_pareto_resource_nmcts | direct_anf | depth | 1 | 5 | 0 | +33.82% |
| and_pareto_resource_nmcts | direct_anf | peak_ancilla | 0 | 5 | 1 | +108.33% |
| and_pareto_resource_nmcts | direct_anf | score | 5 | 1 | 0 | -34.00% |
| and_pareto_resource_nmcts | and_direct_anf | T | 5 | 0 | 1 | -5.24% |
| and_pareto_resource_nmcts | and_direct_anf | CNOT | 5 | 0 | 1 | -4.82% |
| and_pareto_resource_nmcts | and_direct_anf | depth | 5 | 0 | 1 | -4.82% |
| and_pareto_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 5 | 1 | +51.39% |
| and_pareto_resource_nmcts | and_direct_anf | score | 5 | 0 | 1 | -4.89% |
| and_pareto_resource_nmcts | and_boolean_linear_pair_screen | T | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_boolean_linear_pair_screen | CNOT | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_boolean_linear_pair_screen | depth | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_boolean_linear_pair_screen | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_boolean_linear_pair_screen | score | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | T | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | CNOT | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | depth | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | score | 0 | 0 | 6 | +0.00% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n20_4 | 20 | 86012 | 41176 | -52.13% |
| anf_n20_2 | 20 | 14932 | 7208 | -51.73% |
| anf_n20_1 | 20 | 153504 | 74676 | -51.35% |
| anf_n20_3 | 20 | 3040 | 1496 | -50.79% |
| anf_n20_0 | 20 | 108 | 92 | -14.81% |
| anf_n20_5 | 20 | 68 | 68 | +0.00% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n20_4 | 20 | 86012 | 41176 | -52.13% |
| anf_n20_2 | 20 | 14932 | 7208 | -51.73% |
| anf_n20_1 | 20 | 153504 | 74676 | -51.35% |
| anf_n20_3 | 20 | 3040 | 1496 | -50.79% |
| anf_n20_0 | 20 | 108 | 92 | -14.81% |
| anf_n20_5 | 20 | 68 | 68 | +0.00% |

## Largest and-pareto-resource-nmcts gains vs direct ANF

| function | n | direct T | and_pareto_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n20_4 | 20 | 86012 | 41176 | -52.13% |
| anf_n20_2 | 20 | 14932 | 7208 | -51.73% |
| anf_n20_1 | 20 | 153504 | 74676 | -51.35% |
| anf_n20_3 | 20 | 3040 | 1496 | -50.79% |
| anf_n20_0 | 20 | 108 | 92 | -14.81% |
| anf_n20_5 | 20 | 68 | 68 | +0.00% |

## Largest and-boolean-linear-pair-screen gains vs direct ANF

| function | n | direct T | and_boolean_linear_pair_screen T | relative |
|---|---:|---:|---:|---:|
| anf_n20_4 | 20 | 86012 | 41176 | -52.13% |
| anf_n20_2 | 20 | 14932 | 7208 | -51.73% |
| anf_n20_1 | 20 | 153504 | 74676 | -51.35% |
| anf_n20_3 | 20 | 3040 | 1496 | -50.79% |
| anf_n20_0 | 20 | 108 | 92 | -14.81% |
| anf_n20_5 | 20 | 68 | 68 | +0.00% |
