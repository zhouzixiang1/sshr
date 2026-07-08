# Submission Package Verifier

This read-only verifier checks the terminal package invariants after the payload archive has been created.

## Status counts

- pass: 7

| item | status | evidence | next action |
|---|---|---|---|
| Compiled PDF | pass | paper_latex/resource_nmcts_submission_v1.pdf pages=26, bytes=597028. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Payload SHA sidecar | pass | actual=a918be91ac39f2f3c1d5640d3443b47816359d569e06466aa378a581bfc95428; sidecar=a918be91ac39f2f3c1d5640d3443b47816359d569e06466aa378a581bfc95428. | Regenerate the payload archive if the digests differ. |
| Payload manifest consistency | pass | summary=a918be91ac39f2f3c1d5640d3443b47816359d569e06466aa378a581bfc95428; manifest=a918be91ac39f2f3c1d5640d3443b47816359d569e06466aa378a581bfc95428; file_count=824. | Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree. |
| Readiness audit terminal state | pass | status_counts={'pass': 20, 'needs author input': 1}. | Resolve any needs-revision rows; author-specific declarations remain manual. |
| Artifact rerun registry coverage | pass | families=14; registry_raw=144; actual_raw=144. | Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts. |
| Claim-scope lint | pass | unresolved_count=0; status_counts={'guarded': 53, 'pass': 5}. | Run analyze_claim_scope_lint.py and revise unguarded hardware-mapping, universal-dominance, optimality, or full-tool-reproduction claims. |
| LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
