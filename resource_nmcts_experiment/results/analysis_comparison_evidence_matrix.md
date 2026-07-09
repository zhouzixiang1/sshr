# Comparison Evidence Matrix

This table consolidates already-generated experiment evidence into the reviewer-facing comparison scope used by the manuscript.

| evidence block | scope | verified rows | main result | boundary |
|---|---:|---:|---|---|
| Internal logical baselines | n=3-6 | 1770/1770 | Pareto vs direct ANF 172/1/4, -67.80%; vs ESOP-MILP 167/3/7, -29.84% | Same verifier/cost model; includes direct, AND-direct, ESOP beam/MILP, SSHR-H, MCTS, affine, and Pareto variants. |
| Exported SSHR/ABC/BDD extension | n=3-6 | 1416/1416 | Resource-NMCTS vs SSHR-I CNOT 172/5/0, -29.48%; vs ABC-XAG 177/0/0, -64.15% | SSHR-I rows use an 8 s Gurobi budget; ABC/BDD rows are logical estimates over exported truth tables. |
| ROS-style LUT proxy | n=3,4,5,6,14,15,16,18 | 309/309 best rows; 927/927 K-sweep rows; 927/927 garbage-proxy rows; 1059/1059 garbage-budget rows | Pareto vs best-K proxy 309/0/0, -84.27% | Verified LUT and executable garbage-pressure proxies only; no official ROS SAT garbage management, reversible emission, or hardware mapping. |
| Published STG optimum-library counterpoint | n=4-5 | 270/270 | Pareto vs STG T-count optimum 0/40/14, +84.26%; vs direct ANF on STG slice 50/4/0, -58.10% | Public n=4/5 spectral-representative optimum-library table; this is a strong small-function counterpoint, not a reproduced ROS flow or scalable compiler baseline. |
| mockturtle KLUT-to-XAG probe | n=3,4,5,6,14 | 241/241 | n<=6 166/11/0, -31.50%; n=14 64/0/0, -91.49% | Official-header XAG resynthesis probe; still a logical proxy, not full ROS or reversible garbage management. |
| CirKit AIG/MC probe | n=3,4,5,6,14 | 241/241 | n<=6 177/0/0, -62.34%; n=14 64/0/0, -94.46% | AIG multiplicative-complexity probe; strongest current depth-oriented external counterpoint. |
| Legacy RevKit CLI exact oracle | n=3-6 | 708/708 | Pareto vs best-score portfolio 173/0/4, -67.28% | Exact reversible oracle permutation; CNOT/depth are derived from Toffoli-control distributions and ancilla is a visible tradeoff. |
| RevKit phase/Rz branch | n=3-6 | 531/531 | Affine phase vs RevKit oracle_synth 177/0/0, -65.50% | Logical phase/Rz proxy verified up to global phase; sequence evidence is a coarse smoke check, not optimal Clifford+T synthesis. |
| Learned phase pruning | n=3-6 | 7611/7611 | Held-out n=6 rank-diverse top512 vs wide128 0/7/31, +0.00% | Policy-pruned affine candidate ranking; evidence is held-out exact scoring, not a standalone compiler backend. |
| High-dimensional frontier search | n=20,24,28,32,40,48,56,64 | 2088/2088 | Stage-gated vs all-depth scale 0/4/92, +0.04% score; -25.43% time; ultra n=48,56,64 stress 480/480 plan+circuit verified | Term-set symbolic verification with emitted-circuit ANF checks; depth frontier is a planning guard, not a hardware scheduler. |
| Complete truth-table bridges | n=21-25 | 400/400 | Bridge rows verify plan, emitted symbolic circuit, and complete truth table for n=21-25. | Bridge set is intentionally narrow because complete truth tables grow exponentially. |

## Source files

- Internal logical baselines: `results/raw_traditional_resource.csv`
- Exported SSHR/ABC/BDD extension: `results/raw_external_traditional_resource_n6.csv`
- ROS-style LUT proxy: `results/raw_ros_lut_proxy_best.csv; results/raw_ros_lut_proxy_sweep.csv; results/raw_ros_lut_garbage_proxy.csv; results/raw_ros_lut_garbage_budget_frontier.csv`
- Published STG optimum-library counterpoint: `results/raw_stg_published_benchmark.csv; results/summary_stg_published_benchmark.csv`
- mockturtle KLUT-to-XAG probe: `results/raw_mockturtle_xag_probe.csv; results/raw_mockturtle_xag_highdim_probe.csv`
- CirKit AIG/MC probe: `results/raw_cirkit_aig_probe.csv; results/raw_cirkit_aig_highdim_probe.csv`
- Legacy RevKit CLI exact oracle: `results/raw_revkit_cli_multiflow_traditional.csv`
- RevKit phase/Rz branch: `results/raw_phase_parity_affine.csv`
- Learned phase pruning: `results/raw_phase_affine_policy_rank_diverse.csv`
- High-dimensional frontier search: `results/raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv; results/raw_screen_scale_depth_frontier_terms.csv; results/raw_screen_scale_ultra_scale64_terms.csv`
- Complete truth-table bridges: `results/raw_truth_bridge_terms.csv; results/raw_truth_bridge_n23_terms.csv; results/raw_truth_bridge_n23_large_frontier_terms.csv; results/raw_truth_bridge_n23_cost_time003_frontier_terms.csv; results/raw_truth_bridge_n24_terms.csv; results/raw_truth_bridge_n25_terms.csv`
