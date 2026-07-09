# Source Path Privacy Audit

This terminal audit separates strict source/privacy gates from allowed local-path provenance in experiment result files.

## Status counts

- pass: 6

| item | status | scope | files scanned | hits | evidence |
|---|---|---|---:|---:|---|
| Manuscript source local-path hygiene | pass | author/anonymous TeX, bibliography, and generated table inputs | 182 | 0 | local_path_files=none; old_workspace_files=none. |
| Submission support local-path hygiene | pass | public submission_package Markdown/JSON support files | 12 | 0 | local_path_files=none; old_workspace_files=none. |
| Anonymous source identity boundary | pass | anonymous and ACM/TQC review sources | 2 | 0 | missing_anonymous=none; identity_hits=none. |
| Payload private-file membership | pass | results/manifest_submission_payload_archive.json | 1034 | 0 | private_members=none; unsafe_members=none. |
| Payload local-path provenance classification | pass | all text files listed in the upload payload manifest | 991 | 217 | local_path_files=55; strict_local_path_files=none; provenance_local_path_files=55. |
| Old claude workspace path cleanup | pass | all text files listed in the upload payload manifest | 991 | 0 | old_workspace_path_files=none. |
