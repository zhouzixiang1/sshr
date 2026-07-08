# CirKit AIG Multiplicative-Complexity Probe

Scope: ABC converts each exported BLIF into AIGER; official CirKit 3 shell reads the AIG, applies the selected AIG optimization flow, reports `mccost -a`, and writes Verilog that is read back by ABC for truth-table verification.

This is a CirKit-shell AIG/MC probe, not legacy RevKit reversible synthesis, not the full ROS flow, and not hardware mapping.

- CirKit checkout: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit`
- CirKit commit: `4531533394725864a304e710d82087ff74fbe801`
- CirKit binary: `/Users/zhouzixiang/Desktop/tzb/src/tmp/cirkit/build/cli/cirkit`
- rows attempted: 177
- usable rows: 177
- correct rows: 177
- error rows: 0
- timeout rows: 0

## Comparisons

| Target | Baseline | Metric | Items | W/L/T | Mean relative | Median relative |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_cirkit_aig_mc | score | 177 | 177/0/0 | -60.84% | -60.83% |
| and_resource_nmcts | external_cirkit_aig_mc | T | 177 | 177/0/0 | -50.68% | -50.00% |
| and_resource_nmcts | external_cirkit_aig_mc | CNOT | 177 | 162/14/1 | -31.95% | -30.83% |
| and_resource_nmcts | external_cirkit_aig_mc | depth | 177 | 16/156/5 | +104.22% | +84.00% |
| and_resource_nmcts | external_cirkit_aig_mc | peak_ancilla | 177 | 177/0/0 | -87.98% | -90.00% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | score | 177 | 177/0/0 | -62.34% | -62.35% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | T | 177 | 177/0/0 | -52.94% | -52.38% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | CNOT | 177 | 167/9/1 | -35.03% | -34.86% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | depth | 177 | 16/156/5 | +93.16% | +81.63% |
| and_pareto_resource_nmcts | external_cirkit_aig_mc | peak_ancilla | 177 | 177/0/0 | -87.65% | -90.00% |
| and_fprm_polarity_archive | external_cirkit_aig_mc | score | 177 | 177/0/0 | -58.96% | -59.57% |
| and_fprm_polarity_archive | external_cirkit_aig_mc | T | 177 | 176/0/1 | -48.48% | -50.00% |
| and_fprm_polarity_archive | external_cirkit_aig_mc | CNOT | 177 | 163/13/1 | -30.62% | -31.72% |
| and_fprm_polarity_archive | external_cirkit_aig_mc | depth | 177 | 11/165/1 | +102.51% | +89.47% |
| and_fprm_polarity_archive | external_cirkit_aig_mc | peak_ancilla | 177 | 177/0/0 | -86.64% | -89.29% |
| and_direct_anf | external_cirkit_aig_mc | score | 177 | 124/53/0 | -16.74% | -16.78% |
| and_direct_anf | external_cirkit_aig_mc | T | 177 | 64/104/9 | +13.47% | +14.00% |
| and_direct_anf | external_cirkit_aig_mc | CNOT | 177 | 52/121/4 | +24.96% | +25.56% |
| and_direct_anf | external_cirkit_aig_mc | depth | 177 | 6/170/1 | +256.88% | +215.79% |
| and_direct_anf | external_cirkit_aig_mc | peak_ancilla | 177 | 177/0/0 | -87.10% | -88.89% |
| direct_anf | external_cirkit_aig_mc | score | 177 | 46/131/0 | +35.23% | +38.02% |
| direct_anf | external_cirkit_aig_mc | T | 177 | 19/152/6 | +99.85% | +107.55% |
| direct_anf | external_cirkit_aig_mc | CNOT | 177 | 80/94/3 | +5.06% | +4.56% |
| direct_anf | external_cirkit_aig_mc | depth | 177 | 11/165/1 | +194.22% | +168.42% |
| direct_anf | external_cirkit_aig_mc | peak_ancilla | 177 | 177/0/0 | -91.78% | -92.00% |
| and_esop_milp | external_cirkit_aig_mc | score | 177 | 150/27/0 | -39.41% | -48.20% |
| and_esop_milp | external_cirkit_aig_mc | T | 177 | 130/36/11 | -19.67% | -33.33% |
| and_esop_milp | external_cirkit_aig_mc | CNOT | 177 | 128/49/0 | -13.73% | -27.47% |
| and_esop_milp | external_cirkit_aig_mc | depth | 177 | 9/168/0 | +217.00% | +110.53% |
| and_esop_milp | external_cirkit_aig_mc | peak_ancilla | 177 | 177/0/0 | -86.52% | -87.50% |
| sshr_h | external_cirkit_aig_mc | score | 177 | 164/13/0 | -32.83% | -34.63% |
| sshr_h | external_cirkit_aig_mc | T | 177 | 98/70/9 | -4.12% | -5.66% |
| sshr_h | external_cirkit_aig_mc | CNOT | 177 | 171/5/1 | -42.51% | -45.21% |
| sshr_h | external_cirkit_aig_mc | depth | 177 | 11/161/5 | +100.45% | +93.88% |
| sshr_h | external_cirkit_aig_mc | peak_ancilla | 177 | 177/0/0 | -91.55% | -91.67% |

## Interpretation

- The probe converts the previously built CirKit shell into a reproducible external baseline with row-level truth-table verification of the optimized Verilog readback.
- The resource numbers are logic-layer AIG multiplicative-complexity proxies: `T=4*MC`, CNOT/depth/ancilla are derived through the same AND/XAG proxy used by other external logic-network probes.
- The result should be claimed as evidence against an official CirKit AIG optimization and MC-count probe. It should not be described as a reproduced RevKit/ROS reversible-synthesis circuit or as a Clifford+T hardware-mapped result.
