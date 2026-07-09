# Phase Rotation-Sequence Smoke Audit

This audit extracts representative non-Clifford Rz angles from the verified affine phase spectra
and emits concrete single-qubit Clifford+T gate strings with an internal matrix beam search.
The distance metric is global-phase-invariant:
`sqrt(1 - |Tr(U_seq^dagger U_target)|/2)`.

This is a coarse sequence-level smoke test.  It is not Ross--Selinger gridsynth,
not optimal T-count synthesis, not a high-precision compiler, and not hardware mapping.

- target angles: 6
- smoke epsilon: 0.125
- smoke passes: 6/6
- tight epsilon: 0.05
- tight passes: 2/6
- max achieved error among smoke passes: 0.111853
- mean achieved error among smoke passes: 0.071984

| target | angle/pi | support | sequence length | T count | error | smoke pass | sequence |
|---|---:|---:|---:|---:|---:|---:|---|
| den8-small | 1/8 | 1088 | 14 | 8 | 0.1119 | yes | `T H T H T H T H T H T S Td Td` |
| den8-mid | 3/8 | 714 | 12 | 5 | 0.1119 | yes | `T H T H T H T H X Td H Sd` |
| den16-mid-a | 3/16 | 714 | 6 | 3 | 0.0694 | yes | `X Sd Td X Td Td` |
| den16-mid-b | 5/16 | 572 | 11 | 7 | 0.0694 | yes | `S Td Td S Td Td S Td Td S Td` |
| den32-small | 1/32 | 903 | 5 | 2 | 0.0347 | yes | `X Sd T X Td` |
| den32-frequent | 57/32 | 1015 | 17 | 9 | 0.0347 | yes | `X Sd X Sd Td Td S Td Td S Td Td S Td Td S Td` |

## Interpretation

- The six target angles are present in the existing phase-search outputs; this is not a synthetic rotation-only benchmark.
- The bounded beam search closes part of the previous evidence gap by emitting actual Clifford+T strings for representative Rz targets.
- The coarse tolerance and non-optimal sequences mean the manuscript should still keep the phase/Rz branch as a logical proxy and cite Ross--Selinger only for the precision-sensitivity model.
