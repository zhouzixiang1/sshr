# ROS Reproduction Gap Audit

This audit separates verified ROS-style proxy evidence from full official ROS reproduction.

## Status counts

- pass: 8

## Coverage counts

- covered: 4
- not reproduced: 1
- partial: 3

## Boundary matrix

| item | audit status | coverage | current coverage | supported claim | excluded claim |
|---|---|---|---|---|---|
| ROS literature and task anchor | pass | covered | The manuscript and bibliography cite ROS and frame the current study as logical-layer Boolean-oracle synthesis. | ROS is a relevant resource-constrained oracle-synthesis comparator family. | This citation anchor alone does not reproduce the ROS implementation. |
| Verified LUT K-sweep proxy | pass | partial | The project runs an ABC if -K sweep for K=3,4,5, verifies each mapped BLIF truth table, and selects the best K per function. | The paper can report a verified ROS-style LUT proxy and best-K pressure test. | The proxy is not the official ROS mapper or reversible implementation flow. |
| Line and garbage-pressure sensitivity | pass | partial | The line-sensitivity audit reselects the verified LUT sweep under min-ancilla and line-weighted objectives. | The score advantage is robust to line-aware LUT proxy selectors. | This is not SAT garbage management and cannot be called a full ROS reproduction. |
| Official ROS SAT garbage management | pass | not reproduced | The manuscript, README, and line-sensitivity audit explicitly mark SAT garbage management as not reproduced. | The package is transparent about the missing official ROS component. | No result may be described as beating or reproducing full ROS with SAT garbage management. |
| Reversible emission and exact-oracle counterpoint | pass | partial | Legacy RevKit CLI probes synthesize exact oracle permutations and serve as a separate reversible-synthesis counterpoint. | The paper has a genuine exact reversible-oracle toolchain probe in addition to LUT/XAG/AIG proxies. | The RevKit CLI probe is not the ROS hierarchical LUT plus SAT garbage-management flow. |
| External toolchain availability boundary | pass | covered | Toolchain readiness records ABC, mockturtle, CirKit, RevKit API, and legacy RevKit/CirKit availability and separates them from full ROS. | The external-probe environment is reproducible and provenance-recorded. | Tool availability is not the same as official ROS reproduction. |
| Claim wording and comparison protocol | pass | covered | Claim matrix, comparison protocol, claim-scope lint, and manuscript limitations state the ROS boundary. | The paper can use ROS-style evidence without overclaiming full ROS reproduction. | The current evidence cannot support a full-ROS or hardware-mapped dominance statement. |
| Reviewer-facing support visibility | pass | covered | The submission package exposes the ROS-style proxy command and states that full ROS SAT garbage management is not included. | The upload package makes the ROS boundary visible without requiring the reviewer to infer it from code. | Support-package visibility does not add a new official ROS experiment. |
