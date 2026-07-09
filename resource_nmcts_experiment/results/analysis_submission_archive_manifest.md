# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 205.6 KiB | `d5a965d37779da45` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 170 | 0 | 174.5 KiB | `5c28939da2069451` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `7e792ff61993e4e8` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 146 | 0 | 93.1 MiB | `b487b54b2f39140b` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 377 | 0 | 4.4 MiB | `07f9157f2e744337` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 99 | 0 | 169.9 KiB | `47dbd7cd5bdb8fdb` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 129 | 0 | 2.2 MiB | `d2d00d2ac16c97b3` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 11 | 0 | 84.3 KiB | `1850ba9ca1f2ea68` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
