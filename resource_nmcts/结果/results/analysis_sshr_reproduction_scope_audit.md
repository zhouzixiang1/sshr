# SSHR Reproduction Scope Audit

This audit records which SSHR-facing evidence is reproduced, source-anchored, or deliberately bounded in the current logical-layer submission package.

## Status counts

- pass: 8

## Coverage counts

- covered: 7
- partial: 1

## Scope matrix

| item | audit status | coverage | current evidence | supported claim | excluded claim |
|---|---|---|---|---|---|
| SSHR literature and method boundary | pass | covered | The manuscript cites SSHR, states that the proposed method does not search parallelotope candidates, and uses SSHR as a CNOT-oriented small-function baseline. | SSHR is a relevant structured baseline for small Boolean-function oracle synthesis. | The proposed method is not an SSHR variant and does not inherit SSHR's CNOT-only objective. |
| SSHR Table VIII candidate-space reproduction | pass | covered | The package reruns the local SSHR parallelotope enumerator on full n=3..8 hypercubes and matches all six Table VIII candidate-space counts, including n=8 -> 609441. | The paper can explain why SSHR's search space is a CNOT-oriented parallelotope counterpoint rather than the proposed ANF/FPRM action space. | This count reproduction does not rerun SSHR-I Gurobi tables or every published SSHR random benchmark. |
| SSHR-H same-task baseline rows | pass | covered | The traditional bit-flip benchmark includes 177 correct SSHR-H rows and the manuscript keeps SSHR-H visible as the best mean-CNOT baseline in the traditional table. | Resource-NMCTS is compared with a same-function SSHR-H implementation on all traditional benchmark functions. | The SSHR-H row is not evidence of CNOT-only dominance by the proposed method. |
| SSHR-I CNOT/T extension rows | pass | partial | The external n<=6 extension includes SSHR-I CNOT-objective and T-objective rows for the same 177 functions with correctness checks and explicit timeout metadata. | The manuscript can use SSHR-I as a time-limited CNOT/T-oriented counterpoint on the matched traditional slice. | The n<=6 extension is not an exact certificate for all SSHR-I random-paper settings. |
| n<=4 exact/pilot SSHR-I cross-check | pass | covered | The n<=4 external pilot records 72 functions and 216 SSHR-H/SSHR-I rows, and exact small-slice analyses include SSHR-I references as counterpoints. | The small-function exact slice has a harder SSHR-I sanity check than the broad n<=6 timed extension. | Even this slice is a counterpoint under the paper's logical resource projection, not a proof of global reversible optimality. |
| SSHR tradeoff in resource-weight sensitivity | pass | covered | The resource-weight audit explicitly keeps SSHR-H and SSHR-I CNOT-only losses visible while showing paper-score and T-score advantages. | The proposed method improves T-count and weighted resource profiles against SSHR while preserving the CNOT-only counterexample. | Weighted-score wins cannot be rewritten as all-metric or CNOT-only SSHR dominance. |
| Comparison and claim-boundary integration | pass | covered | Comparison answer, target-validity, threats-to-validity, and claim-scope gates all mark SSHR as a CNOT counterpoint rather than the whole comparison target. | The manuscript's SSHR comparison is meaningful and bounded by explicit claim-scope checks. | No paper-facing text may claim full SSHR replacement, universal optimality, or hardware-mapped dominance. |
| Reviewer payload visibility | pass | covered | The submission package exposes the comparison role, reviewer concern brief, and artifact guide so a reviewer can locate SSHR rows and their boundary quickly. | The uploaded artifact makes the SSHR comparison and its limited role findable without reading implementation history. | Support-package visibility does not add a new SSHR random-table rerun. |
