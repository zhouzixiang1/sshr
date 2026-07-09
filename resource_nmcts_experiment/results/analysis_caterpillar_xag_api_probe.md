# Caterpillar XAG API Probe

This bounded probe runs Caterpillar's logic-network synthesis API on the same traditional n<=6 truth-table functions used by the main small-function experiment.

It is a real Caterpillar API performance probe over ANF-XAG inputs, but it is still not the official ROS SAT garbage-management flow.

## Status counts

- pass: 4

## Provenance

- Caterpillar checkout: `tmp/caterpillar`
- Caterpillar commit: `4c6f766`
- input rows: `results/raw_traditional_resource.csv`
- raw probe rows: 531
- unique functions covered by best-of-Caterpillar: 177

## Strategy Summary

| item | status | rows | correct rows | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| xag_fast_lowt | pass | 177 | 177 | 62.9153 | 27.9661 | 31.8249 | 15.7288 | 96.5677 | 0.000094 |
| xag_lowd | pass | 177 | 177 | 62.9153 | 64.0791 | 33.8475 | 22.7740 | 112.4941 | 0.000112 |
| xag_lowt | pass | 177 | 177 | 62.9153 | 27.9661 | 34.1469 | 15.7288 | 96.6025 | 0.000079 |
| best_of_caterpillar_xag_api | pass | 177 | 177 | 62.9153 | 27.9661 | 31.5311 | 15.7288 | 96.5633 | 0.000089 |

## Matched Comparison

| baseline | metric | W/L/T for Caterpillar best | mean relative delta |
|---|---|---:|---:|
| and_pareto_resource_nmcts | score | 0/177/0 | +102.80% |
| and_pareto_resource_nmcts | T | 0/169/8 | +67.76% |
| and_pareto_resource_nmcts | CNOT | 173/4/0 | -60.82% |
| and_pareto_resource_nmcts | depth | 173/0/4 | -58.30% |
| and_pareto_resource_nmcts | peak_ancilla | 0/173/4 | +610.36% |
| and_resource_nmcts | score | 0/177/0 | +96.36% |
| and_resource_nmcts | T | 0/167/10 | +61.89% |
| and_resource_nmcts | CNOT | 173/4/0 | -62.17% |
| and_resource_nmcts | depth | 173/0/4 | -59.54% |
| and_resource_nmcts | peak_ancilla | 0/173/4 | +643.22% |
| and_direct_anf | score | 123/54/0 | -5.82% |
| and_direct_anf | T | 157/0/20 | -28.33% |
| and_direct_anf | CNOT | 173/4/0 | -77.87% |
| and_direct_anf | depth | 173/0/4 | -74.98% |
| and_direct_anf | peak_ancilla | 0/173/4 | +569.54% |
| sshr_h | score | 51/126/0 | +21.11% |
| sshr_h | T | 127/37/13 | -11.87% |
| sshr_h | CNOT | 175/2/0 | -57.02% |
| sshr_h | depth | 177/0/0 | -60.78% |
| sshr_h | peak_ancilla | 2/173/2 | +972.88% |

## Boundary

- Supported claim: Caterpillar can now be cited as a bounded, verified API-level implementation-family counterpoint on the same traditional function names.
- Excluded claim: these rows do not reproduce full ROS SAT garbage management, LUT mapping, reversible emission, routing, or hardware mapping.
