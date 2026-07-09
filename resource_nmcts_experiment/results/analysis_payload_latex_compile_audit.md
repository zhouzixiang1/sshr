# Payload LaTeX Compile Audit

This terminal audit extracts the upload payload and rebuilds the author, anonymous, and ACM/TQC PDFs from the extracted LaTeX sources.

## Status counts

- pass: 4

| item | status | source | returncode | pages | bytes | compile seconds | evidence |
|---|---|---|---:|---:|---:|---:|---|
| Payload extraction for LaTeX compile | pass | `submission_package/dist/resource_nmcts_submission_payload.tar.gz` | n/a | n/a | 1117 | 0.000 | extracted_files=1117; error=none. |
| author payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_v1.tex` | 0 | 48 | 745161 | not_recorded | stdout_lines=1391; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
| anonymous payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_anonymous.tex` | 0 | 47 | 741596 | not_recorded | stdout_lines=1397; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
| acm_tqc payload LaTeX compile | pass | `paper_latex/resource_nmcts_submission_acm_tqc.tex` | 0 | 47 | 912570 | not_recorded | stdout_lines=1922; stderr=none; allowed_bibliography_bootstrap_lines=5; unexpected_log_lines=none. |
