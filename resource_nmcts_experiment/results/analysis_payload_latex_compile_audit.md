# Payload LaTeX Compile Audit

This terminal audit extracts the upload payload and rebuilds the author, anonymous, and ACM/TQC PDFs from the extracted LaTeX sources.

## Status counts

- pass: 4

| item | status | source | returncode | pages | bytes | compile seconds | evidence |
|---|---|---|---:|---:|---:|---:|---|
| Payload extraction for LaTeX compile | pass | `submission_package/dist/resource_nmcts_submission_payload.tar.gz` | n/a | n/a | 1216 | 0.000 | extracted_files=1216; error=none. |
| author payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_v1.tex` | 0 | 54 | 772305 | not_recorded | stdout_lines=1619; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
| anonymous payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_anonymous.tex` | 0 | 54 | 769091 | not_recorded | stdout_lines=1627; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
| acm_tqc payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_acm_tqc.tex` | 0 | 51 | 952841 | not_recorded | stdout_lines=2010; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
