# Large Depth-Frontier Policy Upgrade

This analysis compares the original depth-frontier policy with a larger
retraining and a cost-aware variant of the same structure-level neural
policy.  Each policy still selects one of depth-2, depth-3, or depth-4
Boolean-ring screening; the changes are more labelled frontier data, a
larger hidden layer, or a cost-aware label objective.

## Verification

- old scale: rows 960, plan 960/960, circuit 960/960
- large-policy scale: rows 960, plan 960/960, circuit 960/960
- cost-aware scale: rows 960, plan 960/960, circuit 960/960
- old n=23 bridge: rows 60, truth 60/60, plan 60/60, circuit 60/60
- large-policy n=23 bridge: rows 60, truth 60/60, plan 60/60, circuit 60/60
- cost-aware n=23 bridge: rows 60, truth 60/60, plan 60/60, circuit 60/60

## Comparisons

| source | comparison | pairs | score W/L/T | score | time | T-depth | aux area |
|---|---|---:|---:|---:|---:|---:|---:|
| heldout_training | old heldout policy vs oracle frontier | 32 | 0/9/23 | +0.80% | -58.76% |  |  |
| heldout_training | large heldout policy vs oracle frontier | 48 | 0/3/45 | +0.04% | -51.30% |  |  |
| heldout_training | cost heldout policy vs cost-aware frontier | 48 | 0/6/40 | +0.38% | -71.54% |  |  |
| scale_generalization | large scale policy vs screen_depth2 | 96 | 56/0/40 | -2.34% | +563.80% | -2.28% | +26.13% |
| scale_generalization | old scale policy vs screen_depth2 | 96 | 40/0/56 | -1.85% | +456.43% |  |  |
| scale_generalization | cost scale policy vs screen_depth2 | 96 | 56/0/40 | -1.39% | +170.03% | -1.36% | +14.63% |
| scale_generalization | large scale policy vs adaptive_all_depth | 96 | 0/6/90 | +0.10% | -53.50% | +0.10% | -1.17% |
| scale_generalization | old scale policy vs adaptive_all_depth | 96 | 0/19/77 | +0.61% | -61.25% |  |  |
| scale_generalization | cost scale policy vs adaptive_all_depth | 96 | 0/53/43 | +1.10% | -76.54% | +1.06% | -8.86% |
| scale_generalization | large scale policy vs old policy | 96 | 17/0/79 | -0.49% | +119.26% |  |  |
| scale_generalization | cost scale policy vs old policy | 96 | 16/39/41 | +0.50% | +25.36% |  |  |
| scale_generalization | cost scale policy vs large policy | 96 | 1/48/47 | +0.99% | -33.02% | +0.97% | -7.61% |
| truth_bridge_n23 | large n23 policy vs screen_depth2 | 6 | 5/0/1 | -2.36% | +790.62% | -2.14% | +33.49% |
| truth_bridge_n23 | old n23 policy vs screen_depth2 | 6 | 4/0/2 | -1.88% | +759.95% | -1.69% | +29.49% |
| truth_bridge_n23 | cost n23 policy vs screen_depth2 | 6 | 4/0/2 | -1.46% | +196.09% | -1.43% | +15.95% |
| truth_bridge_n23 | large n23 policy vs adaptive_all_depth | 6 | 0/1/5 | +0.12% | -45.99% | +0.07% | -2.31% |
| truth_bridge_n23 | old n23 policy vs adaptive_all_depth | 6 | 0/1/5 | +0.61% | -48.77% | +0.52% | -5.09% |
| truth_bridge_n23 | cost n23 policy vs adaptive_all_depth | 6 | 0/5/1 | +1.04% | -80.46% | +0.79% | -14.48% |
| truth_bridge_n23 | large n23 policy vs old policy | 6 | 1/0/5 | -0.48% | +46.16% | -0.45% | +4.00% |
| truth_bridge_n23 | cost n23 policy vs old policy | 6 | 0/4/2 | +0.43% | -44.07% | +0.27% | -9.39% |
| truth_bridge_n23 | cost n23 policy vs large policy | 6 | 0/5/1 | +0.92% | -56.29% | +0.73% | -12.62% |

## Interpretation

- The large retraining is a quality-oriented upgrade: it chooses deeper
  screens more often, so it is slower than the original frontier policy.
- On the independent n=24/28/32/40 term-set generalization run, it improves
  the frontier-policy score against the old model by 17/0/79 with a
  -0.49% mean score change, while still saving 53.50% time against
  all-depth adaptive evaluation.
- On the n=23 full truth-table bridge, it improves the old frontier policy
  by 1/0/5 with -0.48% score and -0.45% T-depth proxy, with all 60
  method rows passing truth-table, plan, and emitted-circuit verification.
- The cost-aware retraining is a faster quality mode.  On the same
  independent n=24/28/32/40 generalization run, it keeps the 56/0/40
  score W/L/T pattern against fixed depth-2, but lowers mean plan-time
  overhead from the large model's +563.80% to +170.03%.  On the n=23
  bridge, it reduces plan time by -56.29% and auxiliary lifetime area
  by -12.62% relative to the large model, at a +0.92% score cost.
