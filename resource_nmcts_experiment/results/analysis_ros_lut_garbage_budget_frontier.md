# ROS-Style LUT Garbage Budget Frontier

This audit turns the executable LUT garbage proxy into a small budget frontier.
For each verified best-K LUT DAG, it selects the lowest-score policy among keep-all,
fanout-checkpoint, and zero-checkpoint schedules subject to a relative peak-ancilla budget.

This is a reversible-pebbling-style proxy over verified LUT DAGs.  It is not the official ROS SAT garbage-management algorithm.

## Frontier summary

| budget | functions | mean peak ancilla | mean log10(score+1) | peak reduction vs keep-all | log10 score shift vs keep-all | selected policies |
|---|---:|---:|---:|---:|---:|---|
| keep100 | 309 | 6056.04 | 3.36 | +0.00% | +0.00 | fanout_checkpoint:92;keep_all_bennett:217 |
| line75 | 173 | 1021.84 | 8.74 | +71.48% | +4.38 | fanout_checkpoint:173 |
| line50 | 142 | 1243.39 | 10.02 | +79.95% | +5.23 | fanout_checkpoint:138;zero_checkpoint:4 |
| line25 | 126 | 1396.63 | 10.87 | +84.19% | +5.83 | fanout_checkpoint:118;zero_checkpoint:8 |
| minline | 309 | 27.37 | 5.97 | +45.41% | +2.61 | fanout_checkpoint:148;keep_all_bennett:31;zero_checkpoint:130 |

## Resource comparisons

| target | budgeted LUT baseline | metric | items | W/L/T | mean relative |
|---|---|---|---:|---:|---:|
| and_resource_nmcts | keep100 | score | 309 | 309/0/0 | -83.77% |
| and_resource_nmcts | keep100 | T | 309 | 306/0/3 | -83.65% |
| and_resource_nmcts | keep100 | peak_ancilla | 309 | 308/0/1 | -75.25% |
| and_pareto_resource_nmcts | keep100 | score | 309 | 309/0/0 | -84.27% |
| and_pareto_resource_nmcts | keep100 | T | 309 | 306/0/3 | -84.22% |
| and_pareto_resource_nmcts | keep100 | peak_ancilla | 309 | 303/0/6 | -74.22% |
| and_resource_nmcts | line75 | score | 173 | 173/0/0 | -97.13% |
| and_resource_nmcts | line75 | T | 173 | 170/0/3 | -95.66% |
| and_resource_nmcts | line75 | peak_ancilla | 173 | 173/0/0 | -90.40% |
| and_pareto_resource_nmcts | line75 | score | 173 | 173/0/0 | -97.23% |
| and_pareto_resource_nmcts | line75 | T | 173 | 170/0/3 | -95.76% |
| and_pareto_resource_nmcts | line75 | peak_ancilla | 173 | 173/0/0 | -89.86% |
| and_resource_nmcts | line50 | score | 142 | 142/0/0 | -98.62% |
| and_resource_nmcts | line50 | T | 142 | 139/0/3 | -96.66% |
| and_resource_nmcts | line50 | peak_ancilla | 142 | 142/0/0 | -96.88% |
| and_pareto_resource_nmcts | line50 | score | 142 | 142/0/0 | -98.65% |
| and_pareto_resource_nmcts | line50 | T | 142 | 139/0/3 | -96.69% |
| and_pareto_resource_nmcts | line50 | peak_ancilla | 142 | 142/0/0 | -96.62% |
| and_resource_nmcts | line25 | score | 126 | 126/0/0 | -98.78% |
| and_resource_nmcts | line25 | T | 126 | 123/0/3 | -96.56% |
| and_resource_nmcts | line25 | peak_ancilla | 126 | 126/0/0 | -99.22% |
| and_pareto_resource_nmcts | line25 | score | 126 | 126/0/0 | -98.78% |
| and_pareto_resource_nmcts | line25 | T | 126 | 123/0/3 | -96.56% |
| and_pareto_resource_nmcts | line25 | peak_ancilla | 126 | 126/0/0 | -99.22% |
| and_resource_nmcts | minline | score | 309 | 309/0/0 | -87.71% |
| and_resource_nmcts | minline | T | 309 | 306/0/3 | -87.70% |
| and_resource_nmcts | minline | peak_ancilla | 309 | 308/0/1 | -70.56% |
| and_pareto_resource_nmcts | minline | score | 309 | 309/0/0 | -87.93% |
| and_pareto_resource_nmcts | minline | T | 309 | 306/0/3 | -87.95% |
| and_pareto_resource_nmcts | minline | peak_ancilla | 309 | 303/0/6 | -69.35% |

## Interpretation

- The frontier makes the line/operation trade-off explicit instead of reporting isolated garbage policies.
- Tight line budgets select recomputation-heavy policies; score and T-count can increase sharply even when peak ancilla drops.
- Resource-NMCTS comparisons against these rows are robustness checks against a stronger ROS-style garbage-pressure proxy, not claims about a reproduced official ROS compiler.
