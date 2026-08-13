# MCTS Budget Policy Evaluation

The policy first obtains a verified Resource-NMCTS result and then chooses whether to run the more expensive Pareto-Resource-NMCTS search.
Reported time is conservative: Resource-NMCTS time is added even when Pareto-Resource-NMCTS internally repeats some candidates.

Bootstrap intervals use 4000 deterministic paired resamples.

| threshold | pairs | run/stop | vs Pareto W/L/T | vs Resource W/L/T | mean score regret [95% CI] | quality gain retained [95% CI] | time change [95% CI] |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.600 | 160 | 71/89 | 0/13/147 | 56/0/104 | +0.506% [+0.192, +0.881] | 94.90% [90.43, 98.19] | -13.13% [-20.46, -6.80] |

## Resource metrics

| threshold | metric | policy mean | Resource mean | Pareto mean | policy vs Resource | policy vs Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 0.600 | score | 50.9862 | 54.8399 | 50.7790 | -3.482% | +0.506% |
| 0.600 | T | 41.5750 | 45.2500 | 41.3250 | -3.992% | +0.831% |
| 0.600 | CNOT | 85.7812 | 92.4437 | 85.1750 | -3.842% | +0.842% |
| 0.600 | depth | 90.8375 | 97.0500 | 90.3438 | -3.337% | +0.681% |
| 0.600 | gates | 44.2375 | 46.1375 | 44.1812 | -2.039% | +0.149% |
| 0.600 | peak_ancilla | 2.0875 | 1.9875 | 2.1250 | +4.479% | -1.354% |
