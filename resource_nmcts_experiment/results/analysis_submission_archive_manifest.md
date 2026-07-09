# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 241.9 KiB | `7d6df574ed1ff8b4` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 187 | 0 | 201.4 KiB | `45aa8aa143888004` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.1 MiB | `24477d2f3f8748ca` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 158 | 0 | 97.6 MiB | `e598b352485e8a93` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 412 | 0 | 4.6 MiB | `0c262caef9c7da8d` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 113 | 0 | 203.2 KiB | `8c8693e2ae435150` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 143 | 0 | 2.6 MiB | `27b8440b4b3c49d8` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 13 | 0 | 100.5 KiB | `9e98c982ebb57fa2` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
