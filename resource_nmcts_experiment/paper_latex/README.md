# Paper LaTeX Draft

Working title:

> Resource-NMCTS: Neural Monte Carlo Tree Search with Affine Boolean Preconditioning for Resource-Constrained Quantum Oracle Synthesis

This folder is the manuscript workspace for the resource-constrained quantum
Boolean oracle synthesis project.  The draft is intentionally evidence-first:
claims in `main.tex` are limited to the current `evidence_affine`,
`ablation_affine`, `traditional_resource`, `resource_sweep`,
`large_resource_core`, `highdim_resource`, `highdim_scale_resource`,
`ultra_highdim_resource`, `mega_highdim_resource`, the exact bounded FPRM-DP
slice, and exported SSHR/ABC/BDD/LUT/ESOP baseline results.

Current English submission draft:

- `resource_nmcts_submission_v1.tex` / `resource_nmcts_submission_v1.pdf`:
  English manuscript rebuilt from the latest Chinese v39 evidence.  It adds
  the CirKit AIG/MC probe, legacy RevKit CLI exact-oracle portfolio, Affine-FPRM
  phase-search results, rank-trained diversity-reranked phase-candidate
  pruning, ROS-style LUT line-sensitivity analysis, and the current
  high-dimensional verification boundary.  The claim is explicitly limited to
  logical-layer synthesis, with CirKit depth and RevKit CLI peak-ancilla
  trade-offs stated in the abstract and discussion.

Build:

```bash
latexmk -pdf main.tex
latexmk -pdf resource_nmcts_submission_v1.tex
```

From the project root, the lightweight derived submission package can be
rebuilt with:

```bash
./rebuild_submission_package.sh
```

This regenerates paper-facing analysis tables, figures, the metadata audit,
goal-completion audit, the archive manifest, uploadable payload archive, audits, and
`resource_nmcts_submission_v1.pdf` from existing experiment artifacts.  It does
not rerun raw benchmark sweeps, external-toolchain probes, or neural training.

Submission-support templates are kept in `../submission_package/`:

- `cover_letter_template.md`
- `author_declarations_template.md`
- `submission_checklist.md`
- `reviewer_concern_brief.md`

Fields marked `AUTHOR INPUT REQUIRED` must be filled by the author before
upload.

Current source evidence:

- contribution-to-evidence map CSV:
  `../results/summary_contribution_evidence_map.csv`
- contribution-to-evidence map analysis:
  `../results/analysis_contribution_evidence_map.md`
- method workflow CSV:
  `../results/summary_method_workflow.csv`
- method workflow analysis:
  `../results/analysis_method_workflow.md`
- related-work positioning matrix CSV:
  `../results/summary_related_work_positioning.csv`
- related-work positioning matrix analysis:
  `../results/analysis_related_work_positioning.md`
- baseline claim matrix CSV:
  `../results/summary_baseline_claim_matrix.csv`
- baseline claim matrix analysis:
  `../results/analysis_baseline_claim_matrix.md`
- comparison evidence matrix CSV:
  `../results/summary_comparison_evidence_matrix.csv`
- comparison evidence matrix analysis:
  `../results/analysis_comparison_evidence_matrix.md`
- baseline comparability audit CSV:
  `../results/summary_baseline_comparability_audit.csv`
- baseline comparability audit analysis:
  `../results/analysis_baseline_comparability_audit.md`
- submission traceability audit CSV:
  `../results/summary_submission_traceability_audit.csv`
- submission traceability audit analysis:
  `../results/analysis_submission_traceability_audit.md`
- submission archive manifest CSV:
  `../results/summary_submission_archive_manifest.csv`
- submission archive manifest analysis:
  `../results/analysis_submission_archive_manifest.md`
- submission archive manifest JSON:
  `../results/manifest_submission_archive_manifest.json`
- submission payload archive:
  `../submission_package/dist/resource_nmcts_submission_payload.tar.gz`
- submission payload archive SHA256:
  `../submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256`
- submission payload archive manifest:
  `../results/manifest_submission_payload_archive.json`
- submission metadata audit CSV:
  `../results/summary_submission_metadata_audit.csv`
- submission metadata audit analysis:
  `../results/analysis_submission_metadata_audit.md`
- submission metadata audit JSON:
  `../results/manifest_submission_metadata_audit.json`
- goal-completion audit CSV:
  `../results/summary_goal_completion_audit.csv`
- goal-completion audit analysis:
  `../results/analysis_goal_completion_audit.md`
- goal-completion audit JSON:
  `../results/manifest_goal_completion_audit.json`
- submission-support templates:
  `../submission_package/*.md`
- submission-readiness audit CSV:
  `../results/summary_submission_readiness_audit.csv`
- submission-readiness audit analysis:
  `../results/analysis_submission_readiness_audit.md`
- experiment CSV: `../results/raw_evidence_affine.csv`
- compact analysis: `../results/analysis_evidence_affine.md`
- ablation CSV: `../results/raw_ablation_affine.csv`
- compact ablation analysis: `../results/analysis_ablation_affine.md`
- runtime/resource analysis: `../results/runtime_ablation_affine.md`
- neural-prior ablation CSV: `../results/raw_neural_prior_ablation.csv`
- neural-prior ablation analysis:
  `../results/analysis_neural_prior_ablation.md`
- high-dimensional root-action teacher diagnostic CSV:
  `../results/raw_highdim_root_action_oracle.csv`
- high-dimensional root-action teacher diagnostic analysis:
  `../results/analysis_highdim_root_action_oracle.md`
- matched learned-prior traditional-resource rerun CSV:
  `../results/raw_traditional_resource_learned_prior.csv`
- matched learned-prior traditional-resource rerun summary:
  `../results/summary_traditional_resource_learned_prior.csv`
- traditional baseline CSV: `../results/raw_traditional_resource.csv`
- traditional baseline analysis: `../results/analysis_traditional_resource.md`
- traditional runtime/resource analysis:
  `../results/runtime_traditional_resource.md`
- external exact SSHR-I pilot CSV:
  `../results/raw_external_traditional_resource_n4.csv`
- external exact SSHR-I pilot analysis:
  `../results/analysis_external_traditional_resource_n4.md`
- exact bounded FPRM-DP CSV:
  `../results/raw_exact_fprm_dp.csv`
- exact bounded FPRM-DP analysis:
  `../results/analysis_exact_fprm_dp.md`
- exact XAG multiplicative-complexity lower-bound CSV:
  `../results/raw_exact_xag_mc.csv`
- exact XAG multiplicative-complexity lower-bound analysis:
  `../results/analysis_exact_xag_mc.md`
- external time-limited SSHR-I plus ABC-AIG/ABC-XAG/ABC-LUT/BDD/ABC-ESOP extension CSV:
  `../results/raw_external_traditional_resource_n6.csv`
- external time-limited SSHR-I plus ABC-AIG/ABC-XAG/ABC-LUT/BDD/ABC-ESOP extension analysis:
  `../results/analysis_external_traditional_resource_n6.md`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD CSV:
  `../results/raw_external_highdim_resource.csv`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD analysis:
  `../results/analysis_external_highdim_resource.md`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD scale CSV:
  `../results/raw_external_highdim_scale_resource.csv`
- external high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD scale analysis:
  `../results/analysis_external_highdim_scale_resource.md`
- external ultra-high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD CSV:
  `../results/raw_external_ultra_highdim_resource.csv`
- external ultra-high-dimensional ABC-AIG/ABC-XAG/ABC-LUT/BDD analysis:
  `../results/analysis_external_ultra_highdim_resource.md`
- resource-sweep CSV: `../results/raw_resource_sweep.csv`
- resource-sweep analysis: `../results/analysis_resource_sweep.md`
- large-scale core CSV: `../results/raw_large_resource_core.csv`
- large-scale core analysis: `../results/analysis_large_resource_core.md`
- large-scale core runtime/resource analysis:
  `../results/runtime_large_resource_core.md`
- high-dimensional stress CSV: `../results/raw_highdim_resource.csv`
- high-dimensional stress analysis: `../results/analysis_highdim_resource.md`
- high-dimensional stress runtime/resource analysis:
  `../results/runtime_highdim_resource.md`
- high-dimensional scaling CSV: `../results/raw_highdim_scale_resource.csv`
- high-dimensional scaling analysis:
  `../results/analysis_highdim_scale_resource.md`
- high-dimensional scaling runtime/resource analysis:
  `../results/runtime_highdim_scale_resource.md`
- ultra-high-dimensional scaling CSV:
  `../results/raw_ultra_highdim_resource.csv`
- ultra-high-dimensional scaling analysis:
  `../results/analysis_ultra_highdim_resource.md`
- ultra-high-dimensional scaling runtime/resource analysis:
  `../results/runtime_ultra_highdim_resource.md`
- mega-scale high-dimensional CSV:
  `../results/raw_mega_highdim_resource.csv`
- mega-scale high-dimensional analysis:
  `../results/analysis_mega_highdim_resource.md`
- mega-scale high-dimensional runtime/resource analysis:
  `../results/runtime_mega_highdim_resource.md`
- extended screen-scale term-set CSV:
  `../results/raw_screen_scale_extended_terms.csv`
- extended screen-scale term-set analysis:
  `../results/analysis_screen_scale_extended_terms.md`
- depth-frontier screen-scale term-set CSV:
  `../results/raw_screen_scale_depth_frontier_terms.csv`
- depth-frontier screen-scale term-set analysis:
  `../results/analysis_screen_scale_depth_frontier_terms.md`
- depth-frontier policy CSV:
  `../results/raw_boolean_screen_depth_frontier_policy.csv`
- depth-frontier policy analysis:
  `../results/analysis_boolean_screen_depth_frontier_policy.md`
- depth-frontier policy screen-scale CSV:
  `../results/raw_screen_scale_depth_frontier_policy_terms.csv`
- depth-frontier policy screen-scale analysis:
  `../results/analysis_screen_scale_depth_frontier_policy_terms.md`
- depth-frontier policy generalization CSV:
  `../results/raw_screen_scale_depth_frontier_policy_generalization_terms.csv`
- depth-frontier policy generalization analysis:
  `../results/analysis_screen_scale_depth_frontier_policy_generalization_terms.md`
- large depth-frontier policy CSV:
  `../results/raw_boolean_screen_depth_frontier_policy_large.csv`
- large depth-frontier policy analysis:
  `../results/analysis_boolean_screen_depth_frontier_policy_large.md`
- large depth-frontier policy generalization CSV:
  `../results/raw_screen_scale_depth_frontier_policy_large_generalization_terms.csv`
- large depth-frontier policy generalization analysis:
  `../results/analysis_screen_scale_depth_frontier_policy_large_generalization_terms.md`
- large frontier n=23 truth-table bridge CSV:
  `../results/raw_truth_bridge_n23_large_frontier_terms.csv`
- large frontier n=23 truth-table bridge analysis:
  `../results/analysis_truth_bridge_n23_large_frontier_terms.md`
- cost-aware depth-frontier policy CSV:
  `../results/raw_boolean_screen_depth_frontier_policy_cost_time003.csv`
- cost-aware depth-frontier policy analysis:
  `../results/analysis_boolean_screen_depth_frontier_policy_cost_time003.md`
- cost-aware depth-frontier policy generalization CSV:
  `../results/raw_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.csv`
- cost-aware depth-frontier policy generalization analysis:
  `../results/analysis_screen_scale_depth_frontier_policy_cost_time003_generalization_terms.md`
- cost-aware frontier n=23 truth-table bridge CSV:
  `../results/raw_truth_bridge_n23_cost_time003_frontier_terms.csv`
- cost-aware frontier n=23 truth-table bridge analysis:
  `../results/analysis_truth_bridge_n23_cost_time003_frontier_terms.md`
- frontier-policy upgrade analysis:
  `../results/analysis_frontier_policy_upgrade.md`
- stage-gated frontier CSV:
  `../results/raw_stage_gated_frontier.csv`
- stage-gated frontier analysis:
  `../results/analysis_stage_gated_frontier.md`
- truth-table bridge CSV:
  `../results/raw_truth_bridge_terms.csv`
- truth-table bridge analysis:
  `../results/analysis_truth_bridge_terms.md`
- schedule-proxy generalization CSV:
  `../results/raw_screen_scale_schedule_depth_frontier_policy_generalization_terms.csv`
- schedule-proxy truth-table bridge CSV:
  `../results/raw_schedule_truth_bridge_terms.csv`
- schedule-proxy n=23 truth-table bridge CSV:
  `../results/raw_schedule_truth_bridge_n23_terms.csv`
- schedule-proxy n=23 truth-table bridge analysis:
  `../results/analysis_schedule_truth_bridge_n23_terms.md`
- schedule-proxy combined analysis:
  `../results/analysis_schedule_metrics.md`
- ROS-style LUT proxy sweep CSV:
  `../results/raw_ros_lut_proxy_sweep.csv`
- ROS-style LUT proxy best-K CSV:
  `../results/raw_ros_lut_proxy_best.csv`
- ROS-style LUT proxy analysis:
  `../results/analysis_ros_lut_proxy.md`
- ROS-style LUT line-sensitivity CSV:
  `../results/raw_ros_lut_line_sensitivity.csv`
- ROS-style LUT line-sensitivity analysis:
  `../results/analysis_ros_lut_line_sensitivity.md`
- mockturtle official-header KLUT-to-XAG probe analysis:
  `../results/analysis_mockturtle_xag_probe.md`
- mockturtle high-dimensional KLUT-to-XAG probe analysis:
  `../results/analysis_mockturtle_xag_highdim_probe.md`
- CirKit AIG/MC probe analysis:
  `../results/analysis_cirkit_aig_probe.md`
- CirKit high-dimensional AIG/MC probe analysis:
  `../results/analysis_cirkit_aig_highdim_probe.md`
- legacy RevKit CLI reversible-synthesis portfolio analysis:
  `../results/analysis_revkit_cli_multiflow_traditional.md`
- rank-diverse learned phase-candidate pruning analysis:
  `../results/analysis_phase_affine_policy_rank_diverse.md`
- same-budget random control for learned phase-candidate pruning:
  `../results/analysis_phase_policy_random_control.md`
- learned-control summary figure source:
  `figures/submission_v36/source_data/fig7_learned_control_summary.csv`
- external-tool benchmark exporter: `../export_benchmarks.py`
- ROS-style LUT proxy runner: `../run_ros_lut_proxy.py`
- ROS-style LUT line-sensitivity analyzer:
  `../analyze_ros_lut_line_sensitivity.py`
- LaTeX tables: `tables/runtime_ablation_affine.tex`,
  `tables/resource_ablation_affine.tex`,
  `tables/neural_prior_ablation.tex`,
  `tables/highdim_root_action_oracle.tex`,
  `tables/resource_traditional_resource.tex`,
  `tables/runtime_traditional_resource.tex`,
  `tables/resource_sweep_affine.tex`,
  `tables/resource_sweep_resource.tex`,
  `tables/resource_sweep_winners.tex`,
  `tables/resource_large_resource_core.tex`,
  `tables/runtime_large_resource_core.tex`,
  `tables/resource_highdim_resource.tex`,
  `tables/runtime_highdim_resource.tex`,
  `tables/resource_highdim_scale_resource.tex`,
  `tables/runtime_highdim_scale_resource.tex`,
  `tables/resource_ultra_highdim_resource.tex`,
  `tables/runtime_ultra_highdim_resource.tex`,
  `tables/resource_mega_highdim_resource.tex`,
  `tables/runtime_mega_highdim_resource.tex`,
  `tables/external_traditional_resource_n6.tex`,
  `tables/exact_fprm_dp.tex`,
  `tables/exact_xag_mc.tex`,
  `tables/external_highdim_abc_aig.tex`,
  `tables/external_ultra_highdim_resource.tex`,
  `tables/external_mega_highdim_resource.tex`,
  `tables/screen_scale_extended_terms.tex`,
  `tables/screen_scale_depth_frontier_terms.tex`,
  `tables/boolean_screen_depth_frontier_policy.tex`,
  `tables/screen_scale_depth_frontier_policy_terms.tex`,
	  `tables/screen_scale_depth_frontier_policy_generalization_terms.tex`,
	  `tables/boolean_screen_depth_frontier_policy_large.tex`,
	  `tables/screen_scale_depth_frontier_policy_large_generalization_terms.tex`,
	  `tables/truth_bridge_terms.tex`,
	  `tables/truth_bridge_n23_large_frontier_terms.tex`,
	  `tables/boolean_screen_depth_frontier_policy_cost_time003.tex`,
	  `tables/screen_scale_depth_frontier_policy_cost_time003_generalization_terms.tex`,
	  `tables/truth_bridge_n23_cost_time003_frontier_terms.tex`,
	  `tables/frontier_policy_upgrade.tex`,
	  `tables/stage_gated_frontier.tex`,
	  `tables/schedule_truth_bridge_n23_terms.tex`,
	  `tables/schedule_metrics.tex`,
	  `tables/ros_lut_proxy.tex`,
	  `tables/ros_lut_line_sensitivity.tex`
- manifests: `../results/manifest_evidence_affine.json`,
  `../results/manifest_traditional_resource_learned_prior.json`,
  `../results/manifest_traditional_resource_no_prior.json`,
  `../results/manifest_highdim_resource.json`,
  `../results/manifest_highdim_scale_resource.json`,
  `../results/manifest_ultra_highdim_resource.json`,
  `../results/manifest_mega_highdim_resource.json`,
  `../results/manifest_external_traditional_resource_n4.json`,
  `../results/manifest_external_traditional_resource_n6.json`,
  `../results/manifest_external_highdim_resource.json`,
  `../results/manifest_external_highdim_scale_resource.json`,
  `../results/manifest_external_ultra_highdim_resource.json`,
  `../results/manifest_external_mega_highdim_resource.json`,
  `../results/manifest_ros_lut_proxy.json`,
  `../results/manifest_ros_lut_line_sensitivity.json`,
  `../results/manifest_revkit_oracle_synth_traditional.json`

Known manuscript gaps:

- add reproduced non-ABC/non-LUT/non-BDD high-dimensional external baselines where
  runtime allows; ABC-ESOP is stable on `n <= 6` but times out on complex
  high-dimensional examples;
- extend the external high-dimensional comparison beyond `n=18` only if the
  exported truth-table and ABC/BDD verification path remains practical;
- keep the RevKit Python API baseline as an adverse external boundary, and
  separately reproduce official ROS, mockturtle, or legacy RevKit/CirKit CLI
  flows when those tools are available;
- decide the target venue and required reference/section style.
