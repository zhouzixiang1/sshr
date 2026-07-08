# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 3 | 0 | 71.2 KiB | `c532ac03e3ef5c3d` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 149 | 0 | 127.8 KiB | `bace690076fe9c52` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `824254679c952e58` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 144 | 0 | 92.5 MiB | `87ee477b5c7c1d69` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 311 | 0 | 4.1 MiB | `7c2ba3226f777c20` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 66 | 0 | 79.9 KiB | `38647bc6dbc943c5` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 66 | 0 | 1.2 MiB | `038fe511996a678b` | Documents reproducible entry points; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 4 | 0 | 13.1 KiB | `5904e7722693e3a4` | Includes cover-letter, declaration, checklist, and reviewer-brief templates; author-specific fields remain manual. |
