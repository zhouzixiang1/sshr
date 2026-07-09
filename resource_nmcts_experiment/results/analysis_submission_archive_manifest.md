# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 4 | 0 | 132.7 KiB | `258c54da60bf4e04` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 161 | 0 | 154.5 KiB | `41287ac20a940300` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `5ba5884bfd82e9ed` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 145 | 0 | 93.1 MiB | `a868b9542153ff9b` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 356 | 0 | 4.3 MiB | `7255c03ba8f8e043` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 89 | 0 | 153.7 KiB | `b50990ca8ea85230` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 117 | 0 | 2.0 MiB | `a509112d513f0b81` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 77.2 KiB | `0164dddbbcff5e70` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
