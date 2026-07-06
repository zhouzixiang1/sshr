# Highdim_Resource Analysis

Rows: 448; usable: 448; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_affine_greedy | 64 | -52.51% | -69.71% | +0.00% |
| and_direct_anf | 64 | -39.04% | -49.96% | +0.00% |
| and_fprm_greedy | 64 | -52.51% | -69.71% | +0.00% |
| and_fprm_root_beam | 64 | -52.71% | -69.76% | +0.00% |
| and_profile_resource_nmcts | 64 | -52.71% | -69.76% | +0.00% |
| and_resource_nmcts | 64 | -52.71% | -69.76% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_resource_nmcts | direct_anf | T | 51 | 0 | 13 | -52.71% |
| and_resource_nmcts | direct_anf | CNOT | 13 | 51 | 0 | +10.12% |
| and_resource_nmcts | direct_anf | depth | 13 | 51 | 0 | +10.11% |
| and_resource_nmcts | direct_anf | peak_ancilla | 0 | 38 | 26 | +49.22% |
| and_resource_nmcts | direct_anf | score | 51 | 13 | 0 | -50.39% |
| and_resource_nmcts | and_direct_anf | T | 51 | 0 | 13 | -26.88% |
| and_resource_nmcts | and_direct_anf | CNOT | 51 | 0 | 13 | -20.33% |
| and_resource_nmcts | and_direct_anf | depth | 51 | 0 | 13 | -20.33% |
| and_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_direct_anf | score | 51 | 0 | 13 | -26.23% |
| and_resource_nmcts | and_fprm_greedy | T | 40 | 0 | 24 | -0.58% |
| and_resource_nmcts | and_fprm_greedy | CNOT | 30 | 9 | 25 | -0.26% |
| and_resource_nmcts | and_fprm_greedy | depth | 30 | 9 | 25 | -0.26% |
| and_resource_nmcts | and_fprm_greedy | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_fprm_greedy | score | 41 | 0 | 23 | -0.55% |
| and_resource_nmcts | and_fprm_root_beam | T | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | CNOT | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | depth | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_fprm_root_beam | score | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_affine_greedy | T | 40 | 0 | 24 | -0.58% |
| and_resource_nmcts | and_affine_greedy | CNOT | 30 | 9 | 25 | -0.26% |
| and_resource_nmcts | and_affine_greedy | depth | 30 | 9 | 25 | -0.26% |
| and_resource_nmcts | and_affine_greedy | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_resource_nmcts | and_affine_greedy | score | 41 | 0 | 23 | -0.55% |
| and_profile_resource_nmcts | direct_anf | T | 51 | 0 | 13 | -52.71% |
| and_profile_resource_nmcts | direct_anf | CNOT | 13 | 51 | 0 | +10.12% |
| and_profile_resource_nmcts | direct_anf | depth | 13 | 51 | 0 | +10.11% |
| and_profile_resource_nmcts | direct_anf | peak_ancilla | 0 | 38 | 26 | +49.22% |
| and_profile_resource_nmcts | direct_anf | score | 51 | 13 | 0 | -50.39% |
| and_profile_resource_nmcts | and_direct_anf | T | 51 | 0 | 13 | -26.88% |
| and_profile_resource_nmcts | and_direct_anf | CNOT | 51 | 0 | 13 | -20.33% |
| and_profile_resource_nmcts | and_direct_anf | depth | 51 | 0 | 13 | -20.33% |
| and_profile_resource_nmcts | and_direct_anf | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_direct_anf | score | 51 | 0 | 13 | -26.23% |
| and_profile_resource_nmcts | and_fprm_greedy | T | 40 | 0 | 24 | -0.58% |
| and_profile_resource_nmcts | and_fprm_greedy | CNOT | 30 | 9 | 25 | -0.26% |
| and_profile_resource_nmcts | and_fprm_greedy | depth | 30 | 9 | 25 | -0.26% |
| and_profile_resource_nmcts | and_fprm_greedy | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_fprm_greedy | score | 41 | 0 | 23 | -0.55% |
| and_profile_resource_nmcts | and_fprm_root_beam | T | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | CNOT | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | depth | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_fprm_root_beam | score | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_affine_greedy | T | 40 | 0 | 24 | -0.58% |
| and_profile_resource_nmcts | and_affine_greedy | CNOT | 30 | 9 | 25 | -0.26% |
| and_profile_resource_nmcts | and_affine_greedy | depth | 30 | 9 | 25 | -0.26% |
| and_profile_resource_nmcts | and_affine_greedy | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_affine_greedy | score | 41 | 0 | 23 | -0.55% |
| and_profile_resource_nmcts | and_resource_nmcts | T | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | CNOT | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | depth | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | peak_ancilla | 0 | 0 | 64 | +0.00% |
| and_profile_resource_nmcts | and_resource_nmcts | score | 0 | 0 | 64 | +0.00% |
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

## Largest and-profile-resource-nmcts gains vs direct ANF

| function | n | direct T | and_profile_resource_nmcts T | relative |
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
