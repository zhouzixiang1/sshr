# ROS-Style LUT Checkpoint Optimizer

This audit strengthens the ROS-facing garbage-management proxy by solving
an exact checkpoint-subset subproblem on verified ABC LUT DAGs with small
multi-fanout candidate sets.

It is not the official ROS SAT garbage-management implementation.  It is an
exhaustive optimizer over the checkpoint candidates induced by the already
verified LUT DAGs.

## Scope

- max checkpoint candidates enumerated per DAG: 12
- solved functions: 192
- solved traditional n<=6 functions: 177
- skipped functions: 0

## Frontier summary

| budget | functions | mean peak ancilla | mean log10(score+1) | mean checkpoint candidates | mean evaluated subsets | selected policies |
|---|---:|---:|---:|---:|---:|---|
| keep100 | 192 | 7.16 | 2.18 | 0.17 | 1.65 | keep_all_bennett:192 |
| line75 | 56 | 7.61 | 2.93 | 0.55 | 5.57 | fanout_checkpoint:13;keep_all_bennett:7;zero_checkpoint:36 |
| line50 | 25 | 8.40 | 2.94 | 1.12 | 12.24 | checkpoint_subset:2;fanout_checkpoint:7;keep_all_bennett:7;zero_checkpoint:9 |
| line25 | 9 | 4.22 | 1.76 | 1.11 | 28.89 | fanout_checkpoint:1;keep_all_bennett:7;zero_checkpoint:1 |
| minline | 192 | 4.67 | 2.38 | 0.17 | 1.65 | checkpoint_subset:4;fanout_checkpoint:2;keep_all_bennett:123;zero_checkpoint:63 |

## Resource comparisons on solved rows

| target | optimized LUT baseline | metric | items | W/L/T | mean relative |
|---|---|---|---:|---:|---:|
| and_resource_nmcts | keep100 | score | 192 | 192/0/0 | -74.66% |
| and_resource_nmcts | keep100 | T | 192 | 189/0/3 | -74.53% |
| and_resource_nmcts | keep100 | peak_ancilla | 192 | 191/0/1 | -60.22% |
| and_pareto_resource_nmcts | keep100 | score | 192 | 192/0/0 | -75.47% |
| and_pareto_resource_nmcts | keep100 | T | 192 | 189/0/3 | -75.45% |
| and_pareto_resource_nmcts | keep100 | peak_ancilla | 192 | 186/0/6 | -58.56% |
| and_resource_nmcts | line75 | score | 56 | 56/0/0 | -91.13% |
| and_resource_nmcts | line75 | T | 56 | 53/0/3 | -86.60% |
| and_resource_nmcts | line75 | peak_ancilla | 56 | 56/0/0 | -71.43% |
| and_pareto_resource_nmcts | line75 | score | 56 | 56/0/0 | -91.44% |
| and_pareto_resource_nmcts | line75 | T | 56 | 53/0/3 | -86.92% |
| and_pareto_resource_nmcts | line75 | peak_ancilla | 56 | 56/0/0 | -69.75% |
| and_resource_nmcts | line50 | score | 25 | 25/0/0 | -92.14% |
| and_resource_nmcts | line50 | T | 25 | 22/0/3 | -81.00% |
| and_resource_nmcts | line50 | peak_ancilla | 25 | 25/0/0 | -84.74% |
| and_pareto_resource_nmcts | line50 | score | 25 | 25/0/0 | -92.34% |
| and_pareto_resource_nmcts | line50 | T | 25 | 22/0/3 | -81.21% |
| and_pareto_resource_nmcts | line50 | peak_ancilla | 25 | 25/0/0 | -83.28% |
| and_resource_nmcts | line25 | score | 9 | 9/0/0 | -82.99% |
| and_resource_nmcts | line25 | T | 9 | 6/0/3 | -51.81% |
| and_resource_nmcts | line25 | peak_ancilla | 9 | 9/0/0 | -98.36% |
| and_pareto_resource_nmcts | line25 | score | 9 | 9/0/0 | -82.99% |
| and_pareto_resource_nmcts | line25 | T | 9 | 6/0/3 | -51.81% |
| and_pareto_resource_nmcts | line25 | peak_ancilla | 9 | 9/0/0 | -98.36% |
| and_resource_nmcts | minline | score | 192 | 192/0/0 | -80.21% |
| and_resource_nmcts | minline | T | 192 | 189/0/3 | -80.19% |
| and_resource_nmcts | minline | peak_ancilla | 192 | 191/0/1 | -56.12% |
| and_pareto_resource_nmcts | minline | score | 192 | 192/0/0 | -80.57% |
| and_pareto_resource_nmcts | minline | T | 192 | 189/0/3 | -80.61% |
| and_pareto_resource_nmcts | minline | peak_ancilla | 192 | 186/0/6 | -54.18% |

## Interpretation

- This exact subproblem tests whether the three-policy garbage proxy hides a better checkpoint subset on tractable DAGs.
- The coverage is strongest for the traditional n<=6 comparison slice; large fanout-heavy high-dimensional DAGs remain outside exact enumeration.
- The row should be described as an exact ROS-style checkpoint-subset audit, not as full ROS reproduction or hardware mapping.
