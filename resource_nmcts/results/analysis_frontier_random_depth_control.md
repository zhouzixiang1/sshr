# Frontier Random-Depth Control

This audit compares the large Boolean-ring depth-frontier policy with same-candidate random choices among depth 2, 3, and 4.
No synthesis is rerun: all comparisons reuse already verified depth candidates in the raw frontier files.

## Status counts

- pass: 3

| source | scope | pairs | W/L/T vs random mean | mean score change | mean time change | T-depth change | aux-area change | seed means beaten | sign p |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| held-out frontier policy | test n=28,40 | 48 | 24/1/23 | -0.78% | +59.14% |  |  | 8/8 | 7.748603821e-07 |
| scale generalization | n=24,28,32,40 | 96 | 55/3/38 | -1.12% | +58.78% | -1.10% | +9.92% | 8/8 | 1.129929483e-13 |
| truth-table bridge | n=23 | 6 | 5/0/1 | -0.89% | +71.00% | -0.79% | +11.44% | 8/8 | 0.03125 |

## Interpretation

- The learned frontier policy beats same-candidate random depth selection on score in held-out training, independent n=24/28/32/40 scale rows, and the n=23 truth-table bridge.
- The policy is quality-oriented: it often chooses deeper screens and therefore spends more planning time than random depth selection.
- The control supports learned budget allocation within the Boolean-ring frontier, not hardware scheduling or global optimality.
