# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission audits and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 3 | 0 | 70.4 KiB | `2be3b6d2c53b9bc8` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 149 | 0 | 127.8 KiB | `fc48c8a05fc3b84f` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `824254679c952e58` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 144 | 0 | 92.5 MiB | `87ee477b5c7c1d69` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 309 | 0 | 4.1 MiB | `d99e7e6d15e36c96` | Terminal submission audit outputs are excluded so this manifest remains stable. |
| Run manifests | 65 | 0 | 73.2 KiB | `6a2272e4e76d727a` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 64 | 0 | 1.2 MiB | `86932f3d1f92690e` | Documents reproducible entry points; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 4 | 0 | 11.8 KiB | `cb0ad16a2921f1be` | Includes cover-letter, declaration, checklist, and reviewer-brief templates; author-specific fields remain manual. |
