# Boolean Screen Depth-2 Guard

Conservative structure-level guard for skipping depth-2 Boolean-ring screening.

- train examples: 480
- validation examples: 144
- held-out test examples: 96
- train n: 14,16,18; test n: 20
- feature mode: static
- execution mode: direct
- minimum skip threshold: 0.000000
- selected skip threshold: 0.987388
- validation loss at best checkpoint: 0.2614
- validation accuracy at 0.5: 0.903

The guard uses only static ANF features to dispatch directly to depth-1 when the model predicts that depth-1 ties fixed depth-2 in score; otherwise it runs depth-2 directly.

| split | pairs | skips | false skips | score W/L/T vs depth-2 | mean score vs depth-2 | mean time vs depth-2 | mean time vs all-depth |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 480 | 12 | 0 | 0/0/480 | +0.00% | -0.16% | -23.62% |
| valid | 144 | 3 | 0 | 0/0/144 | +0.00% | -0.28% | -23.45% |
| test | 96 | 4 | 0 | 0/0/96 | +0.00% | -0.54% | -24.74% |
