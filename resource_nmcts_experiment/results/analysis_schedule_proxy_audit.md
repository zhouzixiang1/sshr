# Schedule Proxy Audit

This compact audit promotes the logic-level schedule metrics that are most relevant to a resource-constrained claim.
All metrics are computed before hardware mapping. Lower score, T-depth proxy, and explicit auxiliary lifetime area are better.

## Status counts

- pass: 8

## Focus rows

| evidence slice | comparison | status | items | score W/L/T; mean | T-depth W/L/T; mean | aux lifetime W/L/T; mean | boundary |
|---|---|---|---:|---:|---:|---:|---|
| n=24,28,32,40 scale | depth_frontier_policy vs screen_depth2 | pass | 96 | 40/0/56; -1.85% | 40/0/56; -1.85% | 0/40/56; +20.09% | quality gain with more auxiliary lifetime |
| n=24,28,32,40 scale | depth_frontier_policy vs adaptive_all_depth | pass | 96 | 0/19/77; +0.61% | 0/19/77; +0.55% | 19/0/77; -5.42% | near-ceiling quality with lower lifetime |
| n=21,22 bridge | depth_frontier_policy vs screen_depth2 | pass | 12 | 8/0/4; -3.50% | 8/0/4; -3.32% | 0/8/4; +32.93% | truth-checked quality gain with lifetime cost |
| n=21,22 bridge | depth_frontier_policy vs adaptive_all_depth | pass | 12 | 0/2/10; +0.32% | 0/2/10; +0.32% | 2/0/10; -4.01% | small score gap with lower lifetime |
| n=23 bridge | depth_frontier_policy vs screen_depth2 | pass | 6 | 4/0/2; -1.88% | 4/0/2; -1.69% | 0/4/2; +29.49% | quality gain with lifetime cost |
| n=23 bridge | depth_frontier_policy vs adaptive_all_depth | pass | 6 | 0/1/5; +0.61% | 0/1/5; +0.52% | 1/0/5; -5.09% | small score gap with lower lifetime |
| n=24,28,32,40 scale | adaptive_all_depth vs screen_depth2 | pass | 96 | 58/0/38; -2.44% | 58/0/38; -2.37% | 0/58/38; +27.81% | quality ceiling increases lifetime |
| n=23 bridge | adaptive_all_depth vs screen_depth2 | pass | 6 | 5/0/1; -2.47% | 5/0/1; -2.20% | 0/5/1; +36.83% | truth-checked ceiling increases lifetime |
