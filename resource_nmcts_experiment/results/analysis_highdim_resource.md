# Highdim_Resource Analysis

Rows: 576; usable: 576; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_affine_greedy | 64 | -52.51% | -69.71% | +0.00% |
| and_direct_anf | 64 | -39.04% | -49.96% | +0.00% |
| and_fprm_greedy | 64 | -52.51% | -69.71% | +0.00% |
| and_fprm_linear_pair | 64 | -55.60% | -70.78% | +0.00% |
| and_fprm_root_beam | 64 | -52.71% | -69.76% | +0.00% |
| and_pareto_resource_nmcts | 64 | -57.94% | -71.23% | +0.00% |
| and_profile_resource_nmcts | 64 | -57.43% | -71.23% | +0.00% |
| and_resource_nmcts | 64 | -57.43% | -71.23% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 61 | 0 | 3 | -57.43% |
| and_resource_nmcts | direct_anf | CNOT | 15 | 49 | 0 | +4.90% |
| and_resource_nmcts | direct_anf | depth | 13 | 51 | 0 | +8.04% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 60 | 4 | +127.34% |
| and_resource_nmcts | direct_anf | score | 61 | 3 | 0 | -54.01% |
| and_resource_nmcts | and_direct_anf | T | 61 | 0 | 3 | -32.78% |
| and_resource_nmcts | and_direct_anf | CNOT | 60 | 0 | 4 | -24.30% |
| and_resource_nmcts | and_direct_anf | depth | 52 | 9 | 3 | -21.59% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_resource_nmcts | and_direct_anf | score | 61 | 0 | 3 | -30.86% |
| and_resource_nmcts | and_fprm_greedy | T | 60 | 0 | 4 | -7.68% |
| and_resource_nmcts | and_fprm_greedy | CNOT | 59 | 0 | 5 | -5.12% |
| and_resource_nmcts | and_fprm_greedy | depth | 51 | 9 | 4 | -2.41% |
| and_resource_nmcts | and_fprm_greedy | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_resource_nmcts | and_fprm_greedy | score | 60 | 0 | 4 | -6.29% |
| and_resource_nmcts | and_fprm_root_beam | T | 60 | 0 | 4 | -7.12% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 59 | 0 | 5 | -4.87% |
| and_resource_nmcts | and_fprm_root_beam | depth | 51 | 9 | 4 | -2.16% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_resource_nmcts | and_fprm_root_beam | score | 60 | 0 | 4 | -5.76% |
| and_resource_nmcts | and_affine_greedy | T | 60 | 0 | 4 | -7.68% |
| and_resource_nmcts | and_affine_greedy | CNOT | 59 | 0 | 5 | -5.12% |
| and_resource_nmcts | and_affine_greedy | depth | 51 | 9 | 4 | -2.41% |
| and_resource_nmcts | and_affine_greedy | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_resource_nmcts | and_affine_greedy | score | 60 | 0 | 4 | -6.29% |
| and_profile_resource_nmcts | direct_anf | T | 61 | 0 | 3 | -57.43% |
| and_profile_resource_nmcts | direct_anf | CNOT | 15 | 49 | 0 | +4.90% |
| and_profile_resource_nmcts | direct_anf | depth | 13 | 51 | 0 | +8.04% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 60 | 4 | +127.34% |
| and_profile_resource_nmcts | direct_anf | score | 61 | 3 | 0 | -54.01% |
| and_profile_resource_nmcts | and_direct_anf | T | 61 | 0 | 3 | -32.78% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 60 | 0 | 4 | -24.30% |
| and_profile_resource_nmcts | and_direct_anf | depth | 52 | 9 | 3 | -21.59% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_profile_resource_nmcts | and_direct_anf | score | 61 | 0 | 3 | -30.86% |
| and_profile_resource_nmcts | and_fprm_greedy | T | 60 | 0 | 4 | -7.68% |
| and_profile_resource_nmcts | and_fprm_greedy | CNOT | 59 | 0 | 5 | -5.12% |
| and_profile_resource_nmcts | and_fprm_greedy | depth | 51 | 9 | 4 | -2.41% |
| and_profile_resource_nmcts | and_fprm_greedy | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_profile_resource_nmcts | and_fprm_greedy | score | 60 | 0 | 4 | -6.29% |
| and_profile_resource_nmcts | and_fprm_root_beam | T | 60 | 0 | 4 | -7.12% |
| and_profile_resource_nmcts | and_fprm_root_beam | CNOT | 59 | 0 | 5 | -4.87% |
| and_profile_resource_nmcts | and_fprm_root_beam | depth | 51 | 9 | 4 | -2.16% |
| and_profile_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_profile_resource_nmcts | and_fprm_root_beam | score | 60 | 0 | 4 | -5.76% |
| and_profile_resource_nmcts | and_affine_greedy | T | 60 | 0 | 4 | -7.68% |
| and_profile_resource_nmcts | and_affine_greedy | CNOT | 59 | 0 | 5 | -5.12% |
| and_profile_resource_nmcts | and_affine_greedy | depth | 51 | 9 | 4 | -2.41% |
| and_profile_resource_nmcts | and_affine_greedy | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_profile_resource_nmcts | and_affine_greedy | score | 60 | 0 | 4 | -6.29% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 64 | +0.00% |
| and_fprm_linear_pair | and_fprm_root_beam | T | 60 | 0 | 4 | -4.19% |
| and_fprm_linear_pair | and_fprm_root_beam | CNOT | 57 | 1 | 6 | -3.03% |
| and_fprm_linear_pair | and_fprm_root_beam | depth | 54 | 6 | 4 | -1.51% |
| and_fprm_linear_pair | and_fprm_root_beam | peak_ancilla | 0 | 58 | 6 | +54.30% |
| and_fprm_linear_pair | and_fprm_root_beam | score | 60 | 0 | 4 | -3.00% |
| and_fprm_linear_pair | and_fprm_greedy | T | 60 | 0 | 4 | -4.76% |
| and_fprm_linear_pair | and_fprm_greedy | CNOT | 57 | 1 | 6 | -3.28% |
| and_fprm_linear_pair | and_fprm_greedy | depth | 54 | 6 | 4 | -1.76% |
| and_fprm_linear_pair | and_fprm_greedy | peak_ancilla | 0 | 58 | 6 | +54.30% |
| and_fprm_linear_pair | and_fprm_greedy | score | 60 | 0 | 4 | -3.54% |
| and_resource_nmcts | and_fprm_linear_pair | T | 56 | 0 | 8 | -3.19% |
| and_resource_nmcts | and_fprm_linear_pair | CNOT | 56 | 1 | 7 | -1.90% |
| and_resource_nmcts | and_fprm_linear_pair | depth | 51 | 6 | 7 | -0.56% |
| and_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 1 | 9 | 54 | +3.23% |
| and_resource_nmcts | and_fprm_linear_pair | score | 57 | 0 | 7 | -2.90% |
| and_profile_resource_nmcts | and_fprm_linear_pair | T | 56 | 0 | 8 | -3.19% |
| and_profile_resource_nmcts | and_fprm_linear_pair | CNOT | 56 | 1 | 7 | -1.90% |
| and_profile_resource_nmcts | and_fprm_linear_pair | depth | 51 | 6 | 7 | -0.56% |
| and_profile_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 1 | 9 | 54 | +3.23% |
| and_profile_resource_nmcts | and_fprm_linear_pair | score | 57 | 0 | 7 | -2.90% |
| and_pareto_resource_nmcts | direct_anf | T | 61 | 0 | 3 | -57.94% |
| and_pareto_resource_nmcts | direct_anf | CNOT | 16 | 47 | 1 | +4.19% |
| and_pareto_resource_nmcts | direct_anf | depth | 14 | 50 | 0 | +7.20% |
| and_pareto_resource_nmcts | direct_anf | peak_ancilla | 0 | 60 | 4 | +127.34% |
| and_pareto_resource_nmcts | direct_anf | score | 61 | 3 | 0 | -54.55% |
| and_pareto_resource_nmcts | and_direct_anf | T | 61 | 0 | 3 | -33.30% |
| and_pareto_resource_nmcts | and_direct_anf | CNOT | 61 | 0 | 3 | -24.91% |
| and_pareto_resource_nmcts | and_direct_anf | depth | 52 | 9 | 3 | -22.31% |
| and_pareto_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_pareto_resource_nmcts | and_direct_anf | score | 61 | 0 | 3 | -31.40% |
| and_pareto_resource_nmcts | and_resource_nmcts | T | 10 | 0 | 54 | -0.64% |
| and_pareto_resource_nmcts | and_resource_nmcts | CNOT | 9 | 7 | 48 | -0.64% |
| and_pareto_resource_nmcts | and_resource_nmcts | depth | 7 | 9 | 48 | -0.65% |
| and_pareto_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_pareto_resource_nmcts | and_resource_nmcts | score | 16 | 0 | 48 | -0.59% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | T | 10 | 0 | 54 | -0.64% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | CNOT | 9 | 7 | 48 | -0.64% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | depth | 7 | 9 | 48 | -0.65% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_pareto_resource_nmcts | and_profile_resource_nmcts | score | 16 | 0 | 48 | -0.59% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | T | 58 | 0 | 6 | -3.83% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | CNOT | 59 | 0 | 5 | -2.54% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | depth | 54 | 5 | 5 | -1.26% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | peak_ancilla | 1 | 9 | 54 | +3.23% |
| and_pareto_resource_nmcts | and_fprm_linear_pair | score | 59 | 0 | 5 | -3.49% |
| and_pareto_resource_nmcts | and_fprm_root_beam | T | 60 | 0 | 4 | -7.65% |
| and_pareto_resource_nmcts | and_fprm_root_beam | CNOT | 60 | 0 | 4 | -5.48% |
| and_pareto_resource_nmcts | and_fprm_root_beam | depth | 51 | 9 | 4 | -2.88% |
| and_pareto_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 59 | 5 | +58.33% |
| and_pareto_resource_nmcts | and_fprm_root_beam | score | 60 | 0 | 4 | -6.31% |
| and_fprm_root_beam | and_fprm_greedy | T | 40 | 0 | 24 | -0.58% |
| and_fprm_root_beam | and_fprm_greedy | CNOT | 30 | 9 | 25 | -0.26% |
| and_fprm_root_beam | and_fprm_greedy | depth | 30 | 9 | 25 | -0.26% |
| and_fprm_root_beam | and_fprm_greedy | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_fprm_root_beam | and_fprm_greedy | score | 41 | 0 | 23 | -0.55% |
| and_fprm_root_beam | and_affine_greedy | T | 40 | 0 | 24 | -0.58% |
| and_fprm_root_beam | and_affine_greedy | CNOT | 30 | 9 | 25 | -0.26% |
| and_fprm_root_beam | and_affine_greedy | depth | 30 | 9 | 25 | -0.26% |
| and_fprm_root_beam | and_affine_greedy | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_fprm_root_beam | and_affine_greedy | score | 41 | 0 | 23 | -0.55% |
| and_affine_greedy | and_fprm_greedy | T | 0 | 0 | 64 | +0.00% |
| and_affine_greedy | and_fprm_greedy | CNOT | 0 | 0 | 64 | +0.00% |
| and_affine_greedy | and_fprm_greedy | depth | 0 | 0 | 64 | +0.00% |
| and_affine_greedy | and_fprm_greedy | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_affine_greedy | and_fprm_greedy | score | 0 | 0 | 64 | +0.00% |

## Largest and-resource-nmcts gains vs direct ANF

| function | n | direct T | and_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n14_41 | 14 | 23608 | 6792 | -71.23% |
| anf_n14_50 | 14 | 13664 | 3940 | -71.17% |
| anf_n14_18 | 14 | 26328 | 7616 | -71.07% |
| anf_n14_13 | 14 | 25056 | 7256 | -71.04% |
| anf_n14_55 | 14 | 25180 | 7292 | -71.04% |
| anf_n14_20 | 14 | 33692 | 9816 | -70.87% |
| anf_n14_10 | 14 | 32156 | 9408 | -70.74% |
| anf_n14_2 | 14 | 32960 | 9648 | -70.73% |
| anf_n14_31 | 14 | 21000 | 6148 | -70.72% |
| anf_n14_4 | 14 | 12372 | 3628 | -70.68% |
| anf_n14_48 | 14 | 23420 | 6884 | -70.61% |
| anf_n14_6 | 14 | 11968 | 3520 | -70.59% |

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n14_41 | 14 | 23608 | 6792 | -71.23% |
| anf_n14_50 | 14 | 13664 | 3940 | -71.17% |
| anf_n14_18 | 14 | 26328 | 7616 | -71.07% |
| anf_n14_13 | 14 | 25056 | 7256 | -71.04% |
| anf_n14_55 | 14 | 25180 | 7292 | -71.04% |
| anf_n14_20 | 14 | 33692 | 9816 | -70.87% |
| anf_n14_10 | 14 | 32156 | 9408 | -70.74% |
| anf_n14_2 | 14 | 32960 | 9648 | -70.73% |
| anf_n14_31 | 14 | 21000 | 6148 | -70.72% |
| anf_n14_4 | 14 | 12372 | 3628 | -70.68% |
| anf_n14_48 | 14 | 23420 | 6884 | -70.61% |
| anf_n14_6 | 14 | 11968 | 3520 | -70.59% |

## Largest and-pareto-resource-nmcts gains vs direct ANF

| function | n | direct T | and_pareto_resource_nmcts T | relative |
|---|---:|---:|---:|---:|
| anf_n14_41 | 14 | 23608 | 6792 | -71.23% |
| anf_n14_50 | 14 | 13664 | 3940 | -71.17% |
| anf_n14_18 | 14 | 26328 | 7616 | -71.07% |
| anf_n14_13 | 14 | 25056 | 7256 | -71.04% |
| anf_n14_55 | 14 | 25180 | 7292 | -71.04% |
| anf_n14_20 | 14 | 33692 | 9816 | -70.87% |
| anf_n14_10 | 14 | 32156 | 9408 | -70.74% |
| anf_n14_2 | 14 | 32960 | 9648 | -70.73% |
| anf_n14_31 | 14 | 21000 | 6148 | -70.72% |
| anf_n14_4 | 14 | 12372 | 3628 | -70.68% |
| anf_n14_48 | 14 | 23420 | 6884 | -70.61% |
| anf_n14_6 | 14 | 11968 | 3520 | -70.59% |

## Largest and-affine-greedy gains vs direct ANF

| function | n | direct T | and_affine_greedy T | relative |
|---|---:|---:|---:|---:|
| anf_n14_2 | 14 | 32960 | 9984 | -69.71% |
| anf_n14_20 | 14 | 33692 | 10236 | -69.62% |
| anf_n14_10 | 14 | 32156 | 9780 | -69.59% |
| anf_n14_13 | 14 | 25056 | 7696 | -69.28% |
| anf_n14_18 | 14 | 26328 | 8096 | -69.25% |
| anf_n14_55 | 14 | 25180 | 7760 | -69.18% |
| anf_n14_41 | 14 | 23608 | 7288 | -69.13% |
| anf_n14_31 | 14 | 21000 | 6504 | -69.03% |
| anf_n14_48 | 14 | 23420 | 7260 | -69.00% |
| anf_n14_50 | 14 | 13664 | 4236 | -69.00% |
| anf_n14_6 | 14 | 11968 | 3720 | -68.92% |
| anf_n14_4 | 14 | 12372 | 3852 | -68.87% |

## Largest and-fprm-greedy gains vs direct ANF

| function | n | direct T | and_fprm_greedy T | relative |
|---|---:|---:|---:|---:|
| anf_n14_2 | 14 | 32960 | 9984 | -69.71% |
| anf_n14_20 | 14 | 33692 | 10236 | -69.62% |
| anf_n14_10 | 14 | 32156 | 9780 | -69.59% |
| anf_n14_13 | 14 | 25056 | 7696 | -69.28% |
| anf_n14_18 | 14 | 26328 | 8096 | -69.25% |
| anf_n14_55 | 14 | 25180 | 7760 | -69.18% |
| anf_n14_41 | 14 | 23608 | 7288 | -69.13% |
| anf_n14_31 | 14 | 21000 | 6504 | -69.03% |
| anf_n14_48 | 14 | 23420 | 7260 | -69.00% |
| anf_n14_50 | 14 | 13664 | 4236 | -69.00% |
| anf_n14_6 | 14 | 11968 | 3720 | -68.92% |
| anf_n14_4 | 14 | 12372 | 3852 | -68.87% |

## Largest and-fprm-root-beam gains vs direct ANF

| function | n | direct T | and_fprm_root_beam T | relative |
|---|---:|---:|---:|---:|
| anf_n14_20 | 14 | 33692 | 10188 | -69.76% |
| anf_n14_10 | 14 | 32156 | 9740 | -69.71% |
| anf_n14_2 | 14 | 32960 | 9984 | -69.71% |
| anf_n14_18 | 14 | 26328 | 8032 | -69.49% |
| anf_n14_13 | 14 | 25056 | 7664 | -69.41% |
| anf_n14_41 | 14 | 23608 | 7228 | -69.38% |
| anf_n14_55 | 14 | 25180 | 7720 | -69.34% |
| anf_n14_31 | 14 | 21000 | 6448 | -69.30% |
| anf_n14_48 | 14 | 23420 | 7196 | -69.27% |
| anf_n14_50 | 14 | 13664 | 4212 | -69.17% |
| anf_n14_4 | 14 | 12372 | 3844 | -68.93% |
| anf_n14_6 | 14 | 11968 | 3720 | -68.92% |

## Largest and-fprm-linear-pair gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair T | relative |
|---|---:|---:|---:|---:|
| anf_n14_20 | 14 | 33692 | 9844 | -70.78% |
| anf_n14_10 | 14 | 32156 | 9420 | -70.71% |
| anf_n14_2 | 14 | 32960 | 9668 | -70.67% |
| anf_n14_13 | 14 | 25056 | 7448 | -70.27% |
| anf_n14_41 | 14 | 23608 | 7020 | -70.26% |
| anf_n14_18 | 14 | 26328 | 7844 | -70.21% |
| anf_n14_55 | 14 | 25180 | 7516 | -70.15% |
| anf_n14_50 | 14 | 13664 | 4088 | -70.08% |
| anf_n14_48 | 14 | 23420 | 7020 | -70.03% |
| anf_n14_31 | 14 | 21000 | 6308 | -69.96% |
| anf_n14_4 | 14 | 12372 | 3748 | -69.71% |
| anf_n14_6 | 14 | 11968 | 3628 | -69.69% |
