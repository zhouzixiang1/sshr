# Artifact Reproduction Guide

This guide is for reviewers or artifact evaluators who want to verify the
paper-facing results in the submission package.

The artifact supports two levels of checking:

1. A lightweight rebuild that regenerates manuscript-facing analyses, figures,
   audits, the PDF, and the upload payload from existing experiment artifacts.
2. Heavier raw reruns for benchmark sweeps, external toolchain probes, and
   neural training.  These are intentionally not launched by the lightweight
   rebuild because they depend on optional external tools and can take much
   longer.

## Environment

Use the conda environment prepared for the project:

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python --version
```

The expected local audit context records:

- Python 3.11
- PyTorch with Apple MPS available
- Apple M4 Pro CPU/GPU workstation
- worker counts up to 10 in recorded manifests
- mockturtle, CirKit, and RevKit provenance for external probes when present

The logical resource results do not depend on hardware mapping, routing,
native-gate scheduling, or physical noise simulation.

## Quick Rebuild Check

From `resource_nmcts_experiment/`, run:

```bash
./rebuild_submission_package.sh
./verify_submission_package.sh
```

This command regenerates:

- contribution, method, related-work, baseline, comparison, statistical,
  multi-resource, learned-control, scaling, robustness, and reproducibility
  analyses;
- paper tables under `paper_latex/tables/`;
- figures and figure source data under `paper_latex/figures/submission_v36/`;
- the English submission PDF and optional anonymous-review PDF;
- archive and traceability audits;
- the uploadable payload tarball and SHA256 sidecar;
- the final readiness audit.

It intentionally does not rerun raw benchmark sweeps, external probes, or
neural model training.

## Expected Current Outputs

After the quick rebuild, the current package should report:

- compiled PDF: `paper_latex/resource_nmcts_submission_v1.pdf`
- anonymous review PDF: `paper_latex/resource_nmcts_submission_anonymous.pdf`
- payload archive: `submission_package/dist/resource_nmcts_submission_payload.tar.gz`
- readiness state in `results/analysis_submission_readiness_audit.md`
- comparison protocol state in
  `results/analysis_comparison_protocol_audit.md`
- citation support state in
  `results/analysis_citation_support_audit.md`
- author-input closure state in
  `results/analysis_author_input_closure_audit.md`
- headline numeric consistency in
  `results/analysis_headline_numeric_consistency.md`
- figure asset state in `results/analysis_figure_asset_audit.md`
- LaTeX dependency state in `results/analysis_latex_dependency_audit.md`
- PDF visual render state in `results/analysis_pdf_visual_audit.md`
- payload file count and SHA256 in
  `results/analysis_submission_payload_archive.md`
- payload extraction smoke status in
  `results/analysis_payload_extraction_smoke_audit.md`
- extracted-payload LaTeX compile status in
  `results/analysis_payload_latex_compile_audit.md`
- submission support-file count in
  `results/analysis_submission_archive_manifest.md`
- raw rerun registry in `results/analysis_artifact_rerun_registry.md`

The remaining readiness item is author-specific metadata and cannot be
reconstructed from the artifact.

## Verification Commands

Run these from `resource_nmcts_experiment/`:

```bash
git diff --check
./verify_submission_package.sh
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_submission_package_verifier.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_payload_extraction_smoke_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_payload_latex_compile_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_citation_support_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_author_input_closure_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_headline_numeric_consistency.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_latex_dependency_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_pdf_visual_audit.py
pdfinfo paper_latex/resource_nmcts_submission_v1.pdf | sed -n '1,20p'
rg -n "Warning|Overfull|Underfull|LaTeX Error|Undefined|Rerun" \
  paper_latex/resource_nmcts_submission_v1.log
rg -n "needs author input|pass:|file count|archive sha256|Submission support" \
  results/analysis_submission_readiness_audit.md \
  results/analysis_submission_payload_archive.md \
  results/analysis_submission_archive_manifest.md
```

The current LaTeX log has the existing `\showhyphens` package warning.  It
should not contain LaTeX errors, undefined references, or overfull/underfull
layout warnings.

## Main Evidence Files

- Baseline role and claim boundaries:
  `results/analysis_baseline_claim_matrix.md`
- Verified comparison coverage:
  `results/analysis_comparison_evidence_matrix.md`
- Baseline comparability:
  `results/analysis_baseline_comparability_audit.md`
- Comparison protocol audit:
  `results/analysis_comparison_protocol_audit.md`
- Citation support audit:
  `results/analysis_citation_support_audit.md`
- Author-input closure audit:
  `results/analysis_author_input_closure_audit.md`
- Headline numeric consistency audit:
  `results/analysis_headline_numeric_consistency.md`
- Figure asset audit:
  `results/analysis_figure_asset_audit.md`
- LaTeX dependency audit:
  `results/analysis_latex_dependency_audit.md`
- PDF visual render audit:
  `results/analysis_pdf_visual_audit.md`
- Paired statistics:
  `results/analysis_paired_statistical_evidence.md`
- Raw multi-resource tradeoff:
  `results/analysis_multimetric_pareto_tradeoff.md`
- Learned-control contribution:
  `results/analysis_learned_control_audit.md`
- Scaling and bridge verification:
  `results/analysis_scaling_resource_audit.md`
- Compute and artifact audit:
  `results/analysis_reproducibility_audit.md`
- Raw rerun registry:
  `results/analysis_artifact_rerun_registry.md`
- Submission traceability:
  `results/analysis_submission_traceability_audit.md`
- Payload manifest:
  `results/analysis_submission_payload_archive.md`
- Payload LaTeX compile audit:
  `results/analysis_payload_latex_compile_audit.md`
- Terminal package verifier:
  `results/analysis_submission_package_verifier.md`

## Raw Rerun Entry Points

These scripts are included for deeper reruns or selective checks.  They are not
part of the quick rebuild.

The generated registry `results/analysis_artifact_rerun_registry.md` gives a
family-by-family map from evidence claims to driver scripts, raw CSV coverage,
manifest coverage, rerun tier, and dependency boundary.

- Core traditional resource experiments: `run_experiments.py`
- External baseline aggregation: `run_external_baselines.py`
- ROS-style LUT proxy: `run_ros_lut_proxy.py`
- mockturtle KLUT-to-XAG probe: `run_mockturtle_xag_probe.py`
- CirKit AIG/MC probe: `run_cirkit_aig_probe.py`
- RevKit CLI probe: `run_revkit_cli_probe.py`
- Phase/Rz searches: `run_phase_parity_baseline.py`,
  `run_phase_parity_affine_search.py`, `run_phase_parity_fprm_search.py`
- High-dimensional screen-scale term runs: `run_screen_scale_terms.py`
- Complete truth-table bridge runs: `run_truth_bridge_terms.py`
- Neural policy training: `train_neural_policy.py`,
  `train_phase_affine_policy.py`, `train_screen_depth_policy.py`,
  `train_screen_depth_frontier_policy.py`, `train_sparse_depth4_gate.py`

External-tool reruns require the corresponding toolchain executables and
versions recorded in the reproducibility audit.  If a toolchain is unavailable,
reviewers can still verify the already recorded raw CSVs, generated summaries,
manuscript tables, and archive manifests.

## Interpreting The Artifact

The artifact should be evaluated under the manuscript's stated scope:

- same-task logical Boolean oracle synthesis for primary small-function rows;
- logic-network or exact-oracle probes for external toolchain rows;
- symbolic and bridge-truth-table verification for high-dimensional rows;
- T-count and weighted-score improvements reported separately from CNOT,
  depth, peak ancilla, and line-count tradeoffs.

Do not interpret the artifact as evidence for hardware-mapped quantum-circuit
performance, physical-device execution, or universal raw-resource dominance.
