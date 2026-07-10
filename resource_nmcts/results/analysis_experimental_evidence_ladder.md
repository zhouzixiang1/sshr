# Experimental Evidence Ladder

This audit ranks the experiment package by verification strength and claim use.  It is derived from existing benchmark-suite summaries and manifests.

## Status counts

- pass: 8

## Aggregate ladder coverage

- experiment raw rows represented: 39849
- experiment verified rows represented: 39368

| level | role | n scope | instances | raw rows | verified rows | verification strength | claim use | boundary | status |
|---|---|---:|---:|---:|---:|---|---|---|---|
| 1. Exact same-task core | Headline bit-flip oracle comparison | n=3--6 | 177 | 3819 | 3819 | complete truth-table checks | Primary paired T-count and weighted-score claim over same-function baselines. | Small n is fair and exact, but not a large-n optimality certificate. | pass |
| 2. Small optimum counterpoint | Negative control against precomputed public optima | n=4--5 | 54 | 270 | 270 | public truth tables with exact small-function checks | Shows that the paper does not hide stronger tiny-function optimum rows. | Counterpoint evidence only; it is not a headline victory over optimum libraries. | pass |
| 3. External toolchain stress | Independent Boolean-network and LUT/XAG/AIG pressure | n=3--18 | 373 | 968 | 968 | export/readback and logic-network checks | Checks that the resource story is not only against local hand-written baselines. | Proxy logical-tool evidence, not a full reversible or hardware-mapped reproduction. | pass |
| 4. Reversible and phase boundary | Exact reversible and phase/Rz transfer counterpoint | n=3--6 | 181 | 10286 | 10109 | permutation checks, phase checks up to global phase, smoke sequence checks | Separates reversible/phase transfer evidence from the main bit-flip result. | Not a final approximate Clifford+T rotation-synthesis comparison. | pass |
| 5. Complete high-n semantic bridge | Large-n semantic bridge | n=21--30 | 60 | 880 | 880 | complete truth-table construction and emitted-circuit checks | Connects symbolic large-instance plans to exact semantic checks up to n=30 generated functions. | Deliberately narrow because full truth tables grow exponentially. | pass |
| 6. Ultra-scale symbolic stress | Scalability and resource-profile stress test | n=20--64 | 384 | 7392 | 7392 | symbolic ANF and emitted-circuit ANF checks | Shows the bounded search and emitter still run on generated n=20--64 logical instances. | Symbolic verification is not exhaustive high-dimensional truth-table enumeration. | pass |
| 7. AI/search-control attribution | Neural/MCTS causal and stability evidence | n=3--40 | 385 | 16234 | 15930 | same-budget controls, held-out splits, independent seeds, semantic checks | Separates learned ranking, frontier policies, guards, and MCTS controls from representation effects. | Does not claim deep learning alone causes the full resource reduction. | pass |
| 8. Manuscript integration | Experimental-strength ladder is visible in all submission variants | not applicable | 0 | 0 | 0 | source anchor check | Places benchmark scale, semantic strength, and boundaries before result tables. | Integration evidence is not a new experiment. | pass |

## Source suites

- **1. Exact same-task core**: Matched small Boolean oracles; compute note: `none`
- **2. Small optimum counterpoint**: Published tiny-function optimum counterpoint; compute note: `none`
- **3. External toolchain stress**: External logic-network probes; compute note: `none`
- **4. Reversible and phase boundary**: RevKit reversible and phase probes; compute note: `none`
- **5. Complete high-n semantic bridge**: Complete truth-table bridge slices; compute note: `none`
- **6. Ultra-scale symbolic stress**: Large symbolic term-set scaling; compute note: `ultra_profile_raw_rows=480; n_values=48,56,64; plan_verified=480; circuit_verified=480`
- **7. AI/search-control attribution**: Learned-control and stochastic controls; compute note: `runtime_envelope_rows=5; runtime_status={'pass': 5}`
- **8. Manuscript integration**: none; compute note: `none`
