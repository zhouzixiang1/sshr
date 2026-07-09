# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 4 | 0 | 124.3 KiB | `c94047ac1655cfeb` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 153 | 0 | 135.7 KiB | `32f5e385b2bd06ad` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `824254679c952e58` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 144 | 0 | 92.5 MiB | `87ee477b5c7c1d69` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 341 | 0 | 4.3 MiB | `7b982e413d6e68cb` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 81 | 0 | 127.6 KiB | `8e9feb897625f90b` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 96 | 0 | 1.6 MiB | `7fb2204a61a3feba` | Documents reproducible entry points; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 73.4 KiB | `8c10c2e0fdd025a0` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
