# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 4 | 0 | 129.8 KiB | `8a899a5d3ce949b2` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 159 | 0 | 150.7 KiB | `04d5f157f1396643` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `824254679c952e58` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 144 | 0 | 92.5 MiB | `87ee477b5c7c1d69` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 351 | 0 | 4.3 MiB | `0493db61c0b11c18` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 86 | 0 | 151.4 KiB | `f6e072247cca4f1d` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 101 | 0 | 1.7 MiB | `2298ee897eb624c4` | Documents reproducible entry points; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 77.2 KiB | `0164dddbbcff5e70` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
