# External Baseline Analysis

External rows: 192; usable: 192.
Internal rows: 512; usable: 512.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_abc_aig | 14 | 64 | 24801.44 | 62004.59 | 39933.56 | 0.240 |
| external_abc_xag | 14 | 64 | 31204.56 | 46928.47 | 48965.29 | 0.143 |
| external_bdd | 14 | 64 | 22650.25 | 39705.72 | 28049.34 | 0.493 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_abc_aig | T | 64 | 64 | 0 | 0 | -91.55% |
| and_resource_nmcts | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.92% |
| and_resource_nmcts | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1410.79% |
| and_resource_nmcts | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.79% |
| and_resource_nmcts | external_abc_aig | score | 64 | 64 | 0 | 0 | -94.13% |
| and_resource_nmcts | external_abc_xag | T | 64 | 64 | 0 | 0 | -93.61% |
| and_resource_nmcts | external_abc_xag | CNOT | 64 | 64 | 0 | 0 | -92.42% |
| and_resource_nmcts | external_abc_xag | depth | 64 | 14 | 50 | 0 | +1160.89% |
| and_resource_nmcts | external_abc_xag | peak_ancilla | 64 | 64 | 0 | 0 | -99.84% |
| and_resource_nmcts | external_abc_xag | score | 64 | 64 | 0 | 0 | -95.48% |
| and_resource_nmcts | external_bdd | T | 64 | 64 | 0 | 0 | -92.45% |
| and_resource_nmcts | external_bdd | CNOT | 64 | 64 | 0 | 0 | -92.39% |
| and_resource_nmcts | external_bdd | depth | 64 | 64 | 0 | 0 | -93.25% |
| and_resource_nmcts | external_bdd | peak_ancilla | 64 | 64 | 0 | 0 | -99.50% |
| and_resource_nmcts | external_bdd | score | 64 | 64 | 0 | 0 | -93.24% |
| and_profile_resource_nmcts | external_abc_aig | T | 64 | 64 | 0 | 0 | -91.55% |
| and_profile_resource_nmcts | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.92% |
| and_profile_resource_nmcts | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1410.79% |
| and_profile_resource_nmcts | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.79% |
| and_profile_resource_nmcts | external_abc_aig | score | 64 | 64 | 0 | 0 | -94.13% |
| and_profile_resource_nmcts | external_abc_xag | T | 64 | 64 | 0 | 0 | -93.61% |
| and_profile_resource_nmcts | external_abc_xag | CNOT | 64 | 64 | 0 | 0 | -92.42% |
| and_profile_resource_nmcts | external_abc_xag | depth | 64 | 14 | 50 | 0 | +1160.89% |
| and_profile_resource_nmcts | external_abc_xag | peak_ancilla | 64 | 64 | 0 | 0 | -99.84% |
| and_profile_resource_nmcts | external_abc_xag | score | 64 | 64 | 0 | 0 | -95.48% |
| and_profile_resource_nmcts | external_bdd | T | 64 | 64 | 0 | 0 | -92.45% |
| and_profile_resource_nmcts | external_bdd | CNOT | 64 | 64 | 0 | 0 | -92.39% |
| and_profile_resource_nmcts | external_bdd | depth | 64 | 64 | 0 | 0 | -93.25% |
| and_profile_resource_nmcts | external_bdd | peak_ancilla | 64 | 64 | 0 | 0 | -99.50% |
| and_profile_resource_nmcts | external_bdd | score | 64 | 64 | 0 | 0 | -93.24% |
| and_fprm_linear_pair | external_abc_aig | T | 64 | 64 | 0 | 0 | -91.32% |
| and_fprm_linear_pair | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.83% |
| and_fprm_linear_pair | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1435.32% |
| and_fprm_linear_pair | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.79% |
| and_fprm_linear_pair | external_abc_aig | score | 64 | 64 | 0 | 0 | -93.98% |
| and_fprm_linear_pair | external_abc_xag | T | 64 | 64 | 0 | 0 | -93.43% |
| and_fprm_linear_pair | external_abc_xag | CNOT | 64 | 64 | 0 | 0 | -92.30% |
| and_fprm_linear_pair | external_abc_xag | depth | 64 | 14 | 50 | 0 | +1180.94% |
| and_fprm_linear_pair | external_abc_xag | peak_ancilla | 64 | 64 | 0 | 0 | -99.84% |
| and_fprm_linear_pair | external_abc_xag | score | 64 | 64 | 0 | 0 | -95.36% |
| and_fprm_linear_pair | external_bdd | T | 64 | 64 | 0 | 0 | -92.26% |
| and_fprm_linear_pair | external_bdd | CNOT | 64 | 64 | 0 | 0 | -92.26% |
| and_fprm_linear_pair | external_bdd | depth | 64 | 64 | 0 | 0 | -93.16% |
| and_fprm_linear_pair | external_bdd | peak_ancilla | 64 | 64 | 0 | 0 | -99.50% |
| and_fprm_linear_pair | external_bdd | score | 64 | 64 | 0 | 0 | -93.08% |
| and_fprm_root_beam | external_abc_aig | T | 64 | 64 | 0 | 0 | -90.95% |
| and_fprm_root_beam | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.66% |
| and_fprm_root_beam | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1473.57% |
| and_fprm_root_beam | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.97% |
| and_fprm_root_beam | external_abc_aig | score | 64 | 64 | 0 | 0 | -93.80% |
| and_fprm_root_beam | external_abc_xag | T | 64 | 64 | 0 | 0 | -93.15% |
| and_fprm_root_beam | external_abc_xag | CNOT | 64 | 64 | 0 | 0 | -92.08% |
| and_fprm_root_beam | external_abc_xag | depth | 64 | 14 | 50 | 0 | +1212.59% |
| and_fprm_root_beam | external_abc_xag | peak_ancilla | 64 | 64 | 0 | 0 | -99.98% |
| and_fprm_root_beam | external_abc_xag | score | 64 | 64 | 0 | 0 | -95.21% |
| and_fprm_root_beam | external_bdd | T | 64 | 64 | 0 | 0 | -91.98% |
| and_fprm_root_beam | external_bdd | CNOT | 64 | 64 | 0 | 0 | -92.05% |
| and_fprm_root_beam | external_bdd | depth | 64 | 64 | 0 | 0 | -93.06% |
| and_fprm_root_beam | external_bdd | peak_ancilla | 64 | 64 | 0 | 0 | -99.89% |
| and_fprm_root_beam | external_bdd | score | 64 | 64 | 0 | 0 | -92.88% |
| and_fprm_greedy | external_abc_aig | T | 64 | 64 | 0 | 0 | -90.91% |
| and_fprm_greedy | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -93.65% |
| and_fprm_greedy | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1476.88% |
| and_fprm_greedy | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.97% |
| and_fprm_greedy | external_abc_aig | score | 64 | 64 | 0 | 0 | -93.78% |
| and_fprm_greedy | external_abc_xag | T | 64 | 64 | 0 | 0 | -93.11% |
| and_fprm_greedy | external_abc_xag | CNOT | 64 | 64 | 0 | 0 | -92.07% |
| and_fprm_greedy | external_abc_xag | depth | 64 | 14 | 50 | 0 | +1215.42% |
| and_fprm_greedy | external_abc_xag | peak_ancilla | 64 | 64 | 0 | 0 | -99.98% |
| and_fprm_greedy | external_abc_xag | score | 64 | 64 | 0 | 0 | -95.19% |
| and_fprm_greedy | external_bdd | T | 64 | 64 | 0 | 0 | -91.93% |
| and_fprm_greedy | external_bdd | CNOT | 64 | 64 | 0 | 0 | -92.04% |
| and_fprm_greedy | external_bdd | depth | 64 | 64 | 0 | 0 | -93.05% |
| and_fprm_greedy | external_bdd | peak_ancilla | 64 | 64 | 0 | 0 | -99.89% |
| and_fprm_greedy | external_bdd | score | 64 | 64 | 0 | 0 | -92.85% |
| direct_anf | external_abc_aig | T | 64 | 64 | 0 | 0 | -77.70% |
| direct_anf | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -94.46% |
| direct_anf | external_abc_aig | depth | 64 | 14 | 50 | 0 | +1270.19% |
| direct_anf | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.98% |
| direct_anf | external_abc_aig | score | 64 | 64 | 0 | 0 | -85.67% |
| direct_anf | external_abc_xag | T | 64 | 64 | 0 | 0 | -82.56% |
| direct_anf | external_abc_xag | CNOT | 64 | 64 | 0 | 0 | -93.07% |
| direct_anf | external_abc_xag | depth | 64 | 13 | 51 | 0 | +1047.78% |
| direct_anf | external_abc_xag | peak_ancilla | 64 | 64 | 0 | 0 | -99.99% |
| direct_anf | external_abc_xag | score | 64 | 64 | 0 | 0 | -88.54% |
| direct_anf | external_bdd | T | 64 | 64 | 0 | 0 | -77.45% |
| direct_anf | external_bdd | CNOT | 64 | 64 | 0 | 0 | -93.01% |
| direct_anf | external_bdd | depth | 64 | 64 | 0 | 0 | -93.90% |
| direct_anf | external_bdd | peak_ancilla | 64 | 64 | 0 | 0 | -99.92% |
| direct_anf | external_bdd | score | 64 | 64 | 0 | 0 | -81.27% |
| and_direct_anf | external_abc_aig | T | 64 | 64 | 0 | 0 | -87.33% |
| and_direct_anf | external_abc_aig | CNOT | 64 | 64 | 0 | 0 | -91.79% |
| and_direct_anf | external_abc_aig | depth | 64 | 14 | 50 | 0 | +2179.84% |
| and_direct_anf | external_abc_aig | peak_ancilla | 64 | 64 | 0 | 0 | -99.97% |
| and_direct_anf | external_abc_aig | score | 64 | 64 | 0 | 0 | -91.39% |
| and_direct_anf | external_abc_xag | T | 64 | 64 | 0 | 0 | -90.25% |
| and_direct_anf | external_abc_xag | CNOT | 64 | 64 | 0 | 0 | -89.60% |
| and_direct_anf | external_abc_xag | depth | 64 | 13 | 51 | 0 | +1793.01% |
| and_direct_anf | external_abc_xag | peak_ancilla | 64 | 64 | 0 | 0 | -99.98% |
| and_direct_anf | external_abc_xag | score | 64 | 64 | 0 | 0 | -93.23% |
| and_direct_anf | external_bdd | T | 64 | 64 | 0 | 0 | -88.01% |
| and_direct_anf | external_bdd | CNOT | 64 | 64 | 0 | 0 | -89.13% |
| and_direct_anf | external_bdd | depth | 64 | 64 | 0 | 0 | -90.50% |
| and_direct_anf | external_bdd | peak_ancilla | 64 | 64 | 0 | 0 | -99.89% |
| and_direct_anf | external_bdd | score | 64 | 64 | 0 | 0 | -89.44% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
