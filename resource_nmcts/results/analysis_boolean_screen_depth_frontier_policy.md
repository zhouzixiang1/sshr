# Boolean Screen Depth-Frontier Policy

Structure-level policy for selecting depth-2, depth-3, or depth-4 Boolean-ring screening.

- train examples: 96
- validation examples: 36
- held-out test examples: 32
- train n: 16,20,24; test n: 28,40
- parallel workers for data generation: 6
- validation accuracy at best checkpoint: 0.750
- held-out depth accuracy: 0.625
- held-out mean score gap to oracle frontier: +0.80%
- held-out mean runtime vs all-depth frontier evaluation: -58.76%

Oracle depth distribution on held-out test:

- depth2: 7 oracle / 19 predicted
- depth3: 4 oracle / 0 predicted
- depth4: 21 oracle / 13 predicted

Paired score comparisons on held-out test:

| comparison | pairs | score win/loss/tie | mean relative score | mean relative time |
|---|---:|---:|---:|---:|
| frontier policy vs depth-2 screen | 32 | 13/0/19 | -1.95% | +455.93% |
| frontier policy vs depth-3 screen | 32 | 13/8/11 | -0.17% | +62.88% |
| frontier policy vs depth-4 screen | 32 | 0/9/23 | +0.80% | -25.99% |
| frontier policy vs oracle depth-2/3/4 frontier | 32 | 0/9/23 | +0.80% | -58.76% |
