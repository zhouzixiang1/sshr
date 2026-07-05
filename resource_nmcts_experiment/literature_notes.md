# Literature Notes

## AI-guided quantum synthesis

- Rietsch et al., "Unitary Synthesis of Clifford+T Circuits with Reinforcement
  Learning", arXiv:2404.14865.  Uses Gumbel AlphaZero for exact Clifford+T
  unitary synthesis.  This validates tree-search RL for synthesis, but targets
  general unitaries rather than Boolean oracles.
  <https://arxiv.org/abs/2404.14865>

- Kremer, Javadi-Abhari, and Mukhopadhyay, "Optimizing the non-Clifford-count
  in unitary synthesis using Reinforcement Learning", arXiv:2509.21709.  Uses
  RL to optimize T-count / CS-count for exactly implementable unitaries with
  pruning and canonicalization.
  <https://arxiv.org/abs/2509.21709>

- Machiya et al., "MonteQ: A Monte Carlo Tree Search Based Quantum Circuit
  Synthesis Framework", arXiv:2604.19029.  Uses MCTS as a high-level ordering
  search for Hamiltonian-simulation Pauli rotations and reports CNOT-count
  improvements against Rustiq.
  <https://arxiv.org/abs/2604.19029>

- Riu et al., "Reinforcement Learning Based Quantum Circuit Optimization via
  ZX-Calculus", Quantum 2025.  Uses PPO and graph neural networks to select
  ZX rewrite rules for circuit optimization.
  <https://quantum-journal.org/papers/q-2025-05-28-1758/>

## Boolean oracle synthesis

- Meuli et al., "Xor-And-Inverter Graphs for Quantum Compilation", npj Quantum
  Information 2022.  Motivates XAG as a Boolean representation for
  Clifford+T quantum compilation.
  <https://www.nature.com/articles/s41534-021-00514-y>

- Meuli, Soeken, Roetteler, and De Micheli, "ROS: Resource-constrained Oracle
  Synthesis for Quantum Computers", arXiv:2005.00211.  A LUT-based hierarchical
  oracle synthesis framework with resource-aware LUT mapping and SAT-based
  garbage management.
  <https://arxiv.org/abs/2005.00211>

- Meuli et al., "The Role of Multiplicative Complexity in Compiling Low
  T-count Oracle Circuits", ICCAD 2019.  Relates Boolean multiplicative
  complexity to T-count and ancilla upper bounds for oracle circuits.
  <https://msoeken.github.io/papers/2019_iccad.pdf>

- Wille and Drechsler, "BDD-based Synthesis of Reversible Logic for Large
  Functions", DAC 2009.  Uses BDDs to derive reversible/quantum circuits for
  large Boolean functions.
  <https://agra.informatik.uni-bremen.de/doc/konf/09dac_bdd_synth.pdf>

## Positioning for this project

The current implementation is positioned as a symbolic Boolean-search method:
it uses ANF/FPRM monomials and searches compute/uncompute factorizations under
explicit resource weights.  This differs from unitary-level RL and from SSHR's
parallelotope space, while still matching the XAG/ROS literature's focus on
T-count, CNOT count, depth, and ancilla.

The strongest current novelty is the combination of affine Boolean coordinate
search with resource-weighted neural MCTS.  The affine step changes the ANF/FPRM
basis before factoring, so it can discover low-T decompositions that are not
available to fixed-coordinate monomial factoring.  SSHR remains a comparison
point for small functions, but the method does not call SSHR or use SSHR
parallelotopes.
