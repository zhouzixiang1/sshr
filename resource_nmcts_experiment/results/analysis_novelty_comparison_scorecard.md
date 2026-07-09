# Novelty and Comparison Scorecard

This scorecard answers whether the comparison set is meaningful and whether the novelty claim is bounded by explicit evidence.

## Status counts

- pass: 6

| reviewer question | status | answer | evidence | limitation |
|---|---|---|---|---|
| Is this only an SSHR variant? | pass | No. Resource-NMCTS searches ANF/FPRM and Boolean-ring actions; SSHR is a CNOT-oriented small-function counterpoint. | Tables~\ref{tab:contribution-map}, \ref{tab:counterpoint-boundary} | SSHR remains a strong CNOT reference; the paper claims T-count and weighted-score gains, not CNOT dominance. |
| Are the primary baselines matched to the oracle task? | pass | Yes. Direct ANF, AND-direct ANF, ESOP/MILP, BDD/ABC, and SSHR rows are paired on the same Boolean-oracle functions and resource score. | Tables~\ref{tab:evidence-matrix}, \ref{tab:paired-statistics} | These prove matched logical-resource improvements, not hardware-mapped optimality. |
| Does the comparison go beyond internal baselines? | pass | Yes. The package includes ROS-style LUT, mockturtle, CirKit, RevKit CLI, ABC/BDD, and RevKit phase/Rz probes. | Fig.~\ref{fig:baselines}; Tables~\ref{tab:ros-line}, \ref{tab:revkit-cli} | External rows are logic-level or exact-oracle probes; they are not full hardware mapping or full ROS reproduction. |
| Does a score win hide unfavorable resources? | pass | No. Counterpoint, Pareto, and schedule-proxy audits report where SSHR, CirKit, and RevKit remain strong. | Tables~\ref{tab:counterpoint-boundary}, \ref{tab:multimetric-nondominated}, \ref{tab:schedule-proxy-audit} | The correct claim is a strong T/weighted-score point with explicit CNOT, depth, ancilla, and runtime tradeoffs. |
| Is AI/MCTS actually isolated from deterministic search? | pass | Yes. The search-control audit separates heuristic, beam, no-MCTS, MCTS, Pareto, learned-prior, random-prior, random-depth, and phase controls. | Tables~\ref{tab:search-control-baseline-audit}, \ref{tab:learned-control-audit} | The learned components are promoted only where they give bounded quality, pruning, or budget-allocation evidence. |
| Does the study go beyond small truth-table functions? | pass | Yes. Large n=20,24,28,32,40 symbolic term-set runs and an n=48,56,64 ultra-scale stress slice are paired with n=21--28 complete truth-table bridge slices. | Tables~\ref{tab:scale-audit}, \ref{tab:ultra-scale64-stress}, \ref{tab:ultra-scale64-resource-profile}; Fig.~\ref{fig:validation} | Large-dimensional evidence is symbolic plus bridge-verified, not exhaustive truth-table benchmarking for all large n. |

## Missing Anchors

| reviewer question | missing files | missing manuscript tokens | missing support tokens |
|---|---|---|---|
| Is this only an SSHR variant? | none | none | none |
| Are the primary baselines matched to the oracle task? | none | none | none |
| Does the comparison go beyond internal baselines? | none | none | none |
| Does a score win hide unfavorable resources? | none | none | none |
| Is AI/MCTS actually isolated from deterministic search? | none | none | none |
| Does the study go beyond small truth-table functions? | none | none | none |
