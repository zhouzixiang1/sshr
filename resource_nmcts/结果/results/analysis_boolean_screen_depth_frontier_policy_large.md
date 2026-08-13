# Boolean Screen Depth-Frontier Policy

Structure-level policy for selecting depth-2, depth-3, or depth-4 Boolean-ring screening.

- train examples: 192
- validation examples: 72
- held-out test examples: 48
- train n: 16,20,24; test n: 28,40
- parallel workers for data generation: 8
- validation accuracy at best checkpoint: 0.778
- held-out depth accuracy: 0.667
- held-out mean score gap to oracle frontier: +0.04%
- held-out mean runtime vs all-depth frontier evaluation: -51.30%

Oracle depth distribution on held-out test:

- depth2: 12 oracle / 8 predicted
- depth3: 9 oracle / 18 predicted
- depth4: 27 oracle / 22 predicted

Paired score comparisons on held-out test:

| comparison | pairs | score win/loss/tie | mean relative score | mean relative time |
|---|---:|---:|---:|---:|
| frontier policy vs depth-2 screen | 48 | 24/0/24 | -1.69% | +493.26% |
| frontier policy vs depth-3 screen | 48 | 20/1/27 | -0.65% | +83.41% |
| frontier policy vs depth-4 screen | 48 | 0/3/45 | +0.04% | -8.38% |
| frontier policy vs oracle depth-2/3/4 frontier | 48 | 0/3/45 | +0.04% | -51.30% |
