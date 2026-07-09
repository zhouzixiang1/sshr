# Benchmark Function Diversity Audit

This audit records structural diversity behind the paper's comparison targets.  It is descriptive and post-hoc over existing raw CSVs.

## Status counts

- pass: 5

| slice | role | abstraction | items | raw rows | verified rows | n scope | family/profile coverage | density coverage | degree coverage | term range | boundary | status |
|---|---|---|---:|---:|---:|---|---|---|---|---|---|---|
| Matched n<=6 truth-table core | primary same-task diversity check | stored truth table | 177 | 1770 | 1770 | n=3--6 | arithmetic/mux=5; parity/affine=4; random truth-table=160; threshold/majority=8 | balanced=175; dense=1; sparse=1 | degree 1--6 | ANF terms 2--38 | The density distribution is intentionally reported; these rows are structurally varied but not a distributional sample of all Boolean functions. | pass |
| Published STG optimum counterpoint | tiny-function optimum boundary | stored truth table | 54 | 270 | 270 | n=4--5 | published STG=54 | balanced=35; sparse=19 | degree 2--5 | ANF terms 1--21 | This slice validates a hard small-function counterpoint rather than a headline victory over precomputed optimum libraries. | pass |
| External high-dimensional ANF/network probes | external-tool structure stress | symbolic ANF plus exported logic-network probes | 1876 | 1876 | 1876 | n=14--18 | generated random ANF=1748; highdim=128 | not stored for symbolic rows | not expanded for large-n rows | terms 2--2276 | These rows stress external toolchains but remain logical-network proxies rather than reversible hardware mapping. | pass |
| Large symbolic term-set stress | large-n scalability diversity check | symbolic generated term sets | 1128 | 9552 | 9552 | n=20--64 | deep=3184; mixed=3184; shallow=3184 | not stored for symbolic rows | not expanded for large-n rows | terms 26--288 | This is large-dimensional search evidence, not exhaustive truth-table enumeration. | pass |
| Complete truth-table bridge slices | large-n semantic bridge | generated term sets with complete truth-table construction | 88 | 880 | 880 | n=21--30 | deep=300; mixed=290; shallow=290 | not stored for symbolic rows | not expanded for large-n rows | terms 24--235 | Bridge slices are deliberately narrow because truth tables grow exponentially. | pass |

## Interpretation

- The small truth-table core contains named affine, threshold/majority, arithmetic/mux, and random truth-table families, with exact ANF degree and term-count measurements.
- Most small truth-table rows are balanced-density functions; that fact is recorded as a boundary rather than hidden as representativeness.
- The large-n rows add symbolic and bridge-verified search stress, but they do not become exhaustive large-n Boolean-function coverage.

## Source files

- **Matched n<=6 truth-table core**: `results/raw_traditional_resource.csv`
- **Published STG optimum counterpoint**: `results/raw_stg_published_benchmark.csv`
- **External high-dimensional ANF/network probes**: `results/raw_cirkit_aig_highdim_probe.csv; results/raw_external_highdim_resource.csv; results/raw_external_highdim_scale_resource.csv; results/raw_external_mega_highdim_resource.csv; results/raw_external_ultra_highdim_resource.csv; results/raw_highdim_resource.csv; results/raw_highdim_scale_resource.csv; results/raw_mega_highdim_resource.csv; results/raw_mockturtle_xag_highdim_probe.csv; results/raw_ultra_highdim_resource.csv`
- **Large symbolic term-set stress**: `results/raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv; results/raw_screen_scale_depth_frontier_policy_generalization_terms.csv; results/raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv; results/raw_screen_scale_depth_frontier_policy_terms.csv; results/raw_screen_scale_depth_frontier_terms.csv; results/raw_screen_scale_extended_terms.csv; results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv; results/raw_screen_scale_terms.csv; results/raw_screen_scale_ultra_scale64_terms.csv; results/raw_screen_scale_width12_probe_terms.csv; results/raw_screen_scale_width24_probe_terms.csv; results/raw_screen_scale_width6_probe_terms.csv`
- **Complete truth-table bridge slices**: `results/raw_schedule_truth_bridge_n23_terms.csv; results/raw_schedule_truth_bridge_terms.csv; results/raw_truth_bridge_n23_cost_time003_frontier_terms.csv; results/raw_truth_bridge_n23_large_frontier_terms.csv; results/raw_truth_bridge_n23_terms.csv; results/raw_truth_bridge_n24_terms.csv; results/raw_truth_bridge_n25_terms.csv; results/raw_truth_bridge_n26_terms.csv; results/raw_truth_bridge_n27_terms.csv; results/raw_truth_bridge_n28_terms.csv; results/raw_truth_bridge_n29_terms.csv; results/raw_truth_bridge_n30_terms.csv; results/raw_truth_bridge_terms.csv`
