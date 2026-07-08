# ROS-Style LUT Line Sensitivity

This analysis reuses the verified ABC LUT sweep and reselects the best K
under stricter line pressure. It is a garbage/ancilla sensitivity proxy,
not the official ROS SAT garbage-management algorithm.

Selected rows: 1236.

## LUT selector means

| method | mean K | mean peak ancilla | mean score |
|---|---:|---:|---:|
| external_ros_lut_k4_line_cap | 4.17 | 3978.93 | 228596.16 |
| external_ros_lut_line_w10 | 3.77 | 6054.75 | 164135.88 |
| external_ros_lut_line_w25 | 3.90 | 6049.23 | 164231.79 |
| external_ros_lut_min_ancilla | 4.74 | 2834.76 | 321260.83 |

## Pairwise comparisons

| target | baseline | metric | items | W/L/T | mean relative |
|---|---|---|---:|---:|---:|
| and_resource_nmcts | external_ros_lut_k4_line_cap | T | 309 | 306/0/3 | -84.61% |
| and_resource_nmcts | external_ros_lut_k4_line_cap | CNOT | 309 | 309/0/0 | -82.23% |
| and_resource_nmcts | external_ros_lut_k4_line_cap | depth | 309 | 309/0/0 | -81.14% |
| and_resource_nmcts | external_ros_lut_k4_line_cap | peak_ancilla | 309 | 308/0/1 | -72.41% |
| and_resource_nmcts | external_ros_lut_k4_line_cap | score | 309 | 309/0/0 | -84.54% |
| and_resource_nmcts | external_ros_lut_line_w10 | T | 309 | 306/0/3 | -83.96% |
| and_resource_nmcts | external_ros_lut_line_w10 | CNOT | 309 | 309/0/0 | -81.63% |
| and_resource_nmcts | external_ros_lut_line_w10 | depth | 309 | 309/0/0 | -80.52% |
| and_resource_nmcts | external_ros_lut_line_w10 | peak_ancilla | 309 | 308/0/1 | -72.79% |
| and_resource_nmcts | external_ros_lut_line_w10 | score | 309 | 309/0/0 | -83.96% |
| and_resource_nmcts | external_ros_lut_line_w25 | T | 309 | 306/0/3 | -84.35% |
| and_resource_nmcts | external_ros_lut_line_w25 | CNOT | 309 | 309/0/0 | -81.95% |
| and_resource_nmcts | external_ros_lut_line_w25 | depth | 309 | 309/0/0 | -80.83% |
| and_resource_nmcts | external_ros_lut_line_w25 | peak_ancilla | 309 | 308/0/1 | -71.22% |
| and_resource_nmcts | external_ros_lut_line_w25 | score | 309 | 309/0/0 | -84.28% |
| and_resource_nmcts | external_ros_lut_min_ancilla | T | 309 | 306/0/3 | -85.57% |
| and_resource_nmcts | external_ros_lut_min_ancilla | CNOT | 309 | 309/0/0 | -83.14% |
| and_resource_nmcts | external_ros_lut_min_ancilla | depth | 309 | 309/0/0 | -82.04% |
| and_resource_nmcts | external_ros_lut_min_ancilla | peak_ancilla | 309 | 308/0/1 | -69.54% |
| and_resource_nmcts | external_ros_lut_min_ancilla | score | 309 | 309/0/0 | -85.41% |
| and_pareto_resource_nmcts | external_ros_lut_k4_line_cap | T | 309 | 306/0/3 | -85.15% |
| and_pareto_resource_nmcts | external_ros_lut_k4_line_cap | CNOT | 309 | 309/0/0 | -82.89% |
| and_pareto_resource_nmcts | external_ros_lut_k4_line_cap | depth | 309 | 309/0/0 | -81.74% |
| and_pareto_resource_nmcts | external_ros_lut_k4_line_cap | peak_ancilla | 309 | 303/0/6 | -71.34% |
| and_pareto_resource_nmcts | external_ros_lut_k4_line_cap | score | 309 | 309/0/0 | -85.02% |
| and_pareto_resource_nmcts | external_ros_lut_line_w10 | T | 309 | 306/0/3 | -84.51% |
| and_pareto_resource_nmcts | external_ros_lut_line_w10 | CNOT | 309 | 309/0/0 | -82.30% |
| and_pareto_resource_nmcts | external_ros_lut_line_w10 | depth | 309 | 309/0/0 | -81.13% |
| and_pareto_resource_nmcts | external_ros_lut_line_w10 | peak_ancilla | 309 | 303/0/6 | -71.70% |
| and_pareto_resource_nmcts | external_ros_lut_line_w10 | score | 309 | 309/0/0 | -84.45% |
| and_pareto_resource_nmcts | external_ros_lut_line_w25 | T | 309 | 306/0/3 | -84.88% |
| and_pareto_resource_nmcts | external_ros_lut_line_w25 | CNOT | 309 | 309/0/0 | -82.59% |
| and_pareto_resource_nmcts | external_ros_lut_line_w25 | depth | 309 | 309/0/0 | -81.42% |
| and_pareto_resource_nmcts | external_ros_lut_line_w25 | peak_ancilla | 309 | 303/0/6 | -70.06% |
| and_pareto_resource_nmcts | external_ros_lut_line_w25 | score | 309 | 309/0/0 | -84.75% |
| and_pareto_resource_nmcts | external_ros_lut_min_ancilla | T | 309 | 306/0/3 | -86.03% |
| and_pareto_resource_nmcts | external_ros_lut_min_ancilla | CNOT | 309 | 309/0/0 | -83.72% |
| and_pareto_resource_nmcts | external_ros_lut_min_ancilla | depth | 309 | 309/0/0 | -82.56% |
| and_pareto_resource_nmcts | external_ros_lut_min_ancilla | peak_ancilla | 309 | 301/0/8 | -68.21% |
| and_pareto_resource_nmcts | external_ros_lut_min_ancilla | score | 309 | 309/0/0 | -85.83% |
| and_direct_anf | external_ros_lut_k4_line_cap | T | 309 | 305/1/3 | -68.16% |
| and_direct_anf | external_ros_lut_k4_line_cap | CNOT | 309 | 308/1/0 | -69.57% |
| and_direct_anf | external_ros_lut_k4_line_cap | depth | 309 | 308/1/0 | -69.72% |
| and_direct_anf | external_ros_lut_k4_line_cap | peak_ancilla | 309 | 309/0/0 | -70.38% |
| and_direct_anf | external_ros_lut_k4_line_cap | score | 309 | 308/1/0 | -69.25% |
| and_direct_anf | external_ros_lut_line_w10 | T | 309 | 302/2/5 | -66.48% |
| and_direct_anf | external_ros_lut_line_w10 | CNOT | 309 | 307/2/0 | -68.30% |
| and_direct_anf | external_ros_lut_line_w10 | depth | 309 | 307/2/0 | -68.53% |
| and_direct_anf | external_ros_lut_line_w10 | peak_ancilla | 309 | 309/0/0 | -70.66% |
| and_direct_anf | external_ros_lut_line_w10 | score | 309 | 307/2/0 | -67.90% |
| and_direct_anf | external_ros_lut_line_w25 | T | 309 | 302/2/5 | -67.43% |
| and_direct_anf | external_ros_lut_line_w25 | CNOT | 309 | 307/2/0 | -68.93% |
| and_direct_anf | external_ros_lut_line_w25 | depth | 309 | 307/2/0 | -69.11% |
| and_direct_anf | external_ros_lut_line_w25 | peak_ancilla | 309 | 309/0/0 | -68.93% |
| and_direct_anf | external_ros_lut_line_w25 | score | 309 | 307/2/0 | -68.62% |
| and_direct_anf | external_ros_lut_min_ancilla | T | 309 | 306/0/3 | -70.44% |
| and_direct_anf | external_ros_lut_min_ancilla | CNOT | 309 | 309/0/0 | -71.31% |
| and_direct_anf | external_ros_lut_min_ancilla | depth | 309 | 309/0/0 | -71.37% |
| and_direct_anf | external_ros_lut_min_ancilla | peak_ancilla | 309 | 309/0/0 | -67.00% |
| and_direct_anf | external_ros_lut_min_ancilla | score | 309 | 309/0/0 | -71.22% |
| direct_anf | external_ros_lut_k4_line_cap | T | 309 | 268/33/8 | -45.90% |
| direct_anf | external_ros_lut_k4_line_cap | CNOT | 309 | 309/0/0 | -74.20% |
| direct_anf | external_ros_lut_k4_line_cap | depth | 309 | 309/0/0 | -74.30% |
| direct_anf | external_ros_lut_k4_line_cap | peak_ancilla | 309 | 309/0/0 | -80.79% |
| direct_anf | external_ros_lut_k4_line_cap | score | 309 | 284/25/0 | -51.10% |
| direct_anf | external_ros_lut_line_w10 | T | 309 | 257/44/8 | -42.88% |
| direct_anf | external_ros_lut_line_w10 | CNOT | 309 | 308/1/0 | -73.16% |
| direct_anf | external_ros_lut_line_w10 | depth | 309 | 308/1/0 | -73.34% |
| direct_anf | external_ros_lut_line_w10 | peak_ancilla | 309 | 309/0/0 | -80.90% |
| direct_anf | external_ros_lut_line_w10 | score | 309 | 274/35/0 | -48.88% |
| direct_anf | external_ros_lut_line_w25 | T | 309 | 268/35/6 | -44.60% |
| direct_anf | external_ros_lut_line_w25 | CNOT | 309 | 308/1/0 | -73.66% |
| direct_anf | external_ros_lut_line_w25 | depth | 309 | 308/1/0 | -73.80% |
| direct_anf | external_ros_lut_line_w25 | peak_ancilla | 309 | 309/0/0 | -79.95% |
| direct_anf | external_ros_lut_line_w25 | score | 309 | 280/29/0 | -50.08% |
| direct_anf | external_ros_lut_min_ancilla | T | 309 | 293/9/7 | -50.11% |
| direct_anf | external_ros_lut_min_ancilla | CNOT | 309 | 309/0/0 | -75.55% |
| direct_anf | external_ros_lut_min_ancilla | depth | 309 | 309/0/0 | -75.59% |
| direct_anf | external_ros_lut_min_ancilla | peak_ancilla | 309 | 309/0/0 | -78.82% |
| direct_anf | external_ros_lut_min_ancilla | score | 309 | 301/8/0 | -54.49% |
| external_ros_lut_k4_line_cap | external_ros_lut_proxy | T | 309 | 0/163/146 | +20.91% |
| external_ros_lut_k4_line_cap | external_ros_lut_proxy | CNOT | 309 | 4/159/146 | +16.90% |
| external_ros_lut_k4_line_cap | external_ros_lut_proxy | depth | 309 | 5/156/148 | +16.26% |
| external_ros_lut_k4_line_cap | external_ros_lut_proxy | peak_ancilla | 309 | 163/0/146 | -19.62% |
| external_ros_lut_k4_line_cap | external_ros_lut_proxy | score | 309 | 0/163/146 | +17.15% |
| external_ros_lut_line_w10 | external_ros_lut_proxy | T | 309 | 0/35/274 | +1.81% |
| external_ros_lut_line_w10 | external_ros_lut_proxy | CNOT | 309 | 4/31/274 | +0.85% |
| external_ros_lut_line_w10 | external_ros_lut_proxy | depth | 309 | 6/27/276 | +0.64% |
| external_ros_lut_line_w10 | external_ros_lut_proxy | peak_ancilla | 309 | 35/0/274 | -5.58% |
| external_ros_lut_line_w10 | external_ros_lut_proxy | score | 309 | 0/35/274 | +1.04% |
| external_ros_lut_line_w25 | external_ros_lut_proxy | T | 309 | 0/64/245 | +4.69% |
| external_ros_lut_line_w25 | external_ros_lut_proxy | CNOT | 309 | 4/60/245 | +2.87% |
| external_ros_lut_line_w25 | external_ros_lut_proxy | depth | 309 | 6/56/247 | +2.54% |
| external_ros_lut_line_w25 | external_ros_lut_proxy | peak_ancilla | 309 | 64/0/245 | -9.99% |
| external_ros_lut_line_w25 | external_ros_lut_proxy | score | 309 | 0/64/245 | +3.25% |
| external_ros_lut_min_ancilla | external_ros_lut_proxy | T | 309 | 0/197/112 | +47.69% |
| external_ros_lut_min_ancilla | external_ros_lut_proxy | CNOT | 309 | 3/194/112 | +39.40% |
| external_ros_lut_min_ancilla | external_ros_lut_proxy | depth | 309 | 5/190/114 | +38.19% |
| external_ros_lut_min_ancilla | external_ros_lut_proxy | peak_ancilla | 309 | 197/0/112 | -32.47% |
| external_ros_lut_min_ancilla | external_ros_lut_proxy | score | 309 | 0/197/112 | +40.67% |

## Interpretation

- The line-aware selectors usually move toward larger K because larger LUTs reduce the number of intermediate nodes.
- These selectors make the LUT proxy more ancilla-sensitive, but they still do not implement ROS SAT garbage management.
- Resource-NMCTS comparisons should therefore be framed as robustness to line-aware LUT proxy choices, not as a full official ROS reproduction.
