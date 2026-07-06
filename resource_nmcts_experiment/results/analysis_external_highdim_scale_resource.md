# External Baseline Analysis

External rows: 32; usable: 32.
Internal rows: 288; usable: 288.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_abc_aig | 15 | 32 | 52711.25 | 131779.12 | 84868.67 | 0.496 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.28% |
| and_resource_nmcts | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.40% |
| and_resource_nmcts | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1943.38% |
| and_resource_nmcts | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_resource_nmcts | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.59% |
| and_profile_resource_nmcts | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.28% |
| and_profile_resource_nmcts | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.40% |
| and_profile_resource_nmcts | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1943.38% |
| and_profile_resource_nmcts | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_profile_resource_nmcts | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.59% |
| and_fprm_linear_pair_deep | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.28% |
| and_fprm_linear_pair_deep | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.40% |
| and_fprm_linear_pair_deep | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1943.38% |
| and_fprm_linear_pair_deep | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_fprm_linear_pair_deep | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.59% |
| and_fprm_linear_pair | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.18% |
| and_fprm_linear_pair | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.35% |
| and_fprm_linear_pair | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1962.70% |
| and_fprm_linear_pair | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_fprm_linear_pair | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.53% |
| and_fprm_linear_parity | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.18% |
| and_fprm_linear_parity | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.35% |
| and_fprm_linear_parity | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1962.62% |
| and_fprm_linear_parity | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_fprm_linear_parity | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.53% |
| and_fprm_greedy | external_abc_aig | T | 32 | 32 | 0 | 0 | -91.69% |
| and_fprm_greedy | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.22% |
| and_fprm_greedy | external_abc_aig | depth | 32 | 7 | 25 | 0 | +2012.55% |
| and_fprm_greedy | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| and_fprm_greedy | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.33% |
| direct_anf | external_abc_aig | T | 32 | 32 | 0 | 0 | -81.88% |
| direct_anf | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.97% |
| direct_anf | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1747.48% |
| direct_anf | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| direct_anf | external_abc_aig | score | 32 | 32 | 0 | 0 | -88.33% |
| and_direct_anf | external_abc_aig | T | 32 | 32 | 0 | 0 | -88.99% |
| and_direct_anf | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -92.79% |
| and_direct_anf | external_abc_aig | depth | 32 | 7 | 25 | 0 | +2998.21% |
| and_direct_anf | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| and_direct_anf | external_abc_aig | score | 32 | 32 | 0 | 0 | -92.53% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
