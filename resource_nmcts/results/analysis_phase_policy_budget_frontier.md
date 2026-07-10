# Phase Policy Budget-Frontier Audit

This audit quantifies the exact-scoring budget frontier for the held-out n=6 phase/Rz proxy.
Rows compare learned top-k shortlists with the deterministic budget-32 and wide-128 affine searches using the T/Rz=30 synthesis proxy.

| policy | top-k | functions | exact forms/function | eval reduction vs budget-32 | eval reduction vs wide-128 | W/L/T vs budget-32 | mean vs budget-32 | W/L/T vs wide-128 | mean vs wide-128 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Rank | 64 | 38 | 64/2048/8192 | 96.88% | 99.22% | 11/6/21 | -1.405% | 0/13/25 | +1.766% |
| Rank | 128 | 38 | 128/2048/8192 | 93.75% | 98.44% | 14/4/20 | -1.904% | 0/13/25 | +0.943% |
| Rank | 256 | 38 | 256/2048/8192 | 87.50% | 96.88% | 15/3/20 | -2.389% | 0/12/26 | +0.141% |
| Rank | 512 | 38 | 512/2048/8192 | 75.00% | 93.75% | 17/0/21 | -2.397% | 0/9/29 | +0.133% |
| Diverse | 64 | 38 | 64/2048/8192 | 96.88% | 99.22% | 12/6/20 | -1.896% | 0/13/25 | +0.951% |
| Diverse | 128 | 38 | 128/2048/8192 | 93.75% | 98.44% | 15/3/20 | -2.388% | 0/12/26 | +0.143% |
| Diverse | 256 | 38 | 256/2048/8192 | 87.50% | 96.88% | 16/2/20 | -2.469% | 0/9/29 | +0.012% |
| Diverse | 512 | 38 | 512/2048/8192 | 75.00% | 93.75% | 17/0/21 | -2.477% | 0/7/31 | +0.003% |

## Interpretation

- Diverse top-512 exact-scores 512/8192 affine forms per function, a 93.75% reduction relative to wide-128.
- The same row keeps the budget-32 comparison at 17/0/21 with -2.477% mean score change.
- Its mean gap to wide-128 is +0.003%, so this supports learned pruning of a dense phase/Rz candidate space rather than global phase optimality.
- The phase/Rz branch remains a logical proxy; these rows do not synthesize approximate rotation sequences or claim mapped Clifford+T cost.
