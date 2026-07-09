# Resource-Constrained Neural MCTS Oracle Synthesis

This directory implements a new logic-level line of work for:

> 面向资源约束量子布尔函数综合的神经蒙特卡洛树搜索方法

The method does not use SSHR parallelotope candidates.  It treats Boolean
oracle synthesis as a symbolic factorization search over ANF/XAG-style
compute/uncompute plans, then verifies the generated oracle circuits by
classical simulation.

Comparison scope:

- Boolean-oracle synthesis baselines: direct ANF, logical-AND direct ANF, ESOP
  beam/MILP, BDD, ABC AIG/XAG/LUT/ESOP, XAG, and ROS-style LUT probes.
- External toolchain probes: official-header mockturtle KLUT-to-XAG, CirKit 3
  AIG/multiplicative-complexity, RevKit API, and legacy RevKit CLI exact-oracle
  reversible-synthesis flows.
- Search-policy baselines and ablations: greedy/direct construction, beam,
  fixed-coordinate MCTS, neural-prior ablations, Pareto archives,
  depth-frontier policies, stage-gated frontier control, and rank-diverse
  phase pruning.

SSHR-H/SSHR-I are important CNOT-oriented small-function baselines, but the
project claim is a resource-aware logical-layer AI search framework rather than
an SSHR variant.

The introduction-level contribution map is materialized by
`analyze_contribution_evidence_map.py`, which writes
`results/summary_contribution_evidence_map.csv`,
`results/analysis_contribution_evidence_map.md`, and
`paper_latex/tables/contribution_evidence_map.tex`.  It links the four
headline contributions to implementation mechanisms, manuscript evidence, and
claim boundaries.
The method workflow table is materialized by
`analyze_method_workflow_table.py`, which writes
`results/summary_method_workflow.csv`,
`results/analysis_method_workflow.md`, and
`paper_latex/tables/method_workflow.tex`.  It records the end-to-end synthesis
path from input normalization through candidate generation, neural/MCTS search
control, guarded selection, circuit emission, and semantic reporting.
The literature positioning layer is materialized by
`analyze_related_work_positioning.py`, which writes
`results/summary_related_work_positioning.csv`,
`results/analysis_related_work_positioning.md`, and
`paper_latex/tables/related_work_positioning.tex`.  It separates BDD, LUT/ROS,
XAG, reversible toolchain, SSHR, and learning-guided synthesis families before
the experimental baseline boundaries are introduced.
The comparison claim boundary is materialized by
`analyze_baseline_claim_matrix.py`, which writes
`results/summary_baseline_claim_matrix.csv`,
`results/analysis_baseline_claim_matrix.md`, and
`paper_latex/tables/baseline_claim_matrix.tex`.  It separates primary
logical-oracle baselines, external toolchain probes, reversible-synthesis
probes, phase/Rz proxies, internal ablations, scaling bridges, and trade-off
audits before the quantitative results are presented.
The comparison evidence scope is materialized by
`analyze_comparison_evidence_matrix.py`, which writes
`results/summary_comparison_evidence_matrix.csv`,
`results/analysis_comparison_evidence_matrix.md`, and
`paper_latex/tables/comparison_evidence_matrix.tex` for the submission draft.
The comparison target validity audit is materialized by
`analyze_comparison_target_validity_audit.py`, which writes
`results/summary_comparison_target_validity_audit.csv`,
`results/analysis_comparison_target_validity_audit.md`,
`results/manifest_comparison_target_validity_audit.json`, and
`paper_latex/tables/comparison_target_validity_audit.tex`.  It labels each
comparison family as a primary benchmark, external stress test, exact
reversible counterpoint, phase proxy, causal control, scalability
verification, or non-dominance boundary.
The baseline comparability audit is materialized by
`analyze_baseline_comparability_audit.py`, which writes
`results/summary_baseline_comparability_audit.csv`,
`results/analysis_baseline_comparability_audit.md`, and
`paper_latex/tables/baseline_comparability_audit.tex`.  It explains the task
alignment, fairness controls, residual abstraction risk, and usable claim for
each baseline family, so the paper does not overstate cross-toolchain
comparisons.
The paired statistical layer is materialized by
`analyze_paired_statistical_evidence.py`, which recomputes selected score
comparisons from usable raw CSV rows, reports mean and median relative effects,
and adds an exact two-sided sign test for the paper table
`paper_latex/tables/paired_statistical_evidence.tex`.
The raw multi-resource trade-off layer is materialized by
`analyze_multimetric_pareto_tradeoff.py`, which tests dominance using only
T-count, CNOT count, logical depth, and peak ancilla.  It writes
`results/analysis_multimetric_pareto_tradeoff.md` plus the paper tables
`paper_latex/tables/multimetric_pairwise_dominance.tex` and
`paper_latex/tables/multimetric_nondominated.tex`.
The learned-control audit is materialized by
`analyze_learned_control_audit.py`, which separates promoted learned controls
(frontier policy, staged frontier, sparse depth-4 gate, phase shortlist) from
limited diagnostics (boolean neural guard and root-action neural ranker) in
`paper_latex/tables/learned_control_audit.tex`.  The same evidence is
visualized by `make_submission_figures.py` as
`paper_latex/figures/submission_v36/fig7_learned_control_summary.pdf`, with
source data in
`paper_latex/figures/submission_v36/source_data/fig7_learned_control_summary.csv`.
The Boolean-ring structural audit is materialized by
`analyze_boolean_ring_structural_evidence.py`, which consolidates the
high-dimensional Boolean-ring and Boolean-screen comparisons into
`paper_latex/tables/boolean_ring_structural_evidence.tex`.  It separates
quality-seeking structural guards, time-saving screen gates, and speed-only
negative controls.
The sparse frontier audit is materialized by
`analyze_sparse_depth_frontier.py`, which reconstructs a depth-2/4 Boolean
screen controller from the measured depth-2/3/4 raw rows.  It writes
`paper_latex/tables/sparse_depth_frontier.tex` and shows that the sparse
frontier exactly matches the full measured frontier on the audited scale and
truth-bridge slices while removing the depth-3 evaluation cost.
The learned sparse depth-4 gate is materialized by
`train_sparse_depth4_gate.py`.  It trains a conservative binary controller after
the depth-2 sparse-frontier state, writes `models/sparse_depth4_gate.pt`,
`results/analysis_sparse_depth4_gate.md`, and
`paper_latex/tables/sparse_depth4_gate.tex`.  The independent-seed audit is
materialized by `audit_sparse_depth4_gate_generalization.py`, which writes
`results/analysis_sparse_depth4_gate_generalization.md` and
`paper_latex/tables/sparse_depth4_gate_generalization.tex`; on 144 multi-seed
`n=24,28,32,40` pairs it preserves sparse-frontier score with 0 false skips and
reduces sparse-frontier evaluation time by 13.43%.  Threshold sensitivity is
materialized by `analyze_sparse_depth4_gate_sensitivity.py` and visualized by
`paper_latex/figures/submission_v36/fig6_sparse_gate_sensitivity.pdf`; it shows
a zero-false-skip plateau up to 14.92% time saving on the same audit.
The high-dimensional scale audit is materialized by
`analyze_scaling_resource_audit.py`, which separates functions/settings,
method rows, verified rows, and representative resource means for the large
frontier, stage-gated frontier, width-probe, and complete truth-table bridge
slices in `paper_latex/tables/scaling_resource_audit.tex`.
The compute/reproducibility audit is materialized by
`analyze_reproducibility_audit.py`, which records the local CPU/GPU/Python
environment, manifest-level worker counts, artifact coverage, and external
tool commits in `paper_latex/tables/reproducibility_audit.tex`.
The submission traceability audit is materialized by
`analyze_submission_traceability_audit.py`, which writes
`results/summary_submission_traceability_audit.csv`,
`results/analysis_submission_traceability_audit.md`,
`results/manifest_submission_traceability_audit.json`, and
`paper_latex/tables/submission_traceability_audit.tex`.  It links the main
claim families to the scripts, CSVs, tables, figures, manuscript anchors, and
boundaries that support them.
The submission archive manifest is materialized by
`analyze_submission_archive_manifest.py`, which writes
`results/summary_submission_archive_manifest.csv`,
`results/analysis_submission_archive_manifest.md`,
`results/manifest_submission_archive_manifest.json`, and
`paper_latex/tables/submission_archive_manifest.tex`.  It hashes stable
payload groups for the source package while excluding terminal submission
package/audit outputs and the compiled PDF from the digest set to avoid
self-referential checks.
The submission-support files live in `submission_package/`: a cover-letter
template, author-declarations template, upload checklist, reviewer-concern
brief, and target-venue brief.  These files are ready to use at upload time, but fields marked
`AUTHOR INPUT REQUIRED` must be completed by the author because funding,
affiliations, competing interests, and final archive links cannot be inferred
from experiment artifacts.
The submission metadata audit is materialized by
`analyze_submission_metadata_audit.py`, which writes
`results/summary_submission_metadata_audit.csv`,
`results/analysis_submission_metadata_audit.md`, and
`results/manifest_submission_metadata_audit.json`.  It enumerates author- and
venue-specific fields that remain deliberately human-gated: author identity,
CRediT roles, funding, acknowledgements, competing interests, archive links,
code license/repository metadata, AI-assistance disclosure, preprint history,
cover-letter routing fields, and target-venue policy checks.  The structured
intake template is `submission_package/submission_metadata_template.json`;
copy it to `submission_package/submission_metadata.json`, fill every
`AUTHOR INPUT REQUIRED` value, and rerun the rebuild script.  The filled file
is ignored by Git to avoid accidental commits of author-private metadata.
The venue-selection helper `submission_package/target_venue_brief.md` records
the current venue-fit shortlist and should be used before filling the target
venue fields in `submission_metadata.json`.
The goal-completion audit is materialized by
`analyze_goal_completion_audit.py`, which writes
`results/summary_goal_completion_audit.csv`,
`results/analysis_goal_completion_audit.md`, and
`results/manifest_goal_completion_audit.json`.  It maps the original project
objective to concrete evidence files and keeps the overall closure gate open
until author- and venue-specific metadata are supplied.
The uploadable payload archive is materialized by
`make_submission_payload_archive.py`, which writes
`submission_package/dist/resource_nmcts_submission_payload.tar.gz`,
`submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256`,
`results/summary_submission_payload_archive.csv`,
`results/analysis_submission_payload_archive.md`, and
`results/manifest_submission_payload_archive.json`.  The tarball packages the
stable source/data payload, compiled PDF, and package audits, while excluding
itself and the readiness audit to avoid changing the archive after the final
readiness pass.
The lightweight derived submission package can be regenerated with:

```bash
./rebuild_submission_package.sh
```

This command rebuilds paper-facing analysis tables, figures, the metadata and
goal-completion audits, archive manifest, uploadable payload archive,
traceability and readiness audits, and
`paper_latex/resource_nmcts_submission_v1.pdf` from the existing experiment
artifacts.  It does not rerun raw benchmark sweeps, external-toolchain probes,
or neural training jobs; those remain under the individual `run_*.py` and
`train_*.py` entry points.
The submission-readiness audit is materialized by
`analyze_submission_readiness_audit.py`, which writes
`results/summary_submission_readiness_audit.csv` and
`results/analysis_submission_readiness_audit.md`.  It checks that the
submission draft contains bounded and concise abstract claims,
contribution/evidence mapping, baseline fairness tables, reproducibility
evidence, claim-to-artifact traceability, a derived-package rebuild command,
an archive package manifest, submission-support templates, an uploadable
payload archive, submission metadata audit, goal-completion audit, limitations,
data/code availability, a compiled PDF, and no source TODO markers; it leaves
funding, acknowledgements, competing interests, author metadata, venue fields,
and archival links as author-specific submission-time items.

Latest external-toolchain progress:

- `run_mockturtle_xag_probe.py` builds a small C++ adapter over the official
  mockturtle headers, maps exported BLIFs with ABC `if -K 4`, resynthesizes the
  resulting KLUT networks with mockturtle `xag_npn_resynthesis`, and converts
  XAG AND/XOR/depth counts into the project's logic-level resource proxy.
- Traditional `n<=6`: 177/177 mockturtle rows verified; Pareto-Resource-NMCTS
  vs mockturtle XAG K4 score is 166/11/0, mean -31.50%.
- High-dimensional `n=14`: 64/64 mockturtle rows verified; Pareto-Resource-NMCTS
  vs mockturtle XAG K4 score is 64/0/0, mean -91.49%.
- This is an official-header mockturtle probe, not full ROS, not reversible
  garbage management, and not hardware mapping.
- `run_cirkit_aig_probe.py` builds on the official CirKit 3 shell.  ABC
  converts exported BLIFs to AIGER; CirKit applies `cut_rewrite; resub`, reports
  `mccost -a`, writes Verilog, and ABC reads that Verilog back for row-level
  truth-table verification.
- Traditional `n<=6`: 177/177 CirKit rows verified; Pareto-Resource-NMCTS vs
  CirKit AIG/MC score is 177/0/0, mean -62.34%.  Depth is the visible trade-off:
  Pareto-Resource-NMCTS loses depth on 156/177 rows, mean +93.16%.
- High-dimensional `n=14`: 64/64 CirKit rows verified; Pareto-Resource-NMCTS vs
  CirKit AIG/MC score is 64/0/0, mean -94.46%.  It also wins T/CNOT/ancilla on
  all rows, but loses depth on 50/64 rows under this proxy.
- This is a CirKit-shell AIG/multiplicative-complexity probe, not legacy RevKit
  reversible synthesis, not full ROS, and not hardware mapping.
- `run_revkit_cli_probe.py` builds on the legacy RevKit/CirKit CLI.  Each
  Boolean function is embedded as the exact reversible oracle permutation
  `(x,y)->(x,y xor f(x))`; RevKit reads the SPEC permutation and runs
  TBS/DBS/RMS reversible synthesis flows.
- Traditional `n<=6`: 531/531 direct RevKit CLI flow rows returned and 177
  synthetic best-score portfolio rows were generated.  Pareto-Resource-NMCTS vs
  the RevKit CLI best-score portfolio is 173/0/4 on score, mean -67.28%, and
  173/0/4 on T-count, mean -72.59%.  The visible trade-off is auxiliary lines:
  peak ancilla is 0/169/8, mean +153.11%.
- This is a real legacy reversible-synthesis CLI probe for exact oracle
  permutations.  It is still logic-layer only: CNOT/depth are derived from
  RevKit's Toffoli-control distribution, and the run does not include full ROS,
  hardware mapping, routing, or magic-state scheduling.

Latest phase/Rz progress:

- `run_phase_parity_baseline.py` implements a concrete internal phase-oracle
  emitter by expanding ANF monomials into merged parity-phase Rz gadgets.
- Traditional `n<=6`: 177/177 phase-parity rows verify exactly up to global
  phase.  The baseline has mean lower-bound score 10.11, mean total Rz 27.56,
  and mean non-Clifford Rz 21.75.
- Against RevKit `oracle_synth`, phase-parity ANF is weaker under the raw
  RevKit lower-bound score (40/137/0, mean +69.25%), but wins once each
  non-Clifford Rz is charged: `score+1/Rz` is 177/0/0 with mean -48.16%, and
  the `T/Rz=30` synthesis proxy is 177/0/0 with mean -64.98%.
- `run_phase_parity_fprm_search.py` upgrades this into an exhaustive
  fixed-polarity phase search.  It verifies 531/531 selected rows across three
  rank metrics.  The `T/Rz=30` objective chooses nonzero polarity on 59/177
  functions and improves over phase-parity ANF by 59/0/118, mean -0.47%; it
  remains 177/0/0 vs RevKit under the same proxy, mean -65.16%.
- `run_phase_parity_affine_search.py` extends the phase search with bounded
  invertible linear preconditioning before the FPRM polarity sweep.  The
  selected parity polynomial is translated back to original input masks, so
  this is still a logic-layer algebraic rewrite rather than hardware mapping.
  It verifies 531/531 selected rows.  Under the `T/Rz=30` objective,
  Affine-FPRM chooses a nonidentity transform on 81/177 functions and improves
  over fixed-polarity FPRM by 81/0/96, mean -2.51%; versus phase-parity ANF it
  is 85/0/92, mean -2.98%; versus RevKit under the same proxy it is 177/0/0,
  mean -65.50%.
- This is useful evidence that phase/Rz can be handled as a search problem, but
  not a solved phase/Rz method: affine preconditioning gives a stronger and
  non-degrading search dimension, but the next target is still learned or
  optimized phase/Rz-aware search plus actual rotation-synthesis sequence
  auditing.
- `train_phase_affine_policy.py` adds a rank-trained learned shortlist for the
  Affine-FPRM phase space.  `analyze_phase_policy_random_control.py` then
  audits the held-out `n=6` policy rows against eight same-budget random
  shortlists per top-k.  Diverse top-512 exact-scores 512/8192 affine forms per
  function, is 17/0/21 against the per-function random-repeat mean with
  sign-test p=1.53e-05, and beats all eight random seed means.  This is
  reliable learned pruning for the `T/Rz=30` proxy, not sequence-level
  rotation synthesis.

Latest high-dimensional verification progress:

- `run_truth_bridge_terms.py --ns 24 --per-n 6 --tag truth_bridge_n24` and
  `run_truth_bridge_terms.py --ns 25 --per-n 6 --tag truth_bridge_n25` extend
  the full truth-table bridge from `n=21,22,23` to `n=24,25`.
- The bridge uses the bit-mask ANF truth-table evaluator in `anf_utils.py`; it
  builds variable assignment masks and evaluates monomials with large-integer
  AND/XOR instead of Python-level coefficient zeta expansion.
- `n=24`: 6 generated ANF functions and 60 method rows all verify: 60/60 full
  oracle checks, 60/60 ANF plan checks, 60/60 emitted-circuit symbolic checks,
  mismatches=0.  Mean truth-table build time is 0.18 s per function.
- `n=25`: 6 generated ANF functions and 60 method rows also verify: 60/60 full
  oracle checks, 60/60 ANF plan checks, 60/60 emitted-circuit symbolic checks,
  mismatches=0.  Mean truth-table build time is 0.45 s per function; the
  depth-frontier policy ties depth-4 and adaptive all-depth on score while
  reducing plan time by 8.87% and 46.09%, respectively.
- The action-width probe at widths 6, 12, and 24 shows that simply widening
  the Boolean-ring screen candidate set does not improve the default score on
  the `n=20,28,40` term-set slice; each width verifies 504/504 method rows, and
  width 6 remains the paper-facing default because gains come from recursive
  depth/frontier selection rather than wider root candidates.
- This is a verification-boundary improvement, not a hardware-mapping claim;
  `n=26--64` remain covered by plan/circuit symbolic verification rather than
  full truth-table enumeration.

Core commands:

```bash
cd /Users/zhouzixiang/Desktop/tzb/src/resource_nmcts_experiment
/opt/anaconda3/envs/mcts-qoracle/bin/python tests_smoke.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset rollout --gate-mode logical_and --label-mode rollout --max-depth 3 --child-branch 2 --out models/action_scorer_rollout_logical_and.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset linear_highdim --gate-mode logical_and --label-mode immediate --action-family linear --max-depth 1 --child-branch 1 --out models/linear_action_scorer_highdim.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python train_screen_depth_policy.py --train-per-n 80 --valid-per-n 24 --test-per-n 48 --epochs 140 --hidden 96
/opt/anaconda3/envs/mcts-qoracle/bin/python train_screen_depth_guard.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_structure_gate.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --workers 6
/opt/anaconda3/envs/mcts-qoracle/bin/python train_screen_depth_frontier_policy.py --train-n 16,20,24 --test-n 28,40 --train-per-n 32 --valid-per-n 12 --test-per-n 16 --workers 6 --epochs 160 --hidden 96
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --ns 20,28,40 --per-n 24 --workers 6 --max-screen-depth 4 --tag depth_frontier_policy
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --seed 20260712 --ns 24,28,32,40 --per-n 24 --workers 6 --max-screen-depth 4 --tag depth_frontier_policy_generalization
/opt/anaconda3/envs/mcts-qoracle/bin/python train_screen_depth_frontier_policy.py --seed 20260715 --train-per-n 64 --valid-per-n 24 --test-per-n 24 --epochs 220 --hidden 160 --workers 8 --action-width 6 --tag large --model-out models/boolean_screen_depth_frontier_policy_large.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --seed 20260712 --ns 24,28,32,40 --per-n 24 --workers 8 --max-screen-depth 4 --frontier-policy-model models/boolean_screen_depth_frontier_policy_large.pt --tag depth_frontier_policy_large_generalization
/opt/anaconda3/envs/mcts-qoracle/bin/python train_screen_depth_frontier_policy.py --seed 20260716 --train-per-n 64 --valid-per-n 24 --test-per-n 24 --epochs 220 --hidden 160 --workers 8 --action-width 6 --label-time-weight 0.003 --tag cost_time003 --model-out models/boolean_screen_depth_frontier_policy_cost_time003.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --seed 20260712 --ns 24,28,32,40 --per-n 24 --workers 8 --max-screen-depth 4 --frontier-policy-model models/boolean_screen_depth_frontier_policy_cost_time003.pt --tag depth_frontier_policy_cost_time003_generalization
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --workers 2
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --seed 20260712 --ns 24,28,32,40 --per-n 24 --workers 6 --max-screen-depth 4 --tag schedule_depth_frontier_policy_generalization
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260711 --ns 21,22 --per-n 6 --workers 2 --max-screen-depth 4 --tag schedule_truth_bridge
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260713 --ns 23 --per-n 6 --workers 2 --max-screen-depth 4 --tag schedule_truth_bridge_n23
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260713 --ns 23 --per-n 6 --workers 2 --max-screen-depth 4 --frontier-policy-model models/boolean_screen_depth_frontier_policy_large.pt --tag truth_bridge_n23_large_frontier
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260713 --ns 23 --per-n 6 --workers 2 --max-screen-depth 4 --frontier-policy-model models/boolean_screen_depth_frontier_policy_cost_time003.pt --tag truth_bridge_n23_cost_time003_frontier
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260724 --ns 24 --per-n 6 --workers 4 --action-width 6 --max-screen-depth 4 --tag truth_bridge_n24
/opt/anaconda3/envs/mcts-qoracle/bin/python run_truth_bridge_terms.py --seed 20260725 --ns 25 --per-n 6 --workers 4 --action-width 6 --max-screen-depth 4 --tag truth_bridge_n25
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --seed 20260712 --ns 20,28,40 --per-n 24 --workers 6 --action-width 6 --max-screen-depth 4 --tag screen_scale_width6_probe
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --seed 20260712 --ns 20,28,40 --per-n 24 --workers 6 --action-width 12 --max-screen-depth 4 --tag screen_scale_width12_probe
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --seed 20260712 --ns 20,28,40 --per-n 24 --workers 6 --action-width 24 --max-screen-depth 4 --tag screen_scale_width24_probe
/opt/anaconda3/envs/mcts-qoracle/bin/python run_screen_scale_terms.py --tag ultra_scale64 --ns 48,56,64 --per-n 16 --workers 10 --action-width 6 --max-screen-depth 4
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_ultra_scale64_stress.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_schedule_metrics.py --input schedule_generalization=results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv --input schedule_truth_bridge=results/raw_schedule_truth_bridge_terms.csv --input schedule_truth_bridge_n23=results/raw_schedule_truth_bridge_n23_terms.csv
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_frontier_policy_upgrade.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_stage_gated_frontier.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_sparse_depth4_gate.py --train-n 16,20,24 --test-n 28,40 --train-per-n 32 --valid-per-n 16 --test-per-n 24 --epochs 120 --workers 6
/opt/anaconda3/envs/mcts-qoracle/bin/python audit_sparse_depth4_gate_generalization.py --seeds 20260801,20260802,20260803 --ns 24,28,32,40 --per-n 12 --workers 6
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_sparse_depth4_gate_sensitivity.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_learned_control_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_phase_policy_random_control.py
/opt/anaconda3/envs/mcts-qoracle/bin/python - <<'PY'
import make_submission_figures as m
m.configure()
m.fig_sparse_gate_sensitivity()
PY
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_scaling_resource_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_reproducibility_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_mockturtle_xag_probe.py --workers 4 --timeout 20
/opt/anaconda3/envs/mcts-qoracle/bin/python run_mockturtle_xag_probe.py --manifest highdim=benchmark_exports/highdim_resource_external_seed42/manifest.json --internal highdim=results/raw_highdim_resource.csv --min-n 14 --max-n 14 --workers 4 --timeout 30 --targets and_resource_nmcts,and_profile_resource_nmcts,and_pareto_resource_nmcts,and_direct_anf,direct_anf --out results/raw_mockturtle_xag_highdim_probe.csv --summary results/summary_mockturtle_xag_highdim_probe.csv --analysis results/analysis_mockturtle_xag_highdim_probe.md --latex-out paper_latex/tables/mockturtle_xag_highdim_probe.tex --run-manifest results/manifest_mockturtle_xag_highdim_probe.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_cirkit_aig_probe.py --workers 8 --timeout 45
/opt/anaconda3/envs/mcts-qoracle/bin/python run_cirkit_aig_probe.py --manifest highdim=benchmark_exports/highdim_resource_external_seed42/manifest.json --internal highdim=results/raw_highdim_resource.csv --min-n 14 --max-n 14 --workers 8 --timeout 90 --out results/raw_cirkit_aig_highdim_probe.csv --summary results/summary_cirkit_aig_highdim_probe.csv --analysis results/analysis_cirkit_aig_highdim_probe.md --latex-out paper_latex/tables/cirkit_aig_highdim_probe.tex --run-manifest results/manifest_cirkit_aig_highdim_probe.json
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
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_traditional --model models/action_scorer_rollout_logical_and.pt --workers 10 --checkpoint-every 100 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_traditional
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset search_ablation_traditional
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset search_ablation_highdim --model models/action_scorer_rollout_logical_and.pt --workers 6 --checkpoint-every 16 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset search_ablation_highdim
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset search_ablation_highdim
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_resource --only-methods and_affine_nmcts,and_resource_nmcts,and_pareto_resource_nmcts --model models/action_scorer_rollout_logical_and.pt --out-dir /tmp/resource_nmcts_traditional_learned_prior --workers 10 --checkpoint-every 50
cp /tmp/resource_nmcts_traditional_learned_prior/raw_traditional_resource.csv results/raw_traditional_resource_learned_prior.csv
cp /tmp/resource_nmcts_traditional_learned_prior/summary_traditional_resource.csv results/summary_traditional_resource_learned_prior.csv
cp /tmp/resource_nmcts_traditional_learned_prior/manifest_traditional_resource.json results/manifest_traditional_resource_learned_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset traditional_resource --only-methods and_affine_nmcts,and_resource_nmcts,and_pareto_resource_nmcts --model /tmp/nonexistent_model.pt --out-dir /tmp/resource_nmcts_traditional_no_prior --workers 10 --checkpoint-every 50
cp /tmp/resource_nmcts_traditional_no_prior/raw_traditional_resource.csv results/raw_traditional_resource_no_prior.csv
cp /tmp/resource_nmcts_traditional_no_prior/summary_traditional_resource.csv results/summary_traditional_resource_no_prior.csv
cp /tmp/resource_nmcts_traditional_no_prior/manifest_traditional_resource.json results/manifest_traditional_resource_no_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_neural_prior_ablation.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_neural_prior --model models/linear_action_scorer_highdim.pt --out-dir /tmp/resource_nmcts_highdim_learned_prior --workers 6 --checkpoint-every 6 --isolate-timeouts
cp /tmp/resource_nmcts_highdim_learned_prior/raw_highdim_neural_prior.csv results/raw_highdim_neural_prior_learned_prior.csv
cp /tmp/resource_nmcts_highdim_learned_prior/summary_highdim_neural_prior.csv results/summary_highdim_neural_prior_learned_prior.csv
cp /tmp/resource_nmcts_highdim_learned_prior/manifest_highdim_neural_prior.json results/manifest_highdim_neural_prior_learned_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_neural_prior --model /tmp/nonexistent_model.pt --out-dir /tmp/resource_nmcts_highdim_no_prior --workers 6 --checkpoint-every 6 --isolate-timeouts
cp /tmp/resource_nmcts_highdim_no_prior/raw_highdim_neural_prior.csv results/raw_highdim_neural_prior_no_prior.csv
cp /tmp/resource_nmcts_highdim_no_prior/summary_highdim_neural_prior.csv results/summary_highdim_neural_prior_no_prior.csv
cp /tmp/resource_nmcts_highdim_no_prior/manifest_highdim_neural_prior.json results/manifest_highdim_neural_prior_no_prior.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_neural_prior_ablation.py --learned-csv results/raw_highdim_neural_prior_learned_prior.csv --no-prior-csv results/raw_highdim_neural_prior_no_prior.csv --methods and_resource_nmcts --out-raw results/raw_neural_prior_highdim_ablation.csv --summary results/summary_neural_prior_highdim_ablation.csv --out results/analysis_neural_prior_highdim_ablation.md --latex-out paper_latex/tables/neural_prior_highdim_ablation.tex --dataset-label highdim_neural_prior --model-label models/linear_action_scorer_highdim.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_highdim_root_action_oracle.py
/opt/anaconda3/envs/mcts-qoracle/bin/python train_neural_policy.py --preset linear_root_teacher --seed 31415 --gate-mode logical_and --label-mode root_teacher --action-family linear --max-depth 0 --child-branch 1 --root-teacher-width 24 --rest-direct-limit 450 --hidden 128 --out models/linear_action_scorer_root_teacher.pt
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_highdim_root_action_oracle.py --model models/linear_action_scorer_root_teacher.pt --raw results/raw_highdim_root_action_teacher.csv --summary results/summary_highdim_root_action_teacher.csv --analysis results/analysis_highdim_root_action_teacher.md --latex-out paper_latex/tables/highdim_root_action_teacher.tex
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset highdim_guard_upgrade --model /tmp/nonexistent_model.pt --workers 6 --checkpoint-every 6 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_search_contribution.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_weight_robustness.py
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
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset ultra_highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 1 --checkpoint-every 8 --resume
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset ultra_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset ultra_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset mega_highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 4 --checkpoint-every 5
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset mega_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python run_experiments.py --preset giga_highdim_resource --model models/action_scorer_rollout_logical_and.pt --workers 3 --checkpoint-every 6 --isolate-timeouts
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_results.py --preset giga_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_runtime.py --preset giga_highdim_resource
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset large_resource_core --formats pla,blif,truth
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset traditional_resource --formats pla,blif,truth --out-dir benchmark_exports/traditional_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --max-n 4 --max-ilp-n 4 --timeout 10 --workers 4 --out results/raw_external_traditional_resource_n4.csv --summary results/summary_external_traditional_resource_n4.csv --run-manifest results/manifest_external_traditional_resource_n4.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_traditional_resource_n4.csv --internal-csv results/raw_traditional_resource.csv --out results/analysis_external_traditional_resource_n4.md
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_exact_fprm_dp.py --max-n 4
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_exact_xag_mc.py --max-n 4
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_sshr_h,external_sshr_i_cnot,external_sshr_i_t --max-n 6 --max-ilp-n 6 --timeout 8 --workers 4 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_aig --max-n 6 --max-abc-n 6 --timeout 8 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_esop --max-n 6 --max-esop-n 6 --timeout 8 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_xag --max-n 6 --max-xag-n 6 --timeout 10 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_abc_lut --max-n 6 --max-lut-n 6 --timeout 10 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/traditional_resource_external_seed42/manifest.json --methods external_bdd --max-n 6 --max-bdd-n 6 --bdd-orders 8 --timeout 10 --workers 8 --resume --out results/raw_external_traditional_resource_n6.csv --summary results/summary_external_traditional_resource_n6.csv --run-manifest results/manifest_external_traditional_resource_n6.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_traditional_resource_n6.csv --internal-csv results/raw_traditional_resource.csv --out results/analysis_external_traditional_resource_n6.md --latex-out paper_latex/tables/external_traditional_resource_n6.tex
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_toolchain_readiness.py
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset highdim_resource --formats blif,truth --out-dir benchmark_exports/highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 14 --max-n 14 --max-abc-n 14 --max-xag-n 14 --max-lut-n 14 --max-bdd-n 14 --bdd-orders 8 --timeout 20 --workers 8 --out results/raw_external_highdim_resource.csv --summary results/summary_external_highdim_resource.csv --run-manifest results/manifest_external_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_highdim_resource.csv --internal-csv results/raw_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair,and_fprm_root_beam,and_fprm_greedy,direct_anf,and_direct_anf --out results/analysis_external_highdim_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset highdim_scale_resource --formats blif,truth --out-dir benchmark_exports/highdim_scale_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/highdim_scale_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 15 --max-n 15 --max-abc-n 15 --max-xag-n 15 --max-lut-n 15 --max-bdd-n 15 --bdd-orders 8 --timeout 30 --workers 8 --out results/raw_external_highdim_scale_resource.csv --summary results/summary_external_highdim_scale_resource.csv --run-manifest results/manifest_external_highdim_scale_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_highdim_scale_resource.csv --internal-csv results/raw_highdim_scale_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair_deep,and_fprm_linear_pair,and_fprm_linear_parity,and_fprm_greedy,direct_anf,and_direct_anf --out results/analysis_external_highdim_scale_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset ultra_highdim_resource --formats blif,truth --out-dir benchmark_exports/ultra_highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/ultra_highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 16 --max-n 16 --max-abc-n 16 --max-xag-n 16 --max-lut-n 16 --max-bdd-n 16 --bdd-orders 8 --timeout 45 --workers 8 --out results/raw_external_ultra_highdim_resource.csv --summary results/summary_external_ultra_highdim_resource.csv --run-manifest results/manifest_external_ultra_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_ultra_highdim_resource.csv --internal-csv results/raw_ultra_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_fprm_linear_pair,and_fprm_root_beam,direct_anf,and_direct_anf --out results/analysis_external_ultra_highdim_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python export_benchmarks.py --preset mega_highdim_resource --formats blif,truth --out-dir benchmark_exports/mega_highdim_resource_external_seed42
/opt/anaconda3/envs/mcts-qoracle/bin/python run_external_baselines.py --manifest benchmark_exports/mega_highdim_resource_external_seed42/manifest.json --methods external_abc_aig,external_abc_xag,external_abc_lut,external_bdd --min-n 18 --max-n 18 --max-abc-n 18 --max-xag-n 18 --max-lut-n 18 --max-bdd-n 18 --bdd-orders 8 --timeout 90 --workers 8 --out results/raw_external_mega_highdim_resource.csv --summary results/summary_external_mega_highdim_resource.csv --run-manifest results/manifest_external_mega_highdim_resource.json
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_external_baselines.py --external-csv results/raw_external_mega_highdim_resource.csv --internal-csv results/raw_mega_highdim_resource.csv --targets and_resource_nmcts,and_profile_resource_nmcts,and_pareto_resource_nmcts,and_fprm_linear_pair_fast,and_fprm_root_beam,direct_anf,and_direct_anf --out results/analysis_external_mega_highdim_resource.md
/opt/anaconda3/envs/mcts-qoracle/bin/python run_ros_lut_proxy.py --manifest traditional=benchmark_exports/traditional_resource_external_seed42/manifest.json --manifest n14=benchmark_exports/highdim_resource_external_seed42/manifest.json --manifest n15=benchmark_exports/highdim_scale_resource_external_seed42/manifest.json --manifest n16=benchmark_exports/ultra_highdim_resource_external_seed42/manifest.json --manifest n18=benchmark_exports/mega_highdim_resource_external_seed42/manifest.json --internal traditional=results/raw_traditional_resource.csv --internal n14=results/raw_highdim_resource.csv --internal n15=results/raw_highdim_scale_resource.csv --internal n16=results/raw_ultra_highdim_resource.csv --internal n18=results/raw_mega_highdim_resource.csv --ks 3,4,5 --workers 8 --timeout 45 --raw-out results/raw_ros_lut_proxy_sweep.csv --best-out results/raw_ros_lut_proxy_best.csv --summary results/summary_ros_lut_proxy.csv --analysis results/analysis_ros_lut_proxy.md --latex-out paper_latex/tables/ros_lut_proxy.tex --run-manifest results/manifest_ros_lut_proxy.json
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pip install cmake pybind11
/opt/anaconda3/envs/mcts-qoracle/bin/python -m pip install --no-build-isolation 'git+https://github.com/msoeken/revkit@develop'
/opt/anaconda3/envs/mcts-qoracle/bin/python run_revkit_baseline.py --max-n 6 --workers 8
/opt/anaconda3/envs/mcts-qoracle/bin/python run_revkit_highdim_timeout_probe.py --input results/raw_highdim_resource.csv --min-n 14 --max-n 14 --limit 8 --timeout 30 --workers 4
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_phase_rz_portfolio.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_rz_synthesis_cost.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_phase_parity_baseline.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_phase_parity_fprm_search.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_phase_parity_affine_search.py --max-n 6 --transform-budget 32
```

The RevKit command is a real Python API baseline (`oracle_synth`) on complete
truth-table rows, not the ABC-only ROS-style LUT proxy.  On the 177 usable
`n <= 6` traditional functions it succeeds on all rows, but the returned
Rz-phase netlists are not directly exact Clifford+T: 171/177 rows contain
non-Clifford `Rz` rotations, with 9242 such rotations in total and maximum
angle/pi denominator 64.  Resource-NMCTS vs RevKit is therefore a lower-bound
proxy comparison: 6/171/0 on score, mean score +751.69%, and T-like count
+4060.08%.  As a sensitivity check, adding a symbolic cost of 1 score unit per
non-Clifford Rz changes Resource-NMCTS vs RevKit to 140/37/0 with mean score
-14.52%, and adding 2 units changes it to 177/0/0 with mean score -53.48%.
The phase/Rz portfolio analysis then score-reranks verified internal circuits:
the Resource-NMCTS family reaches 157/20/0 at 1 score unit per non-Clifford Rz
and 177/0/0 at 1.5 units, while the traditional baseline family is only
80/97/0 at 1 unit.
`analyze_rz_synthesis_cost.py` additionally charges every non-Clifford Rz in
the RevKit phase netlist with an approximate Clifford+T rotation-synthesis
proxy `ceil(slope*log2(1/epsilon)+offset)`.  Under the Ross-Selinger-style
`epsilon=1e-3` proxy, `T/Rz=30` and the Resource-NMCTS family reaches 177/0/0
with mean score -95.03%; under the more conservative `4 log2(1/epsilon)+10`
proxy at `epsilon=1e-6`, `T/Rz=90` and it remains 177/0/0 with mean score
-97.01%.
`run_revkit_highdim_timeout_probe.py` audits the high-dimensional RevKit API
path with one subprocess per row and a hard wall-time cutoff.  On the current
`n=14` eight-row probe, RevKit returns one circuit and times out on seven rows
at 30 s.  The returned row has 32767 non-Clifford Rz rotations, so it remains a
phase-netlist boundary case: Resource-NMCTS loses to the RevKit lower-bound
score on that row but wins after a symbolic `score+1/Rz` charge.  Timeout rows
have no circuit metrics and should not be averaged as a paired resource
benchmark.
This result should be presented as a phase-rotation representation-boundary
finding, not as a hardware-mapping or exact Clifford+T T-count claim.

`run_phase_parity_baseline.py` moves this boundary forward by adding a real
internal phase/Rz emitter.  It expands each ANF monomial into a parity-phase
identity, merges equal parity masks, and verifies all 177 `n <= 6` traditional
functions as phase oracles up to global phase.  The result is intentionally
reported as both evidence and limitation: phase-parity ANF loses to RevKit's
raw lower-bound score by 40/137/0, mean +69.25%, but has far fewer
non-Clifford rotations (171/0/6, mean -63.33%) and wins by 177/0/0 once each
non-Clifford Rz is charged one score unit or a `T/Rz=30` synthesis proxy is
used.  This establishes a concrete internal phase-oracle baseline while
setting the next target: learned or optimized phase/Rz-aware search, not naive
parity expansion.

`run_phase_parity_fprm_search.py` makes the first optimization step on top of
that emitter by searching all fixed-polarity Reed-Muller forms for `n <= 6`.
For each polarity it synthesizes `g(z)=f(z xor p)`, translates shifted parity
masks back to `x`, and verifies equivalence up to an arbitrary global phase.
Across three rank metrics it emits 531 selected rows and verifies 531/531.  The
best lower-bound polarity improves over phase-parity ANF by 59/0/118 with mean
score -3.98%; the `T/Rz=30` objective improves by 59/0/118 with mean -0.47%.
The result should be reported as a real but modest search gain, not as the
final phase/Rz-aware method.

`run_phase_parity_affine_search.py` strengthens this step by searching bounded
invertible linear transforms before the FPRM polarity sweep.  For a transform
`B`, it synthesizes `h(y)=f(B^{-1}y)` and `g(z)=h(z xor p)`, then maps each
selected parity mask back to the original variables by `m_x=B^T m_z` and flips
the rotation sign when `m_z dot p=1`.  The identity transform is included, so
Affine-FPRM is non-degrading relative to fixed-polarity FPRM under the same
rank metric.  The run verifies 531/531 selected rows; under `T/Rz=30`,
nonidentity transforms are selected on 81/177 functions and the method improves
over fixed-polarity FPRM by 81/0/96 with mean score -2.51%, over phase-parity
ANF by 85/0/92 with mean score -2.98%, and over RevKit by 177/0/0 with mean
score -65.50%.  This moves the phase/Rz branch from polarity-only search to
affine algebraic preconditioning, while remaining a logic-layer phase-oracle
emitter with no approximate rotation sequences or hardware mapping.

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
- `search_ablation_traditional`: dedicated $n \leq 6$ contribution rerun that
  compares heuristic-only, beam-only, no-MCTS, Resource-NMCTS, and
  Pareto-Resource-NMCTS portfolios on the same functions.
- `search_ablation_highdim`: lightweight $n=14$ random-ANF guard rerun that
  compares heuristic-only, beam-only, root-beam, linear-pair, and no-MCTS
  portfolios without the expensive high-dimensional Pareto tail.
- `highdim_neural_prior`: diagnostic $n=14$ random-ANF learned-prior slice for
  Resource-NMCTS.  It uses a dedicated linear-action scorer and a root-only
  neural linear-pair child, so the learned model can perturb the high-dimensional
  guard without recursively scoring every child subproblem.
- `large_resource_core`: 330-function large logical benchmark through `n=12`,
  now including the profile-aware Resource-NMCTS variant and process-isolated
  hard timeouts for long-tail tasks.
- `highdim_resource`: isolated `n=14` random-ANF stress benchmark with direct
  ANF, logical-AND direct ANF, FPRM-greedy, bounded FPRM root-beam,
  bounded FPRM linear-pair factoring, bounded affine-greedy, Resource-NMCTS,
  Profile-Resource-NMCTS, and Pareto-Resource-NMCTS.  The guarded variants keep
  the root-child beam baseline and use a one-extra-layer CNOT-only pairwise XOR
  factor candidate.
- `highdim_scale_resource`: isolated `n=15` random-ANF scale check with direct
  ANF, logical-AND direct ANF, FPRM-greedy, bounded FPRM root-beam, FPRM
  linear-pair factoring, a one-extra-layer bounded linear-pair refinement,
  a standalone width-three linear-parity ablation, Resource-NMCTS,
  Profile-Resource-NMCTS, and Pareto-Resource-NMCTS.
- `ultra_highdim_resource`: isolated `n=16` random-ANF scale check with direct
  ANF, logical-AND direct ANF, bounded FPRM root-beam, one-layer FPRM
  linear-pair factoring, recursive FPRM linear-pair factoring, a root-neural
  recursive guard, a baseline-preserving AI guard, Resource-NMCTS,
  Profile-Resource-NMCTS, and Pareto-Resource-NMCTS.  Resource/Profile match
  the AI guard at `n=16`; the Pareto row is close but not used as independent
  high-dimensional Pareto separation evidence.
- `mega_highdim_resource`: isolated `n=18` random-ANF stress check with direct
  ANF, logical-AND direct ANF, bounded FPRM root-beam, fast FPRM linear-pair,
  Resource-NMCTS, Profile-Resource-NMCTS, and Pareto-Resource-NMCTS.  It uses a
  fast high-dimensional linear-pair guard that limits expensive rest-branch
  greedy solves and keeps a root-beam baseline.
- `giga_highdim_resource`: isolated `n=20` random-ANF pressure-boundary check
  with direct ANF, logical-AND direct ANF, ANF Boolean-ring linear screen,
  bounded FPRM root-beam, fast FPRM linear-pair, Resource-NMCTS,
  Profile-Resource-NMCTS, and Pareto-Resource-NMCTS.  In the current run,
  root-beam and fast linear-pair hit the 300 s task timeout on all six
  functions, while the ANF-only Boolean-ring screen completes and gives
  Resource/Profile/Pareto a bounded improvement over AND-direct ANF.  Treat
  this as a scale-boundary improvement, not as strong evidence that deep
  high-dimensional neural/FPRM tree search is solved.
- `large_resource`: experimental `n=14` stress extension.  This preset exposed
  the mixed-suite runtime tail and is kept for broader engineering sweeps.
- `main`: large-scale placeholder for broader sweeps.

Outputs are written to `results/`.  The neural prior is saved at
`models/action_scorer_rollout_logical_and.pt`; the high-dimensional linear-action
diagnostic prior is saved at `models/linear_action_scorer_highdim.pt`.
The structure-level Boolean screen-depth policy is trained with
`train_screen_depth_policy.py` and saved at
`models/boolean_screen_depth_policy.pt`; its held-out analysis is written to
`results/analysis_boolean_screen_depth_policy.md`, with the paper table at
`paper_latex/tables/boolean_screen_depth_policy.tex`.
The conservative depth-2 skip guard is trained with
`train_screen_depth_guard.py` and saved at
`models/boolean_screen_depth_guard.pt`; its held-out analysis is written to
`results/analysis_boolean_screen_depth_guard.md`, with the paper table at
`paper_latex/tables/boolean_screen_depth_guard.tex`.  A shallow-feature staged
variant is saved at `models/boolean_screen_depth_guard_shallow_staged.pt`, with
mode comparison in `results/analysis_boolean_screen_depth_guard_modes.md`.
The high-dimensional Resource screen gate is trained with `train_structure_gate.py`
and saved at `models/resource_structure_gate.json`; it adds
`and_resource_nmcts_screen_gate`, a gated Resource-NMCTS variant that skips the
expensive Resource tail when the adaptive Boolean-ring screen is predicted to be
sufficient.
The high-budget Boolean screen depth-frontier policy is trained with
`train_screen_depth_frontier_policy.py` and saved at
`models/boolean_screen_depth_frontier_policy.pt`.  It chooses among depth-2,
depth-3, and depth-4 Boolean-ring screens; its held-out analysis is written to
`results/analysis_boolean_screen_depth_frontier_policy.md`, with the table at
`paper_latex/tables/boolean_screen_depth_frontier_policy.tex`.
The larger depth-frontier policy is saved at
`models/boolean_screen_depth_frontier_policy_large.pt`.  Its training run uses
192 train / 72 validation / 48 held-out generated term sets, hidden width 160,
and a wider action frontier.  The held-out score gap to the oracle depth-2/3/4
frontier falls from +0.80% to +0.04%; on the independent `n=24,28,32,40`
generalization run, it improves over fixed depth-2 by 56/0/40 with -2.34%
mean score, improves over the old policy by 17/0/79 with -0.49% mean score,
and remains +0.10% from all-depth while saving -53.50% planning time.  This is
a quality-strengthened policy, not a faster policy: it chooses depth-3/4 more
often and is slower than the old frontier policy.
The cost-aware depth-frontier policy is saved at
`models/boolean_screen_depth_frontier_policy_cost_time003.pt`.  It uses the
same training size and hidden width as the large model, but labels examples
with a relative objective `score_delta + 0.003*time_delta` against depth-2.  On
the independent `n=24,28,32,40` generalization run, it keeps 56/0/40 score W/L/T
against fixed depth-2 with -1.39% mean score, while lowering mean planning-time
overhead to +170.03% and explicit ancilla lifetime-area overhead to +14.63%.
Against the large quality model it trades +0.99% score for -33.02% time and
-7.61% lifetime area.  On the `n=23` truth-table bridge it passes 60/60
truth/plan/circuit checks and trades +0.92% score for -56.29% time and -12.62%
lifetime area against the large model.
The staged depth-frontier controller is summarized in
`results/analysis_stage_gated_frontier.md`.  It selects a 1.25% depth-4 trigger
on the large-policy validation split, then applies it unchanged to independent
scale and bridge rows.  On `n=24,28,32,40`, it is only +0.04% mean score from
all-depth while reducing staged planning time by -25.43%; on the `n=23`
truth-table bridge it ties all-depth score and saves -11.51% staged time.
This is a high-quality teacher/guard, not a faster replacement for the large
single-shot policy.
The learned sparse depth-4 gate is summarized in
`results/analysis_sparse_depth4_gate.md` and audited in
`results/analysis_sparse_depth4_gate_generalization.md`.  It uses the
deterministic sparse depth-2/4 frontier as the quality reference and predicts
whether the depth-4 screen should run after depth-2 has been evaluated.  The
formal run trains on `n=16,20,24`, selects a conservative validation threshold,
and tests on held-out `n=28,40` generated term sets: 48/48 rows match the sparse
frontier, false skips are 0, and time falls by -17.39%.  The independent audit
then reuses the same gate on three new seeds over `n=24,28,32,40`: 144/144 rows
match the sparse frontier with 0 false skips while saving -13.43%
sparse-frontier evaluation time.  `analyze_sparse_depth4_gate_sensitivity.py`
sweeps deployment thresholds on the same 144-pair audit: the selected threshold
has 0 false skips and -13.43% time, the best zero-false-skip threshold reaches
-14.92% time, and allowing one false skip reaches -15.49% time with a +0.01%
mean score gap.  This is a learned planning-budget controller, not a stronger
quality frontier than the deterministic sparse depth-2/4 audit.
Term-set scale tests beyond truth-table-feasible sizes are run with
`run_screen_scale_terms.py`; outputs are written to
`results/analysis_screen_scale_terms.md`, `results/raw_screen_scale_terms.csv`,
and `paper_latex/tables/screen_scale_terms.tex`.  Each returned factor plan is
also expanded symbolically back to its ANF monomial set, so these runs now
include plan-level ANF equivalence checks.  The emitted X/CNOT/MCT oracle
circuit is then simulated symbolically over GF(2) polynomials, which gives
emitted-circuit equivalence evidence without constructing full truth tables.
The high-dimensional truth-table bridge now covers `n=21,22,23`, plus a large
frontier-policy rerun on the same `n=23` seed: 240/240 method rows pass
complete oracle truth-table verification, plan ANF verification, and
emitted-circuit ANF verification.  The original `n=23` slice contains six
functions and sixty method rows; its frontier policy improves score by 1.88%
and T-depth proxy by 1.69% against fixed depth-2.  The large-policy `n=23`
rerun improves over the old policy by 1/0/5 with -0.48% mean score and -0.45%
T-depth proxy, with the expected increase in explicit ancilla lifetime area.
The cost-aware `n=23` rerun adds another 60 fully verified method rows and is
best treated as a fast-quality operating point: 4/0/2 against fixed depth-2
with -1.46% mean score and +196.09% plan time, while saving -80.46% plan time
against all-depth adaptive.

Current structure-policy evidence:

- Training examples: 240 generated high-dimensional ANF term sets at
  `n=14,16,18`; validation examples: 72; held-out test examples: 48 at `n=20`.
- Held-out depth accuracy: 79.2%.
- Policy vs single Boolean screen: 42/0/6 score win/loss/tie, mean score
  -6.57%.
- Policy vs depth-1 Boolean screen: 34/0/14, mean score -2.57%.
- Policy vs full all-depth adaptive evaluation: mean score +0.28%, mean runtime
  -34.71%.
- Policy vs fixed depth-2 screen: 0/5/43, mean score +0.28%, mean runtime
  -10.85%; therefore this is useful structure-level AI evidence, but not yet a
  final quality improvement over the strongest deterministic depth-2 screen.
- The conservative static-direct depth-2 skip guard removes that quality loss
  on a fresh held-out `n=20` run: 96/96 score ties vs fixed depth-2, 0 false
  skips, 4/96 safe skips, mean runtime -0.54% vs fixed depth-2, and mean
  runtime -24.74% vs all-depth adaptive.  A shallow-staged high-confidence
  variant raises safe skips to 8/48 with 0 false skips and -7.81% runtime vs
  all-depth adaptive, but remains +29.10% slower than fixed depth-2 because it
  evaluates shallow screens before falling back.  This is stronger
  structure-level guard evidence, not a final high-dimensional quality
  breakthrough.
- Term-set scale evidence now covers 192 generated high-dimensional ANF term
  sets at `n=20,22,24,28`.  All-depth adaptive Boolean-ring screening improves
  over single screen by 169/0/23 score W/L/T with a -6.63% mean score change,
  but ties fixed depth-2 in score and costs +47.92% runtime.  The learned depth
  policy preserves nearly all of that quality signal: 169/0/23 vs single screen
  with -6.56% mean score, and 0/6/186 vs all-depth adaptive with only +0.08%
  mean score while saving -31.01% runtime.  At `n=28`, the policy ties
  all-depth adaptive on all 48 term sets and saves -32.15% runtime.  The
  conservative direct depth-2 guard ties fixed depth-2 on all 192 term sets and
  has -0.14% mean runtime change.  Symbolic ANF plan expansion and emitted
  X/CNOT/MCT circuit simulation both verify 1344/1344 generated method rows
  with zero mismatches.  This is large-scale emitted-circuit equivalence
  evidence, but still not full truth-table simulation for `n>20`.
- Extended term-set scale evidence now also covers 144 generated ANF term sets
  at `n=32,36,40`, written separately as
  `results/analysis_screen_scale_extended_terms.md`.  The learned depth policy
  ties all-depth adaptive on all 144 term sets while saving -33.14% mean
  runtime, and improves over single screen by 110/0/34 with a -5.55% mean
  score change.  The emitted X/CNOT/MCT symbolic simulator verifies 1008/1008
  method rows with zero mismatches, with maximum wire-polynomial size 288.
  This strengthens the large-scale structural generalization claim, while
  preserving the same boundary: it is not full truth-table simulation.
- A separate depth-frontier run, `results/analysis_screen_scale_depth_frontier_terms.md`,
  quantifies the high-budget quality mode on 72 generated term sets at
  `n=20,28,40`.  Deeper Boolean-ring screening breaks the fixed-depth-2 quality
  ceiling: depth-3 vs depth-2 gives 49/0/23 score W/L/T with a -1.93% mean
  score change, and depth-4 vs depth-2 gives 49/0/23 with a -3.10% mean score
  change.  The cost is substantial: mean runtime increases by +193.71% and
  +682.97%, respectively.  All 648 method rows pass both symbolic plan
  expansion and emitted-circuit ANF verification with zero mismatches.  This is
  quality-frontier evidence, not the default fast policy.
- The learned depth-frontier policy turns that high-budget frontier into a
  structure-level AI tradeoff.  On the held-out `n=28,40` policy test it is
  +0.80% mean score from the oracle depth-2/3/4 frontier while saving -58.76%
  runtime.  In the `n=20,28,40` scale harness it improves over fixed depth-2 by
  35/0/37 with -2.19% mean score, and is +0.97% mean score from all-depth
  depth<=4 while saving -58.69% runtime.  All 720 method rows pass both
  symbolic plan expansion and emitted-circuit ANF verification.
- An independent-seed depth-frontier-policy generalization run at
  `n=24,28,32,40` gives 40/0/56 score W/L/T against fixed depth-2 with a
  -1.85% mean score change, and is +0.61% mean score from fixed depth-4 while
  saving -23.40% plan time.  All 960 method rows pass both symbolic plan
  expansion and emitted-circuit ANF verification.  This strengthens the claim
  that frontier-policy gains are not tied to the first `n=20,28,40` random
  slice.
- The larger frontier policy rerun at the same independent seed,
  `results/analysis_screen_scale_depth_frontier_policy_large_generalization_terms.md`,
  strengthens the quality side of that claim.  It gives 56/0/40 score W/L/T
  against fixed depth-2 with a -2.34% mean score change, improves over the old
  frontier policy by 17/0/79 with -0.49% mean score, and is only +0.10% mean
  score from all-depth while saving -53.50% plan time.  All 960 method rows
  again pass both symbolic plan expansion and emitted-circuit ANF verification.
- The truth-table bridge runs, `results/analysis_truth_bridge_terms.md` and
  `results/analysis_schedule_truth_bridge_n23_terms.md`, build full truth
  tables for 18 generated `n=21,22,23` ANF functions.  All 180 method rows pass
  complete truth-table oracle verification, ANF plan expansion, and
  emitted-circuit symbolic verification with zero mismatches.  The new `n=23`
  slice has 6 functions / 60 method rows; depth-frontier policy is 4/0/2 vs
  fixed depth-2 with -1.88% mean score, and +0.61% mean score / -48.77% plan
  time vs all-depth adaptive.  This moves the complete-verification boundary
  beyond `n=20` on a small bridge slice; larger `n=24--40` runs remain symbolic
  term-set evaluations.
- The large-policy `n=23` bridge rerun,
  `results/analysis_truth_bridge_n23_large_frontier_terms.md`, adds another
  60 fully verified method rows.  It is 5/0/1 against fixed depth-2 with
  -2.36% mean score, 0/1/5 against all-depth with +0.12% mean score and
  -45.99% plan time, and 1/0/5 against the old frontier policy with -0.48%
  mean score and -0.45% T-depth proxy.
- The cost-aware frontier-policy generalization run,
  `results/analysis_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.md`,
  keeps the same 56/0/40 score W/L/T against fixed depth-2 as the large model
  but reduces the planning-time overhead to +170.03%.  The corresponding
  `n=23` bridge rerun,
  `results/analysis_truth_bridge_n23_cost_time003_frontier_terms.md`, passes
  60/60 complete truth-table, plan, and emitted-circuit checks.
- The ultra-scale symbolic stress run,
  `results/analysis_screen_scale_ultra_scale64_stress.md`, extends the same
  term-set protocol to 48 generated functions at `n=48,56,64`.  All 480 method
  rows pass plan-level ANF and emitted-circuit ANF verification with zero
  mismatches and maximum wire-polynomial size 282.  Depth-4 screening improves
  over fixed depth-2 by 24/0/24 with -1.81% mean score, while the learned
  depth-frontier policy improves over depth-2 by 10/0/38 with -0.84% mean score
  and reduces planning time by 61.61% relative to the full measured frontier.  This
  is ultra-scale symbolic evidence, not a complete truth-table benchmark.
- The staged frontier analysis,
  `results/analysis_stage_gated_frontier.md`, reuses measured and verified
  depth-2/3/4 rows.  Its validation-selected 1.25% trigger gives +0.04% mean
  score and -25.43% staged time against all-depth on the independent
  `n=24,28,32,40` scale run, with 96/96 selected rows verified.
- The learned sparse depth-4 gate,
  `results/analysis_sparse_depth4_gate_generalization.md`, trains on
  `n=16,20,24` generated term sets and is audited without retraining on three
  independent seeds over `n=24,28,32,40`.  It matches the deterministic sparse
  frontier on all 144 audit pairs with 0 false skips while saving -13.43%
  sparse-frontier evaluation time.
- Logic-level schedule-proxy evidence is now emitted by `run_screen_scale_terms.py`
  and `run_truth_bridge_terms.py`, then summarized by
  `analyze_schedule_metrics.py`.  The metrics are not hardware mapping results:
  they are emitted-circuit proxies for parallel logical depth, CNOT-depth,
  T-depth, live explicit ancilla peak, and explicit ancilla lifetime area.  In
  the independent `n=24,28,32,40` schedule run, depth-frontier policy vs fixed
  depth-2 has 40/0/56 score W/L/T with -1.85% mean score and 40/0/56 T-depth
  proxy W/L/T with -1.85%; it trades this for +20.09% explicit ancilla lifetime
  area.  Against depth-4/all-depth it is only +0.55% T-depth proxy but reduces
  explicit ancilla lifetime area by -5.42%.  The schedule truth-table bridge
  reproduces the same pattern on 180 fully verified method rows: on `n=21,22`,
  frontier policy vs depth-2 is 8/0/4 in score (-3.50%) and T-depth proxy
  (-3.32%), with a +32.93% lifetime-area tradeoff; on `n=23`, it is 4/0/2 in
  score (-1.88%) and T-depth proxy (-1.69%), with a +29.49% lifetime-area
  tradeoff.

Current screen-gate evidence:

- The decision-stump gate is trained on 18 labelled adaptive-screen vs
  Resource rows from `n=18` and `n=20`; after safety-first threshold selection
  it uses the rule `n >= 20`.
- On the committed `n=20` `giga_highdim_resource` slice,
  `and_resource_nmcts_screen_gate` matches full `and_resource_nmcts` exactly on
  T, CNOT, depth, peak ancilla, and score (0/0/6 score W/L/T), while mean runtime
  drops from 77.10 s to 20.71 s (-75.58%).
- On the held-out `gate_holdout_resource` slice with 8 functions each at
  `n=19` and `n=20`, the gate matches full Resource-NMCTS on score for all
  16 functions and reduces mean runtime by 36.83% overall.  The dimension split
  matters: at `n=19`, adaptive screen alone loses score on 4/8 functions, so
  the gate correctly keeps the Resource tail; at `n=20`, adaptive screen ties
  full Resource on all 8 functions and the gate skips the tail, saving 73.66%
  mean runtime.

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
  Shannon-network resource estimate.
- `run_ros_lut_proxy.py` is a deliberately marked ROS-style LUT proxy rather
  than an official ROS reproduction.  It reuses the exported BLIF benchmarks,
  runs ABC `if -K` for a configurable K sweep, verifies each mapped BLIF truth
  table, estimates every LUT network by local-ANF compute/action/uncompute
  logic, and chooses the best K under the project score.  It is now complemented
  by a mockturtle KLUT-to-XAG probe, a CirKit-shell AIG/MC probe, a RevKit
  Python API phase-netlist baseline, and a legacy RevKit CLI exact-oracle
  reversible-synthesis probe.  The full official ROS flow remains future work.
- `analyze_toolchain_readiness.py` records external-tool availability for the
  current workstation.  The current audit finds the bundled ABC binary,
  mockturtle source/adapter availability, RevKit Python API availability, and
  CirKit 3 shell availability; the legacy RevKit/CirKit CLI is available
  through `tmp/cirkit_legacy/build/programs/revkit`; see
  `results/analysis_toolchain_readiness.md`.

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
  `and_affine_nmcts`, 39/0/138 for `and_resource_nmcts`, and 29/0/148 for
  `and_pareto_resource_nmcts`.
- Mean score reductions are 1.47%, 1.10%, and 0.78%, respectively.  Paired
  mean relative runtime increases are 91.22%, 55.11%, and 18.77% on this
  small-function slice, so the learned prior is a quality-improving search
  signal rather than the current fastest mode.

High-dimensional neural-prior diagnostic evidence from
`results/analysis_neural_prior_highdim_ablation.md`:

- A first full-recursive neural linear-pair child was too expensive at n=14, so
  the implemented high-dimensional path now uses root-only neural screening and
  deterministic child subplans.
- The dedicated `models/linear_action_scorer_highdim.pt` model was trained on
  6086 high-dimensional linear-action samples with immediate-gain labels.
- On 12 matched n=14 random ANF functions, learned Resource-NMCTS has 1/0/11
  score wins/losses/ties versus no-prior Resource-NMCTS and a -0.01% mean score
  change, with mean runtime rising from 23.26 s to 48.55 s.  This is a boundary
  diagnostic, not a strong high-dimensional AI contribution claim.
- The root-action teacher diagnostic in
  `results/analysis_highdim_root_action_oracle.md` evaluates the same n=14
  slice with actual greedy child plans for a wider CNOT-only linear-pair root
  action set.  Oracle top-24 has 3/0/7 score wins/losses/ties over the current
  heuristic top-4 window with a -0.18% mean score change, and 7/0/3 over
  heuristic top-1 with a -0.43% mean score change.  The existing neural top-4
  ordering is 1/1/8 versus heuristic top-4 with +0.06% mean score change, so
  the current high-dimensional model does not yet exploit this small teacher
  signal.

Search-contribution decomposition evidence from
`results/analysis_search_contribution.md`:

- The report consolidates matched-pair evidence from `ablation_affine`,
  `traditional_resource`, `highdim_resource`, `highdim_scale_resource`,
  `ultra_highdim_resource`, `mega_highdim_resource`, and the learned-prior
  reruns.
- Affine-greedy versus completed fixed-coordinate MCTS pairs has 165 score
  wins, 88 losses, and 68 ties, with a 12.12% mean score reduction; this is
  the largest pre-portfolio algorithmic jump, but not a monotone guard.
- Neural refine over affine-greedy has 65 score wins, 0 losses, and 257 ties;
  guarded Affine-NMCTS over no-guard has 88 score wins, 0 losses, and 234 ties.
- The Pareto archive improves over the strengthened Resource-NMCTS on the
  177-function `traditional_resource` slice with 68 score wins, 0 losses,
  109 ties, and a 3.26% mean score reduction.
- A dedicated `search_ablation_traditional` rerun adds explicit heuristic-only,
  beam-only, and no-MCTS portfolios.  Resource-NMCTS improves over the no-MCTS
  portfolio with 54 score wins, 0 losses, 123 ties, and a 1.44% mean score
  reduction; Pareto-Resource-NMCTS improves over the same no-MCTS portfolio
  with 106 score wins, 0 losses, 71 ties, and a 4.69% mean score reduction.
- A lightweight high-dimensional `search_ablation_highdim` rerun adds a
  same-preset n=14 guard/no-MCTS check with 16 random ANF functions, 8 methods,
  128 rows, and 0 errors/skips.  The no-MCTS portfolio improves over
  heuristic-only by 14/0/2 score W/L/T with a 6.50% mean score reduction, over
  root beam by 14/0/2 with a 6.25% reduction, and over linear-pair by 14/0/2
  with a 3.08% reduction.  This is a bounded high-dimensional mechanism check,
  not a full high-dimensional Pareto rerun.
- The high-dimensional scale contribution is mainly the bounded linear-pair
  guard: score improvements over root beam are 60/0/4 at n=14, 30/0/2 at
  n=15, 23/0/1 at n=16 with the recursive guard, and 6/0/6 at n=18.
  At n=16, the baseline-preserving AI guard further improves over the
  deterministic recursive guard by 6/0/18 with no score losses. Resource and
  Profile match that guarded candidate in the rerun; Pareto selection adds
  further separation in some smaller suites but should not be overstated at
  this high-dimensional scale.

Traditional Boolean/ESOP baseline evidence from
`results/analysis_traditional_resource.md` and
`results/runtime_traditional_resource.md`:

- 177 functions with $n \leq 6$, 10 methods, 1770 result rows, 0 errors, and 0
  skips.
- Mean T-count / composite score: `and_pareto_resource_nmcts` 40.43 / 49.56,
  `and_fprm_polarity_archive` 43.01 / 52.50,
  `and_resource_nmcts` 43.91 / 53.22,
  `and_affine_nmcts` 45.88 / 55.37, fixed MCTS 62.06 / 73.09, ESOP cube beam
  71.32 / 83.82, ESOP MILP 83.59 / 96.73, and SSHR-H 81.04 / 88.19.
- Against Resource-NMCTS, `and_pareto_resource_nmcts` has 68 score wins, 0
  losses, and 109 ties, with a 3.26% mean score reduction.
- Against ESOP cube beam, `and_pareto_resource_nmcts` has 174 score wins, 0
  losses, and 3 ties, with a 35.86% mean score reduction.
- Against time-limited weighted ESOP MILP, `and_pareto_resource_nmcts` has 167
  score wins, 3 losses, and 7 ties, with a 29.84% mean score reduction.
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

Exact bounded FPRM-DP evidence from `results/analysis_exact_fprm_dp.md`:

- Solves an exact dynamic program over the bounded fixed-polarity FPRM factor
  model with all monomial factors and CNOT-only linear-pair factors.  This is a
  same-model optimum, not a global reversible-circuit optimum.
- Covers all 72 `traditional_resource` functions with `n <= 4`, with 0
  errors/skips and successful oracle verification for every emitted circuit.
- `and_resource_nmcts` versus Exact FPRM-DP: 51/3/18 score W/L/T, with a
  12.18% mean score reduction; `and_pareto_resource_nmcts` versus Exact
  FPRM-DP: 51/0/21, with a 12.20% mean score reduction.
- Exact FPRM-DP itself beats weighted ESOP-MILP by 57/12/3 score W/L/T and
  exact SSHR-I by 60/12/0 against CNOT-optimized SSHR-I and 59/12/1 against
  T-optimized SSHR-I.  Its CNOT count is often higher than SSHR-I, so the claim
  remains resource-score/low-T rather than CNOT-only optimality.

Exact XAG multiplicative-complexity evidence from
`results/analysis_exact_xag_mc.md`:

- Computes the exact minimum number of AND nodes in an XOR-AND graph for all 72
  `traditional_resource` functions with `n <= 4`; 72/72 solved, 0 unknown.
  This is a global lower bound on logical-AND T-count (`4 * min AND`), not a
  full CNOT/depth optimum.
- `and_resource_nmcts` and `and_pareto_resource_nmcts` both reach this global
  T lower bound on 12/72 functions, with no row below the bound and a +53.01%
  mean T gap to the lower bound.
- ESOP-MILP reaches the lower bound on 3/72 functions with a +120.14% mean T
  gap; T-optimized SSHR-I reaches it on 5/72 functions with a +143.06% mean T
  gap.  This gives a stronger exact small-scale T-count reference than the
  bounded FPRM-DP model.

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
- The ROS-style LUT proxy sweep covers the same `n=3..6` traditional functions
  plus exported `n=14`, `n=15`, `n=16`, and `n=18` high-dimensional functions.
  It produces 927 K-sweep rows and 309 best-K rows, with all truth-table checks
  passing.  The best-K proxy beats fixed K=4 on weighted score by 219/0/90
  with an 18.12% mean reduction, and `and_resource_nmcts` still beats this
  stronger LUT proxy on all 309 functions with an 83.77% mean score reduction.

External toolchain readiness from `results/analysis_toolchain_readiness.md`:

- ABC is available through `tmp/abc/abc` and is already used for AIG/XAG/LUT/ESOP
  exported-baseline paths.
- mockturtle source plus the project KLUT-to-XAG adapter are available and have
  produced verified official-header probe rows.  CirKit 3 shell is available
  and has produced verified AIG/multiplicative-complexity probe rows.  RevKit
  Python API is available and has produced the `oracle_synth` phase-netlist
  baseline.  Legacy RevKit CLI is available and has produced a TBS/DBS/RMS
  exact-oracle reversible-synthesis portfolio.  Full official ROS reproduction
  remains future work.
- Against CNOT-optimized SSHR-I, `and_resource_nmcts` has 164 T-count wins, 3
  losses, and 10 ties; score wins/losses/ties are 168/9/0 with a 27.92% mean
  score reduction.  CNOT count is worse on 168/177 functions.
- Against T-optimized SSHR-I, `and_resource_nmcts` has 166 T-count wins, 1
  loss, and 10 ties, with a 26.25% mean score reduction.

Exported high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD evidence from
`results/analysis_external_highdim_resource.md` and
`results/analysis_external_highdim_scale_resource.md` and
`results/analysis_external_ultra_highdim_resource.md` and
`results/analysis_external_mega_highdim_resource.md`:

- The external AIG/XAG/LUT/BDD paths now cover 64 exported `n=14` random-ANF
  functions, 32 exported `n=15` random-ANF functions, 24 exported `n=16`
  random-ANF functions, and 12 exported `n=18` random-ANF functions for each of
  ABC-AIG, ABC-XAG, ABC-LUT, and BDD, with 528/528 correct rows and 0
  errors/skips.
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
- At `n=18`, the same guarded methods beat ABC-AIG, ABC-XAG, ABC-LUT, and BDD
  on all 48 T-count, CNOT, peak-ancilla, and weighted-score comparisons.  Mean
  score reductions are 98.85% against AIG, 99.05% against XAG, 99.69% against
  LUT, and 98.30% against BDD.
- ABC-AIG and ABC-XAG remain shallower under the current level-based estimate on
  most high-dimensional functions, including 22/24 `n=16` functions for each of
  ABC-AIG and ABC-XAG and 10/12 and 11/12 `n=18` functions, respectively,
  while ABC-LUT and the BDD Shannon-network estimate are deeper; the claim
  remains weighted-resource and low-ancilla dominance rather than depth-only
  dominance against every possible toolchain.

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

- 64 random ANF functions at `n=14`, 9 methods, 576 result rows, 0 errors, and
  0 skips.
- `and_resource_nmcts`, `and_profile_resource_nmcts`, and
  `and_pareto_resource_nmcts` complete all 64 functions under the
  high-dimensional bounded guard.
- Compared with direct ANF, Pareto-Resource-NMCTS has 61 T-count wins, 0
  losses, and 3 ties, with a 57.94% mean T-count reduction and a 54.55% mean
  score reduction; Resource/Profile have the same win/tie pattern with 57.43%
  and 54.01% reductions.
- Compared with logical-AND direct ANF, Pareto-Resource-NMCTS has 61 score wins,
  0 losses, and 3 ties, with a 31.40% mean score reduction.
- Compared with FPRM-greedy, the high-dimensional guarded variants have
  60 T-count wins, 0 losses, and 4 ties; by weighted score they also have
  60 wins, 0 losses, and 4 ties, with 6.29-6.83% mean score reductions.
  Against the one-layer FPRM linear-pair candidate, Pareto-Resource-NMCTS has
  59 score wins, 0 losses, and 5 ties, with a 3.49% mean score reduction.
  The improvement comes from a bounded recursive FPRM linear-pair candidate
  that factors repeated term pairs as `(x_i xor x_j) * g` using CNOT-only
  linear compute and uncompute around the factored subplan.
- Compared with the standalone FPRM root-beam candidate, the guarded variants
  now have 60 T-count wins, 0 losses, and 4 ties; by weighted score they have
  60 wins, 0 losses, and 4 ties, with 5.76-6.31% mean score reductions.
- The bounded high-dimensional Pareto archive improves over Resource/Profile
  in 16 score cases, loses none, ties 48, and lowers mean score by 0.59%.
- Runtime tails remain visible but bounded: `and_resource_nmcts` completes
  64/64 with median 8.571 s and p95 80.429 s; `and_profile_resource_nmcts`
  completes 64/64 with median 9.294 s and p95 84.226 s;
  `and_pareto_resource_nmcts`
  completes 64/64 with median 67.788 s and p95 300.019 s.  The standalone
  one-layer FPRM linear-pair candidate has median 2.574 s and p95 30.760 s.
  The tradeoff is higher mean peak ancilla: about 3.05-3.06 versus 2.03 for
  FPRM-greedy and root-beam.

Additional scale check from `results/analysis_highdim_scale_resource.md` and
`results/runtime_highdim_scale_resource.md`:

- 32 random ANF functions at `n=15`, 10 methods, 320 result rows, 0 errors, and
  0 skips.
- Compared with FPRM-greedy, the Resource/Profile/Pareto guarded variants have
  30 T-count wins, 0 losses, and 2 ties; by weighted score they also have 30
  wins, 0 losses, and 2 ties, with 5.73-5.75% mean score reductions.
- Compared with the standalone FPRM root-beam candidate, they have 30 weighted
  score wins, 0 losses, and 2 ties, with 5.28-5.31% mean score reductions.
- The one-extra-layer linear-pair refinement recursively searches both the
  quotient and rest branches when the subproblem has at most 900 terms.  Versus
  the one-layer linear-pair candidate, it has 29 weighted-score wins, 0 losses,
  and 3 ties, at mean peak ancilla 3.06 instead of 2.84.
- The width-three linear-parity ablation is dominated by the recursive pair
  candidate under the default weighted score: 0 wins, 29 losses, and 3 ties
  against the recursive pair method.
- The bounded high-dimensional Pareto archive gives a smaller residual gain
  over Resource/Profile: 5 score wins, 0 losses, and 27 ties, with a 0.03% mean
  score reduction.
- Runtime remains finite at `n=15`: `and_resource_nmcts` completes 32/32 with
  median 9.701 s and p95 90.017 s; `and_profile_resource_nmcts` completes
  32/32 with median 11.334 s and p95 93.676 s; `and_pareto_resource_nmcts`
  completes 32/32 with median 117.516 s and p95 300.300 s.

Ultra-high-dimensional scale check from
`results/analysis_ultra_highdim_resource.md` and
`results/runtime_ultra_highdim_resource.md`:

- 24 random ANF functions at `n=16`, 10 methods, 240 result rows, 0 errors, and
  0 skips.
- The ultra guard now uses a baseline-preserving AI guard at `n=16`: it compares
  deterministic recursive FPRM linear-pair factoring with a root-neural
  recursive guard, then keeps the lower-score candidate.  Resource-NMCTS and
  Profile-Resource-NMCTS match that AI guard on all 24 functions; the Pareto
  row is close but not treated as a separate high-dimensional Pareto gain.
- Recursive linear-pair guard improves over the shallow linear-pair guard by
  23/0/1 weighted-score W/L/T with a 2.54% mean score reduction, and over FPRM
  root beam by 23/0/1 with a 4.31% mean score reduction.
- The root-neural recursive guard alone is not stable enough: it scores 6/7/11
  against deterministic recursive guard with a 0.08% mean score increase.  The
  baseline-preserving AI guard converts the useful cases into a safe 6/0/18
  score W/L/T and a 0.05% mean score reduction.
- Compared with direct ANF, Resource-NMCTS has 23 T-count wins, 0 losses, and
  1 tie, with a 63.36% mean T-count reduction and a 60.83% mean score
  reduction.
- Compared with logical-AND direct ANF, it has 23 weighted-score wins, 0
  losses, and 1 tie, with a 33.53% mean score reduction.
- Compared with FPRM root beam, it has 23 weighted-score wins, 0 losses, and 1
  tie, with a 4.36% mean score reduction.
- Runtime remains finite at `n=16`: `and_resource_nmcts` completes 24/24 with
  median 80.633 s and p95 227.312 s; `and_profile_resource_nmcts` completes
  24/24 with median 71.084 s and p95 195.863 s; `and_pareto_resource_nmcts`
  completes 24/24 with median 146.767 s and p95 300.829 s.

`results/analysis_mega_highdim_resource.md` and
`results/runtime_mega_highdim_resource.md`:

- 12 random ANF functions at `n=18`, 7 methods, 84 result rows, 0 errors, and
  0 skips.
- The standalone fast FPRM linear-pair guard has 6 weighted-score wins, 0
  losses, and 6 ties against bounded FPRM root-beam, reducing mean score by
  1.91%.  Resource/Profile/Pareto then improve that fast child on all 12
  functions, reducing mean score by another 3.55%.
- Compared with direct ANF, Resource/Profile/Pareto have 12 T-count wins, 0
  losses, and 0 ties, with a 60.05% mean T-count reduction and a 56.99% mean
  score reduction.
- Compared with bounded FPRM root-beam, Resource/Profile/Pareto have 12
  weighted-score wins, 0 losses, and 0 ties, with a 5.29% mean score reduction.
- At `n=18`, Pareto-Resource-NMCTS is deliberately narrowed to the same stable
  high-dimensional guard as Resource/Profile, so it ties them on all 12
  functions rather than claiming an additional Pareto gain at this scale.
- Runtime remains finite but has a minute-scale tail: `and_resource_nmcts`
  completes 12/12 with median 83.313 s and p95 173.181 s;
  `and_profile_resource_nmcts` completes 12/12 with median 83.339 s and p95
  173.780 s; `and_pareto_resource_nmcts` completes 12/12 with median 83.500 s
  and p95 172.934 s.

`results/analysis_giga_highdim_resource.md`,
`results/analysis_giga_resource_vs_boolean_screen.md`,
`results/analysis_giga_resource_vs_and_direct.md`, and
`results/runtime_giga_highdim_resource.md`:

- 6 random ANF functions at `n=20`, 8 methods, 48 result rows, 12 timeout
  rows, and 0 skipped rows.
- `and_fprm_root_beam` and `and_fprm_linear_pair_fast` timed out on all six
  functions under the 300 s isolated task budget.
- `and_boolean_linear_pair_screen` completed all six functions with median
  runtime 10.659 s, improving over AND-direct ANF on 5/6 functions and tying on
  one.  It reduces mean T-count by 5.24% and mean weighted score by 4.89%
  relative to AND-direct ANF.
- The updated Resource/Pareto portfolio also evaluates a recursive Boolean-ring
  screen.  It completes all six functions and improves over the single screen
  on 5/6 functions, tying on one: mean T-count is 4.62% lower and mean weighted
  score is 4.52% lower than the single Boolean screen.
- A targeted depth-2 recursive Boolean-ring screen rerun in
  `results/analysis_giga_screen_deeper_vs_deep.md` further improves over the
  depth-1 screen on 5/6 functions, tying on one: mean T-count is 3.22% lower
  and mean weighted score is 3.13% lower, with standalone mean runtime 20.152 s.
- With the depth-2 screen in the Resource portfolio, updated Resource-NMCTS has
  5/0/1 score wins/losses/ties versus the previous depth-1 Resource run and
  mean weighted score 3.13% lower.  Relative to old Resource-NMCTS it has
  5/0/1 score wins/losses/ties and mean weighted score 7.47% lower.
- Relative to AND-direct ANF, the depth-2 Resource-NMCTS has 5/0/1 score
  wins/losses/ties, with mean T-count 12.24% lower and mean weighted score
  11.80% lower.  Relative to direct ANF, it has 5/1/0 score wins/losses/ties
  and mean weighted score 38.86% lower.
- The n=20 run is therefore a useful pressure boundary with a stronger bounded
  repair: depth-2 recursive ANF-only Boolean-ring screening verifies
  correctness and separates from AND-direct ANF, but the stronger
  FPRM/root-beam searches remain outside the current 300 s timeout.  The trade
  off is higher runtime and a small peak-ancilla increase.

Scope boundary: all costs are logical-level resource estimates.  The verifier
circuit is deterministic and classically checked, while the logical-AND cost
model accounts for low-T compute and Clifford/measurement-based uncompute.
No hardware mapping or connectivity constraints are included.
