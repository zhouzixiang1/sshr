# Mockturtle XAG Probe Analysis

Scope: ABC maps each exported BLIF with `strash; if -K 4`; official mockturtle then reads the mapped BLIF as a KLUT network and applies `xag_npn_resynthesis` to produce XAG counts.

This is a mockturtle adapter/probe, not the official ROS flow and not hardware mapping.

- mockturtle checkout: `/Users/zhouzixiang/Desktop/tzb/src/tmp/mockturtle`
- mockturtle commit: `25beb0e294e4613bb9fe62319b91d9f2ab764e88`
- stats tool: `/Users/zhouzixiang/Desktop/tzb/src/tmp/bin/mockturtle_blif_xag_stats`
- rows attempted: 177
- usable rows: 177
- correct rows: 177
- error rows: 0
- timeout rows: 0

## Comparisons

| Target | Baseline | Metric | Items | W/L/T | Mean relative | Median relative |
|---|---|---:|---:|---:|---:|---:|
| and_resource_nmcts | external_mockturtle_xag_k4 | score | 177 | 165/12/0 | -28.97% | -29.37% |
| and_resource_nmcts | external_mockturtle_xag_k4 | T | 177 | 45/86/46 | +10.37% | +0.00% |
| and_resource_nmcts | external_mockturtle_xag_k4 | CNOT | 177 | 31/145/1 | +23.72% | +21.52% |
| and_resource_nmcts | external_mockturtle_xag_k4 | depth | 177 | 11/163/3 | +103.36% | +89.09% |
| and_resource_nmcts | external_mockturtle_xag_k4 | peak_ancilla | 177 | 177/0/0 | -82.67% | -85.71% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | score | 177 | 166/11/0 | -31.50% | -32.43% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | T | 177 | 59/70/48 | +5.72% | +0.00% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | CNOT | 177 | 37/139/1 | +18.40% | +16.56% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | depth | 177 | 12/162/3 | +92.87% | +83.72% |
| and_pareto_resource_nmcts | external_mockturtle_xag_k4 | peak_ancilla | 177 | 177/0/0 | -82.22% | -85.71% |
| and_fprm_polarity_archive | external_mockturtle_xag_k4 | score | 177 | 156/21/0 | -25.11% | -25.45% |
| and_fprm_polarity_archive | external_mockturtle_xag_k4 | T | 177 | 46/94/37 | +16.11% | +14.29% |
| and_fprm_polarity_archive | external_mockturtle_xag_k4 | CNOT | 177 | 25/151/1 | +26.91% | +24.14% |
| and_fprm_polarity_archive | external_mockturtle_xag_k4 | depth | 177 | 8/169/0 | +102.67% | +91.84% |
| and_fprm_polarity_archive | external_mockturtle_xag_k4 | peak_ancilla | 177 | 177/0/0 | -80.89% | -83.33% |
| and_direct_anf | external_mockturtle_xag_k4 | score | 177 | 19/158/0 | +50.20% | +47.69% |
| and_direct_anf | external_mockturtle_xag_k4 | T | 177 | 1/168/8 | +150.08% | +146.15% |
| and_direct_anf | external_mockturtle_xag_k4 | CNOT | 177 | 6/169/2 | +125.53% | +124.87% |
| and_direct_anf | external_mockturtle_xag_k4 | depth | 177 | 5/172/0 | +254.13% | +228.00% |
| and_direct_anf | external_mockturtle_xag_k4 | peak_ancilla | 177 | 177/0/0 | -81.47% | -83.33% |
| direct_anf | external_mockturtle_xag_k4 | score | 177 | 9/168/0 | +142.26% | +140.45% |
| direct_anf | external_mockturtle_xag_k4 | T | 177 | 0/170/7 | +335.90% | +330.77% |
| direct_anf | external_mockturtle_xag_k4 | CNOT | 177 | 9/168/0 | +91.21% | +89.66% |
| direct_anf | external_mockturtle_xag_k4 | depth | 177 | 9/168/0 | +192.59% | +176.00% |
| direct_anf | external_mockturtle_xag_k4 | peak_ancilla | 177 | 177/0/0 | -88.10% | -88.24% |
| and_esop_milp | external_mockturtle_xag_k4 | score | 177 | 92/85/0 | +8.18% | -3.30% |
| and_esop_milp | external_mockturtle_xag_k4 | T | 177 | 11/144/22 | +75.82% | +50.00% |
| and_esop_milp | external_mockturtle_xag_k4 | CNOT | 177 | 27/146/4 | +54.29% | +37.93% |
| and_esop_milp | external_mockturtle_xag_k4 | depth | 177 | 6/171/0 | +209.69% | +111.63% |
| and_esop_milp | external_mockturtle_xag_k4 | peak_ancilla | 177 | 177/0/0 | -80.71% | -83.33% |
| sshr_h | external_mockturtle_xag_k4 | score | 177 | 50/127/0 | +33.30% | +18.84% |
| sshr_h | external_mockturtle_xag_k4 | T | 177 | 4/169/4 | +226.22% | +100.00% |
| sshr_h | external_mockturtle_xag_k4 | CNOT | 177 | 83/84/10 | +17.79% | +0.00% |
| sshr_h | external_mockturtle_xag_k4 | depth | 177 | 7/166/4 | +104.96% | +95.35% |
| sshr_h | external_mockturtle_xag_k4 | peak_ancilla | 177 | 177/0/0 | -87.62% | -88.24% |

## Interpretation

- The probe removes the previous `mockturtle is reachable but not adapted` gap: the local checkout now builds a small official-header C++ adapter and runs on exported benchmark BLIFs.
- The resource numbers are still logic-level proxy costs derived from XAG AND/XOR/depth counts; they are not a Clifford+T emission, not a reversible garbage-management flow, and not a routed hardware result.
- If Resource-NMCTS wins under this baseline, the claim should be written as evidence against an official mockturtle KLUT-to-XAG resynthesis probe, not as a full ROS reproduction.
