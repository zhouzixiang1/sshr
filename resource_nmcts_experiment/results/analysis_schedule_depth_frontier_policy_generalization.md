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
