# Submission Package Verifier

This read-only verifier checks the terminal package invariants after the payload archive has been created.

## Status counts

- pass: 10

| item | status | evidence | next action |
|---|---|---|---|
| Compiled PDF | pass | paper_latex/resource_nmcts_submission_v1.pdf pages=26, bytes=597039. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Payload SHA sidecar | pass | actual=6710d0bdd7a32004550ef419ea76c92f08e81b1564dcb0b430861b289ae5a9b6; sidecar=6710d0bdd7a32004550ef419ea76c92f08e81b1564dcb0b430861b289ae5a9b6. | Regenerate the payload archive if the digests differ. |
| Payload manifest consistency | pass | summary=6710d0bdd7a32004550ef419ea76c92f08e81b1564dcb0b430861b289ae5a9b6; manifest=6710d0bdd7a32004550ef419ea76c92f08e81b1564dcb0b430861b289ae5a9b6; file_count=834. | Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree. |
| Readiness audit terminal state | pass | status_counts={'pass': 23, 'needs author input': 1}. | Resolve any needs-revision rows; author-specific declarations remain manual. |
| Artifact rerun registry coverage | pass | families=14; registry_raw=144; actual_raw=144. | Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts. |
| Claim-scope lint | pass | unresolved_count=0; status_counts={'guarded': 53, 'pass': 5}. | Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims. |
| Private metadata validator | pass | needs_revision_count=0; status_counts={'needs author input': 1}. | Run validate_submission_metadata.py and fix metadata format or consistency rows before upload. |
| Metadata pipeline self-test | pass | needs_revision_count=0; status_counts={'pass': 14}; synthetic_only=True; writes_private_metadata=False; writes_private_preview_files=False. | Run selftest_submission_metadata_pipeline.py and keep the fixture synthetic and non-private. |
| Private submission text preview | pass | status_counts={'needs author input': 1}; private_outputs_are_git_ignored=True. | Run make_submission_text_preview.py and keep generated private Markdown files ignored by Git. |
| LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
