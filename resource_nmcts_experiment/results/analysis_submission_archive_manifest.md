# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 297.1 KiB | `f44d19d15e3be461` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 203 | 0 | 227.7 KiB | `c808bb4a0f39d5a9` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.3 MiB | `30253d5b93681ed7` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 458 | 0 | 4.7 MiB | `50564ea2a74267df` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 136 | 0 | 264.6 KiB | `cb321c2d2c5f33b6` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 170 | 0 | 3.1 MiB | `f6aa7571eef1a315` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 18 | 0 | 138.8 KiB | `243ae7b4ae2ebc63` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
