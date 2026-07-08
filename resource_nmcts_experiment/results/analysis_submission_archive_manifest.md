# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 3 | 0 | 72.1 KiB | `be1f55c9d8353ecc` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 149 | 0 | 127.8 KiB | `78be35e9cea9b078` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `824254679c952e58` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 144 | 0 | 92.5 MiB | `87ee477b5c7c1d69` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 313 | 0 | 4.1 MiB | `0e364417e06c6c80` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 67 | 0 | 91.5 KiB | `b95632ade69464c2` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 67 | 0 | 1.2 MiB | `83973bf0a78cbd4c` | Documents reproducible entry points; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 8 | 0 | 31.9 KiB | `4e73809019eeade4` | Includes package README, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; author-specific fields remain manual. |
