# Payload Round-Trip Audit

This terminal audit opens the reviewer/upload tarball and checks manifest agreement, per-file hashes, path hygiene, required artifacts, and deterministic tar metadata.

## Status counts

- pass: 8

| item | status | evidence | next action |
|---|---|---|---|
| Payload archive readable | pass | archive=submission_package/dist/resource_nmcts_submission_payload.tar.gz; members=864; error=none. | Regenerate the payload archive if it cannot be opened by Python tarfile. |
| Payload manifest round-trip | pass | manifest_files=864; archive_files=864; missing=none; extra=none. | Regenerate make_submission_payload_archive.py outputs if manifest and archive contents diverge. |
| Payload per-file SHA256 | pass | checked=864; mismatches=none. | Regenerate the payload archive and manifest if any archived file digest differs from the manifest. |
| Payload path hygiene | pass | unsafe_paths=none; private_hits=none. | Remove unsafe, platform-generated, or private files from the payload inputs. |
| Payload required artifacts | pass | required=12; missing=none. | Ensure the uploadable archive includes manuscript, bibliography, rebuild/verify scripts, handoff docs, and submission audits. |
| Payload reviewer entrypoints | pass | reviewer_entries=7; missing=none. | Ensure the uploadable archive includes reviewer-facing guide, editor/reviewer briefs, venue brief, registry, and reproducibility audit. |
| Payload comparison protocol evidence | pass | comparison_protocol_files=10; missing=none. | Ensure the uploadable archive includes the comparison protocol audit plus its claim, evidence, comparability, counterpoint, statistical, and tradeoff sources. |
| Payload deterministic tar metadata | pass | members_checked=864; metadata_issues=none. | Keep tar member mtime/uid/gid/user/group/mode normalized for deterministic payloads. |
