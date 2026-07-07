# Literature Notes

## Closest Boolean oracle synthesis baselines

- Meuli, Soeken, and De Micheli, "Xor-And-Inverter Graphs for Quantum
  Compilation", npj Quantum Information 8, article 7 (2022),
  doi:10.1038/s41534-021-00514-y.  XAG is the closest logic-network
  representation: XOR nodes are cheap Clifford structure, while AND nodes map
  to non-Clifford cost.  Our affine/FPRM factoring should be framed as another
  symbolic Boolean representation search, not as a replacement for XAG without
  external experiments.
  <https://www.nature.com/articles/s41534-021-00514-y>

- Meuli, Soeken, Roetteler, and De Micheli, "ROS: Resource-constrained Oracle
  Synthesis for Quantum Computers", EPTCS 318:119-130 (2020),
  doi:10.4204/EPTCS.318.8.  ROS is a LUT-based hierarchical oracle synthesis
  framework with resource-aware LUT mapping and SAT-based garbage management.
  It is a required external baseline/export target because it solves the same
  oracle-synthesis task under resource constraints.
  <https://arxiv.org/abs/2005.00211>

- Meuli, Soeken, Campbell, Roetteler, and De Micheli, "The Role of
  Multiplicative Complexity in Compiling Low T-count Oracle Circuits", ICCAD
  2019, doi:10.1109/ICCAD45719.2019.8942093.  This supports the T-count logic:
  low AND-node count in XOR/AND networks translates into low T-count and
  ancilla tradeoffs.  Our resource objective should keep T-count central, even
  when reporting CNOT/depth/ancilla.
  <https://arxiv.org/abs/1908.01609>

- Zheng, Xu, Zhang, Su, and Zheng, "CNOT Oriented Synthesis for Small-Scale
  Boolean Functions Using Spatial Structures of Parallelotopes", ICCAD 2025,
  doi:10.1109/ICCAD66269.2025.11240690.  SSHR is the strongest CNOT-oriented
  small-function comparison in this repo.  Our method should compare against
  SSHR-H/SSHR-I where feasible, but should not use SSHR parallelotope candidates
  internally.
  <https://arxiv.org/abs/2509.01912>

- Wille and Drechsler, "BDD-based Synthesis of Reversible Logic for Large
  Functions", DAC 2009, doi:10.1145/1629911.1629984.  BDD synthesis is a
  scalability baseline for Boolean functions, but its optimization target and
  representation differ from ANF/FPRM factorization.
  <https://dblp.org/rec/conf/dac/WilleD09>

- Yu, Tempia Calvino, Soeken, and De Micheli, "Back-end-aware Fault-tolerant
  Quantum Oracle Synthesis", ASP-DAC 2025, doi:10.1145/3658617.3697776.
  This work extends XAG-based oracle synthesis toward back-end-aware quality
  measures, reporting average improvements in T count, logical time steps, and
  helper qubits after XAG optimization.  It is important boundary literature:
  our current paper is deliberately logic-layer only and must not claim these
  back-end-aware or mapping-level results.
  <https://dl.acm.org/doi/10.1145/3658617.3697776>

## External toolchain sources

- mockturtle is a C++17 logic-network library with AIG, MIG, k-LUT, and generic
  synthesis/optimization support.  It is a plausible source for a future
  reproduced logic-network baseline beyond the current ABC estimates, but it is
  not currently installed in this workstation environment.
  <https://github.com/lsils/mockturtle>

- RevKit is an open-source reversible-logic synthesis framework built around
  tweedledum and mockturtle.  It is the natural candidate for a future
  reversible-toolchain comparison, but it is not currently available as a local
  binary or Python module.
  <https://github.com/msoeken/revkit>

## AI-guided synthesis references

- Tsaras et al., "ShortCircuit: AlphaZero-Driven Circuit Design",
  arXiv:2408.09858.  Classical Boolean circuit synthesis from truth tables is
  already covered by an AlphaZero-style policy/value search for AIG generation.
  This is important for novelty: our claim must be quantum-resource Boolean
  oracle synthesis, not merely "RL + MCTS for Boolean circuits".
  <https://arxiv.org/abs/2408.09858>

- Rietsch et al., "Unitary Synthesis of Clifford+T Circuits with Reinforcement
  Learning", IEEE QCE 2024, doi:10.1109/QCE60285.2024.00102.  Uses Gumbel
  AlphaZero for exact Clifford+T unitary synthesis.  It validates tree-search RL
  for synthesis, but targets general unitaries rather than Boolean oracles.
  <https://arxiv.org/abs/2404.14865>

- Kremer, Javadi-Abhari, and Mukhopadhyay, "Optimizing the non-Clifford-count
  in unitary synthesis using Reinforcement Learning", arXiv:2509.21709.  Uses
  RL to optimize T-count / CS-count for exactly implementable unitaries with
  pruning and canonicalization.
  <https://arxiv.org/abs/2509.21709>

- Machiya, Menickelly, Hovland, and Liu, "MonteQ: A Monte Carlo Tree Search
  Based Quantum Circuit Synthesis Framework", arXiv:2604.19029.  Uses MCTS as
  a high-level ordering search for Hamiltonian-simulation Pauli rotations and
  reports CNOT-count improvements against Rustiq.  It is MCTS-based quantum
  synthesis, but not Boolean oracle synthesis.
  <https://arxiv.org/abs/2604.19029>

- Riu, Nogue, Vilaplana, Garcia-Saez, and Estarellas, "Reinforcement Learning
  Based Quantum Circuit Optimization via ZX-Calculus", Quantum 9, 1758 (2025),
  doi:10.22331/q-2025-05-28-1758.  Uses PPO and graph neural networks to select
  ZX rewrite rules for circuit optimization.  It supports the learned policy
  angle, but acts after a circuit already exists.
  <https://quantum-journal.org/papers/q-2025-05-28-1758/>

## Positioning for this project

The current implementation should be positioned as a symbolic Boolean-search
method: it uses ANF/FPRM monomials, affine coordinate changes, and
compute/uncompute factorizations under explicit resource weights.  This differs
from unitary-level RL, ZX rewriting, Pauli-ordering MCTS, and SSHR's
parallelotope cover space.

The strongest current novelty is the combination of affine Boolean coordinate
search with resource-weighted neural MCTS and guarded high-dimensional FPRM
linear-pair factoring.  The current high-dimensional evidence is promising
against direct ANF, logical-AND direct ANF, root-beam, FPRM-greedy, ABC
AIG/XAG, and a verified BDD/Shannon baseline, but a submission-ready paper
still needs reproduced ROS or mockturtle-style reversible-toolchain results on
the exported benchmarks.

The current local readiness audit is stored in
`results/analysis_toolchain_readiness.md`: ABC is available through the bundled
`tmp/abc/abc` binary, while mockturtle and RevKit are absent from PATH and the
Python environment.  This should be treated as an environment fact, not as a
field-wide statement.
