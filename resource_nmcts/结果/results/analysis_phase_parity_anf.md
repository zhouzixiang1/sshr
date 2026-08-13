# Phase-Parity ANF Baseline

This run emits a concrete parity-phase ANF baseline.  It expands each
ANF monomial into merged parity-phase gadgets using exact rational
coefficients and verifies every function as a phase oracle up to a
global phase.

This is a phase/Rz-aware internal emitter.  It is not the same target
as the existing bit-flip Resource-NMCTS circuits, and it is still a
logic-layer resource model rather than hardware mapping.

- rows: 177
- usable rows: 177
- verified up to global phase: 177/177
- mean lower-bound score: 10.11
- mean CNOT: 87.40
- mean depth: 114.96
- mean total Rz: 27.56
- mean non-Clifford Rz: 21.75
- max angle denominator: 32

## Comparison with RevKit `oracle_synth`

Rows compare the internal phase-parity ANF emitter against RevKit's
Rz-phase lower-bound netlist.  Lower is better for every metric.

| metric | items | W/L/T | mean relative |
|---|---:|---:|---:|
| lower_bound_score | 177 | 40/137/0 | +69.25% |
| score_plus_1_per_rz | 177 | 177/0/0 | -48.16% |
| score_plus_1p5_per_rz | 177 | 177/0/0 | -53.26% |
| score_plus_2_per_rz | 177 | 177/0/0 | -56.05% |
| score_plus_4_per_rz | 177 | 177/0/0 | -60.60% |
| synth_tperrz30_score | 177 | 177/0/0 | -64.98% |
| synth_tperrz60_score | 177 | 177/0/0 | -65.33% |
| non_clifford_rz | 177 | 171/0/6 | -63.33% |
| total_rz | 177 | 173/3/1 | -45.10% |
| CNOT | 177 | 34/140/3 | +34.36% |
| depth | 177 | 77/97/3 | +2.40% |

## Interpretation

- The emitter is exact up to global phase, which is the natural equivalence for phase oracles.
- The lower-bound score charges only T-like Rz rotations; non-Clifford Rz rotations are reported separately.
- If this baseline is poor under lower-bound or synthesized-Rz scoring, that is useful evidence: a naive parity-phase expansion is not enough, and a learned phase/Rz-aware search must reduce parity gadget count or rotation spectrum.
