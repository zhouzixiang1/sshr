# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 231.4 KiB | `435c730f5df444d0` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 179 | 0 | 187.0 KiB | `7d4fd938822be51a` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `8384a386e5af073c` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 151 | 0 | 94.0 MiB | `d654335330ae82a7` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 396 | 0 | 4.5 MiB | `8d0c136841e5f22a` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 109 | 0 | 186.9 KiB | `56b31824be21079d` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 140 | 0 | 2.5 MiB | `3d3706b6d2333133` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 12 | 0 | 92.3 KiB | `20f9f9b4d21dbadb` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
