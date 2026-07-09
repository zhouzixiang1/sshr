# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 4 | 0 | 134.7 KiB | `1c4fbd7299af6b4e` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 163 | 0 | 157.8 KiB | `86f5407828a3cd21` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `a9bdb91e8e0345ac` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 145 | 0 | 93.1 MiB | `a868b9542153ff9b` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 360 | 0 | 4.3 MiB | `d034d8579d1d6797` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 91 | 0 | 155.9 KiB | `82ac16fc46709668` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 119 | 0 | 2.0 MiB | `5904ae2124899a0d` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 79.3 KiB | `49b34c13ee401669` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
