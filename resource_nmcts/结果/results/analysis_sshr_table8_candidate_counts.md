# SSHR Table VIII Candidate-Count Reproduction

This report reruns the local SSHR parallelotope enumerator on full n=3..8 hypercubes and compares the resulting candidate-space sizes with the Table VIII reference counts.

- rows: 6
- matching rows: 6/6
- status: pass

| n | ESOP terms | SSHR candidates | Reference | Factor | Match |
|---|---:|---:|---:|---:|---|
| 3 | 27 | 49 | 49 | 1.8x | yes |
| 4 | 81 | 257 | 257 | 3.2x | yes |
| 5 | 243 | 1539 | 1539 | 6.3x | yes |
| 6 | 729 | 10299 | 10299 | 14.1x | yes |
| 7 | 2187 | 75905 | 75905 | 34.7x | yes |
| 8 | 6561 | 609441 | 609441 | 92.9x | yes |

The reproduction supports only the SSHR search-space anchor used in the comparison discussion.  It does not rerun SSHR-I Gurobi tables or every random benchmark from the SSHR paper.
