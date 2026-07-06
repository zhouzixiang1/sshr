# Resource-Constrained Neural MCTS Oracle Synthesis

This directory implements a new logic-level line of work for:

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

The method does not use SSHR parallelotope candidates.  It treats Boolean
oracle synthesis as a symbolic factorization search over ANF/XAG-style
compute/uncompute plans, then verifies the generated oracle circuits by
classical simulation.

Core commands:

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python tests_smoke.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset rollout --gate-mode logical_and --label-mode rollout --max-depth 3 --child-branch 2 --out models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset smoke
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset evidence_affine --model models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset evidence_affine
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset ablation_affine --model models/action_scorer_rollout_logical_and.pt --resume
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset ablation_affine
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset ablation_affine
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_small --model models/action_scorer_rollout_logical_and.pt --resume
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset traditional_small
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset traditional_small
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_resource --model models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset traditional_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset traditional_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_resource --only-methods and_affine_nmcts,and_resource_nmcts,and_pareto_resource_nmcts --model /tmp/nonexistent_model.pt --out-dir /tmp/resource_nmcts_traditional_no_model --workers 10 --checkpoint-every 50
cp /tmp/resource_nmcts_traditional_no_model/raw_traditional_resource.csv results/raw_traditional_resource_no_prior.csv
cp /tmp/resource_nmcts_traditional_no_model/summary_traditional_resource.csv results/summary_traditional_resource_no_prior.csv
cp /tmp/resource_nmcts_traditional_no_model/manifest_traditional_resource.json results/manifest_traditional_resource_no_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_neural_prior_ablation.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_resource_sweep.py --model models/action_scorer_rollout_logical_and.pt --workers 10
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_resource_sweep.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset large_resource_core --model models/action_scorer_rollout_logical_and.pt --resume --workers 6 --checkpoint-every 1 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset large_resource_core
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset large_resource_core
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 2 --checkpoint-every 5 --resume --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_scale_resource --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 8 --resume --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset highdim_scale_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset highdim_scale_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset ultra_highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 4 --resume --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset ultra_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset ultra_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset mega_highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 4 --checkpoint-every 5 --resume
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset large_resource_core --formats pla,blif,truth
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset traditional_resource --formats pla,blif,truth --out-dir benchmark_exports/traditional_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --max-n 4 --max-ilp-n 4 --timeout 10 --workers 4 --out results/raw_external_traditional_resource_n4.csv --summary results/summary_external_traditional_resource_n4.csv --run-manifest results/manifest_external_traditional_resource_n4.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_traditional_resource_n4.csv --internal-csv results/raw_traditional_resource.csv --out results/analysis_external_traditional_resource_n4.md
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_sshr_h,external_sshr_i_cnot,external_sshr_i_t --max-n 6 --max-ilp-n 6 --timeout 8 --workers 4 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_aig --max-n 6 --max-abc-n 6 --timeout 8 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_esop --max-n 6 --max-esop-n 6 --timeout 8 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_xag --max-n 6 --max-xag-n 6 --timeout 10 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_lut --max-n 6 --max-lut-n 6 --timeout 10 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_bdd --max-n 6 --max-bdd-n 6 --bdd-orders 8 --timeout 10 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_traditional_resource_n6.csv --internal-csv results/raw_traditional_resource.csv --out results/analysis_external_traditional_resource_n6.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset highdim_resource --formats blif,truth --out-dir benchmark_exports/highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 14 --max-n 14 --max-abc-n 14 --max-xag-n 14 --max-lut-n 14 --max-bdd-n 14 --bdd-orders 8 --timeout 20 --workers 8 --out results/raw_external_highdim_resource.csv --summary results/summary_external_highdim_resource.csv --run-manifest results/manifest_external_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_highdim_resource.csv --internal-csv results/raw_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair,and_fprm_root_beam,and_fprm_greedy,direct_anf,and_direct_anf --out results/analysis_external_highdim_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset highdim_scale_resource --formats blif,truth --out-dir benchmark_exports/highdim_scale_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/highdim_scale_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 15 --max-n 15 --max-abc-n 15 --max-xag-n 15 --max-lut-n 15 --max-bdd-n 15 --bdd-orders 8 --timeout 30 --workers 8 --out results/raw_external_highdim_scale_resource.csv --summary results/summary_external_highdim_scale_resource.csv --run-manifest results/manifest_external_highdim_scale_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_highdim_scale_resource.csv --internal-csv results/raw_highdim_scale_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair_deep,and_fprm_linear_pair,and_fprm_linear_parity,and_fprm_greedy,direct_anf,and_direct_anf --out results/analysis_external_highdim_scale_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset ultra_highdim_resource --formats blif,truth --out-dir benchmark_exports/ultra_highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/ultra_highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 16 --max-n 16 --max-abc-n 16 --max-xag-n 16 --max-lut-n 16 --max-bdd-n 16 --bdd-orders 8 --timeout 45 --workers 8 --out results/raw_external_ultra_highdim_resource.csv --summary results/summary_external_ultra_highdim_resource.csv --run-manifest results/manifest_external_ultra_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_ultra_highdim_resource.csv --internal-csv results/raw_ultra_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair,and_fprm_root_beam,direct_anf,and_direct_anf --out results/analysis_external_ultra_highdim_resource.md
```

Current presets:

- `smoke`: fast correctness/regression run.
- `pilot`: medium structured-oracle run with ANF, factor-MCTS, FPRM-MCTS,
  neural-MCTS, and SSHR-H references.
- `evidence_affine`: current paper-facing run.  It compares direct ANF,
  logical-AND direct ANF, fixed-coordinate logical-AND MCTS, affine-preconditioned
  neural MCTS, and SSHR-H on 322 Boolean functions.
- `ablation_affine`: same 322-function suite with affine-greedy and
  affine-no-guard variants added to isolate the neural refine and guard
  contributions.
- `traditional_small`: $n \leq 6$ comparison slice with direct ANF,
  logical-AND direct ANF, fixed-coordinate logical-AND MCTS, affine-preconditioned
  neural MCTS, ESOP cube beam, time-limited weighted ESOP MILP, and SSHR-H.
- `traditional_resource`: same $n \leq 6$ slice with the full Resource-NMCTS
  portfolio guard and Pareto-Resource-NMCTS archive added.
- `large_resource_core`: 330-function large logical benchmark through `n=12`,
  now including the profile-aware Resource-NMCTS variant and process-isolated
  hard timeouts for long-tail tasks.
- `highdim_resource`: isolated `n=14` random-ANF stress benchmark with direct
  ANF, logical-AND direct ANF, FPRM-greedy, bounded FPRM root-beam,
  bounded FPRM linear-pair factoring, bounded affine-greedy, Resource-NMCTS,
  and Profile-Resource-NMCTS.  The guarded variants keep the root-child beam
  baseline and use a one-extra-layer CNOT-only pairwise XOR factor candidate.
- `highdim_scale_resource`: isolated `n=15` random-ANF scale check with direct
  ANF, logical-AND direct ANF, FPRM-greedy, bounded FPRM root-beam, FPRM
  linear-pair factoring, a one-extra-layer bounded linear-pair refinement,
  a standalone width-three linear-parity ablation, Resource-NMCTS, and
  Profile-Resource-NMCTS.
- `ultra_highdim_resource`: isolated `n=16` random-ANF scale check with direct
  ANF, logical-AND direct ANF, bounded FPRM root-beam, one-layer FPRM
  linear-pair factoring, Resource-NMCTS, and Profile-Resource-NMCTS.  It uses
  the ultra-scale guard rather than the recursive n=15 linear-pair branch.
- `mega_highdim_resource`: isolated `n=18` random-ANF stress check with direct
  ANF, logical-AND direct ANF, bounded FPRM root-beam, Resource-NMCTS, and
  Profile-Resource-NMCTS.  It uses the root-beam high-dimensional guard because
  the linear-pair screen has a multi-minute long tail at this scale.
- `large_resource`: experimental `n=14` stress extension.  This preset exposed
  the mixed-suite runtime tail and is kept for broader engineering sweeps.
- `main`: large-scale placeholder for broader sweeps.

Outputs are written to `results/`.  The neural prior is saved at
`models/action_scorer_rollout_logical_and.pt`.

External-tool benchmark exchange:

- `export_benchmarks.py` writes deterministic PLA, BLIF `.names`, and JSON
  truth-table files for any experiment preset, plus `manifest.csv` and
  `manifest.json`.
- The default output directory is `benchmark_exports/<preset>_seed<seed>/` and
  is intentionally git-ignored because the files are regenerable and can be
  large for `n=12` and `n=14` suites.
- This is the bridge for reproducing the same Boolean functions in external
  AIG/XAG/LUT/ROS or mockturtle-style synthesis flows without depending on the
  Python experiment harness.
- `run_external_baselines.py` consumes the exported `manifest.csv`/JSON and
  runs cross-directory baseline backends.  The implemented external backends
  are SSHR-H/SSHR-I from `src/sshr` and a Berkeley ABC AIG path that optimizes
  exported BLIF with `strash; balance; rewrite; refactor; rewrite -z; balance`,
  verifies the optimized BLIF truth table with a bit-parallel full truth-table
  checker, and maps AIG AND/level statistics to a logic-level Bennett
  compute/uncompute resource estimate.  It also includes an ABC XAG/GIA path
  using `&get; &st -m -L 1` plus `&ps -m -x`, verified BLIF output, and a
  logical XAG cost model.  It also includes an ABC LUT-mapping path using
  `strash; if -K 4`, verified mapped BLIF output, and a local LUT-to-ANF
  resource estimate.  It also includes an ABC ESOP path using `&exorcism -q`,
  verified ESOP-PLA output, and the same logical-AND cube cost model as the
  internal ESOP baselines.  It also includes a deterministic reduced ordered BDD
  baseline with multiple variable orders, truth-table verification, and a
  Shannon-network resource estimate.  ROS and mockturtle adapters are still
  future work.

Current evidence from `results/analysis_evidence_affine.md`:

- 322 functions, 5 methods, 1610 result rows.
- `and_affine_nmcts` is correct on all 322 functions.
- Mean T-count reduction versus direct ANF: 61.83%.
- Mean T-count reduction versus logical-AND direct ANF: 40.12%.
- Versus fixed-coordinate logical-AND MCTS, `and_affine_nmcts` has 161 T-count
  wins, 160 ties, and 0 losses over the 321 completed baseline pairs; mean
  T-count reduction is 16.18%.
- Versus SSHR-H on supported functions, `and_affine_nmcts` has 171 wins, 5
  ties, and 1 loss in T-count; mean T-count reduction is 43.89%.
- One fixed-coordinate MCTS baseline row (`anf_n12_10`) timed out at 600 s.
  The affine method completed that same function within the experiment budget.

Ablation evidence from `results/analysis_ablation_affine.md`:

- `and_affine_greedy` alone already reduces mean T-count by 60.92% versus
  direct ANF, showing that affine coordinate search is the dominant source of
  improvement.
- `and_affine_no_guard` improves over `and_affine_greedy` in 65 score cases
  with 0 score losses, isolating the low-dimensional neural-refine benefit.
- `and_affine_nmcts` improves over `and_affine_no_guard` in 88 score cases
  with 0 score losses, isolating the fixed-coordinate MCTS guard benefit.
- `and_affine_nmcts` improves over `and_affine_greedy` in 153 score cases
  with 0 score losses.

Runtime/resource evidence from `results/runtime_ablation_affine.md`:

- affine-greedy completed all 322 functions with median runtime 0.033 s and
  max runtime 1.825 s.
- full `and_affine_nmcts` completed all 322 functions with median runtime
  0.609 s and max runtime 300.025 s.
- fixed-coordinate MCTS completed 321 functions and timed out once; its median
  runtime was 0.076 s and max completed runtime was 89.897 s.
- full `and_affine_nmcts` has the lowest all-suite mean T-count and composite
  score among the non-SSHR methods, while affine-greedy is the fastest strong
  setting.

Neural-prior ablation evidence from `results/analysis_neural_prior_ablation.md`:

- 1062 rows over the 177-function `traditional_resource` slice, comparing
  learned-prior rows against a no-prior rerun for `and_affine_nmcts`,
  `and_resource_nmcts`, and `and_pareto_resource_nmcts`; 0 errors/skips.
- Learned prior versus no-prior score wins/losses/ties are 42/0/135 for
  `and_affine_nmcts`, 41/0/136 for `and_resource_nmcts`, and 29/0/148 for
  `and_pareto_resource_nmcts`.
- Mean score reductions are 1.47%, 1.34%, and 0.78%, respectively.  Runtime
  increases on this small-function slice, so the learned prior is a
  quality-improving search signal rather than the current fastest mode.

Traditional Boolean/ESOP baseline evidence from
`results/analysis_traditional_resource.md` and
`results/runtime_traditional_resource.md`:

- 177 functions with $n \leq 6$, 10 methods, 1770 result rows, 0 errors, and 0
  skips.
- Mean T-count / composite score: `and_pareto_resource_nmcts` 40.77 / 49.83,
  `and_fprm_polarity_archive` 43.01 / 52.50,
  `and_resource_nmcts` 45.74 / 55.21,
  `and_affine_nmcts` 45.88 / 55.37, fixed MCTS 62.06 / 73.09, ESOP cube beam
  71.32 / 83.82, ESOP MILP 83.59 / 96.73, and SSHR-H 81.04 / 88.19.
- Against Resource-NMCTS, `and_pareto_resource_nmcts` has 74 score wins, 0
  losses, and 103 ties, with a 4.59% mean score reduction.
- Against ESOP cube beam, `and_pareto_resource_nmcts` has 174 score wins, 0
  losses, and 3 ties, with a 35.86% mean score reduction.
- Against time-limited weighted ESOP MILP, `and_pareto_resource_nmcts` has 167
  score wins, 3 losses, and 7 ties, with a 29.61% mean score reduction.
- Against SSHR-H, `and_pareto_resource_nmcts` has 173 T-count wins, 0 losses,
  and 4 ties, and 173 score wins with 4 score losses.
- SSHR-H still has the lowest mean CNOT count on this small-function slice, so
  the claim remains low-T/resource-score synthesis rather than CNOT-only
  optimality.

Exported exact SSHR-I pilot evidence from
`results/analysis_external_traditional_resource_n4.md`:

- Exported the `traditional_resource` suite to PLA, BLIF, and truth-table JSON,
  then ran external SSHR-H, CNOT-optimized SSHR-I, and T-optimized SSHR-I on all
  72 functions with `n <= 4`.
- The pilot produced 216 external method/function rows, 216 usable rows, and 0
  errors/skips.
- Against CNOT-optimized SSHR-I, `and_resource_nmcts` has 65 T-count wins, 0
  losses, and 7 ties; score wins/losses/ties are 69/3/0 with a 26.45% mean
  score reduction.  CNOT count is worse on 65/72 functions.
- Against T-optimized SSHR-I, `and_resource_nmcts` has the same 65/0/7 T-count
  win pattern and a 26.21% mean score reduction.  CNOT count is worse on 62/72
  functions.

Time-limited exported SSHR-I, ABC-AIG, ABC-XAG, ABC-LUT, BDD, and ABC-ESOP extension evidence from
`results/analysis_external_traditional_resource_n6.md`:

- Extends the same exported manifest to all 177 functions with `n <= 6`.
- Produces 1416 external rows across SSHR-H, CNOT-optimized SSHR-I,
  T-optimized SSHR-I, ABC-AIG, ABC-XAG, ABC-LUT, BDD, and ABC-ESOP, with 0
  errors/skips.
- The SSHR-I rows use an 8 s per-call Gurobi budget, so this is a
  time-limited extension rather than an exact certificate.
- The ABC-AIG rows use Berkeley ABC 1.01 built from
  `bcfdf592289a408cd67ec19260f8a60a37b085b6`; all 177 optimized BLIF outputs
  pass truth-table verification before resource scoring.
- Against ABC-AIG, `and_resource_nmcts` has 170 T-count wins, 2 losses, and 5
  ties; it wins all 177 CNOT, peak-ancilla, and weighted-score comparisons,
  with mean reductions of 50.60%, 86.29%, and 54.52%, respectively.  ABC-AIG
  has a lower depth estimate on 126/177 functions, which is the main ABC-side
  advantage under this Bennett-style resource model.
- Against ABC-XAG, `and_resource_nmcts` has 176 T-count wins, 0 losses, and 1
  tie; it wins all 177 peak-ancilla and weighted-score comparisons, with mean
  reductions of 89.85% and 63.23%, respectively.  It reduces mean CNOT by
  35.53%, while ABC-XAG has a lower depth estimate on 144/177 functions.
- Against ABC-LUT, `and_resource_nmcts` has 175 T-count wins, 0 losses, and 2
  ties; it wins all 177 CNOT, depth, peak-ancilla, and weighted-score
  comparisons, with a 76.41% mean score reduction.  This is a verified mapped
  BLIF/LUT baseline, not a full reversible LUT mapper.
- Against BDD, `and_resource_nmcts` wins all 177 T-count, CNOT, depth,
  peak-ancilla, and weighted-score comparisons, with a 67.15% mean score
  reduction.  This is a verified ROBDD/Shannon-network baseline rather than a
  full optimized BDD reversible-synthesis toolchain.
- Against ABC-ESOP, `and_resource_nmcts` has 144 T-count wins, 19 losses, and
  14 ties; score wins/losses/ties are 147/24/6 with a 19.88% mean score
  reduction.  This baseline uses ABC `&exorcism -q` and verified ESOP-PLA
  output, making it a stronger external XOR-of-products comparison than the
  AIG-only path.
- Against CNOT-optimized SSHR-I, `and_resource_nmcts` has 164 T-count wins, 3
  losses, and 10 ties; score wins/losses/ties are 168/9/0 with a 27.92% mean
  score reduction.  CNOT count is worse on 168/177 functions.
- Against T-optimized SSHR-I, `and_resource_nmcts` has 166 T-count wins, 1
  loss, and 10 ties, with a 26.25% mean score reduction.

Exported high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD evidence from
`results/analysis_external_highdim_resource.md` and
`results/analysis_external_highdim_scale_resource.md` and
`results/analysis_external_ultra_highdim_resource.md`:

- The external AIG/XAG/LUT/BDD paths now cover 64 exported `n=14` random-ANF
  functions, 32 exported `n=15` random-ANF functions, and 24 exported `n=16`
  random-ANF functions for each of ABC-AIG, ABC-XAG, ABC-LUT, and BDD, with
  480/480 correct rows and 0 errors/skips.
- At `n=14`, `and_resource_nmcts` and `and_profile_resource_nmcts` beat
  ABC-AIG, ABC-XAG, ABC-LUT, and BDD on all 256 T-count, CNOT, peak-ancilla, and
  weighted-score comparisons.  Mean score reductions are 94.13% against AIG,
  95.48% against XAG, 97.44% against LUT, and 93.24% against BDD.
- At `n=15`, the same guarded methods beat ABC-AIG, ABC-XAG, ABC-LUT, and BDD
  on all 128 T-count, CNOT, peak-ancilla, and weighted-score comparisons.  Mean
  score reductions are 94.59% against AIG, 96.33% against XAG, 97.76% against
  LUT, and 94.75% against BDD.
- At `n=16`, the same guarded methods beat ABC-AIG, ABC-XAG, ABC-LUT, and BDD
  on all 96 T-count, CNOT, peak-ancilla, and weighted-score comparisons.  Mean
  score reductions are 97.29% against AIG, 97.88% against XAG, 99.00% against
  LUT, and 96.81% against BDD.
- ABC-AIG and ABC-XAG remain shallower under the current level-based estimate on
  most high-dimensional functions, including 22/24 `n=16` functions for each of
  ABC-AIG and ABC-XAG, while ABC-LUT and the BDD Shannon-network estimate are
  deeper; the claim remains weighted-resource and low-ancilla dominance rather
  than depth-only dominance against every possible toolchain.

Resource-profile stress-test evidence from
`results/analysis_resource_sweep.md`:

- 47 functions with $n \leq 6$, 4 resource profiles, 9 methods, 1692 result
  rows, 0 errors, and 0 skips.
- `and_pareto_resource_nmcts` is best-or-tied on 44/47 functions under T-heavy
  weights, 44/47 under balanced weights, 42/47 under CNOT-depth-heavy weights,
  and 43/47 under ancilla-tight weights.
- Against Profile-Resource-NMCTS, `and_pareto_resource_nmcts` has no score
  losses in any profile, with score wins/ties of 19/28, 19/28, 21/26, and
  15/32.  Mean score reductions are 5.56%, 4.93%, 4.85%, and 2.51%.
- Its mean resource vector changes with the active profile: mean T is 35.91
  under T-heavy/balanced/CNOT-depth weights and 39.74 under ancilla-tight
  weights, while mean peak ancilla drops from 1.87--1.94 to 1.62 under the
  ancilla-tight profile.

Large-scale core evidence from `results/analysis_large_resource_core.md` and
`results/runtime_large_resource_core.md`:

- 330 functions through `n=12`, 6 methods, 1980 result rows, 5 fixed-MCTS
  timeout rows, and 0 skips.  The stable run used process-isolated hard
  timeouts on an Apple M4 Pro with 14 logical CPU cores and 24 GB memory.
- `and_resource_nmcts` and `and_profile_resource_nmcts` completed all 330
  functions.  Fixed-coordinate MCTS timed out on 5 `n=12` random ANF functions.
- Compared with direct ANF, `and_resource_nmcts` has 291 T-count wins, 0
  losses, and 39 ties, with a 60.37% mean T-count reduction and a 56.84% mean
  score reduction.
- Compared with logical-AND direct ANF, it has 286 T-count wins, 0 losses, and
  44 ties, with a 37.25% mean T-count reduction and a 35.21% mean score
  reduction.
- Compared with fixed-coordinate MCTS on completed pairs, it has 139 T-count
  wins, 15 losses, and 171 ties, with an 11.41% mean score reduction.  The
  fixed-MCTS completed-row mean excludes its five timeout rows, so those means
  are censored toward easier functions.
- Compared with standalone Affine-NMCTS, it has 29 score wins, 16 score losses,
  and 285 ties, with a 0.20% mean score reduction.  This is a scalable budgeted
  portfolio result, not a dominance guarantee over the full affine search.
- Runtime for `and_resource_nmcts`: 330/330 completed, median 1.311 s, p95
  58.857 s, max 300.848 s.
- `and_profile_resource_nmcts` trades score for a shorter large-core runtime
  tail: 330/330 completed, median 2.292 s, p95 25.682 s, max 67.609 s, mean
  score 286.54 versus 273.72 for `and_resource_nmcts`.

High-dimensional stress evidence from `results/analysis_highdim_resource.md`
and `results/runtime_highdim_resource.md`:

- 64 random ANF functions at `n=14`, 8 methods, 512 result rows, 0 errors, and
  0 skips.
- `and_resource_nmcts` and `and_profile_resource_nmcts` complete all 64
  functions under the high-dimensional bounded guard.
- Compared with direct ANF, both Resource-NMCTS variants have 61 T-count wins,
  0 losses, and 3 ties, with a 57.42% mean T-count reduction and a 54.03%
  mean score reduction.
- Compared with logical-AND direct ANF, they have 61 T-count wins, 0 losses,
  and 3 ties, with a 32.74% mean T-count reduction and a 30.86% mean score
  reduction.
- Compared with FPRM-greedy, the high-dimensional guarded variants have
  60 T-count wins, 0 losses, and 4 ties; by weighted score they also have
  60 wins, 0 losses, and 4 ties, with a 6.25% mean score reduction.  Against
  the one-layer FPRM linear-pair candidate, they have 53 T-count wins, 0
  losses, and 11 ties, with a 2.87% mean score reduction.  The improvement
  comes from a bounded recursive FPRM linear-pair candidate that factors
  repeated term pairs as `(x_i xor x_j) * g` using CNOT-only linear compute and
  uncompute around the factored subplan.
- Compared with the standalone FPRM root-beam candidate, the guarded variants
  now have 60 T-count wins, 0 losses, and 4 ties; by weighted score they have
  60 wins, 0 losses, and 4 ties, with a 5.73% mean score reduction.
- Runtime tails remain visible but bounded: `and_resource_nmcts` completes
  64/64 with median 8.375 s and p95 76.838 s; `and_profile_resource_nmcts`
  delegates to the same high-dimensional guard.  The standalone one-layer FPRM
  linear-pair candidate has median 2.574 s and p95 30.760 s.  The tradeoff is
  higher mean peak ancilla: 3.05 versus 2.03 for FPRM-greedy and root-beam.

Additional scale check from `results/analysis_highdim_scale_resource.md` and
`results/runtime_highdim_scale_resource.md`:

- 32 random ANF functions at `n=15`, 9 methods, 288 result rows, 0 errors, and
  0 skips.
- Compared with FPRM-greedy, the guarded variants have 30 T-count wins, 0
  losses, and 2 ties; by weighted score they also have 30 wins, 0 losses, and
  2 ties, with a 5.73% mean score reduction.
- Compared with the standalone FPRM root-beam candidate, they have 29 T-count
  wins, 0 losses, and 3 ties; by weighted score they have 30 wins, 0 losses,
  and 2 ties, with a 5.28% mean score reduction.
- The one-extra-layer linear-pair refinement recursively searches both the
  quotient and rest branches when the subproblem has at most 900 terms.  Versus
  the one-layer linear-pair candidate, it has 29 weighted-score wins, 0 losses,
  and 3 ties, at mean peak ancilla 3.06 instead of 2.84.
- The width-three linear-parity ablation is dominated by the recursive pair
  candidate under the default weighted score: 0 wins, 29 losses, and 3 ties
  against the recursive pair method.
- Runtime remains finite at `n=15`: `and_resource_nmcts` completes 32/32 with
  median 16.514 s and p95 135.536 s; `and_profile_resource_nmcts` completes
  32/32 with median 14.684 s and p95 122.842 s.

Ultra-high-dimensional scale check from
`results/analysis_ultra_highdim_resource.md` and
`results/runtime_ultra_highdim_resource.md`:

- 24 random ANF functions at `n=16`, 6 methods, 144 result rows, 0 errors, and
  0 skips.
- The ultra guard switches Resource/Profile to the one-layer FPRM linear-pair
  candidate.  Both guarded variants match that candidate on all 24 functions.
- Compared with direct ANF, the guarded variants have 23 T-count wins, 0
  losses, and 1 tie, with a 62.08% mean T-count reduction and a 59.52% mean
  score reduction.
- Compared with logical-AND direct ANF, they have 23 weighted-score wins, 0
  losses, and 1 tie, with a 31.68% mean score reduction.
- Compared with FPRM root beam, they have 22 weighted-score wins, 0 losses,
  and 2 ties, with a 1.88% mean score reduction.
- Runtime remains finite at `n=16`: `and_resource_nmcts` completes 24/24 with
  median 17.537 s and p95 59.132 s; `and_profile_resource_nmcts` completes
  24/24 with median 17.566 s and p95 58.479 s.

`results/analysis_mega_highdim_resource.md` and
`results/runtime_mega_highdim_resource.md`:

- 12 random ANF functions at `n=18`, 5 methods, 60 result rows, 0 errors, and
  0 skips.
- The mega guard switches Resource/Profile to the bounded FPRM root-beam child.
  Both guarded variants match that child on all 12 functions; this is scale and
  verification evidence rather than a new portfolio-separation claim.
- Compared with direct ANF, the guarded variants have 10 T-count wins, 0
  losses, and 2 ties, with a 55.40% mean T-count reduction and a 53.08% mean
  score reduction.
- Compared with logical-AND direct ANF, they have 10 weighted-score wins, 0
  losses, and 2 ties, with a 27.43% mean score reduction.
- Runtime remains finite but has a minute-scale tail: `and_resource_nmcts`
  completes 12/12 with median 65.995 s and p95 143.671 s;
  `and_profile_resource_nmcts` completes 12/12 with median 66.841 s and p95
  149.190 s.

Scope boundary: all costs are logical-level resource estimates.  The verifier
circuit is deterministic and classically checked, while the logical-AND cost
model accounts for low-T compute and Clifford/measurement-based uncompute.
No hardware mapping or connectivity constraints are included.
