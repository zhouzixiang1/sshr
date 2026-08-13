# Exact FPRM-DP Analysis

This exact slice solves a bounded fixed-polarity FPRM factorization model with dynamic programming over all monomial factors and CNOT-only linear-pair factors.  It is exact only for this model; it is not a global reversible-circuit optimum.

Rows: 72; errors: 0; skipped: 0.

## Mean Exact Resources

| n | functions | mean T | mean CNOT | mean peak ancilla | mean score | mean time s | mean DP states |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 3 | 5.33 | 13.67 | 0.67 | 7.54 | 0.000 | 2.3 |
| 4 | 69 | 17.10 | 35.88 | 1.57 | 22.46 | 0.007 | 9.8 |

## Matched Comparisons

| target | baseline | pairs | score W/L/T | mean score change | mean T change | mean CNOT change |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | and_exact_fprm_dp | 72 | 51/3/18 | -12.18% | -12.55% | -10.25% |
| and_pareto_resource_nmcts | and_exact_fprm_dp | 72 | 51/0/21 | -12.20% | -12.55% | -10.46% |
| and_exact_fprm_dp | direct_anf | 72 | 69/1/2 | -55.77% | -62.43% | -24.87% |
| and_exact_fprm_dp | and_direct_anf | 72 | 69/0/3 | -38.04% | -43.48% | -32.31% |
| and_exact_fprm_dp | and_esop_milp | 72 | 57/12/3 | -13.30% | -17.67% | +0.81% |
| and_exact_fprm_dp | external_sshr_i_cnot | 72 | 60/12/0 | -13.73% | -23.47% | +51.59% |
| and_exact_fprm_dp | external_sshr_i_t | 72 | 59/12/1 | -13.38% | -23.47% | +50.69% |
| and_resource_nmcts | external_sshr_i_cnot | 72 | 70/2/0 | -27.17% | -35.52% | +35.07% |
| and_resource_nmcts | external_sshr_i_t | 72 | 67/4/1 | -26.92% | -35.52% | +34.26% |

## Interpretation

- Exact FPRM-DP is a same-model optimum for the bounded fixed-polarity ANF/FPRM factor search, so it measures how much room remains inside this local search family.
- If Resource/Pareto rows beat exact FPRM-DP on some functions, that means their portfolio found a circuit outside this exact FPRM-DP model, not that the exact solver failed.
- This slice is intentionally restricted to n<=4 because the exact state space grows over term subsets, polarities, and live factor ancilla.
