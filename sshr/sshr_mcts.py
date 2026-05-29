"""
SSHR-MCTS: Monte Carlo Tree Search for Boolean function quantum circuit synthesis.

Sits between SSHR-H (greedy) and SSHR-I (ILP) in quality/speed tradeoff:
  - Better quality than SSHR-H (explores multiple first choices, no greedy lock-in)
  - Faster than SSHR-I (no ILP, anytime algorithm)
  - Scales to n=7,8 where ILP is completely infeasible

Problem: WP-SCP (Weighted Parity Set Covering) — sequential formulation
  State      A  =  frozenset (residual on-set; only points still to cover)
  Action        =  select parallelotope P_i  where vertices(P_i) ⊆ A
  Transition    A' = A XOR vertices(P_i) = A - vertices(P_i)   [A shrinks]
  Terminal      A = ∅
  Reward        r = −total_cost(selected)   [minimise cost]

Algorithm: UCT with domain-informed greedy rollout
  Selection:   argmax_child  Q/N + C·√(ln N_parent / N_child)
  Expansion:   add one untried child (lazy init, shuffled)
  Simulation:  greedy rollout from current state using subset-filtered actions
  Backprop:    propagate cumulative reward to root

Key design choices:
  - Actions at state A: only parallelotopes P with vertices(P) ⊆ A
    → A shrinks monotonically → no off-set contamination
    → full-universe pre-computation + per-node subset filtering
  - Rollout: greedy (highest coverage first) from current state
  - Path completion: MCTS path + greedy completion for remaining minterms
  - Progressive widening for n≥6 (action space can exceed 10,000)
"""
from __future__ import annotations

import math
import time
import random
from typing import Dict, List, Optional, Set, FrozenSet, Tuple

from bool_func import BooleanFunction, QuantumCircuit, mct_cost, mct_cost_rp
from parallelotope import Parallelotope
from parallelotope_enum import enumerate_parallelotopes
from block_synth import synth_block, block_cnot_cost, block_t_cost


# ---------------------------------------------------------------------------
# Cost helpers
# ---------------------------------------------------------------------------

def _block_t_cost_rp(p: Parallelotope, n: int) -> int:
    """T cost using relative-phase Toffoli (T=4 for k=2 MCT)."""
    covered = 0
    for alpha in p.basis:
        covered |= alpha
    n_bits = (1 << n) - 1
    common_count = bin(n_bits & ~covered).count('1')
    n_inner = sum(bin(alpha).count('1') - 1 for alpha in p.basis if alpha)
    k = n_inner + common_count
    if k < 2:
        return 0
    if k == 2:
        return 4  # relative-phase Toffoli
    return mct_cost(k)["T"]


def _get_cost_fn(objective: str):
    if objective == "cnot":
        return block_cnot_cost
    else:
        return _block_t_cost_rp


# ---------------------------------------------------------------------------
# Greedy rollout — returns (cost, list_of_indices)
# Valid actions: only P with vertices(P) ⊆ current A
# ---------------------------------------------------------------------------

def _greedy_from_state(
    state_A: FrozenSet[int],
    vert_sets: List[FrozenSet[int]],
    costs: List[float],
    n: int,
) -> Tuple[float, List[int]]:
    """
    Greedy synthesis from state_A. At each step pick the parallelotope P with:
      1. vertices(P) ⊆ A  (subset constraint)
      2. highest |P| (most coverage, maximise minterms removed per step)
      3. tie-break: lower cost first
    Returns (total_cost, [indices_of_selected]).
    """
    A: Set[int] = set(state_A)
    total_cost = 0.0
    path: List[int] = []

    while A:
        best_i = -1
        best_size = -1
        best_cost_tie = float("inf")

        for i, vs in enumerate(vert_sets):
            if not vs.issubset(A):
                continue
            sz = len(vs)
            if sz > best_size or (sz == best_size and costs[i] < best_cost_tie):
                best_size = sz
                best_cost_tie = costs[i]
                best_i = i

        if best_i == -1:
            # No fitting parallelotope — should not happen if singletons are included
            break

        path.append(best_i)
        total_cost += costs[best_i]
        A -= vert_sets[best_i]  # A shrinks (subset guarantee)

    return total_cost, path


# ---------------------------------------------------------------------------
# MCTS Node
# ---------------------------------------------------------------------------

class MCTSNode:
    """
    state_A       : frozenset — current residual on-set
    cost_so_far   : accumulated cost of parallelotopes selected to reach here
    parent        : parent MCTSNode (None for root)
    action_idx    : index of the parallelotope that led to this node (-1 root)
    children      : action_idx → child MCTSNode
    visits        : N(v)
    total_value   : Q(v) — sum of rewards from simulations through this node
    untried       : shuffled list of valid action indices not yet expanded
    """
    __slots__ = (
        "state_A", "cost_so_far", "parent", "action_idx",
        "children", "visits", "total_value", "untried",
    )

    def __init__(
        self,
        state_A: FrozenSet[int],
        cost_so_far: float,
        parent: Optional["MCTSNode"] = None,
        action_idx: int = -1,
    ):
        self.state_A = state_A
        self.cost_so_far = cost_so_far
        self.parent = parent
        self.action_idx = action_idx
        self.children: Dict[int, "MCTSNode"] = {}
        self.visits: int = 0
        self.total_value: float = 0.0
        self.untried: Optional[List[int]] = None  # lazy init

    @property
    def is_terminal(self) -> bool:
        return len(self.state_A) == 0

    def uct_score(self, C: float, parent_visits: int) -> float:
        if self.visits == 0:
            return float("inf")
        exploit = self.total_value / self.visits
        explore = C * math.sqrt(math.log(max(parent_visits, 1)) / self.visits)
        return exploit + explore


# ---------------------------------------------------------------------------
# MCTS four steps
# ---------------------------------------------------------------------------

def _init_untried(
    node: MCTSNode,
    vert_sets: List[FrozenSet[int]],
    rng: random.Random,
) -> None:
    """Lazily compute valid actions for node: only P with vertices ⊆ state_A."""
    A = node.state_A
    valid = [i for i, vs in enumerate(vert_sets) if vs.issubset(A)]
    rng.shuffle(valid)
    node.untried = valid


def _select(root: MCTSNode, C: float, C_pw: float, alpha_pw: float) -> MCTSNode:
    """UCT traversal until a node with unexplored actions or terminal node."""
    node = root
    while not node.is_terminal:
        if node.untried is None:
            break  # needs expansion
        max_ch = max(1, math.ceil(C_pw * (max(node.visits, 1) ** alpha_pw)))
        if node.untried and len(node.children) < max_ch:
            break  # can still expand
        if not node.children:
            break  # no valid actions at this node
        # All children expanded within widening limit — UCT select best child
        node = max(
            node.children.values(),
            key=lambda ch: ch.uct_score(C, node.visits),
        )
    return node


def _expand(
    node: MCTSNode,
    vert_sets: List[FrozenSet[int]],
    costs: List[float],
    rng: random.Random,
) -> MCTSNode:
    """Add one new child to node; return the new child."""
    if node.is_terminal:
        return node
    if node.untried is None:
        _init_untried(node, vert_sets, rng)
    if not node.untried:
        return node  # no valid actions
    idx = node.untried.pop()
    new_A = node.state_A - vert_sets[idx]   # A shrinks (subset guarantee)
    child = MCTSNode(
        state_A=frozenset(new_A),
        cost_so_far=node.cost_so_far + costs[idx],
        parent=node,
        action_idx=idx,
    )
    node.children[idx] = child
    return child


def _simulate(
    node: MCTSNode,
    vert_sets: List[FrozenSet[int]],
    costs: List[float],
    n: int,
) -> Tuple[float, List[int]]:
    """Greedy rollout from node.state_A. Returns (reward, rollout_indices)."""
    rollout_cost, rollout_path = _greedy_from_state(node.state_A, vert_sets, costs, n)
    total_cost = node.cost_so_far + rollout_cost
    return -total_cost, rollout_path  # reward = −cost


def _backpropagate(node: MCTSNode, reward: float) -> None:
    cur = node
    while cur is not None:
        cur.visits += 1
        cur.total_value += reward
        cur = cur.parent


# ---------------------------------------------------------------------------
# Reconstruct circuit from action index sequence
# ---------------------------------------------------------------------------

def _build_circuit(
    indices: List[int],
    parallelotopes: List[Parallelotope],
    n: int,
) -> QuantumCircuit:
    circuit = QuantumCircuit(n + 1)
    for idx in indices:
        block = synth_block(parallelotopes[idx], n)
        circuit.add_block(block)
    return circuit


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def sshr_mcts(
    bf: BooleanFunction,
    objective: str = "cnot",
    n_iterations: int = 1000,
    time_limit: float = 30.0,
    C_explore: float = 1.4,
    use_progressive_widening: bool = True,
    C_pw: float = 2.0,
    alpha_pw: float = 0.5,
    seed: Optional[int] = None,
    verbose: bool = False,
) -> QuantumCircuit:
    """
    Synthesise a quantum oracle for `bf` using SSHR-MCTS.

    Parameters
    ----------
    bf                       : Boolean function to synthesise
    objective                : "cnot" or "t"
    n_iterations             : max MCTS iterations (stops early if time_limit hit)
    time_limit               : wall-clock seconds budget per function
    C_explore                : UCT exploration constant (√2 ≈ 1.414)
    use_progressive_widening : limit children per node (recommended for n≥6)
    C_pw, alpha_pw           : progressive widening parameters
    seed                     : RNG seed for reproducibility
    verbose                  : print per-iteration progress

    Returns
    -------
    QuantumCircuit  (n+1 qubits, last qubit is output)
    """
    n = bf.n
    onset = bf.onset
    circuit = QuantumCircuit(n + 1)
    if not onset:
        return circuit

    rng = random.Random(seed)

    # ── Pre-compute parallelotopes from full universe ────────────────────────
    # Includes ALL possible parallelotopes (any subset of {0..2^n-1}).
    # At each MCTS node, we filter to those with vertices ⊆ current A.
    full_universe = list(range(1 << n))
    all_parallelotopes = enumerate_parallelotopes(full_universe, n)
    # Add dim-0 singletons (handle any remaining single minterms)
    for v in range(1 << n):
        all_parallelotopes.append(Parallelotope(v, []))

    cost_fn = _get_cost_fn(objective)
    costs: List[float] = [float(cost_fn(p, n)) for p in all_parallelotopes]
    vert_sets: List[FrozenSet[int]] = [p.vertices() for p in all_parallelotopes]

    if not use_progressive_widening:
        C_pw_eff, alpha_pw_eff = 1e9, 0.0
    else:
        C_pw_eff, alpha_pw_eff = C_pw, alpha_pw

    # ── Initialise root ──────────────────────────────────────────────────────
    root = MCTSNode(state_A=frozenset(onset), cost_so_far=0.0)

    # ── Track best COMPLETE solution ─────────────────────────────────────────
    # best_path = sequence of indices (MCTS prefix + greedy completion)
    best_cost = float("inf")
    best_full_path: List[int] = []

    # Initialise with a pure greedy solution (SSHR-H equivalent)
    greedy_cost, greedy_path = _greedy_from_state(
        root.state_A, vert_sets, costs, n
    )
    if greedy_cost < best_cost:
        best_cost = greedy_cost
        best_full_path = greedy_path

    # ── MCTS iterations ──────────────────────────────────────────────────────
    t_start = time.time()
    for it in range(n_iterations):
        if time.time() - t_start > time_limit:
            break

        # 1. Selection
        node = _select(root, C_explore, C_pw_eff, alpha_pw_eff)

        # 2. Expansion
        if not node.is_terminal:
            node = _expand(node, vert_sets, costs, rng)

        # 3. Simulation (greedy rollout from node)
        reward, rollout_path = _simulate(node, vert_sets, costs, n)

        # 4. Backpropagation
        _backpropagate(node, reward)

        # 5. Update best complete solution
        total_cost = -reward
        if total_cost < best_cost:
            best_cost = total_cost
            # Reconstruct MCTS prefix path from node up to root
            prefix: List[int] = []
            cur = node
            while cur.parent is not None:
                prefix.append(cur.action_idx)
                cur = cur.parent
            prefix.reverse()
            best_full_path = prefix + rollout_path

        if verbose and (it + 1) % max(1, n_iterations // 10) == 0:
            elapsed = time.time() - t_start
            print(f"  iter {it+1}/{n_iterations}: best={best_cost:.0f} "
                  f"({elapsed:.1f}s)", flush=True)

    if verbose:
        elapsed = time.time() - t_start
        print(f"  MCTS done: {it+1} iters, best={best_cost:.0f}, "
              f"time={elapsed:.2f}s", flush=True)

    # ── Build final circuit ───────────────────────────────────────────────────
    circuit = _build_circuit(best_full_path, all_parallelotopes, n)
    return circuit


# ---------------------------------------------------------------------------
# Cost statistics helper
# ---------------------------------------------------------------------------

def circuit_stats(circ: QuantumCircuit, objective: str = "cnot") -> dict:
    """Return T, CNOT, ancilla counts for a synthesised circuit."""
    T, C, anc = 0, 0, 0
    cost_fn = mct_cost_rp if objective == "t" else mct_cost
    for g in circ.gates:
        if g.type == "MCT":
            c = cost_fn(len(g.controls))
            T += c["T"]; C += c["CNOT"]; anc = max(anc, c["ancilla"])
        elif g.type == "CNOT":
            C += 1
    return {"T": T, "CNOT": C, "ancilla": anc}
