# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 224.2 KiB | `5161fc52f192f242` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 177 | 0 | 184.7 KiB | `7366e54fab61c4f4` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `8384a386e5af073c` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 149 | 0 | 93.8 MiB | `30d67e8ff400d4d5` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 392 | 0 | 4.5 MiB | `177a5a6d8a7bec8e` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 107 | 0 | 182.7 KiB | `0dd75236e4c70242` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 137 | 0 | 2.4 MiB | `8b7553e3df811c2e` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 12 | 0 | 92.3 KiB | `20f9f9b4d21dbadb` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
