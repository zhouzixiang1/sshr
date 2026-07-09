# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 234.8 KiB | `56177e862fac0096` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 180 | 0 | 188.7 KiB | `ca3b1146b61bbc89` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `8384a386e5af073c` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 152 | 0 | 97.5 MiB | `9d767a6f10619874` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 398 | 0 | 4.5 MiB | `abca7431e4561b12` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 111 | 0 | 190.0 KiB | `9a6b065e6f158d05` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 141 | 0 | 2.5 MiB | `bd80b47b085086e0` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 12 | 0 | 92.3 KiB | `a560f49231396bd4` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
