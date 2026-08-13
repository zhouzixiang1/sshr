# Mega_Highdim_Resource Analysis

Rows: 84; usable: 84; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 12 | -41.34% | -49.98% | +0.00% |
| and_fprm_linear_pair_fast | 12 | -57.75% | -69.22% | -9.09% |
| and_fprm_root_beam | 12 | -55.40% | -69.22% | +0.00% |
| and_pareto_resource_nmcts | 12 | -60.05% | -69.63% | -18.18% |
| and_profile_resource_nmcts | 12 | -60.05% | -69.63% | -18.18% |
| and_resource_nmcts | 12 | -60.05% | -69.63% | -18.18% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 12 | 0 | 0 | -60.05% |
| and_resource_nmcts | direct_anf | CNOT | 2 | 10 | 0 | +12.08% |
| and_resource_nmcts | direct_anf | depth | 2 | 10 | 0 | +13.82% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 12 | 0 | +150.00% |
| and_resource_nmcts | direct_anf | score | 12 | 0 | 0 | -56.99% |
| and_resource_nmcts | and_direct_anf | T | 12 | 0 | 0 | -33.39% |
| and_resource_nmcts | and_direct_anf | CNOT | 12 | 0 | 0 | -26.23% |
| and_resource_nmcts | and_direct_anf | depth | 11 | 1 | 0 | -24.73% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 12 | 0 | +58.33% |
| and_resource_nmcts | and_direct_anf | score | 12 | 0 | 0 | -32.01% |
| and_resource_nmcts | and_fprm_root_beam | T | 12 | 0 | 0 | -6.19% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 12 | 0 | 0 | -4.32% |
| and_resource_nmcts | and_fprm_root_beam | depth | 11 | 1 | 0 | -2.83% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 12 | 0 | +58.33% |
| and_resource_nmcts | and_fprm_root_beam | score | 12 | 0 | 0 | -5.29% |
| and_profile_resource_nmcts | direct_anf | T | 12 | 0 | 0 | -60.05% |
| and_profile_resource_nmcts | direct_anf | CNOT | 2 | 10 | 0 | +12.08% |
| and_profile_resource_nmcts | direct_anf | depth | 2 | 10 | 0 | +13.82% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 12 | 0 | +150.00% |
| and_profile_resource_nmcts | direct_anf | score | 12 | 0 | 0 | -56.99% |
| and_profile_resource_nmcts | and_direct_anf | T | 12 | 0 | 0 | -33.39% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 12 | 0 | 0 | -26.23% |
| and_profile_resource_nmcts | and_direct_anf | depth | 11 | 1 | 0 | -24.73% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 12 | 0 | +58.33% |
| and_profile_resource_nmcts | and_direct_anf | score | 12 | 0 | 0 | -32.01% |
| and_profile_resource_nmcts | and_fprm_root_beam | T | 12 | 0 | 0 | -6.19% |
| and_profile_resource_nmcts | and_fprm_root_beam | CNOT | 12 | 0 | 0 | -4.32% |
| and_profile_resource_nmcts | and_fprm_root_beam | depth | 11 | 1 | 0 | -2.83% |
| and_profile_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 12 | 0 | +58.33% |
| and_profile_resource_nmcts | and_fprm_root_beam | score | 12 | 0 | 0 | -5.29% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 12 | +0.00% |
| and_fprm_linear_pair_fast | and_fprm_root_beam | T | 6 | 0 | 6 | -2.72% |
| and_fprm_linear_pair_fast | and_fprm_root_beam | CNOT | 5 | 0 | 7 | -1.79% |
| and_fprm_linear_pair_fast | and_fprm_root_beam | depth | 5 | 1 | 6 | +0.14% |
| and_fprm_linear_pair_fast | and_fprm_root_beam | peak_ancilla | 0 | 6 | 6 | +37.50% |
| and_fprm_linear_pair_fast | and_fprm_root_beam | score | 6 | 0 | 6 | -1.91% |
| and_resource_nmcts | and_fprm_linear_pair_fast | T | 12 | 0 | 0 | -3.75% |
| and_resource_nmcts | and_fprm_linear_pair_fast | CNOT | 12 | 0 | 0 | -2.65% |
| and_resource_nmcts | and_fprm_linear_pair_fast | depth | 12 | 0 | 0 | -2.96% |
| and_resource_nmcts | and_fprm_linear_pair_fast | peak_ancilla | 0 | 6 | 6 | +20.83% |
| and_resource_nmcts | and_fprm_linear_pair_fast | score | 12 | 0 | 0 | -3.55% |
| and_profile_resource_nmcts | and_fprm_linear_pair_fast | T | 12 | 0 | 0 | -3.75% |
| and_profile_resource_nmcts | and_fprm_linear_pair_fast | CNOT | 12 | 0 | 0 | -2.65% |
| and_profile_resource_nmcts | and_fprm_linear_pair_fast | depth | 12 | 0 | 0 | -2.96% |
| and_profile_resource_nmcts | and_fprm_linear_pair_fast | peak_ancilla | 0 | 6 | 6 | +20.83% |
| and_profile_resource_nmcts | and_fprm_linear_pair_fast | score | 12 | 0 | 0 | -3.55% |
| and_pareto_resource_nmcts | direct_anf | T | 12 | 0 | 0 | -60.05% |
| and_pareto_resource_nmcts | direct_anf | CNOT | 2 | 10 | 0 | +12.08% |
| and_pareto_resource_nmcts | direct_anf | depth | 2 | 10 | 0 | +13.82% |
| and_pareto_resource_nmcts | direct_anf | peak_ancilla | 0 | 12 | 0 | +150.00% |
| and_pareto_resource_nmcts | direct_anf | score | 12 | 0 | 0 | -56.99% |
| and_pareto_resource_nmcts | and_direct_anf | T | 12 | 0 | 0 | -33.39% |
| and_pareto_resource_nmcts | and_direct_anf | CNOT | 12 | 0 | 0 | -26.23% |
| and_pareto_resource_nmcts | and_direct_anf | depth | 11 | 1 | 0 | -24.73% |
| and_pareto_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 12 | 0 | +58.33% |
| and_pareto_resource_nmcts | and_direct_anf | score | 12 | 0 | 0 | -32.01% |
| and_pareto_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | T | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | CNOT | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | depth | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | score | 0 | 0 | 12 | +0.00% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_fast | T | 12 | 0 | 0 | -3.75% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_fast | CNOT | 12 | 0 | 0 | -2.65% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_fast | depth | 12 | 0 | 0 | -2.96% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_fast | peak_ancilla | 0 | 6 | 6 | +20.83% |
| and_pareto_resource_nmcts | and_fprm_linear_pair_fast | score | 12 | 0 | 0 | -3.55% |
| and_pareto_resource_nmcts | and_fprm_root_beam | T | 12 | 0 | 0 | -6.19% |
| and_pareto_resource_nmcts | and_fprm_root_beam | CNOT | 12 | 0 | 0 | -4.32% |
| and_pareto_resource_nmcts | and_fprm_root_beam | depth | 11 | 1 | 0 | -2.83% |
| and_pareto_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 12 | 0 | +58.33% |
| and_pareto_resource_nmcts | and_fprm_root_beam | score | 12 | 0 | 0 | -5.29% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n18_3 | 18 | 80524 | 24452 | -69.63% |
| anf_n18_2 | 18 | 34904 | 10644 | -69.50% |
| anf_n18_7 | 18 | 57036 | 17560 | -69.21% |
| anf_n18_1 | 18 | 32424 | 10004 | -69.15% |
| anf_n18_5 | 18 | 21488 | 6748 | -68.60% |
| anf_n18_10 | 18 | 12108 | 3840 | -68.29% |
| anf_n18_4 | 18 | 8864 | 2916 | -67.10% |
| anf_n18_11 | 18 | 4540 | 1532 | -66.26% |
| anf_n18_8 | 18 | 4908 | 1676 | -65.85% |
| anf_n18_6 | 18 | 616 | 240 | -61.04% |
| anf_n18_0 | 18 | 72 | 52 | -27.78% |
| anf_n18_9 | 18 | 44 | 36 | -18.18% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n18_3 | 18 | 80524 | 24452 | -69.63% |
| anf_n18_2 | 18 | 34904 | 10644 | -69.50% |
| anf_n18_7 | 18 | 57036 | 17560 | -69.21% |
| anf_n18_1 | 18 | 32424 | 10004 | -69.15% |
| anf_n18_5 | 18 | 21488 | 6748 | -68.60% |
| anf_n18_10 | 18 | 12108 | 3840 | -68.29% |
| anf_n18_4 | 18 | 8864 | 2916 | -67.10% |
| anf_n18_11 | 18 | 4540 | 1532 | -66.26% |
| anf_n18_8 | 18 | 4908 | 1676 | -65.85% |
| anf_n18_6 | 18 | 616 | 240 | -61.04% |
| anf_n18_0 | 18 | 72 | 52 | -27.78% |
| anf_n18_9 | 18 | 44 | 36 | -18.18% |

## Largest and-pareto-resource-nmcts gains vs direct ANF

| function | n | direct T | and_pareto_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n18_3 | 18 | 80524 | 24452 | -69.63% |
| anf_n18_2 | 18 | 34904 | 10644 | -69.50% |
| anf_n18_7 | 18 | 57036 | 17560 | -69.21% |
| anf_n18_1 | 18 | 32424 | 10004 | -69.15% |
| anf_n18_5 | 18 | 21488 | 6748 | -68.60% |
| anf_n18_10 | 18 | 12108 | 3840 | -68.29% |
| anf_n18_4 | 18 | 8864 | 2916 | -67.10% |
| anf_n18_11 | 18 | 4540 | 1532 | -66.26% |
| anf_n18_8 | 18 | 4908 | 1676 | -65.85% |
| anf_n18_6 | 18 | 616 | 240 | -61.04% |
| anf_n18_0 | 18 | 72 | 52 | -27.78% |
| anf_n18_9 | 18 | 44 | 36 | -18.18% |

## Largest and-fprm-root-beam gains vs direct ANF

| function | n | direct T | and_fprm_root_beam T | relative |
|---|---:|---:|---:|---:|
| anf_n18_3 | 18 | 80524 | 24784 | -69.22% |
| anf_n18_2 | 18 | 34904 | 10796 | -69.07% |
| anf_n18_7 | 18 | 57036 | 17784 | -68.82% |
| anf_n18_1 | 18 | 32424 | 10120 | -68.79% |
| anf_n18_5 | 18 | 21488 | 6912 | -67.83% |
| anf_n18_10 | 18 | 12108 | 4084 | -66.27% |
| anf_n18_4 | 18 | 8864 | 3016 | -65.97% |
| anf_n18_8 | 18 | 4908 | 1724 | -64.87% |
| anf_n18_11 | 18 | 4540 | 1596 | -64.85% |
| anf_n18_6 | 18 | 616 | 252 | -59.09% |
| anf_n18_0 | 18 | 72 | 72 | +0.00% |
| anf_n18_9 | 18 | 44 | 44 | +0.00% |

## Largest and-fprm-linear-pair-fast gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair_fast T | relative |
|---|---:|---:|---:|---:|
| anf_n18_3 | 18 | 80524 | 24784 | -69.22% |
| anf_n18_2 | 18 | 34904 | 10796 | -69.07% |
| anf_n18_7 | 18 | 57036 | 17784 | -68.82% |
| anf_n18_1 | 18 | 32424 | 10120 | -68.79% |
| anf_n18_5 | 18 | 21488 | 6912 | -67.83% |
| anf_n18_4 | 18 | 8864 | 2952 | -66.70% |
| anf_n18_10 | 18 | 12108 | 4084 | -66.27% |
| anf_n18_11 | 18 | 4540 | 1560 | -65.64% |
| anf_n18_8 | 18 | 4908 | 1708 | -65.20% |
| anf_n18_6 | 18 | 616 | 248 | -59.74% |
| anf_n18_0 | 18 | 72 | 60 | -16.67% |
| anf_n18_9 | 18 | 44 | 40 | -9.09% |
