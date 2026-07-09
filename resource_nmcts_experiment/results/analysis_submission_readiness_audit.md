# Submission Readiness Audit

This audit checks paper-level readiness markers in `paper_latex/resource_nmcts_submission_v1.tex` and the compiled PDF.

## Status counts

- needs author input: 1
- pass: 27

## Checklist

| item | status | evidence | next action |
|---|---|---|---|
| Bounded abstract claim | pass | Abstract states logical-layer scope and excludes hardware-mapped/depth-only claims. | Keep hardware and mapping claims out of the abstract unless new evidence is added. |
| Abstract concision | pass | Abstract word count is 287. | Keep the abstract compact; detailed per-baseline numbers belong in Results tables. |
| First-pages scope and assumptions | pass | Introduction states the logical-layer scope, excluded hardware assumptions, score role, and comparison boundary. | Keep the scope and assumptions visible in the first pages after venue-specific template conversion. |
| Contribution-to-evidence chain | pass | Introduction includes a contribution-to-evidence map. | Update the map whenever a headline contribution changes. |
| Executable method workflow | pass | Method includes an end-to-end synthesis and verification workflow table. | Keep the workflow table aligned with new candidate generators or verification stages. |
| Baseline fairness and scope | pass | Experimental design includes claim, evidence, and comparability matrices. | Keep cross-toolchain claims tied to the comparability audit. |
| Paired effect uncertainty | pass | Manuscript includes bootstrap uncertainty intervals for paired score-effect estimates. | Rerun analyze_paired_effect_uncertainty.py after changing paired comparisons or score fields. |
| Claim-scope lint | pass | Claim-scope lint scans manuscript and handoff files; unresolved_count=0. | Rerun analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims. |
| Reproducibility evidence | pass | Manuscript includes compute, worker, artifact, and external-tool provenance table. | Rerun analyze_reproducibility_audit.py after adding scripts, tables, or figures. |
| Raw rerun registry | pass | Artifact rerun registry maps evidence families to driver scripts, raw CSV coverage, manifests, rerun tiers, and dependency boundaries. | Rerun analyze_artifact_rerun_registry.py after adding raw data families, run scripts, or external-tool probes. |
| Claim-to-artifact traceability | pass | Manuscript includes a submission traceability audit linking claim families to scripts, data, tables, and figures. | Rerun analyze_submission_traceability_audit.py after adding or moving headline evidence. |
| Archive package manifest | pass | Manuscript includes an archive-level payload manifest with generated CSV, Markdown, and JSON outputs. | Rerun analyze_submission_archive_manifest.py after adding tables, figures, scripts, models, or result files. |
| Submission support templates | pass | Package README, author-input packet, artifact guide, cover letter, author declarations, upload checklist, reviewer-concern brief, editor-screening brief, and target-venue brief are present. | Fill the author-specific fields before journal upload. |
| Submission metadata audit | pass | Author- and venue-specific metadata fields are enumerated in CSV, Markdown, and JSON audit outputs. | Rerun analyze_submission_metadata_audit.py after filling author declarations or choosing a target venue. |
| Submission metadata validator | pass | Private metadata format validator exists; status_counts={'needs author input': 1}; needs_revision_count=0. | Rerun validate_submission_metadata.py after filling private metadata; fix format or consistency rows before upload. |
| Submission metadata pipeline self-test | pass | Synthetic metadata self-test exercises validator and preview renderers; status_counts={'pass': 14}; needs_revision_count=0; synthetic_only=True; writes_private_outputs=False. | Rerun selftest_submission_metadata_pipeline.py after changing required metadata paths, validators, or preview renderers. |
| Private submission text preview | pass | Private preview generator audit exists; status_counts={'needs author input': 1}; private_outputs_are_git_ignored=True. | Rerun make_submission_text_preview.py after filling private metadata; generated_*.md files must remain ignored by Git. |
| Anonymous-review readiness path | pass | Anonymous-review audit exists; status_counts={'needs author input': 3, 'pass': 2}; needs_revision_count=0; needs_author_input_count=3. | If the selected venue requires double-blind review, produce an anonymized manuscript copy and anonymous artifact links before upload. |
| Goal completion audit | pass | The original project objective is mapped to concrete evidence files, boundaries, and remaining author-gated items. | Rerun analyze_goal_completion_audit.py after adding major evidence or filling author/venue metadata. |
| Uploadable payload archive | pass | Deterministic submission payload tarball, SHA256 sidecar, CSV, Markdown, and JSON manifest are present. | Rerun make_submission_payload_archive.py after adding or removing upload payload files. |
| Payload round-trip integrity | pass | Payload round-trip audit exists; status_counts={'pass': 6}; needs_revision_count=0. | Rerun analyze_payload_roundtrip_audit.py after payload creation and fix any archive/manifest/path/hash issues. |
| Terminal package verifier | pass | Fast pre-upload verifier script and read-only verifier outputs check PDF availability, payload SHA consistency, readiness state, raw registry coverage, claim-scope lint, private metadata validation, metadata-pipeline self-test, anonymous-review readiness, private-preview protection, private payload exclusion, payload round-trip integrity, and LaTeX log boundaries. | Run verify_submission_package.sh after rebuilding the payload archive. |
| Derived package rebuild command | pass | A lightweight rebuild script is present and cited in Data and Code Availability. | Keep the rebuild script aligned with paper-facing analysis, figure, audit, and PDF outputs. |
| Limitations and failure modes | pass | Discussion names logical-layer, ROS-proxy, RevKit-derived, and high-dimensional bridge boundaries. | Add any new negative result to Discussion rather than hiding it in tables. |
| Data and code availability | pass | Manuscript has an availability section pointing to scripts, CSVs, manifests, tables, and figures. | Replace repository-relative wording with an archival DOI or anonymous link at submission time if required. |
| Clean submission source | pass | 0 TODO/TBD/placeholder markers in submission TeX. | Remove all source placeholders before journal upload. |
| Compiled PDF artifact | pass | Compiled PDF detected with 26 pages. | Run latexmk and visual spot checks after each table or figure change. |
| Author-specific declarations | needs author input | Funding, acknowledgements, author metadata, competing interests, target-venue fields, and final archival links are author-specific even though templates, metadata audit, and goal-completion audit are prepared. | Complete `submission_package/author_declarations_template.md`, update the cover letter/checklist, and replace repository-relative availability links at the target journal's submission step. |
