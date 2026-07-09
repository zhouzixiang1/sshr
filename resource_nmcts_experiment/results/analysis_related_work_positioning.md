# Related-Work Positioning Matrix

This matrix records how each literature family is used in the manuscript argument.

| line | representative work | main lever | paper use |
|---|---|---|---|
| BDD-based reversible synthesis | BDD reversible synthesis | Symbolic decision-diagram representation for large Boolean functions. | Used as a representation-level baseline family, not as the proposed search space. |
| LUT/ROS-style oracle synthesis | ROS, STG benchmarks, and back-end-aware oracle synthesis | Resource-aware LUT mapping, small-function optimum libraries, and downstream implementation-cost estimates. | Used through a verified ROS-style LUT proxy, line-aware reselection stress tests, and a published STG counterpoint. |
| Recent oracle-resource and Boolean-encoding work | HRSE/ASDT oracle modeling, ESOP SAT oracles, and T-depth Boolean-circuit constructions | Improves oracle resource modeling, application-level Boolean encodings, or analytic T-depth bounds. | Used as recent adjacent oracle-resource context, not as direct experimental baselines. |
| XAG and multiplicative complexity | XAG compilation and multiplicative-complexity oracle cost | Separates XOR-linear structure from AND nodes as a non-Clifford proxy. | Used through ABC, mockturtle, and CirKit probes plus exact small XAG lower-bound checks. |
| Logic and reversible toolchains | ABC, EPFL libraries, RevKit, mockturtle, Caterpillar, and CirKit | Mature optimization passes and reversible-synthesis flows. | Used as external probes, API-level implementation-family checks, and exact-oracle reversible-synthesis comparisons. |
| SSHR geometric synthesis | Parallelotope-based CNOT-oriented synthesis | Small-scale Boolean hypercube geometry targeting CNOT-oriented covers. | Used as a CNOT-oriented small-function baseline; not used by the proposed method. |
| Learning-guided circuit synthesis | AlphaZero, diffusion, reinforcement learning, supervised search, MCTS, and ZX-guided synthesis | Learns or searches over circuit-design, unitary-synthesis, block-resynthesis, and circuit-transformation actions. | Motivates neural/MCTS control while keeping actions verifiable at the Boolean-algebraic oracle layer. |
