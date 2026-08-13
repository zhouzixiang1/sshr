# Logic-Level Schedule Proxy Analysis

These metrics are computed from emitted X/CNOT/MCT oracle circuits without
hardware mapping. They are backend-relevant logic-level proxies: parallel
logical depth, CNOT-depth proxy, T-depth proxy, explicit live-ancilla peak,
and explicit ancilla lifetime area.

| dataset | method | baseline | metric | items | W/L/T | mean relative |
|---|---|---|---|---:|---:|---:|
| schedule_generalization | adaptive_all_depth | screen_depth2 | Score | 96 | 58/0/38 | -2.44% |
| schedule_generalization | adaptive_all_depth | screen_depth2 | parallel logical depth | 96 | 15/42/39 | +0.97% |
| schedule_generalization | adaptive_all_depth | screen_depth2 | CNOT-depth proxy | 96 | 58/0/38 | -2.16% |
| schedule_generalization | adaptive_all_depth | screen_depth2 | T-depth proxy | 96 | 58/0/38 | -2.37% |
| schedule_generalization | adaptive_all_depth | screen_depth2 | explicit live ancilla peak | 96 | 1/0/95 | -0.52% |
| schedule_generalization | adaptive_all_depth | screen_depth2 | explicit ancilla lifetime area | 96 | 0/58/38 | +27.81% |
| schedule_generalization | adaptive_all_depth | screen_depth2 | peak ancilla | 96 | 0/5/91 | +0.93% |
| schedule_generalization | depth2_guard_direct | screen_depth2 | Score | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth2_guard_direct | screen_depth2 | parallel logical depth | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth2_guard_direct | screen_depth2 | CNOT-depth proxy | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth2_guard_direct | screen_depth2 | T-depth proxy | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth2_guard_direct | screen_depth2 | explicit live ancilla peak | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth2_guard_direct | screen_depth2 | explicit ancilla lifetime area | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth2_guard_direct | screen_depth2 | peak ancilla | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth_frontier_policy | adaptive_all_depth | Score | 96 | 0/19/77 | +0.61% |
| schedule_generalization | depth_frontier_policy | adaptive_all_depth | parallel logical depth | 96 | 18/1/77 | -0.66% |
| schedule_generalization | depth_frontier_policy | adaptive_all_depth | CNOT-depth proxy | 96 | 0/19/77 | +0.55% |
| schedule_generalization | depth_frontier_policy | adaptive_all_depth | T-depth proxy | 96 | 0/19/77 | +0.55% |
| schedule_generalization | depth_frontier_policy | adaptive_all_depth | explicit live ancilla peak | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth_frontier_policy | adaptive_all_depth | explicit ancilla lifetime area | 96 | 19/0/77 | -5.42% |
| schedule_generalization | depth_frontier_policy | adaptive_all_depth | peak ancilla | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth_frontier_policy | screen_depth2 | Score | 96 | 40/0/56 | -1.85% |
| schedule_generalization | depth_frontier_policy | screen_depth2 | parallel logical depth | 96 | 14/25/57 | +0.28% |
| schedule_generalization | depth_frontier_policy | screen_depth2 | CNOT-depth proxy | 96 | 40/0/56 | -1.63% |
| schedule_generalization | depth_frontier_policy | screen_depth2 | T-depth proxy | 96 | 40/0/56 | -1.85% |
| schedule_generalization | depth_frontier_policy | screen_depth2 | explicit live ancilla peak | 96 | 1/0/95 | -0.52% |
| schedule_generalization | depth_frontier_policy | screen_depth2 | explicit ancilla lifetime area | 96 | 0/40/56 | +20.09% |
| schedule_generalization | depth_frontier_policy | screen_depth2 | peak ancilla | 96 | 0/5/91 | +0.93% |
| schedule_generalization | depth_frontier_policy | screen_depth4 | Score | 96 | 0/19/77 | +0.61% |
| schedule_generalization | depth_frontier_policy | screen_depth4 | parallel logical depth | 96 | 18/1/77 | -0.66% |
| schedule_generalization | depth_frontier_policy | screen_depth4 | CNOT-depth proxy | 96 | 0/19/77 | +0.55% |
| schedule_generalization | depth_frontier_policy | screen_depth4 | T-depth proxy | 96 | 0/19/77 | +0.55% |
| schedule_generalization | depth_frontier_policy | screen_depth4 | explicit live ancilla peak | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth_frontier_policy | screen_depth4 | explicit ancilla lifetime area | 96 | 19/0/77 | -5.42% |
| schedule_generalization | depth_frontier_policy | screen_depth4 | peak ancilla | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth_policy | screen_depth2 | Score | 96 | 0/1/95 | +0.03% |
| schedule_generalization | depth_policy | screen_depth2 | parallel logical depth | 96 | 1/0/95 | -0.03% |
| schedule_generalization | depth_policy | screen_depth2 | CNOT-depth proxy | 96 | 0/1/95 | +0.03% |
| schedule_generalization | depth_policy | screen_depth2 | T-depth proxy | 96 | 0/1/95 | +0.03% |
| schedule_generalization | depth_policy | screen_depth2 | explicit live ancilla peak | 96 | 0/0/96 | +0.00% |
| schedule_generalization | depth_policy | screen_depth2 | explicit ancilla lifetime area | 96 | 1/0/95 | -0.28% |
| schedule_generalization | depth_policy | screen_depth2 | peak ancilla | 96 | 0/0/96 | +0.00% |
| schedule_generalization | screen_depth3 | screen_depth2 | Score | 96 | 58/0/38 | -1.42% |
| schedule_generalization | screen_depth3 | screen_depth2 | parallel logical depth | 96 | 13/35/48 | +0.48% |
| schedule_generalization | screen_depth3 | screen_depth2 | CNOT-depth proxy | 96 | 58/0/38 | -1.25% |
| schedule_generalization | screen_depth3 | screen_depth2 | T-depth proxy | 96 | 58/0/38 | -1.38% |
| schedule_generalization | screen_depth3 | screen_depth2 | explicit live ancilla peak | 96 | 1/0/95 | -0.52% |
| schedule_generalization | screen_depth3 | screen_depth2 | explicit ancilla lifetime area | 96 | 0/58/38 | +15.07% |
| schedule_generalization | screen_depth3 | screen_depth2 | peak ancilla | 96 | 1/3/92 | +0.35% |
| schedule_generalization | screen_depth4 | screen_depth2 | Score | 96 | 58/0/38 | -2.44% |
| schedule_generalization | screen_depth4 | screen_depth2 | parallel logical depth | 96 | 15/42/39 | +0.97% |
| schedule_generalization | screen_depth4 | screen_depth2 | CNOT-depth proxy | 96 | 58/0/38 | -2.16% |
| schedule_generalization | screen_depth4 | screen_depth2 | T-depth proxy | 96 | 58/0/38 | -2.37% |
| schedule_generalization | screen_depth4 | screen_depth2 | explicit live ancilla peak | 96 | 1/0/95 | -0.52% |
| schedule_generalization | screen_depth4 | screen_depth2 | explicit ancilla lifetime area | 96 | 0/58/38 | +27.81% |
| schedule_generalization | screen_depth4 | screen_depth2 | peak ancilla | 96 | 0/5/91 | +0.93% |
| schedule_truth_bridge | adaptive_all_depth | screen_depth2 | Score | 12 | 10/0/2 | -3.81% |
| schedule_truth_bridge | adaptive_all_depth | screen_depth2 | parallel logical depth | 12 | 5/4/3 | +0.78% |
| schedule_truth_bridge | adaptive_all_depth | screen_depth2 | CNOT-depth proxy | 12 | 10/0/2 | -3.61% |
| schedule_truth_bridge | adaptive_all_depth | screen_depth2 | T-depth proxy | 12 | 10/0/2 | -3.63% |
| schedule_truth_bridge | adaptive_all_depth | screen_depth2 | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | adaptive_all_depth | screen_depth2 | explicit ancilla lifetime area | 12 | 0/10/2 | +38.31% |
| schedule_truth_bridge | adaptive_all_depth | screen_depth2 | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth2_guard_direct | screen_depth2 | Score | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth2_guard_direct | screen_depth2 | parallel logical depth | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth2_guard_direct | screen_depth2 | CNOT-depth proxy | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth2_guard_direct | screen_depth2 | T-depth proxy | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth2_guard_direct | screen_depth2 | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth2_guard_direct | screen_depth2 | explicit ancilla lifetime area | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth2_guard_direct | screen_depth2 | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_frontier_policy | adaptive_all_depth | Score | 12 | 0/2/10 | +0.32% |
| schedule_truth_bridge | depth_frontier_policy | adaptive_all_depth | parallel logical depth | 12 | 2/0/10 | -0.73% |
| schedule_truth_bridge | depth_frontier_policy | adaptive_all_depth | CNOT-depth proxy | 12 | 0/2/10 | +0.36% |
| schedule_truth_bridge | depth_frontier_policy | adaptive_all_depth | T-depth proxy | 12 | 0/2/10 | +0.32% |
| schedule_truth_bridge | depth_frontier_policy | adaptive_all_depth | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_frontier_policy | adaptive_all_depth | explicit ancilla lifetime area | 12 | 2/0/10 | -4.01% |
| schedule_truth_bridge | depth_frontier_policy | adaptive_all_depth | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth2 | Score | 12 | 8/0/4 | -3.50% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth2 | parallel logical depth | 12 | 5/2/5 | +0.02% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth2 | CNOT-depth proxy | 12 | 8/0/4 | -3.26% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth2 | T-depth proxy | 12 | 8/0/4 | -3.32% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth2 | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth2 | explicit ancilla lifetime area | 12 | 0/8/4 | +32.93% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth2 | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth4 | Score | 12 | 0/2/10 | +0.32% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth4 | parallel logical depth | 12 | 2/0/10 | -0.73% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth4 | CNOT-depth proxy | 12 | 0/2/10 | +0.36% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth4 | T-depth proxy | 12 | 0/2/10 | +0.32% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth4 | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth4 | explicit ancilla lifetime area | 12 | 2/0/10 | -4.01% |
| schedule_truth_bridge | depth_frontier_policy | screen_depth4 | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_policy | screen_depth2 | Score | 12 | 0/1/11 | +0.24% |
| schedule_truth_bridge | depth_policy | screen_depth2 | parallel logical depth | 12 | 1/0/11 | -0.54% |
| schedule_truth_bridge | depth_policy | screen_depth2 | CNOT-depth proxy | 12 | 0/1/11 | +0.22% |
| schedule_truth_bridge | depth_policy | screen_depth2 | T-depth proxy | 12 | 0/1/11 | +0.22% |
| schedule_truth_bridge | depth_policy | screen_depth2 | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | depth_policy | screen_depth2 | explicit ancilla lifetime area | 12 | 1/0/11 | -2.78% |
| schedule_truth_bridge | depth_policy | screen_depth2 | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | screen_depth3 | screen_depth2 | Score | 12 | 10/0/2 | -2.33% |
| schedule_truth_bridge | screen_depth3 | screen_depth2 | parallel logical depth | 12 | 4/4/4 | +0.55% |
| schedule_truth_bridge | screen_depth3 | screen_depth2 | CNOT-depth proxy | 12 | 10/0/2 | -2.18% |
| schedule_truth_bridge | screen_depth3 | screen_depth2 | T-depth proxy | 12 | 10/0/2 | -2.26% |
| schedule_truth_bridge | screen_depth3 | screen_depth2 | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | screen_depth3 | screen_depth2 | explicit ancilla lifetime area | 12 | 0/10/2 | +22.02% |
| schedule_truth_bridge | screen_depth3 | screen_depth2 | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | screen_depth4 | screen_depth2 | Score | 12 | 10/0/2 | -3.81% |
| schedule_truth_bridge | screen_depth4 | screen_depth2 | parallel logical depth | 12 | 5/4/3 | +0.78% |
| schedule_truth_bridge | screen_depth4 | screen_depth2 | CNOT-depth proxy | 12 | 10/0/2 | -3.61% |
| schedule_truth_bridge | screen_depth4 | screen_depth2 | T-depth proxy | 12 | 10/0/2 | -3.63% |
| schedule_truth_bridge | screen_depth4 | screen_depth2 | explicit live ancilla peak | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge | screen_depth4 | screen_depth2 | explicit ancilla lifetime area | 12 | 0/10/2 | +38.31% |
| schedule_truth_bridge | screen_depth4 | screen_depth2 | peak ancilla | 12 | 0/0/12 | +0.00% |
| schedule_truth_bridge_n23 | adaptive_all_depth | screen_depth2 | Score | 6 | 5/0/1 | -2.47% |
| schedule_truth_bridge_n23 | adaptive_all_depth | screen_depth2 | parallel logical depth | 6 | 0/5/1 | +2.90% |
| schedule_truth_bridge_n23 | adaptive_all_depth | screen_depth2 | CNOT-depth proxy | 6 | 5/0/1 | -2.15% |
| schedule_truth_bridge_n23 | adaptive_all_depth | screen_depth2 | T-depth proxy | 6 | 5/0/1 | -2.20% |
| schedule_truth_bridge_n23 | adaptive_all_depth | screen_depth2 | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | adaptive_all_depth | screen_depth2 | explicit ancilla lifetime area | 6 | 0/5/1 | +36.83% |
| schedule_truth_bridge_n23 | adaptive_all_depth | screen_depth2 | peak ancilla | 6 | 0/1/5 | +2.78% |
| schedule_truth_bridge_n23 | depth2_guard_direct | screen_depth2 | Score | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth2_guard_direct | screen_depth2 | parallel logical depth | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth2_guard_direct | screen_depth2 | CNOT-depth proxy | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth2_guard_direct | screen_depth2 | T-depth proxy | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth2_guard_direct | screen_depth2 | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth2_guard_direct | screen_depth2 | explicit ancilla lifetime area | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth2_guard_direct | screen_depth2 | peak ancilla | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_frontier_policy | adaptive_all_depth | Score | 6 | 0/1/5 | +0.61% |
| schedule_truth_bridge_n23 | depth_frontier_policy | adaptive_all_depth | parallel logical depth | 6 | 1/0/5 | -1.28% |
| schedule_truth_bridge_n23 | depth_frontier_policy | adaptive_all_depth | CNOT-depth proxy | 6 | 0/1/5 | +0.41% |
| schedule_truth_bridge_n23 | depth_frontier_policy | adaptive_all_depth | T-depth proxy | 6 | 0/1/5 | +0.52% |
| schedule_truth_bridge_n23 | depth_frontier_policy | adaptive_all_depth | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_frontier_policy | adaptive_all_depth | explicit ancilla lifetime area | 6 | 1/0/5 | -5.09% |
| schedule_truth_bridge_n23 | depth_frontier_policy | adaptive_all_depth | peak ancilla | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth2 | Score | 6 | 4/0/2 | -1.88% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth2 | parallel logical depth | 6 | 0/4/2 | +1.51% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth2 | CNOT-depth proxy | 6 | 4/0/2 | -1.75% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth2 | T-depth proxy | 6 | 4/0/2 | -1.69% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth2 | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth2 | explicit ancilla lifetime area | 6 | 0/4/2 | +29.49% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth2 | peak ancilla | 6 | 0/1/5 | +2.78% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth4 | Score | 6 | 0/1/5 | +0.61% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth4 | parallel logical depth | 6 | 1/0/5 | -1.28% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth4 | CNOT-depth proxy | 6 | 0/1/5 | +0.41% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth4 | T-depth proxy | 6 | 0/1/5 | +0.52% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth4 | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth4 | explicit ancilla lifetime area | 6 | 1/0/5 | -5.09% |
| schedule_truth_bridge_n23 | depth_frontier_policy | screen_depth4 | peak ancilla | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_policy | screen_depth2 | Score | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_policy | screen_depth2 | parallel logical depth | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_policy | screen_depth2 | CNOT-depth proxy | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_policy | screen_depth2 | T-depth proxy | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_policy | screen_depth2 | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_policy | screen_depth2 | explicit ancilla lifetime area | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | depth_policy | screen_depth2 | peak ancilla | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | screen_depth3 | screen_depth2 | Score | 6 | 5/0/1 | -1.94% |
| schedule_truth_bridge_n23 | screen_depth3 | screen_depth2 | parallel logical depth | 6 | 0/5/1 | +1.03% |
| schedule_truth_bridge_n23 | screen_depth3 | screen_depth2 | CNOT-depth proxy | 6 | 5/0/1 | -1.70% |
| schedule_truth_bridge_n23 | screen_depth3 | screen_depth2 | T-depth proxy | 6 | 5/0/1 | -1.88% |
| schedule_truth_bridge_n23 | screen_depth3 | screen_depth2 | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | screen_depth3 | screen_depth2 | explicit ancilla lifetime area | 6 | 0/5/1 | +19.95% |
| schedule_truth_bridge_n23 | screen_depth3 | screen_depth2 | peak ancilla | 6 | 0/1/5 | +2.78% |
| schedule_truth_bridge_n23 | screen_depth4 | screen_depth2 | Score | 6 | 5/0/1 | -2.47% |
| schedule_truth_bridge_n23 | screen_depth4 | screen_depth2 | parallel logical depth | 6 | 0/5/1 | +2.90% |
| schedule_truth_bridge_n23 | screen_depth4 | screen_depth2 | CNOT-depth proxy | 6 | 5/0/1 | -2.15% |
| schedule_truth_bridge_n23 | screen_depth4 | screen_depth2 | T-depth proxy | 6 | 5/0/1 | -2.20% |
| schedule_truth_bridge_n23 | screen_depth4 | screen_depth2 | explicit live ancilla peak | 6 | 0/0/6 | +0.00% |
| schedule_truth_bridge_n23 | screen_depth4 | screen_depth2 | explicit ancilla lifetime area | 6 | 0/5/1 | +36.83% |
| schedule_truth_bridge_n23 | screen_depth4 | screen_depth2 | peak ancilla | 6 | 0/1/5 | +2.78% |
