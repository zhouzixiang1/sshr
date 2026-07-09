# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 241.9 KiB | `c5b8781e4ad25d77` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 182 | 0 | 194.1 KiB | `48368b2a8c0a5d0d` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.1 MiB | `96917266930212f5` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 153 | 0 | 97.6 MiB | `efc9edba2fff2544` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 402 | 0 | 4.5 MiB | `3013cf740b709266` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 113 | 0 | 201.8 KiB | `40fdf97270e61b88` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 143 | 0 | 2.6 MiB | `b2dbb997616c7df2` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 13 | 0 | 100.5 KiB | `fb055468dc4b7941` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
