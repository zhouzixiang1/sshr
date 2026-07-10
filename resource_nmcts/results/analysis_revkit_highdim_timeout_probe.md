# RevKit High-dimensional Timeout Probe

Input: `resource_nmcts_experiment/results/raw_highdim_resource.csv`
n range: 14..14; requested limit: 8; per-row timeout: 30s; workers: 4.

Each RevKit `oracle_synth` call was executed in a disposable subprocess.
Rows that exceeded the cutoff were terminated and recorded as timeout rows.

## Summary

- rows attempted: 8
- usable RevKit circuits returned: 1
- timed out rows: 7
- other errors: 0

| n | items | usable | timeouts | other errors | median time (s) | max time (s) |
|---:|---:|---:|---:|---:|---:|---:|
| 14 | 8 | 1 | 7 | 0 | 30.00 | 30.01 |

## Returned-row Comparison Against `and_resource_nmcts`

Only rows for which RevKit returned a circuit are included here.
`lower-bound` is the raw RevKit phase-netlist score; `score+1/Rz` adds one score unit per non-Clifford Rz rotation.

| name | target score | RevKit lower-bound score | non-Clifford Rz | lower-bound result | RevKit score+1/Rz | score+1/Rz result |
|---|---:|---:|---:|---:|---:|---:|
| anf_n14_10 | 10358.47 | 2948.79 | 32767 | loss (+251.28%) | 35715.79 | win (-71.00%) |

## Interpretation Boundary

- This is an engineering scalability and adapter-boundary probe, not a paired resource benchmark.
- Timed-out rows have no RevKit circuit metrics and are not averaged against Resource-NMCTS.
- Returned high-dimensional rows are still Rz-phase lower-bound netlists when `rz_non_clifford > 0`; rotation-aware scores are sensitivity checks, not emitted Clifford+T sequences.
- The result supports restricting the current formal RevKit API comparison to the validated `n <= 6` truth-table suite.
- Future RevKit high-dimensional comparison would need either a faster RevKit configuration, a different RevKit/CirKit flow, or smaller/highly structured functions that return within the same cutoff.
