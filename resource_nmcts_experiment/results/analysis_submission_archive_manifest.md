# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 214.8 KiB | `62a0444dd3d47f35` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 173 | 0 | 180.3 KiB | `4f477dd07d69c8a8` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `7e792ff61993e4e8` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 148 | 0 | 93.4 MiB | `e6cf345fec4c6a8a` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 383 | 0 | 4.4 MiB | `b12ac69fc53d52ac` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 102 | 0 | 177.1 KiB | `d583c256f03f3c99` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 132 | 0 | 2.3 MiB | `c5e2b01b0b9f78df` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 85.5 KiB | `41394fd7ea752e23` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
