# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 241.9 KiB | `945102657f0a4d9d` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 185 | 0 | 198.7 KiB | `82655109ff44e9a4` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.1 MiB | `21bcc9aff5c14097` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 156 | 0 | 97.6 MiB | `2eb62382885540bd` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 408 | 0 | 4.5 MiB | `cd386928698cc7b3` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 113 | 0 | 203.1 KiB | `c41fa5a213b49795` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 143 | 0 | 2.6 MiB | `c8c0f275c02182fe` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 13 | 0 | 100.5 KiB | `589e5d47ff0161cf` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
