# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 263.5 KiB | `4824399f65b62468` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 192 | 0 | 209.3 KiB | `8a83f1e47c3b58cc` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `57c8751f06116db0` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 424 | 0 | 4.6 MiB | `49950dc1ed52598a` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 119 | 0 | 220.7 KiB | `7e314cf404f6b5c0` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 149 | 0 | 2.7 MiB | `3de37f66fa2b1842` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 13 | 0 | 103.4 KiB | `acb4332fadd705d1` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
