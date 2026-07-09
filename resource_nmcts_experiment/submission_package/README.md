# Submission Package README

This directory contains the human-facing upload and handoff files for the
manuscript "Resource-Constrained Neural Monte Carlo Tree Search for Quantum
Boolean Oracle Synthesis".

The package is prepared for a logical-layer quantum Boolean oracle synthesis
paper.  It does not include hardware mapping, routing, native-gate scheduling,
noise modeling, or magic-state-factory accounting.

## Primary Upload Artifacts

- Main manuscript source: `../paper_latex/resource_nmcts_submission_v1.tex`
- Main manuscript PDF: `../paper_latex/resource_nmcts_submission_v1.pdf`
- Optional anonymous review source:
  `../paper_latex/resource_nmcts_submission_anonymous.tex`
- Optional anonymous review PDF:
  `../paper_latex/resource_nmcts_submission_anonymous.pdf`
- Optional ACM/TQC anonymous review-format source:
  `../paper_latex/resource_nmcts_submission_acm_tqc.tex`
- Optional ACM/TQC anonymous review-format PDF:
  `../paper_latex/resource_nmcts_submission_acm_tqc.pdf`
- Bibliography: `../paper_latex/references.bib`
- Generated tables: `../paper_latex/tables/*.tex`
- Generated figures and source data:
  `../paper_latex/figures/submission_v36/`
- Uploadable source/data payload:
  `dist/resource_nmcts_submission_payload.tar.gz`
- Payload checksum:
  `dist/resource_nmcts_submission_payload.tar.gz.sha256`

## Support Documents

- `AUTHOR_INPUT_REQUIRED.md`: consolidated author and target-venue fields that
  must be supplied before final upload.
- `AUTHOR_METADATA_QUESTIONNAIRE_zh.md`: Chinese field-by-field questionnaire
  that maps the remaining human answers to `submission_metadata.json` paths
  without storing private values in a tracked file.
- `AUTHOR_MINIMAL_RESPONSE_FORM_zh.md`: shortest Chinese response form for
  collecting the final author/venue answers in one pass before filling the
  ignored private metadata JSON.
- `LAST_MILE_ACTION_CARD_zh.md`: one-page Chinese action card for the final
  upload pass after the machine-generated research package is complete.
- `TARGET_VENUE_POLICY_CHECKLIST_zh.md`: Chinese upload-policy checklist that
  maps ACM TQC, Quantum, and archive/license gates to private metadata fields.
- `FINAL_SUBMISSION_HANDOFF_zh.md`: Chinese final-upload handoff that turns the
  remaining author/venue gates into an execution order.
- `COMPARISON_HANDOFF_zh.md`: Chinese comparison-positioning handoff that
  explains what the method is compared against, why those comparisons are
  meaningful, and which claims must remain excluded before upload.
- `COMPARISON_SIGNIFICANCE_MATRIX_zh.md`: Chinese comparison matrix that maps
  each baseline family to its role, supported conclusion, invalid conclusion,
  and main evidence entry points.
- `cover_letter_template.md`: editor-facing cover-letter draft with author
  fields left blank.
- `artifact_reproduction_guide.md`: reviewer-facing quick rebuild path,
  expected outputs, raw rerun entry points, and artifact interpretation
  boundary.
- `editor_screening_brief.md`: one-page scope, comparison, and claim-boundary
  brief for editor or associate-editor screening.
- `reviewer_concern_brief.md`: anticipated reviewer concerns and manuscript
  anchors.
- `target_venue_brief.md`: venue-fit shortlist and pre-upload action list.
- `author_declarations_template.md`: author, funding, acknowledgement,
  competing-interest, data, code, AI-disclosure, and prior-submission intake.
- `submission_metadata_answers_template.json`: short machine-readable answer
  template for producing ignored private metadata from author/venue answers.
- `submission_metadata_template.json`: structured version of the author and
  venue fields that must be filled before upload.
- `../results/analysis_submission_metadata_validator.md`: public, redacted
  format/consistency validation for the private metadata file.
- `../results/analysis_author_input_closure_audit.md`: audit that checks
  metadata-template placeholder coverage, author-input packet coverage,
  support-document visibility, private metadata Git protection, private-preview
  gates, anonymous-review decision state, and metadata/packet count
  consistency.
- `../results/analysis_author_minimal_form_coverage.md`: audit that checks the
  shortest Chinese author response form covers every required author/venue
  metadata path before private answers are filled.
- `../results/analysis_submission_metadata_closure_path.md`: audit that checks
  the final author/venue metadata closure path, including safe starter prefill,
  private-file Git protection, validator/preview gates, synthetic rehearsal,
  anonymous-review gate, and handoff document coverage.
- `../results/analysis_final_upload_sequence_audit.md`: terminal audit that
  checks the final author-facing upload order from venue selection through
  private metadata intake, rebuild/verification, private previews,
  availability-link replacement, comparison-claim boundaries, and the
  human-only goal gate.
- `../results/analysis_upload_bundle_matrix_audit.md`: terminal audit that
  maps the author, anonymous, ACM/TQC, source/data payload, support-template,
  private-local, and venue-decision bundles to checked files and upload
  boundaries.
- `../results/analysis_editorial_screening_audit.md`: audit that checks the
  editor-facing path for scope, novelty, comparison fairness, counterpoints,
  AI-claim boundaries, large-scale verification boundaries, reproducibility,
  and remaining author/venue gates.
- `../results/analysis_submission_support_packet_audit.md`: audit that checks
  the public cover-letter, declaration, venue, checklist, handoff, and
  editor/reviewer support packet before private author metadata is filled.
- `../results/analysis_ros_reproduction_gap_audit.md`: audit that separates
  verified ROS-style LUT proxy evidence from full official ROS reproduction
  and SAT garbage-management claims.
- `../results/analysis_caterpillar_ros_family_probe.md`: local source/API/build
  and toy compile smoke audit for the Caterpillar implementation family; this
  is not a standalone ROS performance baseline.
- `../results/analysis_caterpillar_xag_api_probe.md`: bounded Caterpillar
  `logic_network_synthesis` API performance probe over the same traditional
  `n<=6` functions; it verifies 531/531 ANF-XAG strategy rows and 177/177
  best-of-Caterpillar rows, but is still not the full ROS LUT/SAT flow.
- `../results/analysis_submission_metadata_pipeline_selftest.md`: synthetic,
  non-private self-test for the metadata validator and private-preview
  renderers.
- `../results/analysis_anonymous_review_readiness.md`: public audit that
  separates the author-labeled manuscript from double-blind review actions.
- `../results/analysis_submission_text_preview.md`: public audit for the
  private generated submission-system text previews.
- `../results/analysis_target_venue_policy_checklist.md`: public policy-source
  checklist that maps ACM TQC, Quantum, and archive/license gates to private
  metadata fields before upload.
- `../results/analysis_payload_roundtrip_audit.md`: terminal check that opens
  the upload tarball and verifies internal paths, hashes, required artifacts,
  reviewer entrypoints, comparison-protocol, editorial-screening,
  support-packet, citation-support, and headline-numeric evidence files, and
  deterministic tar metadata.
- `../results/analysis_payload_extraction_smoke_audit.md`: terminal check that
  extracts the upload tarball into a temporary directory and runs lightweight
  reviewer-facing audits from inside the extracted payload.
- `../results/analysis_payload_verifier_smoke_audit.md`: terminal check that
  extracts the upload tarball and runs `verify_submission_package.sh` from
  inside the extracted payload tree.
- `../results/analysis_payload_latex_compile_audit.md`: terminal check that
  extracts the upload tarball and rebuilds the author, anonymous, and ACM/TQC
  PDFs from the extracted LaTeX source tree.
- `submission_checklist.md`: final upload checklist and verification commands.
- `../results/analysis_claim_scope_lint.md`: automated claim-boundary lint for
  the manuscript and handoff files.
- `../results/analysis_comparison_protocol_audit.md`: machine-readable audit
  that checks each baseline layer has a role, evidence, comparability boundary,
  counterpoint coverage where relevant, and manuscript anchors.
- `../results/analysis_comparison_route_decision_audit.md`: comparison-route
  decision audit that maps each reviewer-facing claim to the comparator family
  that can answer it and the stronger conclusion that remains excluded.
- `../results/analysis_benchmark_suite_audit.md`: benchmark-suite composition
  audit that records suite roles, n scopes, item counts, verified rows,
  verification routes, and representativeness boundaries.
- `../results/analysis_comparison_answer_scorecard.md`: quantitative answer to
  "compared with what?", aligned with `COMPARISON_SIGNIFICANCE_MATRIX_zh.md`.
- `../results/analysis_sshr_reproduction_scope_audit.md`: audit that separates
  source-anchored SSHR paper references, same-function SSHR-H rows, timed
  SSHR-I rows, exact n<=4 pilot checks, and excluded full-paper SSHR reruns.
- `../results/analysis_citation_support_audit.md`: audit that checks
  related-work families, cited BibTeX keys, bibliography resolution, and
  DOI/URL/eprint locator coverage.
- `../results/analysis_headline_numeric_consistency.md`: audit that
  recomputes abstract-level numerical claims from CSV evidence and checks the
  author and anonymous TeX sources contain the matching headline tokens.
- `../results/analysis_figure_asset_audit.md`: figure-asset audit that checks
  manuscript figure references, PDF/PNG/SVG outputs, and source-data CSVs.
- `../results/analysis_latex_dependency_audit.md`: terminal audit that checks
  author, anonymous, and ACM/TQC TeX inputs, figure references, and bibliography
  files exist locally and are included in the upload payload.
- `../results/analysis_pdf_visual_audit.md`: terminal audit that renders every
  page of the author and anonymous PDFs with Poppler and checks for readable,
  nonblank page images.
- `../results/analysis_pdf_text_audit.md`: terminal audit that extracts
  searchable text from the author and anonymous PDFs with Poppler and checks
  title, scope, baseline, availability, reference, headline-number, identity,
  and public-placeholder anchors.
- `../results/analysis_pdf_metadata_audit.md`: terminal audit that checks
  PDF metadata and flags with Poppler `pdfinfo`, including privacy-sensitive
  fields, encryption, JavaScript, forms, and page geometry.
- `../results/analysis_source_path_privacy_audit.md`: terminal audit that
  separates strict manuscript/support source path gates from allowed
  toolchain-provenance local paths in result artifacts.

## Required Author Actions Before Upload

Do not infer these fields from the experiment artifacts.  They must be supplied
by the author or selected target venue.

- Choose the target venue and manuscript type.
- Read `LAST_MILE_ACTION_CARD_zh.md` first if you want the shortest final
  execution path from current machine-ready state to real venue upload.
- Use `FINAL_SUBMISSION_HANDOFF_zh.md` as the final Chinese execution checklist
  if working through the upload process in Chinese.
- Run `/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_metadata_from_answers.py --init-private-answers`
  to create an ignored private `submission_metadata_answers.json`, fill the
  short answer file, then run `/opt/anaconda3/envs/mcts-qoracle/bin/python
  make_submission_metadata_from_answers.py --write-private` to produce the
  ignored private `submission_metadata.json` with current repository fields
  prefilled.  Use `AUTHOR_METADATA_QUESTIONNAIRE_zh.md` as the Chinese
  field-by-field guide, or copy `submission_metadata_template.json` manually if
  you prefer the full blank metadata file.
- Confirm author order, affiliations, ORCID IDs, and corresponding-author
  details.
- Complete funding, acknowledgements, author contributions, competing
  interests, AI-assistance disclosure, and prior-submission statements.
- Replace repository-relative availability text with a permanent archive DOI,
  repository URL, or anonymous review link if the venue requires it.
- Confirm venue template, reference style, word limit, supplementary-material
  policy, data/code policy, and anonymous-review policy.
- If the venue requires double-blind review, produce a venue-specific anonymous
  manuscript copy and anonymous artifact links; the rebuild generates an
  anonymous review draft, while the current source remains author-labeled.

`submission_metadata_answers.json` and `submission_metadata.json` are
intentionally ignored by Git so private author metadata is not committed
accidentally.
After it is complete, `./rebuild_submission_package.sh` generates ignored
generated private previews:

- `generated_author_declarations.md`
- `generated_availability_statements.md`
- `generated_cover_letter.md`
- `generated_submission_text.md`

These generated files are for local copy/paste into a target venue submission
system and are excluded from the public payload archive.
The same rebuild also runs `validate_submission_metadata.py`, which checks
field formats such as email addresses, ORCID-like identifiers, URL/DOI links,
target-venue policy flags, and code commit hash consistency without writing
private values to tracked outputs.
It also runs `selftest_submission_metadata_pipeline.py` with synthetic
non-private metadata so validator and preview-renderer regressions are caught
before any real author metadata is supplied.

## Claim Boundary Check

Keep the paper framed as a logical-layer resource-synthesis contribution.
`../results/analysis_claim_scope_lint.md` is generated by the rebuild script
and should have zero unresolved items before upload.
`../results/analysis_ros_reproduction_gap_audit.md` records the ROS-specific
boundary between the verified LUT proxy and the unreproduced full ROS
SAT-garbage-management flow.

Supported:

- Resource-constrained ANF/FPRM search for Boolean oracle synthesis.
- Neural/MCTS/search-control assistance with guarded candidate selection.
- T-count and weighted-score gains under matched logical resource models.
- Layered comparison against direct/ESOP/SSHR/ABC/BDD/toolchain/RevKit probes.
- High-dimensional symbolic and bridge-truth-table verification within the
  stated generated-instance scope.

Not supported:

- Hardware-mapped performance.
- Universal CNOT, depth, ancilla, or line-count dominance.
- A full ROS SAT garbage-management reproduction.
- Official ROS source-discovery note: no official ROS implementation repository
  or local ROS executable is included; the accessible public artifacts are the
  ROS paper and the STG benchmark table.  The Caterpillar API probe is an
  implementation-family performance counterpoint, not an official ROS run.
- A final Clifford+T decomposition claim for RevKit `oracle_synth` Rz outputs.
- Exhaustive truth-table benchmarking for all large-dimensional functions.

## Rebuild And Verification

Run these commands from `../` after any payload-affecting edit:

```bash
./rebuild_submission_package.sh
./verify_submission_package.sh
git diff --check
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_submission_package_verifier.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_claim_scope_lint.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_comparison_protocol_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_comparison_target_validity_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_comparison_route_decision_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_sshr_reproduction_scope_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_caterpillar_ros_family_probe.py
/opt/anaconda3/envs/mcts-qoracle/bin/python run_caterpillar_xag_api_probe.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_ros_reproduction_gap_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_editorial_screening_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_submission_support_packet_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_citation_support_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_headline_numeric_consistency.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_figure_asset_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_latex_dependency_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_pdf_visual_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_pdf_text_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_pdf_metadata_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_source_path_privacy_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python validate_submission_metadata.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_author_input_closure_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_submission_metadata_closure_path.py
/opt/anaconda3/envs/mcts-qoracle/bin/python selftest_submission_metadata_pipeline.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_anonymous_review_readiness.py
/opt/anaconda3/envs/mcts-qoracle/bin/python make_submission_text_preview.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_payload_roundtrip_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_payload_extraction_smoke_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_payload_verifier_smoke_audit.py
/opt/anaconda3/envs/mcts-qoracle/bin/python analyze_payload_latex_compile_audit.py
pdfinfo paper_latex/resource_nmcts_submission_v1.pdf | sed -n '1,20p'
rg -n "Warning|Overfull|Underfull|LaTeX Error|Undefined|Rerun" \
  paper_latex/resource_nmcts_submission_v1.log
rg -n "needs author input|pass:|file count|archive sha256|Submission support|unresolved_count" \
  results/analysis_submission_readiness_audit.md \
  results/analysis_claim_scope_lint.md \
  results/analysis_comparison_protocol_audit.md \
  results/analysis_ros_reproduction_gap_audit.md \
  results/analysis_editorial_screening_audit.md \
  results/analysis_submission_support_packet_audit.md \
  results/analysis_citation_support_audit.md \
  results/analysis_headline_numeric_consistency.md \
  results/analysis_figure_asset_audit.md \
  results/analysis_latex_dependency_audit.md \
  results/analysis_pdf_visual_audit.md \
  results/analysis_pdf_text_audit.md \
  results/analysis_pdf_metadata_audit.md \
  results/analysis_source_path_privacy_audit.md \
  results/manifest_claim_scope_lint.json \
  results/analysis_submission_metadata_validator.md \
  results/analysis_author_input_closure_audit.md \
  results/analysis_submission_metadata_closure_path.md \
  results/analysis_submission_metadata_pipeline_selftest.md \
  results/analysis_anonymous_review_readiness.md \
  results/analysis_submission_text_preview.md \
  results/analysis_payload_roundtrip_audit.md \
  results/analysis_payload_extraction_smoke_audit.md \
  results/analysis_payload_verifier_smoke_audit.md \
  results/analysis_payload_latex_compile_audit.md \
  results/analysis_submission_payload_archive.md \
  results/analysis_submission_archive_manifest.md
```

Expected current boundary: the readiness audit should pass all paper/package
checks except author-specific declarations; the editorial screening audit
should pass all editor-facing scope, novelty, comparison, counterpoint,
AI-boundary, scale-boundary, reproducibility, and author-gate rows.
