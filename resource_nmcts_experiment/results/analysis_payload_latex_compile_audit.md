# Payload LaTeX Compile Audit

This terminal audit extracts the upload payload and rebuilds the author and anonymous PDFs from the extracted LaTeX sources.

## Status counts

- pass: 3

| item | status | source | returncode | pages | bytes | compile seconds | evidence |
|---|---|---|---:|---:|---:|---:|---|
| Payload extraction for LaTeX compile | pass | `submission_package/dist/resource_nmcts_submission_payload.tar.gz` | n/a | n/a | 905 | 0.000 | extracted_files=905; error=none. |
| author payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_v1.tex` | 0 | 29 | 606528 | not_recorded | stdout_lines=1092; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
| anonymous payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_anonymous.tex` | 0 | 29 | 603182 | not_recorded | stdout_lines=1100; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
