# Related-Work Positioning Matrix

This matrix records how each literature family is used in the manuscript argument.

| line | representative work | main lever | paper use |
|---|---|---|---|
| BDD-based reversible synthesis | BDD reversible synthesis | Symbolic decision-diagram representation for large Boolean functions. | Used as a representation-level baseline family, not as the proposed search space. |
| LUT/ROS-style oracle synthesis | ROS and back-end-aware oracle synthesis | Resource-aware LUT mapping and downstream implementation-cost estimates. | Reproduced through a verified ROS-style LUT proxy and line-aware reselection stress tests. |
| XAG and multiplicative complexity | XAG compilation and multiplicative-complexity oracle cost | Separates XOR-linear structure from AND nodes as a non-Clifford proxy. | Used through ABC, mockturtle, and CirKit probes plus exact small XAG lower-bound checks. |
| Logic and reversible toolchains | ABC, EPFL libraries, RevKit, mockturtle, and CirKit | Mature optimization passes and reversible-synthesis flows. | Used as external probes and exact-oracle reversible-synthesis comparisons. |
| SSHR geometric synthesis | Parallelotope-based CNOT-oriented synthesis | Small-scale Boolean hypercube geometry targeting CNOT-oriented covers. | Used as a CNOT-oriented small-function baseline; not used by the proposed method. |
| Learning-guided circuit synthesis | AlphaZero, reinforcement learning, MCTS, and ZX-guided synthesis | Learns or searches over circuit-design and circuit-transformation actions. | Motivates neural/MCTS control while keeping actions verifiable at the Boolean-algebraic oracle layer. |
