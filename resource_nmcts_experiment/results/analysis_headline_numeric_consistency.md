# Headline Numeric Consistency Audit

This audit recomputes central abstract numbers from generated evidence files and checks that both author and anonymous LaTeX sources contain the corresponding headline tokens.

## Status counts

- pass: 15

## Claims

| claim | status | computed | expected | source | manuscript tokens |
|---|---|---|---|---|---|
| n<=6 Pareto vs direct ANF mean T-count reduction | pass | pairs=177; W/L/T=172/0/5; mean=-72.25% | pairs=177; W/L/T=172/0/5; mean=-72.25% | `results/summary_weight_robustness.csv` | 72.25% |
| n<=6 Pareto vs direct ANF paired score | pass | pairs=177; W/L/T=172/1/4; mean=-67.80% | pairs=177; W/L/T=172/1/4; mean=-67.80% | `results/summary_paired_statistical_evidence.csv` | 177; 67.80% |
| n<=6 Pareto vs ESOP beam paired score | pass | pairs=177; W/L/T=174/0/3; mean=-36.09% | pairs=177; W/L/T=174/0/3; mean=-36.09% | `results/summary_paired_statistical_evidence.csv` | 174/0/3 |
| n<=6 Pareto vs ESOP-MILP paired score | pass | pairs=177; W/L/T=167/3/7; mean=-29.84% | pairs=177; W/L/T=167/3/7; mean=-29.84% | `results/summary_paired_statistical_evidence.csv` | 167/3/7 |
| n<=6 Pareto vs SSHR-H paired score | pass | pairs=177; W/L/T=173/4/0; mean=-41.06% | pairs=177; W/L/T=173/4/0; mean=-41.06% | `results/summary_paired_statistical_evidence.csv` | 173/4/0 |
| ROS-style LUT best-K paired score | pass | pairs=309; W/L/T=309/0/0; mean=-84.27% | pairs=309; W/L/T=309/0/0; mean=-84.27% | `results/summary_paired_statistical_evidence.csv` | 309/0/0 |
| mockturtle XAG n<=6 paired score | pass | pairs=177; W/L/T=166/11/0; mean=-31.50% | pairs=177; W/L/T=166/11/0; mean=-31.50% | `results/summary_paired_statistical_evidence.csv` | 166/11/0 |
| mockturtle XAG n=14 paired score | pass | pairs=64; W/L/T=64/0/0; mean=-91.49% | pairs=64; W/L/T=64/0/0; mean=-91.49% | `results/summary_paired_statistical_evidence.csv` | 64/0/0 |
| CirKit AIG/MC n<=6 paired score | pass | pairs=177; W/L/T=177/0/0; mean=-62.34% | pairs=177; W/L/T=177/0/0; mean=-62.34% | `results/summary_paired_statistical_evidence.csv` | 177/0/0 |
| CirKit AIG/MC n=14 paired score | pass | pairs=64; W/L/T=64/0/0; mean=-94.46% | pairs=64; W/L/T=64/0/0; mean=-94.46% | `results/summary_paired_statistical_evidence.csv` | 64/0/0 |
| RevKit CLI exact oracle paired score | pass | pairs=177; W/L/T=173/0/4; mean=-67.28% | pairs=177; W/L/T=173/0/4; mean=-67.28% | `results/summary_paired_statistical_evidence.csv` | 173/0/4 |
| phase diverse top-512 shortlist tracks wide search | pass | held_out_items=38; exact_scored=512/8192; mean_delta=-0.01% | held_out_items=38; exact_scored=512/8192; |mean_delta|<=0.0125% | `results/summary_phase_policy_random_control.csv` | 512 of 8192; 0.01%; T/R_z=30 |
| sparse depth-2/4 frontier bridge time reduction | pass | bridge_rows=3; time_range=24.94%--28.88%; score_tied=True | bridge_rows=3; time_range=24.94%--28.88%; score_tied=True | `results/summary_sparse_depth_frontier.csv` | 24.94--28.88% |
| learned sparse depth-4 gate selected operating point | pass | pairs=144; score_wlt_vs_sparse=0/0/144; time_saving=13.43% | pairs=144; score_wlt_vs_sparse=0/0/144; time_saving=13.43% | `results/summary_sparse_depth4_gate_threshold_operating_points.csv` | 144-pair; 13.43% |
| headline verification row count | pass | verified_total=15,294; bridge_400_400=True; all_exact=True | verified_total=15,294; bridge_400_400=True; all_exact=True | `paper_latex/figures/submission_v36/source_data/fig5_validation.csv` | 15,294; 400/400 |
