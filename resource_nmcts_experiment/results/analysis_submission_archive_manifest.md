# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 219.8 KiB | `e55a5e9a0382d198` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 176 | 0 | 183.8 KiB | `4f672a0941e8c296` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `8384a386e5af073c` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 149 | 0 | 93.8 MiB | `30d67e8ff400d4d5` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 390 | 0 | 4.4 MiB | `efb90a8bd199231b` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 106 | 0 | 181.4 KiB | `9aec220b93866428` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 136 | 0 | 2.4 MiB | `addb61cd20bad0f8` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 12 | 0 | 92.3 KiB | `2e11f5b30d98d20c` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
