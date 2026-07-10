# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 314.3 KiB | `c0e0909622098c41` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 210 | 0 | 245.0 KiB | `a345ad4b69d149f5` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `2acf9185fa333dea` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 162 | 0 | 98.2 MiB | `440bd6af52b01926` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 472 | 0 | 4.8 MiB | `e98c6e2eb5dfc9eb` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 143 | 0 | 278.6 KiB | `0bdda9cc26e742b1` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 176 | 0 | 3.3 MiB | `66a81fe1fe9cd23a` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 139.4 KiB | `7fb3f0dbd9f32b6c` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
