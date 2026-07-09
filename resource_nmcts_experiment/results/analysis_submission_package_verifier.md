# Submission Package Verifier

This read-only verifier checks the terminal package invariants after the payload archive has been created.

## Status counts

- pass: 9

| item | status | evidence | next action |
|---|---|---|---|
| Compiled PDF | pass | paper_latex/resource_nmcts_submission_v1.pdf pages=26, bytes=596931. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Payload SHA sidecar | pass | actual=6632aa8451f08b8b6424c2ce2d78960caa10c0aab33784f4985330198633d346; sidecar=6632aa8451f08b8b6424c2ce2d78960caa10c0aab33784f4985330198633d346. | Regenerate the payload archive if the digests differ. |
| Payload manifest consistency | pass | summary=6632aa8451f08b8b6424c2ce2d78960caa10c0aab33784f4985330198633d346; manifest=6632aa8451f08b8b6424c2ce2d78960caa10c0aab33784f4985330198633d346; file_count=831. | Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree. |
| Readiness audit terminal state | pass | status_counts={'pass': 22, 'needs author input': 1}. | Resolve any needs-revision rows; author-specific declarations remain manual. |
| Artifact rerun registry coverage | pass | families=14; registry_raw=144; actual_raw=144. | Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts. |
| Claim-scope lint | pass | unresolved_count=0; status_counts={'guarded': 53, 'pass': 5}. | Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims. |
| Private metadata validator | pass | needs_revision_count=0; status_counts={'needs author input': 1}. | Run validate_submission_metadata.py and fix metadata format or consistency rows before upload. |
| Private submission text preview | pass | status_counts={'needs author input': 1}; private_outputs_are_git_ignored=True. | Run make_submission_text_preview.py and keep generated private Markdown files ignored by Git. |
| LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
