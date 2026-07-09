# Submission Package Verifier

This read-only verifier checks the terminal package invariants after the payload archive has been created.

## Status counts

- pass: 15

| item | status | evidence | next action |
|---|---|---|---|
| Compiled author PDF | pass | paper_latex/resource_nmcts_submission_v1.pdf pages=27, bytes=601116. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Compiled anonymous PDF | pass | paper_latex/resource_nmcts_submission_anonymous.pdf pages=27, bytes=597775. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Payload SHA sidecar | pass | actual=df4212b70b24404795908e8853271276ee702ede3b3237bd7ff84fe32e216ec8; sidecar=df4212b70b24404795908e8853271276ee702ede3b3237bd7ff84fe32e216ec8. | Regenerate the payload archive if the digests differ. |
| Payload manifest consistency | pass | summary=df4212b70b24404795908e8853271276ee702ede3b3237bd7ff84fe32e216ec8; manifest=df4212b70b24404795908e8853271276ee702ede3b3237bd7ff84fe32e216ec8; file_count=850. | Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree. |
| Readiness audit terminal state | pass | status_counts={'pass': 27, 'needs author input': 1}. | Resolve any needs-revision rows; author-specific declarations remain manual. |
| Artifact rerun registry coverage | pass | families=14; registry_raw=144; actual_raw=144. | Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts. |
| Claim-scope lint | pass | unresolved_count=0; status_counts={'guarded': 59, 'pass': 5}. | Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims. |
| Private metadata validator | pass | needs_revision_count=0; status_counts={'needs author input': 1}. | Run validate_submission_metadata.py and fix metadata format or consistency rows before upload. |
| Metadata pipeline self-test | pass | needs_revision_count=0; status_counts={'pass': 14}; synthetic_only=True; writes_private_metadata=False; writes_private_preview_files=False. | Run selftest_submission_metadata_pipeline.py and keep the fixture synthetic and non-private. |
| Anonymous-review readiness audit | pass | needs_revision_count=0; needs_author_input_count=3; status_counts={'needs author input': 3, 'pass': 3}. | Run analyze_anonymous_review_readiness.py and resolve needs-revision rows; double-blind conversion remains venue-dependent author input. |
| Private submission text preview | pass | status_counts={'needs author input': 1}; private_outputs_are_git_ignored=True. | Run make_submission_text_preview.py and keep generated private Markdown files ignored by Git. |
| Private metadata payload exclusion | pass | private_payload_hits=none; checked_basenames=['generated_author_declarations.md', 'generated_availability_statements.md', 'generated_cover_letter.md', 'generated_submission_text.md', 'submission_metadata.json']. | Regenerate the payload after removing ignored private metadata or preview files from package inputs. |
| Payload round-trip audit | pass | needs_revision_count=0; status_counts={'pass': 6}. | Run analyze_payload_roundtrip_audit.py after payload creation and fix any archive/manifest/path/hash issues. |
| Author LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
| Anonymous LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
