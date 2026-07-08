# Boolean Screen Depth-Frontier Policy

Structure-level policy for selecting depth-2, depth-3, or depth-4 Boolean-ring screening.

- train examples: 192
- validation examples: 72
- held-out test examples: 48
- train n: 16,20,24; test n: 28,40
- label objective: score_delta + 0.003*time_delta + 0*ancilla_delta vs depth-2
- parallel workers for data generation: 8
- validation accuracy at best checkpoint: 0.611
- held-out depth accuracy: 0.583
- held-out mean score gap to oracle frontier: +0.38%
- held-out mean runtime vs all-depth frontier evaluation: -71.54%

Oracle depth distribution on held-out test:

- depth2: 14 oracle / 7 predicted
- depth3: 25 oracle / 38 predicted
- depth4: 9 oracle / 3 predicted

Paired score comparisons on held-out test:

| comparison | pairs | score win/loss/tie | mean relative score | mean relative time |
|---|---:|---:|---:|---:|
| frontier policy vs depth-2 screen | 48 | 26/0/22 | -1.47% | +190.57% |
| frontier policy vs depth-3 screen | 48 | 1/0/47 | -0.02% | +1.52% |
| frontier policy vs depth-4 screen | 48 | 0/24/24 | +0.99% | -40.32% |
| frontier policy vs oracle depth-2/3/4 frontier | 48 | 2/6/40 | +0.38% | -71.54% |
