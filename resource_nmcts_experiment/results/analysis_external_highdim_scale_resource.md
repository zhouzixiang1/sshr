# External Baseline Analysis

External rows: 96; usable: 96.
Internal rows: 288; usable: 288.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_abc_aig | 15 | 32 | 52711.25 | 131779.12 | 84868.67 | 0.520 |
| external_abc_xag | 15 | 32 | 66132.50 | 99351.31 | 103660.77 | 0.308 |
| external_bdd | 15 | 32 | 44732.00 | 78360.00 | 55331.98 | 1.256 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.28% |
| and_resource_nmcts | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.40% |
| and_resource_nmcts | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1943.38% |
| and_resource_nmcts | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_resource_nmcts | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.59% |
| and_resource_nmcts | external_abc_xag | T | 32 | 32 | 0 | 0 | -94.87% |
| and_resource_nmcts | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -93.89% |
| and_resource_nmcts | external_abc_xag | depth | 32 | 6 | 26 | 0 | +1408.93% |
| and_resource_nmcts | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.81% |
| and_resource_nmcts | external_abc_xag | score | 32 | 32 | 0 | 0 | -96.33% |
| and_resource_nmcts | external_bdd | T | 32 | 32 | 0 | 0 | -94.14% |
| and_resource_nmcts | external_bdd | CNOT | 32 | 32 | 0 | 0 | -94.14% |
| and_resource_nmcts | external_bdd | depth | 32 | 32 | 0 | 0 | -94.77% |
| and_resource_nmcts | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.65% |
| and_resource_nmcts | external_bdd | score | 32 | 32 | 0 | 0 | -94.75% |
| and_profile_resource_nmcts | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.28% |
| and_profile_resource_nmcts | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.40% |
| and_profile_resource_nmcts | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1943.38% |
| and_profile_resource_nmcts | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_profile_resource_nmcts | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.59% |
| and_profile_resource_nmcts | external_abc_xag | T | 32 | 32 | 0 | 0 | -94.87% |
| and_profile_resource_nmcts | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -93.89% |
| and_profile_resource_nmcts | external_abc_xag | depth | 32 | 6 | 26 | 0 | +1408.93% |
| and_profile_resource_nmcts | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.81% |
| and_profile_resource_nmcts | external_abc_xag | score | 32 | 32 | 0 | 0 | -96.33% |
| and_profile_resource_nmcts | external_bdd | T | 32 | 32 | 0 | 0 | -94.14% |
| and_profile_resource_nmcts | external_bdd | CNOT | 32 | 32 | 0 | 0 | -94.14% |
| and_profile_resource_nmcts | external_bdd | depth | 32 | 32 | 0 | 0 | -94.77% |
| and_profile_resource_nmcts | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.65% |
| and_profile_resource_nmcts | external_bdd | score | 32 | 32 | 0 | 0 | -94.75% |
| and_fprm_linear_pair_deep | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.28% |
| and_fprm_linear_pair_deep | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.40% |
| and_fprm_linear_pair_deep | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1943.38% |
| and_fprm_linear_pair_deep | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_fprm_linear_pair_deep | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.59% |
| and_fprm_linear_pair_deep | external_abc_xag | T | 32 | 32 | 0 | 0 | -94.87% |
| and_fprm_linear_pair_deep | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -93.89% |
| and_fprm_linear_pair_deep | external_abc_xag | depth | 32 | 6 | 26 | 0 | +1408.93% |
| and_fprm_linear_pair_deep | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.81% |
| and_fprm_linear_pair_deep | external_abc_xag | score | 32 | 32 | 0 | 0 | -96.33% |
| and_fprm_linear_pair_deep | external_bdd | T | 32 | 32 | 0 | 0 | -94.14% |
| and_fprm_linear_pair_deep | external_bdd | CNOT | 32 | 32 | 0 | 0 | -94.14% |
| and_fprm_linear_pair_deep | external_bdd | depth | 32 | 32 | 0 | 0 | -94.77% |
| and_fprm_linear_pair_deep | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.65% |
| and_fprm_linear_pair_deep | external_bdd | score | 32 | 32 | 0 | 0 | -94.75% |
| and_fprm_linear_pair | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.18% |
| and_fprm_linear_pair | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.35% |
| and_fprm_linear_pair | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1962.70% |
| and_fprm_linear_pair | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_fprm_linear_pair | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.53% |
| and_fprm_linear_pair | external_abc_xag | T | 32 | 32 | 0 | 0 | -94.78% |
| and_fprm_linear_pair | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -93.82% |
| and_fprm_linear_pair | external_abc_xag | depth | 32 | 6 | 26 | 0 | +1424.72% |
| and_fprm_linear_pair | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.81% |
| and_fprm_linear_pair | external_abc_xag | score | 32 | 32 | 0 | 0 | -96.28% |
| and_fprm_linear_pair | external_bdd | T | 32 | 32 | 0 | 0 | -94.06% |
| and_fprm_linear_pair | external_bdd | CNOT | 32 | 32 | 0 | 0 | -94.08% |
| and_fprm_linear_pair | external_bdd | depth | 32 | 32 | 0 | 0 | -94.73% |
| and_fprm_linear_pair | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.66% |
| and_fprm_linear_pair | external_bdd | score | 32 | 32 | 0 | 0 | -94.68% |
| and_fprm_linear_parity | external_abc_aig | T | 32 | 32 | 0 | 0 | -92.18% |
| and_fprm_linear_parity | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.35% |
| and_fprm_linear_parity | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1962.62% |
| and_fprm_linear_parity | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.67% |
| and_fprm_linear_parity | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.53% |
| and_fprm_linear_parity | external_abc_xag | T | 32 | 32 | 0 | 0 | -94.79% |
| and_fprm_linear_parity | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -93.82% |
| and_fprm_linear_parity | external_abc_xag | depth | 32 | 6 | 26 | 0 | +1424.61% |
| and_fprm_linear_parity | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.81% |
| and_fprm_linear_parity | external_abc_xag | score | 32 | 32 | 0 | 0 | -96.28% |
| and_fprm_linear_parity | external_bdd | T | 32 | 32 | 0 | 0 | -94.06% |
| and_fprm_linear_parity | external_bdd | CNOT | 32 | 32 | 0 | 0 | -94.08% |
| and_fprm_linear_parity | external_bdd | depth | 32 | 32 | 0 | 0 | -94.73% |
| and_fprm_linear_parity | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.66% |
| and_fprm_linear_parity | external_bdd | score | 32 | 32 | 0 | 0 | -94.69% |
| and_fprm_greedy | external_abc_aig | T | 32 | 32 | 0 | 0 | -91.69% |
| and_fprm_greedy | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.22% |
| and_fprm_greedy | external_abc_aig | depth | 32 | 7 | 25 | 0 | +2012.55% |
| and_fprm_greedy | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| and_fprm_greedy | external_abc_aig | score | 32 | 32 | 0 | 0 | -94.33% |
| and_fprm_greedy | external_abc_xag | T | 32 | 32 | 0 | 0 | -94.44% |
| and_fprm_greedy | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -93.64% |
| and_fprm_greedy | external_abc_xag | depth | 32 | 6 | 26 | 0 | +1461.89% |
| and_fprm_greedy | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| and_fprm_greedy | external_abc_xag | score | 32 | 32 | 0 | 0 | -96.13% |
| and_fprm_greedy | external_bdd | T | 32 | 32 | 0 | 0 | -93.81% |
| and_fprm_greedy | external_bdd | CNOT | 32 | 32 | 0 | 0 | -93.92% |
| and_fprm_greedy | external_bdd | depth | 32 | 32 | 0 | 0 | -94.70% |
| and_fprm_greedy | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.95% |
| and_fprm_greedy | external_bdd | score | 32 | 32 | 0 | 0 | -94.51% |
| direct_anf | external_abc_aig | T | 32 | 32 | 0 | 0 | -81.88% |
| direct_anf | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -94.97% |
| direct_anf | external_abc_aig | depth | 32 | 7 | 25 | 0 | +1747.48% |
| direct_anf | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| direct_anf | external_abc_aig | score | 32 | 32 | 0 | 0 | -88.33% |
| direct_anf | external_abc_xag | T | 32 | 32 | 0 | 0 | -86.60% |
| direct_anf | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -94.46% |
| direct_anf | external_abc_xag | depth | 32 | 6 | 26 | 0 | +1268.24% |
| direct_anf | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| direct_anf | external_abc_xag | score | 32 | 32 | 0 | 0 | -91.19% |
| direct_anf | external_bdd | T | 32 | 32 | 0 | 0 | -82.70% |
| direct_anf | external_bdd | CNOT | 32 | 32 | 0 | 0 | -94.66% |
| direct_anf | external_bdd | depth | 32 | 32 | 0 | 0 | -95.34% |
| direct_anf | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.97% |
| direct_anf | external_bdd | score | 32 | 32 | 0 | 0 | -85.62% |
| and_direct_anf | external_abc_aig | T | 32 | 32 | 0 | 0 | -88.99% |
| and_direct_anf | external_abc_aig | CNOT | 32 | 32 | 0 | 0 | -92.79% |
| and_direct_anf | external_abc_aig | depth | 32 | 7 | 25 | 0 | +2998.21% |
| and_direct_anf | external_abc_aig | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| and_direct_anf | external_abc_aig | score | 32 | 32 | 0 | 0 | -92.53% |
| and_direct_anf | external_abc_xag | T | 32 | 32 | 0 | 0 | -92.29% |
| and_direct_anf | external_abc_xag | CNOT | 32 | 32 | 0 | 0 | -91.74% |
| and_direct_anf | external_abc_xag | depth | 32 | 6 | 26 | 0 | +2177.51% |
| and_direct_anf | external_abc_xag | peak_ancilla | 32 | 32 | 0 | 0 | -99.99% |
| and_direct_anf | external_abc_xag | score | 32 | 32 | 0 | 0 | -94.65% |
| and_direct_anf | external_bdd | T | 32 | 32 | 0 | 0 | -90.76% |
| and_direct_anf | external_bdd | CNOT | 32 | 32 | 0 | 0 | -91.62% |
| and_direct_anf | external_bdd | depth | 32 | 32 | 0 | 0 | -92.68% |
| and_direct_anf | external_bdd | peak_ancilla | 32 | 32 | 0 | 0 | -99.95% |
| and_direct_anf | external_bdd | score | 32 | 32 | 0 | 0 | -91.86% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
