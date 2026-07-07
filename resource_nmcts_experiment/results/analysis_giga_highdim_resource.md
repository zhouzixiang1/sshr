# Giga_Highdim_Resource Analysis

Rows: 42; usable: 30; errors: 12; skipped: 0.

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
| and_direct_anf | 6 | -32.93% | -49.98% | +0.00% |
| and_pareto_resource_nmcts | 6 | -32.93% | -49.98% | +0.00% |
| and_profile_resource_nmcts | 6 | -32.93% | -49.98% | +0.00% |
| and_resource_nmcts | 6 | -32.93% | -49.98% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 4 | 0 | 2 | -32.93% |
| and_resource_nmcts | direct_anf | CNOT | 1 | 5 | 0 | +40.24% |
| and_resource_nmcts | direct_anf | depth | 1 | 5 | 0 | +40.24% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 3 | 3 | +41.67% |
| and_resource_nmcts | direct_anf | score | 4 | 2 | 0 | -30.34% |
| and_resource_nmcts | and_direct_anf | T | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_direct_anf | CNOT | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_direct_anf | depth | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_resource_nmcts | and_direct_anf | score | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | direct_anf | T | 4 | 0 | 2 | -32.93% |
| and_profile_resource_nmcts | direct_anf | CNOT | 1 | 5 | 0 | +40.24% |
| and_profile_resource_nmcts | direct_anf | depth | 1 | 5 | 0 | +40.24% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 3 | 3 | +41.67% |
| and_profile_resource_nmcts | direct_anf | score | 4 | 2 | 0 | -30.34% |
| and_profile_resource_nmcts | and_direct_anf | T | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_direct_anf | depth | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_direct_anf | score | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | direct_anf | T | 4 | 0 | 2 | -32.93% |
| and_pareto_resource_nmcts | direct_anf | CNOT | 1 | 5 | 0 | +40.24% |
| and_pareto_resource_nmcts | direct_anf | depth | 1 | 5 | 0 | +40.24% |
| and_pareto_resource_nmcts | direct_anf | peak_ancilla | 0 | 3 | 3 | +41.67% |
| and_pareto_resource_nmcts | direct_anf | score | 4 | 2 | 0 | -30.34% |
| and_pareto_resource_nmcts | and_direct_anf | T | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_direct_anf | CNOT | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_direct_anf | depth | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 6 | +0.00% |
| and_pareto_resource_nmcts | and_direct_anf | score | 0 | 0 | 6 | +0.00% |
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
| anf_n20_1 | 20 | 153504 | 76784 | -49.98% |
| anf_n20_4 | 20 | 86012 | 43052 | -49.95% |
| anf_n20_2 | 20 | 14932 | 7504 | -49.75% |
| anf_n20_3 | 20 | 3040 | 1584 | -47.89% |
| anf_n20_0 | 20 | 108 | 108 | +0.00% |
| anf_n20_5 | 20 | 68 | 68 | +0.00% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n20_1 | 20 | 153504 | 76784 | -49.98% |
| anf_n20_4 | 20 | 86012 | 43052 | -49.95% |
| anf_n20_2 | 20 | 14932 | 7504 | -49.75% |
| anf_n20_3 | 20 | 3040 | 1584 | -47.89% |
| anf_n20_0 | 20 | 108 | 108 | +0.00% |
| anf_n20_5 | 20 | 68 | 68 | +0.00% |

## Largest and-pareto-resource-nmcts gains vs direct ANF

| function | n | direct T | and_pareto_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n20_1 | 20 | 153504 | 76784 | -49.98% |
| anf_n20_4 | 20 | 86012 | 43052 | -49.95% |
| anf_n20_2 | 20 | 14932 | 7504 | -49.75% |
| anf_n20_3 | 20 | 3040 | 1584 | -47.89% |
| anf_n20_0 | 20 | 108 | 108 | +0.00% |
| anf_n20_5 | 20 | 68 | 68 | +0.00% |
