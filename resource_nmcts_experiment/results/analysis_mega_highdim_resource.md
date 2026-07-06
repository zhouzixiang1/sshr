# Mega_Highdim_Resource Analysis

Rows: 60; usable: 60; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 12 | -41.34% | -49.98% | +0.00% |
| and_fprm_root_beam | 12 | -55.40% | -69.22% | +0.00% |
| and_profile_resource_nmcts | 12 | -55.40% | -69.22% | +0.00% |
| and_resource_nmcts | 12 | -55.40% | -69.22% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 10 | 0 | 2 | -55.40% |
| and_resource_nmcts | direct_anf | CNOT | 1 | 11 | 0 | +17.03% |
| and_resource_nmcts | direct_anf | depth | 1 | 11 | 0 | +17.03% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 9 | 3 | +62.50% |
| and_resource_nmcts | direct_anf | score | 10 | 2 | 0 | -53.08% |
| and_resource_nmcts | and_direct_anf | T | 10 | 0 | 2 | -27.94% |
| and_resource_nmcts | and_direct_anf | CNOT | 10 | 0 | 2 | -22.47% |
| and_resource_nmcts | and_direct_anf | depth | 10 | 0 | 2 | -22.47% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_resource_nmcts | and_direct_anf | score | 10 | 0 | 2 | -27.43% |
| and_resource_nmcts | and_fprm_root_beam | T | 0 | 0 | 12 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 0 | 0 | 12 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | depth | 0 | 0 | 12 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | score | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | direct_anf | T | 10 | 0 | 2 | -55.40% |
| and_profile_resource_nmcts | direct_anf | CNOT | 1 | 11 | 0 | +17.03% |
| and_profile_resource_nmcts | direct_anf | depth | 1 | 11 | 0 | +17.03% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 9 | 3 | +62.50% |
| and_profile_resource_nmcts | direct_anf | score | 10 | 2 | 0 | -53.08% |
| and_profile_resource_nmcts | and_direct_anf | T | 10 | 0 | 2 | -27.94% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 10 | 0 | 2 | -22.47% |
| and_profile_resource_nmcts | and_direct_anf | depth | 10 | 0 | 2 | -22.47% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_direct_anf | score | 10 | 0 | 2 | -27.43% |
| and_profile_resource_nmcts | and_fprm_root_beam | T | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | CNOT | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | depth | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | score | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 12 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 12 | +0.00% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
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

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
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
