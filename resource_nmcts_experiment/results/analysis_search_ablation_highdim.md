# Search_Ablation_Highdim Analysis

Rows: 128; usable: 128; errors: 0; skipped: 0.

## Mean T-count improvement vs direct ANF

| method | functions | mean relative T | best | worst |
|---|---:|---:|---:|---:|
| and_direct_anf | 16 | -34.26% | -49.94% | +0.00% |
| and_fprm_greedy | 16 | -46.92% | -69.71% | +0.00% |
| and_fprm_linear_pair | 16 | -50.21% | -70.71% | +0.00% |
| and_fprm_root_beam | 16 | -47.01% | -69.71% | +0.00% |
| and_resource_beam_only | 16 | -50.21% | -70.71% | +0.00% |
| and_resource_heuristic | 16 | -46.92% | -69.71% | +0.00% |
| and_resource_no_mcts | 16 | -52.34% | -71.04% | +0.00% |

## T-count wins/losses vs SSHR-H

| method | wins | losses | mean relative T |
|---|---:|---:|---:|

## Focused method comparisons

| target | baseline | metric | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|
| and_fprm_linear_pair | and_fprm_root_beam | T | 14 | 0 | 2 | -4.26% |
| and_fprm_linear_pair | and_fprm_root_beam | CNOT | 14 | 0 | 2 | -3.52% |
| and_fprm_linear_pair | and_fprm_root_beam | depth | 13 | 1 | 2 | -2.94% |
| and_fprm_linear_pair | and_fprm_root_beam | peak_ancilla | 0 | 14 | 2 | +40.62% |
| and_fprm_linear_pair | and_fprm_root_beam | score | 14 | 0 | 2 | -3.37% |
| and_fprm_linear_pair | and_fprm_greedy | T | 14 | 0 | 2 | -4.54% |
| and_fprm_linear_pair | and_fprm_greedy | CNOT | 14 | 0 | 2 | -3.59% |
| and_fprm_linear_pair | and_fprm_greedy | depth | 13 | 1 | 2 | -3.02% |
| and_fprm_linear_pair | and_fprm_greedy | peak_ancilla | 0 | 14 | 2 | +40.62% |
| and_fprm_linear_pair | and_fprm_greedy | score | 14 | 0 | 2 | -3.62% |
| and_fprm_root_beam | and_fprm_greedy | T | 9 | 0 | 7 | -0.28% |
| and_fprm_root_beam | and_fprm_greedy | CNOT | 5 | 3 | 8 | -0.08% |
| and_fprm_root_beam | and_fprm_greedy | depth | 5 | 3 | 8 | -0.08% |
| and_fprm_root_beam | and_fprm_greedy | peak_ancilla | 0 | 0 | 16 | +0.00% |
| and_fprm_root_beam | and_fprm_greedy | score | 9 | 0 | 7 | -0.26% |

## Largest and-fprm-greedy gains vs direct ANF

| function | n | direct T | and_fprm_greedy T | relative |
|---|---:|---:|---:|---:|
| anf_n14_2 | 14 | 32960 | 9984 | -69.71% |
| anf_n14_10 | 14 | 32156 | 9780 | -69.59% |
| anf_n14_13 | 14 | 25056 | 7696 | -69.28% |
| anf_n14_6 | 14 | 11968 | 3720 | -68.92% |
| anf_n14_4 | 14 | 12372 | 3852 | -68.87% |
| anf_n14_5 | 14 | 17180 | 5400 | -68.57% |
| anf_n14_7 | 14 | 10784 | 3400 | -68.47% |
| anf_n14_12 | 14 | 6660 | 2148 | -67.75% |
| anf_n14_11 | 14 | 7204 | 2368 | -67.13% |
| anf_n14_3 | 14 | 4756 | 1584 | -66.69% |
| anf_n14_9 | 14 | 4692 | 1604 | -65.81% |
| anf_n14_0 | 14 | 36 | 36 | +0.00% |

## Largest and-fprm-root-beam gains vs direct ANF

| function | n | direct T | and_fprm_root_beam T | relative |
|---|---:|---:|---:|---:|
| anf_n14_10 | 14 | 32156 | 9740 | -69.71% |
| anf_n14_2 | 14 | 32960 | 9984 | -69.71% |
| anf_n14_13 | 14 | 25056 | 7664 | -69.41% |
| anf_n14_4 | 14 | 12372 | 3844 | -68.93% |
| anf_n14_6 | 14 | 11968 | 3720 | -68.92% |
| anf_n14_5 | 14 | 17180 | 5368 | -68.75% |
| anf_n14_7 | 14 | 10784 | 3380 | -68.66% |
| anf_n14_12 | 14 | 6660 | 2144 | -67.81% |
| anf_n14_11 | 14 | 7204 | 2348 | -67.41% |
| anf_n14_3 | 14 | 4756 | 1576 | -66.86% |
| anf_n14_9 | 14 | 4692 | 1592 | -66.07% |
| anf_n14_0 | 14 | 36 | 36 | +0.00% |

## Largest and-fprm-linear-pair gains vs direct ANF

| function | n | direct T | and_fprm_linear_pair T | relative |
|---|---:|---:|---:|---:|
| anf_n14_10 | 14 | 32156 | 9420 | -70.71% |
| anf_n14_2 | 14 | 32960 | 9668 | -70.67% |
| anf_n14_13 | 14 | 25056 | 7448 | -70.27% |
| anf_n14_4 | 14 | 12372 | 3748 | -69.71% |
| anf_n14_6 | 14 | 11968 | 3628 | -69.69% |
| anf_n14_5 | 14 | 17180 | 5276 | -69.29% |
| anf_n14_7 | 14 | 10784 | 3324 | -69.18% |
| anf_n14_11 | 14 | 7204 | 2288 | -68.24% |
| anf_n14_12 | 14 | 6660 | 2128 | -68.05% |
| anf_n14_9 | 14 | 4692 | 1532 | -67.35% |
| anf_n14_3 | 14 | 4756 | 1572 | -66.95% |
| anf_n14_14 | 14 | 48 | 36 | -25.00% |
