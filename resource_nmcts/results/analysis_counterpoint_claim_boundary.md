# Counterpoint Claim-Boundary Audit

This audit records the strongest opposing evidence that bounds the paper's comparison claims.

| counterpoint | opposing evidence | favorable evidence | claim boundary |
|---|---|---|---|
| SSHR family CNOT optimum | vs SSHR-I CNOT: CNOT 0/168/9, +62.06%; vs SSHR-H: CNOT 43/128/6, +18.99% | score vs SSHR-I CNOT 173/4/0, -31.89%; score vs SSHR-H 173/4/0, -41.06% | Use SSHR as a small-function CNOT counterpoint; claim T-count and weighted-score advantage, not CNOT dominance. |
| CirKit AIG/MC depth | depth 16/156/5, +93.16% | score 177/0/0, -62.34% | Use CirKit as a depth-oriented external probe; do not claim depth dominance over logic-network synthesis. |
| Caterpillar API CNOT pressure | CNOT 4/173/0, +195.18% | score 177/0/0, -47.94% | Use Caterpillar as a bounded ANF-XAG implementation-family counterpoint; do not claim CNOT-only, full-ROS, or hardware-mapped dominance. |
| RevKit exact-oracle auxiliary lines | peak ancilla 0/169/8, +153.11% | score 173/0/4, -67.28% | Use RevKit CLI as an exact reversible-oracle probe; do not claim line-count or mapped Clifford+T dominance. |
| Learned prior is incremental | time 37/140/0, +18.77% versus no-prior rerun | score 29/0/148, -0.78% | Frame AI as search control, ranking, pruning, and gating; do not claim deep RL alone explains the main resource drop. |
| Large-n verification is bounded | complete truth-table enumeration is limited to bridge slices | symbolic scale rows 1608/1608; complete truth-table bridge rows 700/700 | Claim logical correctness inside symbolic and bridge-verification envelopes, not exhaustive large-dimensional benchmarking. |
