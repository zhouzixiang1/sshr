# ROS-Style LUT Proxy Sweep

This analysis is a logic-level proxy for ROS-style resource-constrained LUT
oracle synthesis. It uses exported BLIF benchmarks, runs ABC `if -K` for
multiple K values, estimates each mapped LUT network as local-ANF
compute/action/uncompute logic, and chooses the best K per function under
the project score. It is not the official ROS, RevKit, or mockturtle flow.

Sweep rows: 927; usable: 927.
Best-K rows: 309.

## Selected K Distribution

| dataset | n | K | functions |
|---|---:|---:|---:|
| n14 | 14 | 3 | 55 |
| n14 | 14 | 4 | 3 |
| n14 | 14 | 5 | 6 |
| n15 | 15 | 3 | 28 |
| n15 | 15 | 4 | 1 |
| n15 | 15 | 5 | 3 |
| n16 | 16 | 3 | 23 |
| n16 | 16 | 5 | 1 |
| n18 | 18 | 3 | 12 |
| traditional | 3 | 3 | 1 |
| traditional | 3 | 4 | 1 |
| traditional | 3 | 5 | 1 |
| traditional | 4 | 3 | 19 |
| traditional | 4 | 4 | 21 |
| traditional | 4 | 5 | 29 |
| traditional | 5 | 3 | 14 |
| traditional | 5 | 4 | 15 |
| traditional | 5 | 5 | 38 |
| traditional | 6 | 3 | 15 |
| traditional | 6 | 4 | 16 |
| traditional | 6 | 5 | 7 |

## Pairwise Comparisons

| target | baseline | metric | items | W/L/T | mean relative |
|---|---|---|---:|---:|---:|
| and_resource_nmcts | external_ros_lut_proxy | T | 309 | 306/0/3 | -83.65% |
| and_resource_nmcts | external_ros_lut_proxy | CNOT | 309 | 309/0/0 | -81.46% |
| and_resource_nmcts | external_ros_lut_proxy | depth | 309 | 309/0/0 | -80.39% |
| and_resource_nmcts | external_ros_lut_proxy | peak_ancilla | 309 | 308/0/1 | -75.25% |
| and_resource_nmcts | external_ros_lut_proxy | score | 309 | 309/0/0 | -83.77% |
| and_resource_nmcts | external_ros_lut_k4 | T | 309 | 307/0/2 | -86.20% |
| and_resource_nmcts | external_ros_lut_k4 | CNOT | 309 | 309/0/0 | -83.94% |
| and_resource_nmcts | external_ros_lut_k4 | depth | 309 | 309/0/0 | -82.98% |
| and_resource_nmcts | external_ros_lut_k4 | peak_ancilla | 309 | 308/0/1 | -76.96% |
| and_resource_nmcts | external_ros_lut_k4 | score | 309 | 309/0/0 | -85.94% |
| and_profile_resource_nmcts | external_ros_lut_proxy | T | 132 | 132/0/0 | -97.21% |
| and_profile_resource_nmcts | external_ros_lut_proxy | CNOT | 132 | 132/0/0 | -97.13% |
| and_profile_resource_nmcts | external_ros_lut_proxy | depth | 132 | 132/0/0 | -96.98% |
| and_profile_resource_nmcts | external_ros_lut_proxy | peak_ancilla | 132 | 132/0/0 | -99.35% |
| and_profile_resource_nmcts | external_ros_lut_proxy | score | 132 | 132/0/0 | -97.38% |
| and_profile_resource_nmcts | external_ros_lut_k4 | T | 132 | 132/0/0 | -97.91% |
| and_profile_resource_nmcts | external_ros_lut_k4 | CNOT | 132 | 132/0/0 | -97.83% |
| and_profile_resource_nmcts | external_ros_lut_k4 | depth | 132 | 132/0/0 | -97.76% |
| and_profile_resource_nmcts | external_ros_lut_k4 | peak_ancilla | 132 | 132/0/0 | -99.56% |
| and_profile_resource_nmcts | external_ros_lut_k4 | score | 132 | 132/0/0 | -98.01% |
| and_pareto_resource_nmcts | external_ros_lut_proxy | T | 309 | 306/0/3 | -84.22% |
| and_pareto_resource_nmcts | external_ros_lut_proxy | CNOT | 309 | 309/0/0 | -82.14% |
| and_pareto_resource_nmcts | external_ros_lut_proxy | depth | 309 | 309/0/0 | -81.01% |
| and_pareto_resource_nmcts | external_ros_lut_proxy | peak_ancilla | 309 | 303/0/6 | -74.22% |
| and_pareto_resource_nmcts | external_ros_lut_proxy | score | 309 | 309/0/0 | -84.27% |
| and_pareto_resource_nmcts | external_ros_lut_k4 | T | 309 | 307/0/2 | -86.69% |
| and_pareto_resource_nmcts | external_ros_lut_k4 | CNOT | 309 | 309/0/0 | -84.54% |
| and_pareto_resource_nmcts | external_ros_lut_k4 | depth | 309 | 309/0/0 | -83.54% |
| and_pareto_resource_nmcts | external_ros_lut_k4 | peak_ancilla | 309 | 308/0/1 | -76.26% |
| and_pareto_resource_nmcts | external_ros_lut_k4 | score | 309 | 309/0/0 | -86.38% |
| and_fprm_linear_pair | external_ros_lut_proxy | T | 120 | 120/0/0 | -96.91% |
| and_fprm_linear_pair | external_ros_lut_proxy | CNOT | 120 | 120/0/0 | -96.85% |
| and_fprm_linear_pair | external_ros_lut_proxy | depth | 120 | 120/0/0 | -96.72% |
| and_fprm_linear_pair | external_ros_lut_proxy | peak_ancilla | 120 | 120/0/0 | -99.29% |
| and_fprm_linear_pair | external_ros_lut_proxy | score | 120 | 120/0/0 | -97.10% |
| and_fprm_linear_pair | external_ros_lut_k4 | T | 120 | 120/0/0 | -97.67% |
| and_fprm_linear_pair | external_ros_lut_k4 | CNOT | 120 | 120/0/0 | -97.62% |
| and_fprm_linear_pair | external_ros_lut_k4 | depth | 120 | 120/0/0 | -97.57% |
| and_fprm_linear_pair | external_ros_lut_k4 | peak_ancilla | 120 | 120/0/0 | -99.53% |
| and_fprm_linear_pair | external_ros_lut_k4 | score | 120 | 120/0/0 | -97.80% |
| and_fprm_linear_pair_fast | external_ros_lut_proxy | T | 12 | 12/0/0 | -99.55% |
| and_fprm_linear_pair_fast | external_ros_lut_proxy | CNOT | 12 | 12/0/0 | -99.55% |
| and_fprm_linear_pair_fast | external_ros_lut_proxy | depth | 12 | 12/0/0 | -99.54% |
| and_fprm_linear_pair_fast | external_ros_lut_proxy | peak_ancilla | 12 | 12/0/0 | -99.94% |
| and_fprm_linear_pair_fast | external_ros_lut_proxy | score | 12 | 12/0/0 | -99.58% |
| and_fprm_linear_pair_fast | external_ros_lut_k4 | T | 12 | 12/0/0 | -99.66% |
| and_fprm_linear_pair_fast | external_ros_lut_k4 | CNOT | 12 | 12/0/0 | -99.65% |
| and_fprm_linear_pair_fast | external_ros_lut_k4 | depth | 12 | 12/0/0 | -99.64% |
| and_fprm_linear_pair_fast | external_ros_lut_k4 | peak_ancilla | 12 | 12/0/0 | -99.89% |
| and_fprm_linear_pair_fast | external_ros_lut_k4 | score | 12 | 12/0/0 | -99.67% |
| and_direct_anf | external_ros_lut_proxy | T | 309 | 302/2/5 | -65.68% |
| and_direct_anf | external_ros_lut_proxy | CNOT | 309 | 307/2/0 | -67.95% |
| and_direct_anf | external_ros_lut_proxy | depth | 309 | 307/2/0 | -68.28% |
| and_direct_anf | external_ros_lut_proxy | peak_ancilla | 309 | 309/0/0 | -73.50% |
| and_direct_anf | external_ros_lut_proxy | score | 309 | 307/2/0 | -67.45% |
| and_direct_anf | external_ros_lut_k4 | T | 309 | 306/1/2 | -70.89% |
| and_direct_anf | external_ros_lut_k4 | CNOT | 309 | 308/1/0 | -72.18% |
| and_direct_anf | external_ros_lut_k4 | depth | 309 | 308/1/0 | -72.37% |
| and_direct_anf | external_ros_lut_k4 | peak_ancilla | 309 | 309/0/0 | -75.30% |
| and_direct_anf | external_ros_lut_k4 | score | 309 | 308/1/0 | -71.76% |
| direct_anf | external_ros_lut_proxy | T | 309 | 243/55/11 | -41.50% |
| direct_anf | external_ros_lut_proxy | CNOT | 309 | 308/1/0 | -72.86% |
| direct_anf | external_ros_lut_proxy | depth | 309 | 308/1/0 | -73.12% |
| direct_anf | external_ros_lut_proxy | peak_ancilla | 309 | 309/0/0 | -82.72% |
| direct_anf | external_ros_lut_proxy | score | 309 | 272/37/0 | -48.16% |
| direct_anf | external_ros_lut_k4 | T | 309 | 275/29/5 | -50.32% |
| direct_anf | external_ros_lut_k4 | CNOT | 309 | 309/0/0 | -76.44% |
| direct_anf | external_ros_lut_k4 | depth | 309 | 309/0/0 | -76.57% |
| direct_anf | external_ros_lut_k4 | peak_ancilla | 309 | 309/0/0 | -83.66% |
| direct_anf | external_ros_lut_k4 | score | 309 | 287/22/0 | -55.05% |
| external_ros_lut_proxy | external_ros_lut_k4 | T | 309 | 218/0/91 | -19.98% |
| external_ros_lut_proxy | external_ros_lut_k4 | CNOT | 309 | 218/1/90 | -18.02% |
| external_ros_lut_proxy | external_ros_lut_k4 | depth | 309 | 215/2/92 | -17.74% |
| external_ros_lut_proxy | external_ros_lut_k4 | peak_ancilla | 309 | 53/163/93 | +22.73% |
| external_ros_lut_proxy | external_ros_lut_k4 | score | 309 | 219/0/90 | -18.12% |
