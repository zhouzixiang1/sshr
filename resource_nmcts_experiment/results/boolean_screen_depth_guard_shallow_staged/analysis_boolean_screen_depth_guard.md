# Boolean Screen Depth-2 Guard

Conservative structure-level guard for skipping depth-2 Boolean-ring screening.

- train examples: 240
- validation examples: 72
- held-out test examples: 48
- train n: 14,16,18; test n: 20
- feature mode: shallow
- execution mode: staged
- minimum skip threshold: 0.950000
- selected skip threshold: 0.950000
- validation loss at best checkpoint: 0.0037
- validation accuracy at 0.5: 1.000

The guard runs shallow screening and uses depth-1 only when the model predicts that depth-1 ties fixed depth-2 in score. Otherwise it falls back to depth-2.

| split | pairs | skips | false skips | score W/L/T vs depth-2 | mean score vs depth-2 | mean time vs depth-2 | mean time vs all-depth |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 240 | 22 | 0 | 0/0/240 | +0.00% | +25.86% | -4.49% |
| valid | 72 | 3 | 0 | 0/0/72 | +0.00% | +26.63% | -1.60% |
| test | 48 | 8 | 0 | 0/0/48 | +0.00% | +29.10% | -7.81% |
