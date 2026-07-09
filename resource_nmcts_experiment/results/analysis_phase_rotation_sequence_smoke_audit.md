# Phase Rotation-Sequence Smoke Audit

This audit extracts representative non-Clifford Rz angles from the verified affine phase spectra
and emits concrete single-qubit Clifford+T gate strings with an internal matrix beam search.
The distance metric is global-phase-invariant:
`sqrt(1 - |Tr(U_seq^dagger U_target)|/2)`.

This is a coarse sequence-level smoke test.  It is not Ross--Selinger gridsynth,
not optimal T-count synthesis, not a high-precision compiler, and not hardware mapping.

- target angles: 20
- target selection: top-20 most frequent non-Clifford/non-T-like angles in the verified phase-search outputs
- smoke epsilon: 0.125
- smoke passes: 20/20
- tight epsilon: 0.05
- tight passes: 5/20
- max achieved error among smoke passes: 0.111853
- mean achieved error among smoke passes: 0.081338

| target | angle/pi | support | sequence length | T count | error | smoke pass | sequence |
|---|---:|---:|---:|---:|---:|---:|---|
| freq01-den8-15 | 15/8 | 1155 | 11 | 6 | 0.1119 | yes | `Td H Td H Td H Td H Td H Td` |
| freq02-den8-1 | 1/8 | 1088 | 14 | 8 | 0.1119 | yes | `T H T H T H T H T H T S Td Td` |
| freq03-den32-57 | 57/32 | 1015 | 17 | 9 | 0.0347 | yes | `X Sd X Sd Td Td S Td Td S Td Td S Td Td S Td` |
| freq04-den32-61 | 61/32 | 991 | 0 | 0 | 0.1040 | yes | `I` |
| freq05-den32-19 | 19/32 | 986 | 11 | 6 | 0.1040 | yes | `X Sd Td X Td Td S Td Td S Td` |
| freq06-den32-59 | 59/32 | 905 | 23 | 13 | 0.1040 | yes | `X Sd X Sd Td Td S Td Td S Td Td S Td Td S Td Td S Td Td S Td` |
| freq07-den32-3 | 3/32 | 904 | 18 | 10 | 0.1040 | yes | `X Sd Td X Sd Td Td S Td Td S Td Td S Td Td S Td` |
| freq08-den32-1 | 1/32 | 903 | 5 | 2 | 0.0347 | yes | `X Sd T X Td` |
| freq09-den16-31 | 31/16 | 784 | 0 | 0 | 0.0694 | yes | `I` |
| freq10-den32-63 | 63/32 | 775 | 5 | 2 | 0.0347 | yes | `X S Td X T` |
| freq11-den32-13 | 13/32 | 741 | 10 | 6 | 0.1040 | yes | `X Td X T T Sd T T Sd T` |
| freq12-den32-17 | 17/32 | 730 | 8 | 4 | 0.0347 | yes | `X Sd Td X Td Td S Td` |
| freq13-den16-1 | 1/16 | 729 | 5 | 2 | 0.0694 | yes | `X Sd T X Td` |
| freq14-den32-15 | 15/32 | 726 | 1 | 0 | 0.0347 | yes | `S` |
| freq15-den8-3 | 3/8 | 714 | 12 | 5 | 0.1119 | yes | `T H T H T H T H X Td H Sd` |
| freq16-den16-3 | 3/16 | 714 | 6 | 3 | 0.0694 | yes | `X Sd Td X Td Td` |
| freq17-den16-29 | 29/16 | 706 | 1 | 1 | 0.0694 | yes | `Td` |
| freq18-den32-11 | 11/32 | 680 | 23 | 15 | 0.1040 | yes | `S Td Td S Td Td S Td Td S Td Td S Td Td S Td Td S Td Td S Td` |
| freq19-den32-21 | 21/32 | 664 | 14 | 9 | 0.1040 | yes | `S T T Sd T T Sd T T Sd T T Sd T` |
| freq20-den8-13 | 13/8 | 630 | 12 | 5 | 0.1119 | yes | `H Td H X T H Td H T H S Td` |

## Interpretation

- The 20 target angles are the most frequent non-Clifford/non-T-like angles in the existing phase-search outputs; this is not a synthetic rotation-only benchmark.
- The bounded beam search closes part of the previous evidence gap by emitting actual Clifford+T strings for source-derived Rz targets.
- The coarse tolerance and non-optimal sequences mean the manuscript should still keep the phase/Rz branch as a logical proxy and cite Ross--Selinger only for the precision-sensitivity model.
