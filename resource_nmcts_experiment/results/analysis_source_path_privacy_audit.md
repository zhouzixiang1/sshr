# Source Path Privacy Audit

This terminal audit separates strict source/privacy gates from allowed local-path provenance in experiment result files.

## Status counts

- pass: 6

| item | status | scope | files scanned | hits | evidence |
|---|---|---|---:|---:|---|
| Manuscript source local-path hygiene | pass | author/anonymous TeX, bibliography, and generated table inputs | 178 | 0 | local_path_files=none; old_workspace_files=none. |
| Submission support local-path hygiene | pass | public submission_package Markdown/JSON support files | 11 | 0 | local_path_files=none; old_workspace_files=none. |
| Anonymous source identity boundary | pass | anonymous and ACM/TQC review sources | 2 | 0 | missing_anonymous=none; identity_hits=none. |
| Payload private-file membership | pass | results/manifest_submission_payload_archive.json | 1008 | 0 | private_members=none; unsafe_members=none. |
| Payload local-path provenance classification | pass | all text files listed in the upload payload manifest | 965 | 213 | local_path_files=53; strict_local_path_files=none; provenance_local_path_files=53. |
| Old claude workspace path cleanup | pass | all text files listed in the upload payload manifest | 965 | 0 | old_workspace_path_files=none. |
