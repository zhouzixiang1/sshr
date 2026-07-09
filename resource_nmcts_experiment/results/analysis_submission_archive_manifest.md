# Submission Archive Manifest

This audit hashes stable submission payload groups while excluding terminal submission package/audit outputs and the compiled PDF.

## Status counts

- complete categories: 10/10

| category | files | missing | size | digest | boundary |
|---|---:|---:|---:|---|---|
| Manuscript source | 5 | 0 | 275.4 KiB | `09ff7ea70d0a2c1b` | Compiled PDF is checked by readiness audit to avoid self-referential hashes. |
| Paper tables | 198 | 0 | 223.0 KiB | `de10b5b8add52547` | Terminal submission audit tables are excluded from the stable payload digest. |
| Submission figures | 28 | 0 | 1.2 MiB | `57c8751f06116db0` | Includes generated figure assets and plotted source data, not raw benchmark reruns. |
| Raw measurements | 161 | 0 | 98.2 MiB | `fa1965cc81bb079f` | Raw CSVs are regenerated only by the heavier run scripts, not by the lightweight rebuild. |
| Derived summaries | 444 | 0 | 4.7 MiB | `b761d21a15af0462` | Terminal submission/package outputs are excluded so this manifest remains stable. |
| Run manifests | 129 | 0 | 255.4 KiB | `f3f2bbd96d2b35bb` | Submission-level terminal manifests are excluded from this digest group. |
| Scripts and docs | 161 | 0 | 3.0 MiB | `57f251b1bf9df93c` | Includes reproducible entry points and top-level core implementation modules; raw sweeps still require their individual drivers. |
| Models | 20 | 0 | 1.1 MiB | `4c5c2a1bfc19ff5d` | Includes trained local policy artifacts when present; model retraining is not part of the lightweight rebuild. |
| External adapters | 1 | 0 | 2.2 KiB | `de5aa3b78998ebbd` | Includes local adapter source files used for external toolchain probes, not vendored tool repositories. |
| Submission support | 17 | 0 | 131.2 KiB | `ee70f2df184eac6b` | Includes public package README, author-input packet, artifact guide, cover-letter, declaration, checklist, reviewer-brief, editor-screening, venue-selection, and structured metadata templates; ignored generated private submission text is excluded. |
