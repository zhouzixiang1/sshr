# Submission Checklist

Use this checklist immediately before uploading the manuscript.

## Required Author Input

- AUTHOR INPUT REQUIRED: Work through `submission_package/AUTHOR_INPUT_REQUIRED.md` before uploading.
- If working in Chinese, follow `submission_package/FINAL_SUBMISSION_HANDOFF_zh.md` for the final execution order.
- AUTHOR INPUT REQUIRED: Choose the target venue using `submission_package/target_venue_brief.md` as a planning aid, then copy the final choice into `submission_package/submission_metadata.json`.
- AUTHOR INPUT REQUIRED: Run `/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py --write-private`, or copy `submission_package/submission_metadata_template.json` manually, then fill every `AUTHOR INPUT REQUIRED` value in `submission_package/submission_metadata.json`.
- AUTHOR INPUT REQUIRED: Confirm author order, affiliations, ORCID IDs, and corresponding author details.
- AUTHOR INPUT REQUIRED: Complete funding, acknowledgements, author contributions, and competing-interest statements.
- AUTHOR INPUT REQUIRED: Replace repository-relative availability wording with the target venue's required archive DOI, repository URL, or anonymous review link.
- AUTHOR INPUT REQUIRED: Confirm whether the venue requires an AI-assistance disclosure.
- AUTHOR INPUT REQUIRED: Confirm target journal formatting, reference style, manuscript type, word limit, and supplementary-material policy.

## Manuscript Files

- Submission package guide: `submission_package/README.md`
- Main source: `paper_latex/resource_nmcts_submission_v1.tex`
- Main PDF: `paper_latex/resource_nmcts_submission_v1.pdf`
- Optional anonymous review source:
  `paper_latex/resource_nmcts_submission_anonymous.tex`
- Optional anonymous review PDF:
  `paper_latex/resource_nmcts_submission_anonymous.pdf`
- Bibliography: `paper_latex/references.bib`
- Generated tables: `paper_latex/tables/*.tex`
- Generated figures: `paper_latex/figures/submission_v36/`
- Figure source data: `paper_latex/figures/submission_v36/source_data/*.csv`
- Uploadable payload archive: `submission_package/dist/resource_nmcts_submission_payload.tar.gz`
- Payload archive checksum: `submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256`

## Reproducibility Files

- Rebuild script: `rebuild_submission_package.sh`
- Fast verifier script: `verify_submission_package.sh`
- Readiness audit: `results/analysis_submission_readiness_audit.md`
- Author input packet: `submission_package/AUTHOR_INPUT_REQUIRED.md`
- Chinese final handoff: `submission_package/FINAL_SUBMISSION_HANDOFF_zh.md`
- Terminal package verifier: `results/analysis_submission_package_verifier.md`
- Claim-scope lint: `results/analysis_claim_scope_lint.md`
- Comparison protocol audit: `results/analysis_comparison_protocol_audit.md`
- Comparison target validity audit: `results/analysis_comparison_target_validity_audit.md`
- Novelty/comparison scorecard: `results/analysis_novelty_comparison_scorecard.md`
- ROS reproduction gap audit: `results/analysis_ros_reproduction_gap_audit.md`
- Search-control baseline audit: `results/analysis_search_control_baseline_audit.md`
- Frontier random-depth control: `results/analysis_frontier_random_depth_control.md`
- Editorial screening audit: `results/analysis_editorial_screening_audit.md`
- Target-venue decision audit: `results/analysis_target_venue_decision_audit.md`
- Submission support packet audit: `results/analysis_submission_support_packet_audit.md`
- Citation support audit: `results/analysis_citation_support_audit.md`
- Headline numeric consistency audit: `results/analysis_headline_numeric_consistency.md`
- Figure asset audit: `results/analysis_figure_asset_audit.md`
- LaTeX dependency audit: `results/analysis_latex_dependency_audit.md`
- PDF visual render audit: `results/analysis_pdf_visual_audit.md`
- PDF text/searchability audit: `results/analysis_pdf_text_audit.md`
- PDF metadata/privacy audit: `results/analysis_pdf_metadata_audit.md`
- Source/path privacy audit: `results/analysis_source_path_privacy_audit.md`
- Metadata audit: `results/analysis_submission_metadata_audit.md`
- Metadata validator: `results/analysis_submission_metadata_validator.md`
- Author-input closure audit: `results/analysis_author_input_closure_audit.md`
- Metadata closure-path audit: `results/analysis_submission_metadata_closure_path.md`
- Metadata pipeline self-test: `results/analysis_submission_metadata_pipeline_selftest.md`
- Anonymous-review readiness audit: `results/analysis_anonymous_review_readiness.md`
- Private submission text preview audit: `results/analysis_submission_text_preview.md`
- Goal-completion audit: `results/analysis_goal_completion_audit.md`
- Raw rerun registry: `results/analysis_artifact_rerun_registry.md`
- Artifact reproduction guide: `submission_package/artifact_reproduction_guide.md`
- Editor screening brief: `submission_package/editor_screening_brief.md`
- Target venue brief: `submission_package/target_venue_brief.md`
- Structured metadata template: `submission_package/submission_metadata_template.json`
- Traceability audit: `results/analysis_submission_traceability_audit.md`
- Archive manifest: `results/analysis_submission_archive_manifest.md`
- Payload archive manifest: `results/analysis_submission_payload_archive.md`
- Payload round-trip audit: `results/analysis_payload_roundtrip_audit.md`
- Payload extraction smoke audit: `results/analysis_payload_extraction_smoke_audit.md`
- Payload verifier smoke audit: `results/analysis_payload_verifier_smoke_audit.md`
- Payload LaTeX compile audit: `results/analysis_payload_latex_compile_audit.md`
- Reproducibility audit: `results/analysis_reproducibility_audit.md`
- Raw data: `results/raw_*.csv`
- Summary data: `results/summary_*.csv`
- Run manifests: `results/manifest_*.json`
- Trained local policy artifacts: `models/`
- External adapter source: `tools/`

## Verification Commands

Run these from `resource_nmcts_experiment/`:

```bash
/opt/anaconda3/envs/mcts-qoracle/bin/python -m py_compile \
  analyze_goal_completion_audit.py \
  analyze_submission_archive_manifest.py \
  analyze_claim_scope_lint.py \
  analyze_comparison_protocol_audit.py \
  analyze_comparison_target_validity_audit.py \
  analyze_novelty_comparison_scorecard.py \
  analyze_ros_reproduction_gap_audit.py \
  analyze_frontier_random_depth_control.py \
  analyze_search_control_baseline_audit.py \
  analyze_ultra_scale64_stress.py \
  analyze_ultra_scale64_resource_profile.py \
  analyze_editorial_screening_audit.py \
  analyze_target_venue_decision_audit.py \
  analyze_submission_support_packet_audit.py \
  analyze_citation_support_audit.py \
  analyze_headline_numeric_consistency.py \
  analyze_figure_asset_audit.py \
  analyze_latex_dependency_audit.py \
  analyze_pdf_visual_audit.py \
  analyze_pdf_text_audit.py \
  analyze_pdf_metadata_audit.py \
  analyze_source_path_privacy_audit.py \
  analyze_submission_metadata_audit.py \
  analyze_author_input_closure_audit.py \
  analyze_anonymous_review_readiness.py \
  analyze_submission_readiness_audit.py \
  analyze_submission_traceability_audit.py \
  validate_submission_metadata.py \
  make_submission_metadata_starter.py \
  selftest_submission_metadata_pipeline.py \
  analyze_payload_roundtrip_audit.py \
  analyze_payload_extraction_smoke_audit.py \
  analyze_payload_verifier_smoke_audit.py \
  analyze_payload_latex_compile_audit.py \
  make_anonymous_review_draft.py \
  make_submission_text_preview.py
./rebuild_submission_package.sh
./verify_submission_package.sh
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_starter.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_submission_package_verifier.py
rg -n "Overfull|Underfull|undefined|Undefined|Warning|Error|LaTeX Warning|Rerun" \
  paper_latex/resource_nmcts_submission_v1.log
```

Expected current state:

- Machine snapshot tokens checked by `analyze_public_handoff_freshness_audit.py`:
  PDF pages=36/35; readiness=57 pass + 1 needs author input;
  payload_files=979; artifact_registry=24 families / 146 raw CSV / 60036 raw rows;
  source_privacy=0 strict leaks / 53 provenance files / 937 payload text files;
  comparison_validity=7/7 pass; novelty_scorecard=6/6 pass;
  goal_gate=author/venue metadata remains open.
- Archive manifest: all payload groups complete.
- Payload archive: tarball, SHA256 sidecar, CSV, Markdown, and JSON manifest are present.
- Payload round-trip audit: archive contents match manifest paths and hashes, required files, reviewer entrypoints, comparison-protocol evidence files, comparison-target validity files, novelty/comparison scorecard files, ROS reproduction-boundary evidence files, editorial-screening evidence files, support-packet evidence files, citation-support evidence files, author-input closure evidence files, source/path privacy audit code, and headline-numeric evidence files are present, private files are absent, and tar metadata is deterministic.
- Payload extraction smoke audit: the upload tarball extracts safely and runs comparison protocol, comparison-target validity, novelty/comparison scorecard, ROS reproduction gap, editorial screening, support-packet, citation support, source/path privacy, author-input closure, headline numeric consistency, claim-scope lint, and artifact-rerun registry checks from the extracted tree.
- Payload verifier smoke audit: the upload tarball extracts safely and `verify_submission_package.sh` passes from inside the extracted payload tree.
- Payload LaTeX compile audit: the upload tarball extracts safely and rebuilds both author and anonymous PDFs from the extracted LaTeX source tree.
- Claim-scope lint: all required boundaries pass and no unguarded overclaim remains.
- Comparison protocol audit: all baseline layers have role, evidence, comparability, counterpoint, artifact, and manuscript-anchor coverage.
- Comparison target validity audit: comparison families are explicitly labeled as primary benchmark, external stress test, exact reversible counterpoint, phase proxy, causal control, scalability verification, or non-dominance boundary.
- Novelty/comparison scorecard: reviewer-facing method identity, baseline meaning, external probe, tradeoff, AI/MCTS, and scale-boundary questions all pass with manuscript and support-brief anchors.
- ROS reproduction gap audit: ROS-style LUT and line-sensitivity are proxy evidence; the official ROS SAT garbage-management component is not reproduced and must not be claimed.
- Search-control baseline audit: heuristic, beam, no-MCTS, MCTS, Pareto, learned-prior, bit-flip random-prior, frontier random-depth, and phase random-control rows all pass.
- Ultra-scale n=48/56/64 stress and resource-profile audits: 480/480 plan ANF rows and 480/480 emitted-circuit ANF rows pass with zero mismatches; the profile exposes score/T/CNOT/depth/ancilla/T-depth/lifetime/time tradeoffs, and this remains symbolic scaling evidence rather than full truth-table enumeration.
- Frontier random-depth control: same-candidate depth-2/3/4 random controls pass on held-out, scale, and truth-table bridge slices; the result is a quality/budget-allocation claim, not a runtime claim.
- Editorial screening audit: scope, novelty, comparison route, negative-result visibility, AI-boundary, large-scale boundary, reproducibility path, and author/venue gate all pass.
- Target-venue decision audit: source-backed venue fit, recommended order, metadata gate, anonymous-review policy gate, and AI-disclosure policy gate all pass while the final target venue remains author input.
- Submission support packet audit: cover letter, declarations, target-venue brief, checklist, handoff, private-preview gate, anonymous-review fork, and editor/reviewer triage all pass.
- Citation support audit: related-work families, cited BibTeX keys, bibliography entries, and DOI/URL/eprint locators are all closed.
- Headline numeric consistency audit: all abstract-level numbers match generated CSV evidence and both author/anonymous TeX sources.
- Figure asset audit: every manuscript figure has generated PDF/PNG/SVG assets and non-empty source-data CSV.
- LaTeX dependency audit: every author/anonymous TeX input, figure reference, and bibliography file exists locally and is included in the upload payload.
- PDF visual render audit: every author/anonymous PDF page renders through Poppler with stable dimensions and nonblank visible content.
- PDF text/searchability audit: every author/anonymous PDF extracts searchable text through Poppler with title, scope, baseline, availability, reference, headline-number, identity, and public-placeholder anchors checked.
- PDF metadata/privacy audit: every author/anonymous PDF passes `pdfinfo` metadata and flag checks for page geometry, encryption, JavaScript, forms, and privacy-sensitive metadata strings.
- Source/path privacy audit: manuscript TeX, table inputs, and public submission support files contain no local absolute paths; local toolchain paths in raw/result artifacts are classified as provenance rather than manuscript/support leakage.
- Metadata audit: all author- and venue-specific fields are enumerated before upload, and any filled `submission_metadata.json` is checked.
- Metadata validator: no `needs revision` rows; missing private metadata remains an author-input gate until filled.
- Author-input closure audit: metadata-template placeholders, author-input packet fields, support docs, private Git protection, private-preview gates, and anonymous-review decision gates are mutually consistent.
- Metadata closure-path audit: final author/venue metadata intake is explicit, private, ignored by Git, rehearsed with synthetic metadata, and tied to the goal-closure gate.
- Metadata pipeline self-test: synthetic non-private metadata exercises validator and preview renderers with no `needs revision` rows.
- Anonymous-review readiness: no `needs revision` rows; an anonymous review draft is compiled, and final anonymous artifact links remain explicit author-input actions if double-blind review is required.
- Private submission text preview: public audit exists; generated private Markdown previews remain ignored by Git and excluded from the payload archive.
- Goal-completion audit: all research/package requirements pass and only author/venue gates remain open.
- Traceability audit: all claim families complete.
- Readiness audit: all paper/package checks pass except author-specific declarations.
- Terminal package verifier: all read-only package invariants pass.
- LaTeX warning status: only the existing `\showhyphens` package warning should remain.

## Claim Boundary Check

- Do not claim hardware mapping, routing, native-gate scheduling, or noise-aware compilation.
- Do not claim universal dominance over SSHR, CirKit, RevKit, or all CNOT/depth/ancilla metrics.
- Keep ROS-style LUT results framed as proxy evidence; `analysis_ros_reproduction_gap_audit.md` must show zero `needs revision` rows before upload.
- Keep RevKit `oracle_synth` framed as a phase/Rz lower-bound or sensitivity probe, not a final Clifford+T comparison.
- Keep learned-control claims bounded: neural controls contribute measurable guarded or pruning gains, but the largest gains come from the algebraic action space and guarded portfolio search.

## Upload Order

1. Upload the main PDF and source archive required by the venue.
2. Upload `submission_package/dist/resource_nmcts_submission_payload.tar.gz` or a venue-specific source archive assembled from it.
3. Upload generated figure files and source data separately if the venue requires them outside the payload archive.
4. Paste author declarations into the submission system.
5. Paste generated private preview text from `submission_package/generated_*.md` after reviewing venue wording, or paste the manually edited declarations if the venue requires a different format.
6. Paste the cover letter and reviewer suggestions if requested.
7. Review the generated proof for table placement and figure readability before final approval.
