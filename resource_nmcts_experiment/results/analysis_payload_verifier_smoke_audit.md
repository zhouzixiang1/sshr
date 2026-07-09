# Payload Verifier Smoke Audit

This terminal audit extracts the upload payload and runs `verify_submission_package.sh` from inside the extracted tree.

## Status counts

- pass: 2

| item | status | source | returncode | elapsed seconds | evidence | next action |
|---|---|---|---:|---:|---|---|
| Payload extraction for verifier smoke | pass | `submission_package/dist/resource_nmcts_submission_payload.tar.gz` | n/a | 0.000 | extracted_files=904; error=none. | Regenerate the payload archive if it cannot be safely extracted. |
| Extracted payload verifier command | pass | `verify_submission_package.sh` | 0 | not_recorded | verifier_returncode=0; verifier_rows=33; verifier_needs_revision_count=0; extracted_payload_mode=True; status_counts={'pass': 33}; stdout_lines=111; stderr=none. | Inspect the verifier outputs generated inside the extracted payload directory. |
