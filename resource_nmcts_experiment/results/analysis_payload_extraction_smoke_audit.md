# Payload Extraction Smoke Audit

This terminal audit extracts the reviewer/upload payload into a temporary directory and runs lightweight reviewer-facing checks from the extracted tree.

## Status counts

- pass: 4

| item | status | evidence | next action |
|---|---|---|---|
| Payload extraction | pass | archive=submission_package/dist/resource_nmcts_submission_payload.tar.gz; extracted_files=859; error=none. | Regenerate the payload archive if it cannot be safely extracted. |
| Comparison protocol audit | pass | returncode=0; manifest=results/manifest_comparison_protocol_audit.json; needs_revision_count=0; layers=7; stderr=none | Inspect the extracted payload audit output and regenerate the archive if this smoke test fails. |
| Claim-scope lint | pass | returncode=0; manifest=results/manifest_claim_scope_lint.json; unresolved_count=0; required_boundary_count=5; stderr=none | Inspect the extracted payload audit output and regenerate the archive if this smoke test fails. |
| Artifact rerun registry | pass | returncode=0; manifest=results/manifest_artifact_rerun_registry.json; complete_rows=14; rows=14; stderr=none | Inspect the extracted payload audit output and regenerate the archive if this smoke test fails. |
