# Payload LaTeX Compile Audit

This terminal audit extracts the upload payload and rebuilds the author and anonymous PDFs from the extracted LaTeX sources.

## Status counts

- pass: 3

| item | status | source | returncode | pages | bytes | compile seconds | evidence |
|---|---|---|---:|---:|---:|---:|---|
| Payload extraction for LaTeX compile | pass | `submission_package/dist/resource_nmcts_submission_payload.tar.gz` | n/a | n/a | 876 | 0.000 | extracted_files=876; error=none. |
| author payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_v1.tex` | 0 | 27 | 601127 | 2.301 | stdout_lines=1073; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
| anonymous payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_anonymous.tex` | 0 | 27 | 597774 | 2.383 | stdout_lines=1081; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
