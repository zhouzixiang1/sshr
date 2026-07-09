# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 3 | 0 | 72.1 KiB | `be1f55c9d8353ecc` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 150 | 0 | 130.4 KiB | `3881ccff4866072e` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `824254679c952e58` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 144 | 0 | 92.5 MiB | `87ee477b5c7c1d69` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 325 | 0 | 4.2 MiB | `de7696267fdedca3` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 74 | 0 | 125.3 KiB | `d908c30c3d66743a` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 74 | 0 | 1.3 MiB | `95fcf1f3c0ca2ae7` | Documents reproducible entry points; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 10 | 0 | 52.3 KiB | `a087633d8e78b384` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
