# External Baseline Analysis

External rows: 48; usable: 48.
Internal rows: 84; usable: 84.

## External Summary

| method | n | functions | mean T | mean CNOT | mean score | mean time s |
|---|---:|---:|---:|---:|---:|---:|
| external_abc_aig | 18 | 12 | 404488.67 | 1011222.67 | 651231.24 | 10.102 |
| external_abc_lut | 18 | 12 | 2334208.67 | 3953442.67 | 2661190.63 | 9.538 |
| external_abc_xag | 18 | 12 | 510997.33 | 766749.50 | 799984.00 | 8.647 |
| external_bdd | 18 | 12 | 330043.33 | 577771.17 | 407822.95 | 40.668 |

## Pairwise Comparisons on Common Functions

| target | external baseline | metric | functions | wins | losses | ties | mean relative |
|---|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_abc_aig | T | 12 | 12 | 0 | 0 | -98.34% |
| and_resource_nmcts | external_abc_aig | CNOT | 12 | 12 | 0 | 0 | -98.81% |
| and_resource_nmcts | external_abc_aig | depth | 12 | 2 | 10 | 0 | +3367.66% |
| and_resource_nmcts | external_abc_aig | peak_ancilla | 12 | 12 | 0 | 0 | -99.96% |
| and_resource_nmcts | external_abc_aig | score | 12 | 12 | 0 | 0 | -98.85% |
| and_resource_nmcts | external_abc_lut | T | 12 | 12 | 0 | 0 | -99.68% |
| and_resource_nmcts | external_abc_lut | CNOT | 12 | 12 | 0 | 0 | -99.66% |
| and_resource_nmcts | external_abc_lut | depth | 12 | 12 | 0 | 0 | -99.65% |
| and_resource_nmcts | external_abc_lut | peak_ancilla | 12 | 12 | 0 | 0 | -99.89% |
| and_resource_nmcts | external_abc_lut | score | 12 | 12 | 0 | 0 | -99.69% |
| and_resource_nmcts | external_abc_xag | T | 12 | 12 | 0 | 0 | -98.67% |
| and_resource_nmcts | external_abc_xag | CNOT | 12 | 12 | 0 | 0 | -98.42% |
| and_resource_nmcts | external_abc_xag | depth | 12 | 2 | 10 | 0 | +1555.41% |
| and_resource_nmcts | external_abc_xag | peak_ancilla | 12 | 12 | 0 | 0 | -99.97% |
| and_resource_nmcts | external_abc_xag | score | 12 | 12 | 0 | 0 | -99.05% |
| and_resource_nmcts | external_bdd | T | 12 | 12 | 0 | 0 | -98.12% |
| and_resource_nmcts | external_bdd | CNOT | 12 | 12 | 0 | 0 | -98.08% |
| and_resource_nmcts | external_bdd | depth | 12 | 12 | 0 | 0 | -98.27% |
| and_resource_nmcts | external_bdd | peak_ancilla | 12 | 12 | 0 | 0 | -99.83% |
| and_resource_nmcts | external_bdd | score | 12 | 12 | 0 | 0 | -98.30% |
| and_profile_resource_nmcts | external_abc_aig | T | 12 | 12 | 0 | 0 | -98.34% |
| and_profile_resource_nmcts | external_abc_aig | CNOT | 12 | 12 | 0 | 0 | -98.81% |
| and_profile_resource_nmcts | external_abc_aig | depth | 12 | 2 | 10 | 0 | +3367.66% |
| and_profile_resource_nmcts | external_abc_aig | peak_ancilla | 12 | 12 | 0 | 0 | -99.96% |
| and_profile_resource_nmcts | external_abc_aig | score | 12 | 12 | 0 | 0 | -98.85% |
| and_profile_resource_nmcts | external_abc_lut | T | 12 | 12 | 0 | 0 | -99.68% |
| and_profile_resource_nmcts | external_abc_lut | CNOT | 12 | 12 | 0 | 0 | -99.66% |
| and_profile_resource_nmcts | external_abc_lut | depth | 12 | 12 | 0 | 0 | -99.65% |
| and_profile_resource_nmcts | external_abc_lut | peak_ancilla | 12 | 12 | 0 | 0 | -99.89% |
| and_profile_resource_nmcts | external_abc_lut | score | 12 | 12 | 0 | 0 | -99.69% |
| and_profile_resource_nmcts | external_abc_xag | T | 12 | 12 | 0 | 0 | -98.67% |
| and_profile_resource_nmcts | external_abc_xag | CNOT | 12 | 12 | 0 | 0 | -98.42% |
| and_profile_resource_nmcts | external_abc_xag | depth | 12 | 2 | 10 | 0 | +1555.41% |
| and_profile_resource_nmcts | external_abc_xag | peak_ancilla | 12 | 12 | 0 | 0 | -99.97% |
| and_profile_resource_nmcts | external_abc_xag | score | 12 | 12 | 0 | 0 | -99.05% |
| and_profile_resource_nmcts | external_bdd | T | 12 | 12 | 0 | 0 | -98.12% |
| and_profile_resource_nmcts | external_bdd | CNOT | 12 | 12 | 0 | 0 | -98.08% |
| and_profile_resource_nmcts | external_bdd | depth | 12 | 12 | 0 | 0 | -98.27% |
| and_profile_resource_nmcts | external_bdd | peak_ancilla | 12 | 12 | 0 | 0 | -99.83% |
| and_profile_resource_nmcts | external_bdd | score | 12 | 12 | 0 | 0 | -98.30% |
| and_pareto_resource_nmcts | external_abc_aig | T | 12 | 12 | 0 | 0 | -98.34% |
| and_pareto_resource_nmcts | external_abc_aig | CNOT | 12 | 12 | 0 | 0 | -98.81% |
| and_pareto_resource_nmcts | external_abc_aig | depth | 12 | 2 | 10 | 0 | +3367.66% |
| and_pareto_resource_nmcts | external_abc_aig | peak_ancilla | 12 | 12 | 0 | 0 | -99.96% |
| and_pareto_resource_nmcts | external_abc_aig | score | 12 | 12 | 0 | 0 | -98.85% |
| and_pareto_resource_nmcts | external_abc_lut | T | 12 | 12 | 0 | 0 | -99.68% |
| and_pareto_resource_nmcts | external_abc_lut | CNOT | 12 | 12 | 0 | 0 | -99.66% |
| and_pareto_resource_nmcts | external_abc_lut | depth | 12 | 12 | 0 | 0 | -99.65% |
| and_pareto_resource_nmcts | external_abc_lut | peak_ancilla | 12 | 12 | 0 | 0 | -99.89% |
| and_pareto_resource_nmcts | external_abc_lut | score | 12 | 12 | 0 | 0 | -99.69% |
| and_pareto_resource_nmcts | external_abc_xag | T | 12 | 12 | 0 | 0 | -98.67% |
| and_pareto_resource_nmcts | external_abc_xag | CNOT | 12 | 12 | 0 | 0 | -98.42% |
| and_pareto_resource_nmcts | external_abc_xag | depth | 12 | 2 | 10 | 0 | +1555.41% |
| and_pareto_resource_nmcts | external_abc_xag | peak_ancilla | 12 | 12 | 0 | 0 | -99.97% |
| and_pareto_resource_nmcts | external_abc_xag | score | 12 | 12 | 0 | 0 | -99.05% |
| and_pareto_resource_nmcts | external_bdd | T | 12 | 12 | 0 | 0 | -98.12% |
| and_pareto_resource_nmcts | external_bdd | CNOT | 12 | 12 | 0 | 0 | -98.08% |
| and_pareto_resource_nmcts | external_bdd | depth | 12 | 12 | 0 | 0 | -98.27% |
| and_pareto_resource_nmcts | external_bdd | peak_ancilla | 12 | 12 | 0 | 0 | -99.83% |
| and_pareto_resource_nmcts | external_bdd | score | 12 | 12 | 0 | 0 | -98.30% |
| and_fprm_linear_pair_fast | external_abc_aig | T | 12 | 12 | 0 | 0 | -98.27% |
| and_fprm_linear_pair_fast | external_abc_aig | CNOT | 12 | 12 | 0 | 0 | -98.77% |
| and_fprm_linear_pair_fast | external_abc_aig | depth | 12 | 2 | 10 | 0 | +3424.28% |
| and_fprm_linear_pair_fast | external_abc_aig | peak_ancilla | 12 | 12 | 0 | 0 | -99.96% |
| and_fprm_linear_pair_fast | external_abc_aig | score | 12 | 12 | 0 | 0 | -98.80% |
| and_fprm_linear_pair_fast | external_abc_lut | T | 12 | 12 | 0 | 0 | -99.66% |
| and_fprm_linear_pair_fast | external_abc_lut | CNOT | 12 | 12 | 0 | 0 | -99.65% |
| and_fprm_linear_pair_fast | external_abc_lut | depth | 12 | 12 | 0 | 0 | -99.64% |
| and_fprm_linear_pair_fast | external_abc_lut | peak_ancilla | 12 | 12 | 0 | 0 | -99.89% |
| and_fprm_linear_pair_fast | external_abc_lut | score | 12 | 12 | 0 | 0 | -99.67% |
| and_fprm_linear_pair_fast | external_abc_xag | T | 12 | 12 | 0 | 0 | -98.61% |
| and_fprm_linear_pair_fast | external_abc_xag | CNOT | 12 | 12 | 0 | 0 | -98.37% |
| and_fprm_linear_pair_fast | external_abc_xag | depth | 12 | 2 | 10 | 0 | +1583.18% |
| and_fprm_linear_pair_fast | external_abc_xag | peak_ancilla | 12 | 12 | 0 | 0 | -99.97% |
| and_fprm_linear_pair_fast | external_abc_xag | score | 12 | 12 | 0 | 0 | -99.01% |
| and_fprm_linear_pair_fast | external_bdd | T | 12 | 12 | 0 | 0 | -98.04% |
| and_fprm_linear_pair_fast | external_bdd | CNOT | 12 | 12 | 0 | 0 | -98.03% |
| and_fprm_linear_pair_fast | external_bdd | depth | 12 | 12 | 0 | 0 | -98.21% |
| and_fprm_linear_pair_fast | external_bdd | peak_ancilla | 12 | 12 | 0 | 0 | -99.83% |
| and_fprm_linear_pair_fast | external_bdd | score | 12 | 12 | 0 | 0 | -98.23% |
| and_fprm_root_beam | external_abc_aig | T | 12 | 12 | 0 | 0 | -98.19% |
| and_fprm_root_beam | external_abc_aig | CNOT | 12 | 12 | 0 | 0 | -98.74% |
| and_fprm_root_beam | external_abc_aig | depth | 12 | 2 | 10 | 0 | +3429.31% |
| and_fprm_root_beam | external_abc_aig | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| and_fprm_root_beam | external_abc_aig | score | 12 | 12 | 0 | 0 | -98.76% |
| and_fprm_root_beam | external_abc_lut | T | 12 | 12 | 0 | 0 | -99.65% |
| and_fprm_root_beam | external_abc_lut | CNOT | 12 | 12 | 0 | 0 | -99.64% |
| and_fprm_root_beam | external_abc_lut | depth | 12 | 12 | 0 | 0 | -99.64% |
| and_fprm_root_beam | external_abc_lut | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| and_fprm_root_beam | external_abc_lut | score | 12 | 12 | 0 | 0 | -99.66% |
| and_fprm_root_beam | external_abc_xag | T | 12 | 12 | 0 | 0 | -98.55% |
| and_fprm_root_beam | external_abc_xag | CNOT | 12 | 12 | 0 | 0 | -98.33% |
| and_fprm_root_beam | external_abc_xag | depth | 12 | 1 | 11 | 0 | +1586.42% |
| and_fprm_root_beam | external_abc_xag | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| and_fprm_root_beam | external_abc_xag | score | 12 | 12 | 0 | 0 | -98.98% |
| and_fprm_root_beam | external_bdd | T | 12 | 12 | 0 | 0 | -97.97% |
| and_fprm_root_beam | external_bdd | CNOT | 12 | 12 | 0 | 0 | -97.99% |
| and_fprm_root_beam | external_bdd | depth | 12 | 12 | 0 | 0 | -98.24% |
| and_fprm_root_beam | external_bdd | peak_ancilla | 12 | 12 | 0 | 0 | -99.99% |
| and_fprm_root_beam | external_bdd | score | 12 | 12 | 0 | 0 | -98.19% |
| direct_anf | external_abc_aig | T | 12 | 12 | 0 | 0 | -95.48% |
| direct_anf | external_abc_aig | CNOT | 12 | 12 | 0 | 0 | -98.93% |
| direct_anf | external_abc_aig | depth | 12 | 2 | 10 | 0 | +2885.32% |
| direct_anf | external_abc_aig | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| direct_anf | external_abc_aig | score | 12 | 12 | 0 | 0 | -97.10% |
| direct_anf | external_abc_lut | T | 12 | 12 | 0 | 0 | -99.18% |
| direct_anf | external_abc_lut | CNOT | 12 | 12 | 0 | 0 | -99.69% |
| direct_anf | external_abc_lut | depth | 12 | 12 | 0 | 0 | -99.70% |
| direct_anf | external_abc_lut | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| direct_anf | external_abc_lut | score | 12 | 12 | 0 | 0 | -99.25% |
| direct_anf | external_abc_xag | T | 12 | 12 | 0 | 0 | -96.40% |
| direct_anf | external_abc_xag | CNOT | 12 | 12 | 0 | 0 | -98.57% |
| direct_anf | external_abc_xag | depth | 12 | 2 | 10 | 0 | +1325.59% |
| direct_anf | external_abc_xag | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| direct_anf | external_abc_xag | score | 12 | 12 | 0 | 0 | -97.63% |
| direct_anf | external_bdd | T | 12 | 12 | 0 | 0 | -94.80% |
| direct_anf | external_bdd | CNOT | 12 | 12 | 0 | 0 | -98.29% |
| direct_anf | external_bdd | depth | 12 | 12 | 0 | 0 | -98.50% |
| direct_anf | external_bdd | peak_ancilla | 12 | 12 | 0 | 0 | -99.99% |
| direct_anf | external_bdd | score | 12 | 12 | 0 | 0 | -95.66% |
| and_direct_anf | external_abc_aig | T | 12 | 12 | 0 | 0 | -97.46% |
| and_direct_anf | external_abc_aig | CNOT | 12 | 12 | 0 | 0 | -98.36% |
| and_direct_anf | external_abc_aig | depth | 12 | 2 | 10 | 0 | +5027.98% |
| and_direct_anf | external_abc_aig | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| and_direct_anf | external_abc_aig | score | 12 | 12 | 0 | 0 | -98.27% |
| and_direct_anf | external_abc_lut | T | 12 | 12 | 0 | 0 | -99.52% |
| and_direct_anf | external_abc_lut | CNOT | 12 | 12 | 0 | 0 | -99.54% |
| and_direct_anf | external_abc_lut | depth | 12 | 12 | 0 | 0 | -99.55% |
| and_direct_anf | external_abc_lut | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| and_direct_anf | external_abc_lut | score | 12 | 12 | 0 | 0 | -99.54% |
| and_direct_anf | external_abc_xag | T | 12 | 12 | 0 | 0 | -97.97% |
| and_direct_anf | external_abc_xag | CNOT | 12 | 12 | 0 | 0 | -97.82% |
| and_direct_anf | external_abc_xag | depth | 12 | 1 | 11 | 0 | +2335.75% |
| and_direct_anf | external_abc_xag | peak_ancilla | 12 | 12 | 0 | 0 | -100.00% |
| and_direct_anf | external_abc_xag | score | 12 | 12 | 0 | 0 | -98.58% |
| and_direct_anf | external_bdd | T | 12 | 12 | 0 | 0 | -97.11% |
| and_direct_anf | external_bdd | CNOT | 12 | 12 | 0 | 0 | -97.35% |
| and_direct_anf | external_bdd | depth | 12 | 12 | 0 | 0 | -97.68% |
| and_direct_anf | external_bdd | peak_ancilla | 12 | 12 | 0 | 0 | -99.99% |
| and_direct_anf | external_bdd | score | 12 | 12 | 0 | 0 | -97.44% |

## External Baseline Error/Skip Rows

| function | n | method | skipped | error |
|---|---:|---|---|---|
