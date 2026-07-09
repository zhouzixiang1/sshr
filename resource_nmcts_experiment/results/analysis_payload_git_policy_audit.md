# Payload Git Policy Audit

This audit checks that the deterministic upload tarball is available locally after a rebuild but remains a generated, ignored Git artifact.

## Status counts

- pass: 4

| item | status | evidence | next action |
|---|---|---|---|
| Generated payload presence | pass | archive_exists=True; sha256_exists=True; archive=submission_package/dist/resource_nmcts_submission_payload.tar.gz. | Run make_submission_payload_archive.py or rebuild_submission_package.sh to regenerate the upload tarball and sidecar. |
| Generated payload SHA sidecar | pass | actual=84e8b2ef8a9f7e3489b28322683f37cca5f0f8915f1847e6f8aa45eb1cf43a10; sidecar=84e8b2ef8a9f7e3489b28322683f37cca5f0f8915f1847e6f8aa45eb1cf43a10; bytes=42139214. | Regenerate the tarball and sidecar if their digests differ. |
| Generated payload Git policy | pass | tracked=none; ignored=['resource_nmcts_experiment/submission_package/dist/resource_nmcts_submission_payload.tar.gz', 'resource_nmcts_experiment/submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256']; git_root=/Users/zhouzixiang/Desktop/tzb/src. | Keep submission_package/dist/*.tar.gz and the SHA sidecar ignored and out of the Git index. |
| Generated payload regeneration path | pass | rebuild_script=True; verify_script=True. | Restore rebuild_submission_package.sh and verify_submission_package.sh if either entrypoint is missing. |
