# CirKit AIG Multiplicative-Complexity Probe

Scope: ABC converts each exported BLIF into AIGER; official CirKit 3 shell reads the AIG, applies the selected AIG optimization flow, reports `mccost -a`, and writes Verilog that is read back by ABC for truth-table verification.

This is a CirKit-shell AIG/MC probe, not legacy RevKit reversible synthesis, not the full ROS flow, and not hardware mapping.

- CirKit checkout: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit`
- CirKit commit: `4531533394725864a304e710d82087ff74fbe801`
- CirKit binary: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit/build/cli/cirkit`
- rows attempted: 64
- usable rows: 64
- correct rows: 64
- error rows: 0
- timeout rows: 0

## Comparisons

| Target | Baseline | Metric | Items | W/L/T | Mean relative | Median relative |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_cirkit_aig_mc | score | 64 | 64/0/0 | -94.42% | -96.08% |
| and_resource_nmcts | external_cirkit_aig_mc | T | 64 | 64/0/0 | -92.19% | -94.56% |
| and_resource_nmcts | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -90.65% | -93.24% |
| and_resource_nmcts | external_cirkit_aig_mc | depth | 64 | 14/50/0 | +1171.09% | +623.12% |
| and_resource_nmcts | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.81% | -99.95% |
| and_profile_resource_nmcts | external_cirkit_aig_mc | score | 64 | 64/0/0 | -94.42% | -96.08% |
| and_profile_resource_nmcts | external_cirkit_aig_mc | T | 64 | 64/0/0 | -92.19% | -94.56% |
| and_profile_resource_nmcts | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -90.65% | -93.24% |
| and_profile_resource_nmcts | external_cirkit_aig_mc | depth | 64 | 14/50/0 | +1171.09% | +623.12% |
| and_profile_resource_nmcts | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.81% | -99.95% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | score | 64 | 64/0/0 | -94.46% | -96.10% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | T | 64 | 64/0/0 | -92.24% | -94.66% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -90.72% | -93.24% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | depth | 64 | 14/50/0 | +1170.71% | +623.12% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.81% | -99.95% |
| and_fprm_linear_pair | external_cirkit_aig_mc | score | 64 | 64/0/0 | -94.27% | -95.87% |
| and_fprm_linear_pair | external_cirkit_aig_mc | T | 64 | 64/0/0 | -91.97% | -94.31% |
| and_fprm_linear_pair | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -90.51% | -93.02% |
| and_fprm_linear_pair | external_cirkit_aig_mc | depth | 64 | 14/50/0 | +1192.26% | +636.33% |
| and_fprm_linear_pair | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.81% | -99.96% |
| and_fprm_root_beam | external_cirkit_aig_mc | score | 64 | 64/0/0 | -94.11% | -95.76% |
| and_fprm_root_beam | external_cirkit_aig_mc | T | 64 | 64/0/0 | -91.64% | -93.98% |
| and_fprm_root_beam | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -90.25% | -92.96% |
| and_fprm_root_beam | external_cirkit_aig_mc | depth | 64 | 14/50/0 | +1224.16% | +654.32% |
| and_fprm_root_beam | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.97% | -99.97% |
| and_fprm_greedy | external_cirkit_aig_mc | score | 64 | 64/0/0 | -94.08% | -95.74% |
| and_fprm_greedy | external_cirkit_aig_mc | T | 64 | 64/0/0 | -91.60% | -93.96% |
| and_fprm_greedy | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -90.23% | -92.96% |
| and_fprm_greedy | external_cirkit_aig_mc | depth | 64 | 14/50/0 | +1227.02% | +658.81% |
| and_fprm_greedy | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.97% | -99.97% |
| and_affine_greedy | external_cirkit_aig_mc | score | 64 | 64/0/0 | -94.08% | -95.74% |
| and_affine_greedy | external_cirkit_aig_mc | T | 64 | 64/0/0 | -91.60% | -93.96% |
| and_affine_greedy | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -90.23% | -92.96% |
| and_affine_greedy | external_cirkit_aig_mc | depth | 64 | 14/50/0 | +1227.02% | +658.81% |
| and_affine_greedy | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.97% | -99.97% |
| and_direct_anf | external_cirkit_aig_mc | score | 64 | 64/0/0 | -91.76% | -94.02% |
| and_direct_anf | external_cirkit_aig_mc | T | 64 | 64/0/0 | -88.23% | -91.48% |
| and_direct_anf | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -87.31% | -90.76% |
| and_direct_anf | external_cirkit_aig_mc | depth | 64 | 13/51/0 | +1808.92% | +922.08% |
| and_direct_anf | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.97% | -99.97% |
| direct_anf | external_cirkit_aig_mc | score | 64 | 64/0/0 | -86.22% | -92.21% |
| direct_anf | external_cirkit_aig_mc | T | 64 | 64/0/0 | -79.15% | -88.32% |
| direct_anf | external_cirkit_aig_mc | CNOT | 64 | 64/0/0 | -91.47% | -94.08% |
| direct_anf | external_cirkit_aig_mc | depth | 64 | 13/51/0 | +1057.97% | +526.88% |
| direct_anf | external_cirkit_aig_mc | peak_ancilla | 64 | 64/0/0 | -99.98% | -99.98% |

## Interpretation

- The probe converts the previously built CirKit shell into a reproducible external baseline with row-level truth-table verification of the optimized Verilog readback.
- The resource numbers are logic-layer AIG multiplicative-complexity proxies: `T=4*MC`, CNOT/depth/ancilla are derived through the same AND/XAG proxy used by other external logic-network probes.
- The result should be claimed as evidence against an official CirKit AIG optimization and MC-count probe. It should not be described as a reproduced RevKit/ROS reversible-synthesis circuit or as a Clifford+T hardware-mapped result.
