# Payload Git Policy Audit

This audit checks that the deterministic upload tarball is available locally after a rebuild but remains a generated, ignored Git artifact.

## Status counts

- pass: 4

| item | status | evidence | next action |
|---|---|---|---|
| Generated payload presence | pass | archive_exists=True; sha256_exists=True; archive=submission_package/dist/resource_nmcts_submission_payload.tar.gz. | Run make_submission_payload_archive.py or rebuild_submission_package.sh to regenerate the upload tarball and sidecar. |
| Generated payload SHA sidecar | pass | actual=4542b1e0c5ee8eac13658e5dd7717c51de9d6e080ef1117d60f5dca1b4d7ad91; sidecar=4542b1e0c5ee8eac13658e5dd7717c51de9d6e080ef1117d60f5dca1b4d7ad91; bytes=41961078. | Regenerate the tarball and sidecar if their digests differ. |
| Generated payload Git policy | pass | tracked=none; ignored=['resource_nmcts_experiment/submission_package/dist/resource_nmcts_submission_payload.tar.gz', 'resource_nmcts_experiment/submission_package/dist/resource_nmcts_submission_payload.tar.gz.sha256']; git_root=/Users/zhouzixiang/Desktop/tzb/src. | Keep submission_package/dist/*.tar.gz and the SHA sidecar ignored and out of the Git index. |
| Generated payload regeneration path | pass | rebuild_script=True; verify_script=True. | Restore rebuild_submission_package.sh and verify_submission_package.sh if either entrypoint is missing. |
