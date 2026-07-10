# Boolean Screen Depth Policy

Structure-level policy for selecting single, depth-1, or depth-2 Boolean-ring screening.

- train examples: 240
- validation examples: 72
- held-out test examples: 48
- train n: 14,16,18; test n: 20
- validation accuracy at best checkpoint: 0.861
- held-out depth accuracy: 0.792
- held-out mean score gap to oracle adaptive: +0.28%
- held-out mean runtime vs all-depth oracle evaluation: -34.71%

Oracle depth distribution on held-out test:

- single: 5 oracle / 0 predicted
- depth1: 4 oracle / 13 predicted
- depth2: 39 oracle / 35 predicted

Paired score comparisons on held-out test:

| comparison | pairs | score win/loss/tie | mean relative score | mean relative time |
|---|---:|---:|---:|---:|
| policy vs single screen | 48 | 42/0/6 | -6.57% | +2224.00% |
| policy vs depth-1 screen | 48 | 34/0/14 | -2.57% | +257.27% |
| policy vs depth-2 screen | 48 | 0/5/43 | +0.28% | -10.85% |
| policy vs oracle adaptive all-depth | 48 | 0/5/43 | +0.28% | -34.71% |
