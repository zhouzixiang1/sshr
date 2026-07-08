# Approximate Rz Synthesis Cost Analysis

This analysis charges every non-Clifford Rz in the RevKit `oracle_synth`
netlist by a configurable approximate Clifford+T synthesis model
`ceil(slope*log2(1/epsilon)+offset)` T gates.

The default `ross_selinger_z` proxy uses slope 3 and offset 0, reflecting
the typical z-rotation asymptotic T-count reported by Ross and Selinger.
The `selinger_su2` proxy uses slope 4 and offset 10 as a more conservative
single-qubit approximation proxy.

This remains a logic-layer cost model: no approximate rotation sequence is
emitted, no synthesis runtime is measured, and no hardware mapping is used.

## Summary

| portfolio | model | epsilon | T/Rz | W/L/T | mean relative | mean RevKit synth score | mean extra T |
|---|---|---:|---:|---:|---:|---:|---:|
| resource_nmcts_family | ross_selinger_z | 1e-03 | 30 | 177/0/0 | -95.03% | 1611.39 | 1566.44 |
| resource_nmcts_family | ross_selinger_z | 1e-06 | 60 | 177/0/0 | -96.51% | 3216.99 | 3132.88 |
| resource_nmcts_family | ross_selinger_z | 1e-10 | 100 | 177/0/0 | -97.11% | 5357.80 | 5221.47 |
| resource_nmcts_family | selinger_su2 | 1e-03 | 50 | 177/0/0 | -96.22% | 2681.79 | 2610.73 |
| resource_nmcts_family | selinger_su2 | 1e-06 | 90 | 177/0/0 | -97.01% | 4822.59 | 4699.32 |
| resource_nmcts_family | selinger_su2 | 1e-10 | 143 | 177/0/0 | -97.38% | 7659.16 | 7466.70 |
| traditional_baseline_family | ross_selinger_z | 1e-03 | 30 | 177/0/0 | -94.10% | 1611.39 | 1566.44 |
| traditional_baseline_family | ross_selinger_z | 1e-06 | 60 | 177/0/0 | -96.05% | 3216.99 | 3132.88 |
| traditional_baseline_family | ross_selinger_z | 1e-10 | 100 | 177/0/0 | -96.84% | 5357.80 | 5221.47 |
| traditional_baseline_family | selinger_su2 | 1e-03 | 50 | 177/0/0 | -95.66% | 2681.79 | 2610.73 |
| traditional_baseline_family | selinger_su2 | 1e-06 | 90 | 177/0/0 | -96.71% | 4822.59 | 4699.32 |
| traditional_baseline_family | selinger_su2 | 1e-10 | 143 | 177/0/0 | -97.19% | 7659.16 | 7466.70 |

## Boundary

- This is stricter than the lower-bound Rz-phase score but still not exact synthesis.
- Exact or approximate rotation synthesis can change constants and depth scheduling.
- The result should be used to set a phase/Rz-aware emitter target, not as a final Clifford+T proof.
