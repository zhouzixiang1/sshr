# ROS-Style LUT Garbage Proxy

This analysis re-runs the verified best-K ABC LUT mappings and compares
three reversible garbage policies over the same LUT DAG. It is a
resource-pressure proxy, not official ROS SAT garbage management.

## Status counts

- pass: 927

## Policy summary

| policy | rows | correct | mean log10(T+1) | mean peak ancilla | mean log10(score+1) | peak vs keep-all | score vs keep-all |
|---|---:|---:|---:|---:|---:|---|---|
| keep_all_bennett | 309 | 309 | 3.29 | 6056.04 | 3.36 | 0/309/0 | 0/309/0 |
| fanout_checkpoint | 309 | 309 | 5.80 | 573.70 | 5.86 | 186/123/0 | 0/92/217 |
| zero_checkpoint | 309 | 309 | 5.93 | 27.37 | 5.99 | 186/123/0 | 0/92/217 |

## Interpretation

- Fanout-checkpoint and zero-checkpoint rows measure the qubit/operation trade-off that a garbage-management stage is meant to expose.
- A lower peak-ancilla result is useful only as a line-pressure sensitivity result when its T-count and score increase are reported alongside it.
- These rows strengthen the ROS-facing comparison boundary but still exclude claims about the official ROS SAT algorithm.
