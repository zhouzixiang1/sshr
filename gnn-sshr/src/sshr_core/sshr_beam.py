"""
SSHR-Beam: Beam search for Boolean function quantum circuit synthesis.

A lighter alternative to MCTS when a fixed-width best-first search suffices.

Algorithm:
  1. Maintain a beam of `width` candidate partial solutions.
     Each candidate: (A_mask, cost_so_far, path_indices)
  2. At each step, expand every candidate with its best `branch` valid actions.
  3. Score each expanded state by (cost_so_far + greedy_lb(A)) where
     greedy_lb uses the numpy-accelerated rollout as a lower-bound estimate.
  4. Keep the top-`width` candidates by score (lower = better).
  5. Repeat until all candidates have A=∅.

Complexity per function:
  O(depth × width × branch × |S|_numpy)
  For n=7: depth≈16, width=50, branch=5 → ~4000 numpy calls per fn.

Key property: guaranteed to find the greedy solution (width=1, branch=1 is pure greedy).
"""
from __future__ import annotations

import heapq
from typing import List, Tuple, Optional, FrozenSet

import numpy as np

from .bool_func import BooleanFunction, QuantumCircuit, mct_cost, mct_cost_rp
from .parallelotope import Parallelotope
from .parallelotope_enum import enumerate_parallelotopes
from .block_synth import synth_block, block_cnot_cost, block_t_cost


# ---------------------------------------------------------------------------
# Cost helper
# ---------------------------------------------------------------------------

def _block_t_cost_rp(p: Parallelotope, n: int) -> int:
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
        return 4
    return mct_cost(k)["T"]


def _get_cost_fn(objective: str):
    if objective == "cnot":
        return block_cnot_cost
    else:
        return _block_t_cost_rp


# ---------------------------------------------------------------------------
# Numpy engine (shared with sshr_mcts_v2 design)
# ---------------------------------------------------------------------------

class _BeamEngine:
    def __init__(self, n: int, objective: str = "cnot"):
        self.n = n
        all_p: List[Parallelotope] = enumerate_parallelotopes(list(range(1 << n)), n)
        for v in range(1 << n):
            all_p.append(Parallelotope(v, []))
        self.all_p = all_p

        cost_fn = _get_cost_fn(objective)
        costs = [float(cost_fn(p, n)) for p in all_p]
        verts = [p.vertices() for p in all_p]
        sizes = [len(vs) for vs in verts]
        bitmasks = [sum(1 << v for v in vs) for vs in verts]

        self.costs_list = costs
        self.bitmasks_list = bitmasks

        P_sizes_arr = np.array(sizes, dtype=np.int32)
        P_costs_arr = np.array(costs, dtype=np.float32)
        bitmasks_int = bitmasks

        if n <= 6:
            self._mode = "single"
            P_masks = np.array([m & ((1 << 64) - 1) for m in bitmasks_int], dtype=np.uint64)
            self.P_masks = P_masks
        elif n == 7:
            self._mode = "double"
            self.P_lo = np.array([m & ((1 << 64) - 1) for m in bitmasks_int], dtype=np.uint64)
            self.P_hi = np.array([m >> 64 for m in bitmasks_int], dtype=np.uint64)
        else:
            self._mode = "object"
            self.P_masks_py = bitmasks_int

        self.P_sizes = P_sizes_arr
        self.P_costs = P_costs_arr

        # Pre-sort by (size DESC, cost ASC) for candidate enumeration
        sorted_idx = sorted(range(len(all_p)), key=lambda i: (-sizes[i], costs[i]))
        self.sorted_idx = sorted_idx
        self.sorted_sizes = np.array([sizes[i] for i in sorted_idx], dtype=np.int32)
        self.sorted_costs = np.array([costs[i] for i in sorted_idx], dtype=np.float32)
        if n <= 6:
            self.sorted_masks = np.array(
                [(bitmasks_int[i] & ((1 << 64) - 1)) for i in sorted_idx], dtype=np.uint64
            )
        elif n == 7:
            self.sorted_lo = np.array(
                [(bitmasks_int[i] & ((1 << 64) - 1)) for i in sorted_idx], dtype=np.uint64
            )
            self.sorted_hi = np.array(
                [bitmasks_int[i] >> 64 for i in sorted_idx], dtype=np.uint64
            )

    def _valid(self, A_mask: int) -> np.ndarray:
        if self._mode == "single":
            Am = np.uint64(A_mask & ((1 << 64) - 1))
            return (self.P_masks & Am) == self.P_masks
        elif self._mode == "double":
            Al = np.uint64(A_mask & ((1 << 64) - 1))
            Ah = np.uint64((A_mask >> 64) & ((1 << 64) - 1))
            return ((self.P_lo & Al) == self.P_lo) & ((self.P_hi & Ah) == self.P_hi)
        else:
            return np.array([(m & A_mask) == m for m in self.P_masks_py], dtype=bool)

    def _valid_sorted(self, A_mask: int) -> np.ndarray:
        """Valid mask in sorted order."""
        if self._mode == "single":
            Am = np.uint64(A_mask & ((1 << 64) - 1))
            return (self.sorted_masks & Am) == self.sorted_masks
        elif self._mode == "double":
            Al = np.uint64(A_mask & ((1 << 64) - 1))
            Ah = np.uint64((A_mask >> 64) & ((1 << 64) - 1))
            return ((self.sorted_lo & Al) == self.sorted_lo) & ((self.sorted_hi & Ah) == self.sorted_hi)
        else:
            bm = self.bitmasks_list
            so = self.sorted_idx
            return np.array([(bm[i] & A_mask) == bm[i] for i in so], dtype=bool)

    def greedy_lb(self, A_mask: int) -> float:
        """
        Greedy lower-bound: fast cost estimate for synthesising the remaining A.
        Uses max-size valid parallelotope each step.
        """
        total = 0.0
        while A_mask:
            valid = self._valid(A_mask)
            if not valid.any():
                break
            valid_sz = np.where(valid, self.P_sizes, 0)
            best_sz = int(valid_sz.max())
            if best_sz == 0:
                break
            sz_match = valid & (self.P_sizes == best_sz)
            best_i = int(np.where(sz_match, self.P_costs, np.float32(np.inf)).argmin())
            total += float(self.P_costs[best_i])
            A_mask ^= self.bitmasks_list[best_i]
        return total

    def top_k_actions(self, A_mask: int, k: int) -> List[Tuple[int, float]]:
        """
        Return up to k best valid actions (orig_idx, cost) sorted by
        (size DESC, cost ASC) — greedy-optimal order.
        Stops early once k actions of the best available size are found.
        """
        valid_sorted = self._valid_sorted(A_mask)
        if not valid_sorted.any():
            return []

        # Find best size among valid
        best_sz = int(np.where(valid_sorted, self.sorted_sizes, 0).max())
        if best_sz == 0:
            return []

        # Collect all actions of best size, up to k
        results: List[Tuple[int, float]] = []
        for j in range(len(self.sorted_idx)):
            if self.sorted_sizes[j] < best_sz:
                break
            if valid_sorted[j]:
                orig = self.sorted_idx[j]
                results.append((orig, float(self.sorted_costs[j])))
                if len(results) == k:
                    break
        return results


# ---------------------------------------------------------------------------
# Beam search state
# ---------------------------------------------------------------------------

# State: (score, tiebreak_id, A_mask, cost_so_far, path)
# score = cost_so_far + greedy_lb(A)  — lower is better

def _mask_to_int(onset: frozenset) -> int:
    m = 0
    for v in onset:
        m |= (1 << v)
    return m


def sshr_beam(
    bf: BooleanFunction,
    objective: str = "cnot",
    width: int = 50,
    branch: int = 5,
    verbose: bool = False,
) -> QuantumCircuit:
    """
    Synthesise a quantum oracle for `bf` using beam search.

    At each step, expand each beam candidate with up to `branch` best valid
    actions, then keep the top `width` candidates by (cost_so_far + greedy_lb).

    Parameters
    ----------
    bf        : Boolean function to synthesise
    objective : "cnot" or "t"
    width     : beam width (number of candidates to maintain)
    branch    : max actions to try per candidate per step
    verbose   : print per-step progress

    Returns
    -------
    QuantumCircuit  (n+1 qubits)
    """
    n = bf.n
    onset = bf.onset
    circuit = QuantumCircuit(n + 1)
    if not onset:
        return circuit

    engine = _BeamEngine(n, objective)
    A0 = _mask_to_int(frozenset(onset))

    # Initial beam: single state (greedy from start)
    # Format: (score, uid, A_mask, cost_so_far, path_list)
    uid = [0]

    def new_state(A_mask: int, cost: float, path: List[int]) -> tuple:
        lb = engine.greedy_lb(A_mask)
        uid[0] += 1
        return (cost + lb, uid[0], A_mask, cost, list(path))

    beam: List[tuple] = [new_state(A0, 0.0, [])]

    step = 0
    while True:
        # Check if any beam candidate is complete
        complete = [s for s in beam if s[2] == 0]  # A_mask == 0
        if complete:
            # Take the one with minimum actual cost
            best = min(complete, key=lambda s: s[3])
            if verbose:
                print(f"  Beam done: step={step}, cost={best[3]:.0f}")
            # Build circuit
            circuit = QuantumCircuit(n + 1)
            for idx in best[4]:
                circuit.add_block(synth_block(engine.all_p[idx], n))
            return circuit

        # Expand beam
        all_next: List[tuple] = []
        for s in beam:
            score, _, A_mask, cost_so_far, path = s
            if A_mask == 0:
                all_next.append(s)
                continue
            actions = engine.top_k_actions(A_mask, branch)
            if not actions:
                # No valid action — use singleton for each remaining minterm
                # Add singletons manually and mark as complete
                A_remaining = A_mask
                total_cost = cost_so_far
                extended_path = list(path)
                while A_remaining:
                    v = (A_remaining & -A_remaining).bit_length() - 1  # lowest set bit
                    singleton_idx = len(engine.all_p) - (1 << n) + v
                    extended_path.append(singleton_idx)
                    total_cost += engine.costs_list[singleton_idx]
                    A_remaining ^= (1 << v)
                all_next.append(new_state(0, total_cost, extended_path))
                continue

            for orig_idx, action_cost in actions:
                bm = engine.bitmasks_list[orig_idx]
                new_A = A_mask ^ bm   # subset removal: since bm ⊆ A_mask
                new_cost = cost_so_far + action_cost
                all_next.append(new_state(new_A, new_cost, path + [orig_idx]))

        if not all_next:
            break

        # Keep top-`width` by score
        all_next.sort(key=lambda s: (s[0], s[1]))
        beam = all_next[:width]
        step += 1

        if verbose:
            best_score = beam[0][0]
            print(f"  step={step}: beam_size={len(beam)} best_score={best_score:.0f}")

    # Fallback: take best partial solution
    best = min(beam, key=lambda s: s[3])
    circuit_out = QuantumCircuit(n + 1)
    for idx in best[4]:
        circuit_out.add_block(synth_block(engine.all_p[idx], n))
    return circuit_out


# ---------------------------------------------------------------------------
# Cost statistics helper
# ---------------------------------------------------------------------------

def circuit_stats(circ: QuantumCircuit, objective: str = "cnot") -> dict:
    T, C, anc = 0, 0, 0
    cost_fn = mct_cost_rp if objective == "t" else mct_cost
    for g in circ.gates:
        if g.type == "MCT":
            c = cost_fn(len(g.controls))
            T += c["T"]; C += c["CNOT"]; anc = max(anc, c["ancilla"])
        elif g.type == "CNOT":
            C += 1
    return {"T": T, "CNOT": C, "ancilla": anc}
