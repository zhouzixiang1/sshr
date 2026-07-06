# External Baseline Analysis

External rows: 96; usable: 96.
Internal rows: 144; usable: 144.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_abc_aig | 16 | 24 | 113742.17 | 284356.42 | 183128.96 | 1.269 |
| external_abc_lut | 16 | 24 | 649014.00 | 1101490.58 | 740149.73 | 1.084 |
| external_abc_xag | 16 | 24 | 143405.83 | 215318.08 | 224654.34 | 0.804 |
| external_bdd | 16 | 24 | 95484.67 | 167226.33 | 118064.57 | 3.047 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_abc_aig | T | 24 | 24 | 0 | 0 | -96.05% |
| and_resource_nmcts | external_abc_aig | CNOT | 24 | 24 | 0 | 0 | -97.24% |
| and_resource_nmcts | external_abc_aig | depth | 24 | 2 | 22 | 0 | +2171.79% |
| and_resource_nmcts | external_abc_aig | peak_ancilla | 24 | 24 | 0 | 0 | -99.96% |
| and_resource_nmcts | external_abc_aig | score | 24 | 24 | 0 | 0 | -97.29% |
| and_resource_nmcts | external_abc_lut | T | 24 | 24 | 0 | 0 | -98.94% |
| and_resource_nmcts | external_abc_lut | CNOT | 24 | 24 | 0 | 0 | -98.95% |
| and_resource_nmcts | external_abc_lut | depth | 24 | 24 | 0 | 0 | -98.97% |
| and_resource_nmcts | external_abc_lut | peak_ancilla | 24 | 24 | 0 | 0 | -99.90% |
| and_resource_nmcts | external_abc_lut | score | 24 | 24 | 0 | 0 | -99.00% |
| and_resource_nmcts | external_abc_xag | T | 24 | 24 | 0 | 0 | -96.98% |
| and_resource_nmcts | external_abc_xag | CNOT | 24 | 24 | 0 | 0 | -96.52% |
| and_resource_nmcts | external_abc_xag | depth | 24 | 2 | 22 | 0 | +1453.24% |
| and_resource_nmcts | external_abc_xag | peak_ancilla | 24 | 24 | 0 | 0 | -99.97% |
| and_resource_nmcts | external_abc_xag | score | 24 | 24 | 0 | 0 | -97.88% |
| and_resource_nmcts | external_bdd | T | 24 | 24 | 0 | 0 | -96.42% |
| and_resource_nmcts | external_bdd | CNOT | 24 | 24 | 0 | 0 | -96.45% |
| and_resource_nmcts | external_bdd | depth | 24 | 24 | 0 | 0 | -96.90% |
| and_resource_nmcts | external_bdd | peak_ancilla | 24 | 24 | 0 | 0 | -99.91% |
| and_resource_nmcts | external_bdd | score | 24 | 24 | 0 | 0 | -96.81% |
| and_profile_resource_nmcts | external_abc_aig | T | 24 | 24 | 0 | 0 | -96.05% |
| and_profile_resource_nmcts | external_abc_aig | CNOT | 24 | 24 | 0 | 0 | -97.24% |
| and_profile_resource_nmcts | external_abc_aig | depth | 24 | 2 | 22 | 0 | +2171.79% |
| and_profile_resource_nmcts | external_abc_aig | peak_ancilla | 24 | 24 | 0 | 0 | -99.96% |
| and_profile_resource_nmcts | external_abc_aig | score | 24 | 24 | 0 | 0 | -97.29% |
| and_profile_resource_nmcts | external_abc_lut | T | 24 | 24 | 0 | 0 | -98.94% |
| and_profile_resource_nmcts | external_abc_lut | CNOT | 24 | 24 | 0 | 0 | -98.95% |
| and_profile_resource_nmcts | external_abc_lut | depth | 24 | 24 | 0 | 0 | -98.97% |
| and_profile_resource_nmcts | external_abc_lut | peak_ancilla | 24 | 24 | 0 | 0 | -99.90% |
| and_profile_resource_nmcts | external_abc_lut | score | 24 | 24 | 0 | 0 | -99.00% |
| and_profile_resource_nmcts | external_abc_xag | T | 24 | 24 | 0 | 0 | -96.98% |
| and_profile_resource_nmcts | external_abc_xag | CNOT | 24 | 24 | 0 | 0 | -96.52% |
| and_profile_resource_nmcts | external_abc_xag | depth | 24 | 2 | 22 | 0 | +1453.24% |
| and_profile_resource_nmcts | external_abc_xag | peak_ancilla | 24 | 24 | 0 | 0 | -99.97% |
| and_profile_resource_nmcts | external_abc_xag | score | 24 | 24 | 0 | 0 | -97.88% |
| and_profile_resource_nmcts | external_bdd | T | 24 | 24 | 0 | 0 | -96.42% |
| and_profile_resource_nmcts | external_bdd | CNOT | 24 | 24 | 0 | 0 | -96.45% |
| and_profile_resource_nmcts | external_bdd | depth | 24 | 24 | 0 | 0 | -96.90% |
| and_profile_resource_nmcts | external_bdd | peak_ancilla | 24 | 24 | 0 | 0 | -99.91% |
| and_profile_resource_nmcts | external_bdd | score | 24 | 24 | 0 | 0 | -96.81% |
| and_fprm_linear_pair | external_abc_aig | T | 24 | 24 | 0 | 0 | -96.05% |
| and_fprm_linear_pair | external_abc_aig | CNOT | 24 | 24 | 0 | 0 | -97.24% |
| and_fprm_linear_pair | external_abc_aig | depth | 24 | 2 | 22 | 0 | +2171.79% |
| and_fprm_linear_pair | external_abc_aig | peak_ancilla | 24 | 24 | 0 | 0 | -99.96% |
| and_fprm_linear_pair | external_abc_aig | score | 24 | 24 | 0 | 0 | -97.29% |
| and_fprm_linear_pair | external_abc_lut | T | 24 | 24 | 0 | 0 | -98.94% |
| and_fprm_linear_pair | external_abc_lut | CNOT | 24 | 24 | 0 | 0 | -98.95% |
| and_fprm_linear_pair | external_abc_lut | depth | 24 | 24 | 0 | 0 | -98.97% |
| and_fprm_linear_pair | external_abc_lut | peak_ancilla | 24 | 24 | 0 | 0 | -99.90% |
| and_fprm_linear_pair | external_abc_lut | score | 24 | 24 | 0 | 0 | -99.00% |
| and_fprm_linear_pair | external_abc_xag | T | 24 | 24 | 0 | 0 | -96.98% |
| and_fprm_linear_pair | external_abc_xag | CNOT | 24 | 24 | 0 | 0 | -96.52% |
| and_fprm_linear_pair | external_abc_xag | depth | 24 | 2 | 22 | 0 | +1453.24% |
| and_fprm_linear_pair | external_abc_xag | peak_ancilla | 24 | 24 | 0 | 0 | -99.97% |
| and_fprm_linear_pair | external_abc_xag | score | 24 | 24 | 0 | 0 | -97.88% |
| and_fprm_linear_pair | external_bdd | T | 24 | 24 | 0 | 0 | -96.42% |
| and_fprm_linear_pair | external_bdd | CNOT | 24 | 24 | 0 | 0 | -96.45% |
| and_fprm_linear_pair | external_bdd | depth | 24 | 24 | 0 | 0 | -96.90% |
| and_fprm_linear_pair | external_bdd | peak_ancilla | 24 | 24 | 0 | 0 | -99.91% |
| and_fprm_linear_pair | external_bdd | score | 24 | 24 | 0 | 0 | -96.81% |
| and_fprm_root_beam | external_abc_aig | T | 24 | 24 | 0 | 0 | -95.95% |
| and_fprm_root_beam | external_abc_aig | CNOT | 24 | 24 | 0 | 0 | -97.18% |
| and_fprm_root_beam | external_abc_aig | depth | 24 | 2 | 22 | 0 | +2211.04% |
| and_fprm_root_beam | external_abc_aig | peak_ancilla | 24 | 24 | 0 | 0 | -99.99% |
| and_fprm_root_beam | external_abc_aig | score | 24 | 24 | 0 | 0 | -97.23% |
| and_fprm_root_beam | external_abc_lut | T | 24 | 24 | 0 | 0 | -98.92% |
| and_fprm_root_beam | external_abc_lut | CNOT | 24 | 24 | 0 | 0 | -98.93% |
| and_fprm_root_beam | external_abc_lut | depth | 24 | 24 | 0 | 0 | -98.95% |
| and_fprm_root_beam | external_abc_lut | peak_ancilla | 24 | 24 | 0 | 0 | -99.98% |
| and_fprm_root_beam | external_abc_lut | score | 24 | 24 | 0 | 0 | -98.99% |
| and_fprm_root_beam | external_abc_xag | T | 24 | 24 | 0 | 0 | -96.90% |
| and_fprm_root_beam | external_abc_xag | CNOT | 24 | 24 | 0 | 0 | -96.44% |
| and_fprm_root_beam | external_abc_xag | depth | 24 | 2 | 22 | 0 | +1480.09% |
| and_fprm_root_beam | external_abc_xag | peak_ancilla | 24 | 24 | 0 | 0 | -99.99% |
| and_fprm_root_beam | external_abc_xag | score | 24 | 24 | 0 | 0 | -97.84% |
| and_fprm_root_beam | external_bdd | T | 24 | 24 | 0 | 0 | -96.34% |
| and_fprm_root_beam | external_bdd | CNOT | 24 | 24 | 0 | 0 | -96.38% |
| and_fprm_root_beam | external_bdd | depth | 24 | 24 | 0 | 0 | -96.84% |
| and_fprm_root_beam | external_bdd | peak_ancilla | 24 | 24 | 0 | 0 | -99.96% |
| and_fprm_root_beam | external_bdd | score | 24 | 24 | 0 | 0 | -96.75% |
| direct_anf | external_abc_aig | T | 24 | 24 | 0 | 0 | -90.11% |
| direct_anf | external_abc_aig | CNOT | 24 | 24 | 0 | 0 | -97.58% |
| direct_anf | external_abc_aig | depth | 24 | 2 | 22 | 0 | +1863.67% |
| direct_anf | external_abc_aig | peak_ancilla | 24 | 24 | 0 | 0 | -100.00% |
| direct_anf | external_abc_aig | score | 24 | 24 | 0 | 0 | -93.65% |
| direct_anf | external_abc_lut | T | 24 | 24 | 0 | 0 | -97.89% |
| direct_anf | external_abc_lut | CNOT | 24 | 24 | 0 | 0 | -99.08% |
| direct_anf | external_abc_lut | depth | 24 | 24 | 0 | 0 | -99.10% |
| direct_anf | external_abc_lut | peak_ancilla | 24 | 24 | 0 | 0 | -99.99% |
| direct_anf | external_abc_lut | score | 24 | 24 | 0 | 0 | -98.10% |
| direct_anf | external_abc_xag | T | 24 | 24 | 0 | 0 | -92.25% |
| direct_anf | external_abc_xag | CNOT | 24 | 24 | 0 | 0 | -96.95% |
| direct_anf | external_abc_xag | depth | 24 | 2 | 22 | 0 | +1249.21% |
| direct_anf | external_abc_xag | peak_ancilla | 24 | 24 | 0 | 0 | -100.00% |
| direct_anf | external_abc_xag | score | 24 | 24 | 0 | 0 | -94.91% |
| direct_anf | external_bdd | T | 24 | 24 | 0 | 0 | -89.64% |
| direct_anf | external_bdd | CNOT | 24 | 24 | 0 | 0 | -96.88% |
| direct_anf | external_bdd | depth | 24 | 24 | 0 | 0 | -97.27% |
| direct_anf | external_bdd | peak_ancilla | 24 | 24 | 0 | 0 | -99.98% |
| direct_anf | external_bdd | score | 24 | 24 | 0 | 0 | -91.39% |
| and_direct_anf | external_abc_aig | T | 24 | 24 | 0 | 0 | -94.38% |
| and_direct_anf | external_abc_aig | CNOT | 24 | 24 | 0 | 0 | -96.37% |
| and_direct_anf | external_abc_aig | depth | 24 | 2 | 22 | 0 | +3214.93% |
| and_direct_anf | external_abc_aig | peak_ancilla | 24 | 24 | 0 | 0 | -99.99% |
| and_direct_anf | external_abc_aig | score | 24 | 24 | 0 | 0 | -96.18% |
| and_direct_anf | external_abc_lut | T | 24 | 24 | 0 | 0 | -98.64% |
| and_direct_anf | external_abc_lut | CNOT | 24 | 24 | 0 | 0 | -98.72% |
| and_direct_anf | external_abc_lut | depth | 24 | 24 | 0 | 0 | -98.74% |
| and_direct_anf | external_abc_lut | peak_ancilla | 24 | 24 | 0 | 0 | -99.98% |
| and_direct_anf | external_abc_lut | score | 24 | 24 | 0 | 0 | -98.72% |
| and_direct_anf | external_abc_xag | T | 24 | 24 | 0 | 0 | -95.65% |
| and_direct_anf | external_abc_xag | CNOT | 24 | 24 | 0 | 0 | -95.37% |
| and_direct_anf | external_abc_xag | depth | 24 | 2 | 22 | 0 | +2158.13% |
| and_direct_anf | external_abc_xag | peak_ancilla | 24 | 24 | 0 | 0 | -99.99% |
| and_direct_anf | external_abc_xag | score | 24 | 24 | 0 | 0 | -96.98% |
| and_direct_anf | external_bdd | T | 24 | 24 | 0 | 0 | -94.54% |
| and_direct_anf | external_bdd | CNOT | 24 | 24 | 0 | 0 | -95.06% |
| and_direct_anf | external_bdd | depth | 24 | 24 | 0 | 0 | -95.69% |
| and_direct_anf | external_bdd | peak_ancilla | 24 | 24 | 0 | 0 | -99.96% |
| and_direct_anf | external_bdd | score | 24 | 24 | 0 | 0 | -95.19% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
