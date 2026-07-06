# External Baseline Analysis

External rows: 64; usable: 64.
Internal rows: 512; usable: 512.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_abc_aig | 14 | 64 | 24801.44 | 62004.59 | 39933.56 | 0.231 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_abc_aig | T | 64 | 64 | 0 | 0 | -91.55% |
| and_resource_nmcts | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.92% |
| and_resource_nmcts | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1410.79% |
| and_resource_nmcts | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.79% |
| and_resource_nmcts | external_abc_aig | score | 64 | 64 | 0 | 0 | -94.13% |
| and_profile_resource_nmcts | external_abc_aig | T | 64 | 64 | 0 | 0 | -91.55% |
| and_profile_resource_nmcts | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.92% |
| and_profile_resource_nmcts | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1410.79% |
| and_profile_resource_nmcts | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.79% |
| and_profile_resource_nmcts | external_abc_aig | score | 64 | 64 | 0 | 0 | -94.13% |
| and_fprm_linear_pair | external_abc_aig | T | 64 | 64 | 0 | 0 | -91.32% |
| and_fprm_linear_pair | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.83% |
| and_fprm_linear_pair | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1435.32% |
| and_fprm_linear_pair | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.79% |
| and_fprm_linear_pair | external_abc_aig | score | 64 | 64 | 0 | 0 | -93.98% |
| and_fprm_root_beam | external_abc_aig | T | 64 | 64 | 0 | 0 | -90.95% |
| and_fprm_root_beam | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.66% |
| and_fprm_root_beam | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1473.57% |
| and_fprm_root_beam | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.97% |
| and_fprm_root_beam | external_abc_aig | score | 64 | 64 | 0 | 0 | -93.80% |
| and_fprm_greedy | external_abc_aig | T | 64 | 64 | 0 | 0 | -90.91% |
| and_fprm_greedy | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.65% |
| and_fprm_greedy | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1476.88% |
| and_fprm_greedy | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.97% |
| and_fprm_greedy | external_abc_aig | score | 64 | 64 | 0 | 0 | -93.78% |
| direct_anf | external_abc_aig | T | 64 | 64 | 0 | 0 | -77.70% |
| direct_anf | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -94.46% |
| direct_anf | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1270.19% |
| direct_anf | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.98% |
| direct_anf | external_abc_aig | score | 64 | 64 | 0 | 0 | -85.67% |
| and_direct_anf | external_abc_aig | T | 64 | 64 | 0 | 0 | -87.33% |
| and_direct_anf | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -91.79% |
| and_direct_anf | external_abc_aig | depth | 64 | 14 | 50 | 0 | +2179.84% |
| and_direct_anf | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.97% |
| and_direct_anf | external_abc_aig | score | 64 | 64 | 0 | 0 | -91.39% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
