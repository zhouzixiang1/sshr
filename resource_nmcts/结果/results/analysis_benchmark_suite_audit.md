# Benchmark Suite Audit

This audit records what benchmark slices are represented in the paper package, how each slice is verified, and which representativeness boundary remains.

## Status counts

- pass: 7

## Aggregate coverage

- raw rows across suite families: 39849
- verified rows across suite families: 39368

| suite | role | n scope | instances | raw rows | verified rows | methods | verification route | boundary | status |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| Matched small Boolean oracles | primary same-task benchmark | n=3--6 | 177 | 3819 | 3819 | 18 | complete truth table for n<=6 rows; timeout/skipped rows remain explicit | Small functions are enumerable and fair for method comparison, but they are not a large-n optimality claim. | pass |
| Published tiny-function optimum counterpoint | optimum-library boundary | n=4--5 | 54 | 270 | 270 | 5 | public n=4/5 truth tables with complete correctness checks | Used as a small-function boundary, not as evidence that the proposed search beats precomputed optima. | pass |
| External logic-network probes | toolchain stress test | n=3--18 | 373 | 968 | 968 | 4 | export/readback, ABC BLIF/Verilog, XAG/AIG/API checks where available | These are logical probes, not full ROS SAT garbage management, reversible emission, routing, or hardware mapping. | pass |
| RevKit reversible and phase probes | reversible/phase counterpoint | n=3--6 | 181 | 10286 | 10109 | 55 | exact reversible permutation checks, phase verification up to global phase, and coarse rotation-sequence smoke checks | Rz rows are proxy-level phase evidence and do not constitute final approximate Clifford+T rotation synthesis. | pass |
| Large symbolic term-set scaling | scalability and stress test | n=20--64 | 384 | 7392 | 7392 | 10 | symbolic ANF and emitted-circuit ANF checks | Symbolic large-n rows are not exhaustive truth-table enumeration and do not prove global optimality. | pass |
| Complete truth-table bridge slices | large-n semantic bridge | n=21--30 | 60 | 880 | 880 | 10 | complete truth-table construction plus plan and emitted-circuit checks | The bridge is intentionally narrow because full truth tables grow exponentially. | pass |
| Learned-control and stochastic controls | causal attribution and stability control | n=3--40 | 385 | 16234 | 15930 | 46 | same-budget random controls, disjoint training, validation, and test splits, independent seeds, and semantic checks | These rows support bounded control gains; they do not imply that deep learning or reinforcement learning alone causes the main resource reduction. | pass |

## Source files

- **Matched small Boolean oracles**: `results/raw_external_traditional_resource_n4.csv; results/raw_external_traditional_resource_n5.csv; results/raw_external_traditional_resource_n6.csv; results/raw_traditional_resource.csv`
- **Published tiny-function optimum counterpoint**: `results/raw_stg_published_benchmark.csv`
- **External logic-network probes**: `results/raw_caterpillar_xag_api_best.csv; results/raw_cirkit_aig_highdim_probe.csv; results/raw_cirkit_aig_probe.csv; results/raw_mockturtle_xag_highdim_probe.csv; results/raw_mockturtle_xag_probe.csv; results/raw_ros_lut_proxy_best.csv`
- **RevKit reversible and phase probes**: `results/raw_phase_affine_policy_rank_diverse.csv; results/raw_phase_parity_affine.csv; results/raw_phase_parity_affine_wide128.csv; results/raw_phase_parity_anf.csv; results/raw_phase_parity_fprm.csv; results/raw_phase_rotation_sequence_smoke_audit.csv; results/raw_revkit_cli_multiflow_traditional.csv; results/raw_revkit_oracle_synth_traditional.csv`
- **Large symbolic term-set scaling**: `results/raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv; results/raw_screen_scale_depth_frontier_policy_generalization_terms.csv; results/raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv; results/raw_screen_scale_depth_frontier_policy_terms.csv; results/raw_screen_scale_extended_terms.csv; results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv; results/raw_screen_scale_terms.csv; results/raw_screen_scale_ultra_scale64_terms.csv`
- **Complete truth-table bridge slices**: `results/raw_schedule_truth_bridge_n23_terms.csv; results/raw_schedule_truth_bridge_terms.csv; results/raw_truth_bridge_n23_cost_time003_frontier_terms.csv; results/raw_truth_bridge_n23_large_frontier_terms.csv; results/raw_truth_bridge_n23_terms.csv; results/raw_truth_bridge_n24_terms.csv; results/raw_truth_bridge_n25_terms.csv; results/raw_truth_bridge_n26_terms.csv; results/raw_truth_bridge_n27_terms.csv; results/raw_truth_bridge_n28_terms.csv; results/raw_truth_bridge_n29_terms.csv; results/raw_truth_bridge_n30_terms.csv; results/raw_truth_bridge_terms.csv`
- **Learned-control and stochastic controls**: `results/raw_bitflip_neural_budget_sweep.csv; results/raw_bitflip_random_prior_control.csv; results/raw_mcts_budget_policy_decisions.csv; results/raw_phase_affine_policy.csv; results/raw_phase_affine_policy_rank_diverse.csv; results/raw_sparse_depth4_gate_generalization.csv`
