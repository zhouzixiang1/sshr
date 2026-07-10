# Mockturtle XAG Probe Analysis

Scope: ABC maps each exported BLIF with `strash; if -K 4`; official mockturtle then reads the mapped BLIF as a KLUT network and applies `xag_npn_resynthesis` to produce XAG counts.

This is a mockturtle adapter/probe, not the official ROS flow and not hardware mapping.

- mockturtle checkout: `/Users/zhouzixiang/Desktop/tzb/src/tmp/mockturtle`
- mockturtle commit: `25beb0e294e4613bb9fe62319b91d9f2ab764e88`
- stats tool: `/Users/zhouzixiang/Desktop/tzb/src/tmp/bin/mockturtle_blif_xag_stats`
- rows attempted: 64
- usable rows: 64
- correct rows: 64
- error rows: 0
- timeout rows: 0

## Comparisons

| Target | Baseline | Metric | Items | W/L/T | Mean relative | Median relative |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_mockturtle_xag_k4 | score | 64 | 64/0/0 | -91.41% | -95.50% |
| and_resource_nmcts | external_mockturtle_xag_k4 | T | 64 | 61/0/3 | -85.38% | -93.05% |
| and_resource_nmcts | external_mockturtle_xag_k4 | CNOT | 64 | 64/0/0 | -85.46% | -92.55% |
| and_resource_nmcts | external_mockturtle_xag_k4 | depth | 64 | 11/53/0 | +1169.72% | +630.73% |
| and_resource_nmcts | external_mockturtle_xag_k4 | peak_ancilla | 64 | 64/0/0 | -99.73% | -99.96% |
| and_profile_resource_nmcts | external_mockturtle_xag_k4 | score | 64 | 64/0/0 | -91.41% | -95.50% |
| and_profile_resource_nmcts | external_mockturtle_xag_k4 | T | 64 | 61/0/3 | -85.38% | -93.05% |
| and_profile_resource_nmcts | external_mockturtle_xag_k4 | CNOT | 64 | 64/0/0 | -85.46% | -92.55% |
| and_profile_resource_nmcts | external_mockturtle_xag_k4 | depth | 64 | 11/53/0 | +1169.72% | +630.73% |
| and_profile_resource_nmcts | external_mockturtle_xag_k4 | peak_ancilla | 64 | 64/0/0 | -99.73% | -99.96% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | score | 64 | 64/0/0 | -91.49% | -95.50% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | T | 64 | 61/0/3 | -85.51% | -93.05% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | CNOT | 64 | 64/0/0 | -85.64% | -92.55% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | depth | 64 | 11/53/0 | +1169.33% | +630.73% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | peak_ancilla | 64 | 64/0/0 | -99.73% | -99.96% |
| and_direct_anf | external_mockturtle_xag_k4 | score | 64 | 64/0/0 | -88.40% | -93.07% |
| and_direct_anf | external_mockturtle_xag_k4 | T | 64 | 60/1/3 | -79.94% | -88.94% |
| and_direct_anf | external_mockturtle_xag_k4 | CNOT | 64 | 64/0/0 | -81.76% | -89.41% |
| and_direct_anf | external_mockturtle_xag_k4 | depth | 64 | 11/53/0 | +1808.70% | +918.95% |
| and_direct_anf | external_mockturtle_xag_k4 | peak_ancilla | 64 | 64/0/0 | -99.98% | -99.97% |
| direct_anf | external_mockturtle_xag_k4 | score | 64 | 64/0/0 | -82.58% | -88.54% |
| direct_anf | external_mockturtle_xag_k4 | T | 64 | 60/1/3 | -69.36% | -80.25% |
| direct_anf | external_mockturtle_xag_k4 | CNOT | 64 | 64/0/0 | -86.82% | -93.61% |
| direct_anf | external_mockturtle_xag_k4 | depth | 64 | 13/51/0 | +1054.79% | +529.13% |
| direct_anf | external_mockturtle_xag_k4 | peak_ancilla | 64 | 64/0/0 | -99.98% | -99.98% |

## Interpretation

- The probe removes the previous `mockturtle is reachable but not adapted` gap: the local checkout now builds a small official-header C++ adapter and runs on exported benchmark BLIFs.
- The resource numbers are still logic-level proxy costs derived from XAG AND/XOR/depth counts; they are not a Clifford+T emission, not a reversible garbage-management flow, and not a routed hardware result.
- If Resource-NMCTS wins under this baseline, the claim should be written as evidence against an official mockturtle KLUT-to-XAG resynthesis probe, not as a full ROS reproduction.
