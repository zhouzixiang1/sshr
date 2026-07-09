# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 284.7 KiB | `28934081777df1de` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 200 | 0 | 224.8 KiB | `f5c512a066201f78` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `da755afcf0b28535` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 452 | 0 | 4.7 MiB | `a4630740fc526ac7` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 133 | 0 | 260.5 KiB | `71d473f0ce1424dd` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 167 | 0 | 3.1 MiB | `31245adfaf2a7492` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 138.7 KiB | `2f25be4c6ffd9867` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
