# Submission Package Verifier

This read-only verifier checks the terminal package invariants after the payload archive has been created.

## Status counts

- pass: 6

| item | status | evidence | next action |
|---|---|---|---|
| Compiled PDF | pass | paper_latex/resource_nmcts_submission_v1.pdf pages=26, bytes=597029. | Rebuild the submission package and inspect latexmk output if the PDF is missing. |
| Payload SHA sidecar | pass | actual=fffab1370bbf1d6153f1c86cabaf88d021541eaa407d030c64644d96a29cf429; sidecar=fffab1370bbf1d6153f1c86cabaf88d021541eaa407d030c64644d96a29cf429. | Regenerate the payload archive if the digests differ. |
| Payload manifest consistency | pass | summary=fffab1370bbf1d6153f1c86cabaf88d021541eaa407d030c64644d96a29cf429; manifest=fffab1370bbf1d6153f1c86cabaf88d021541eaa407d030c64644d96a29cf429; file_count=817. | Regenerate make_submission_payload_archive.py outputs if summary and manifest disagree. |
| Readiness audit terminal state | pass | status_counts={'pass': 19, 'needs author input': 1}. | Resolve any needs-revision rows; author-specific declarations remain manual. |
| Artifact rerun registry coverage | pass | families=14; registry_raw=144; actual_raw=144. | Rerun analyze_artifact_rerun_registry.py after adding raw CSVs or driver scripts. |
| LaTeX log boundary | pass | Only allowed rerunfilecheck/showhyphens log lines found. | Inspect the LaTeX log and fix unexpected warnings or errors. |
