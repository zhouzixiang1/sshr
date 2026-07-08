# Submission Package Verifier

This read-only verifier checks the terminal package invariants after the payload archive has been created.

## Status counts

- pass: 8

| item | status | evidence | next action |
|---|---|---|---|
| Compiled PDF | pass | paper_latex/resource_nmcts_submission_v1.pdf pages=26, bytes=597043. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Payload SHA sidecar | pass | actual=f9d5314b52cfd16aa5bff479fbd5ed4e042ed8aa16fb877f7be45c7f596f395a; sidecar=f9d5314b52cfd16aa5bff479fbd5ed4e042ed8aa16fb877f7be45c7f596f395a. | Regenerate the payload archive if the digests differ. |
| Payload manifest consistency | pass | summary=f9d5314b52cfd16aa5bff479fbd5ed4e042ed8aa16fb877f7be45c7f596f395a; manifest=f9d5314b52cfd16aa5bff479fbd5ed4e042ed8aa16fb877f7be45c7f596f395a; file_count=828. | Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree. |
| Readiness audit terminal state | pass | status_counts={'pass': 21, 'needs author input': 1}. | Resolve any needs-revision rows; author-specific declarations remain manual. |
| Artifact rerun registry coverage | pass | families=14; registry_raw=144; actual_raw=144. | Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts. |
| Claim-scope lint | pass | unresolved_count=0; status_counts={'guarded': 53, 'pass': 5}. | Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims. |
| Private submission text preview | pass | status_counts={'needs author input': 1}; private_outputs_are_git_ignored=True. | Run make_submission_text_preview.py and keep generated private Markdown files ignored by Git. |
| LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
