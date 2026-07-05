#!/usr/bin/env python3
"""Policy/value guided MCTS over SSHR parallelotope blocks.

This module implements a practical version of the RL+MCTS idea from
``new-idea.pdf``.  Instead of searching raw quantum gates and storing full
unitary matrices, it searches over SSHR parallelotope blocks.  Each action is
semantically closed: choosing a block flips exactly the vertices of the
parallelotope, and ``synth_block`` deterministically produces the circuit.

The search uses monotone semantics:

    valid action: vertices(P) subset A
    transition:   A <- A - vertices(P)

This is directly comparable to the existing SSHR-Beam / SSHR-MCTS monotone
backends in ``sshr/``.
"""
from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SSHR_DIR = REPO_ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))

from bool_func import BooleanFunction, QuantumCircuit, mct_cost, mct_cost_rp  # noqa: E402
from block_synth import block_cnot_cost, synth_block  # noqa: E402
from parallelotope import Parallelotope  # noqa: E402
from parallelotope_enum import enumerate_parallelotopes  # noqa: E402


def onset_mask(bf: BooleanFunction) -> int:
    mask = 0
    for v in bf.onset:
        mask |= 1 << v
    return mask


def popcount(x: int) -> int:
    return int(x.bit_count())


def circuit_cost(circ: QuantumCircuit, objective: str = "cnot") -> int:
    total = 0
    for gate in circ.gates:
        if gate.type == "CNOT":
            if objective == "cnot":
                total += 1
        elif gate.type == "MCT":
            k = len(gate.controls)
            c = mct_cost_rp(k) if objective == "t" else mct_cost(k)
            total += c["T"] if objective == "t" else c["CNOT"]
    return int(total)


def verify_circuit(circ: QuantumCircuit, bf: BooleanFunction) -> bool:
    n = bf.n
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)] + [0]
        out = circ.simulate(bits)
        if out[n] != bf.evaluate(x):
            return False
    return True


@dataclass(frozen=True)
class Candidate:
    idx: int
    p: Parallelotope
    mask: int
    size: int
    cost: float
    dim: int
    prior_score: float


@dataclass
class SearchResult:
    circuit: QuantumCircuit
    path: List[int]
    cost: int
    time_s: float
    correct: bool
    steps: int
    method: str


class BlockSearchEngine:
    """Candidate cache and policy/value utilities for one ``n``."""

    def __init__(
        self,
        n: int,
        objective: str = "cnot",
        prior: str = "balanced",
    ) -> None:
        self.n = n
        self.objective = objective
        self.prior = prior
        all_p = enumerate_parallelotopes(list(range(1 << n)), n)
        seen = {p.vertices() for p in all_p}
        for v in range(1 << n):
            s = frozenset([v])
            if s not in seen:
                all_p.append(Parallelotope(v, []))
                seen.add(s)

        self.candidates: List[Candidate] = []
        for i, p in enumerate(all_p):
            verts = p.vertices()
            mask = sum(1 << v for v in verts)
            cost = float(block_cnot_cost(p, n))
            if cost <= 0:
                cost = 0.001
            size = len(verts)
            dim = p.dim
            prior_score = self._prior_score(size=size, cost=cost, dim=dim)
            self.candidates.append(
                Candidate(
                    idx=i,
                    p=p,
                    mask=mask,
                    size=size,
                    cost=cost,
                    dim=dim,
                    prior_score=prior_score,
                )
            )

        # Descending policy preference; tie-break by lower cost and stable idx.
        self.sorted_idx = sorted(
            range(len(self.candidates)),
            key=lambda i: (
                -self.candidates[i].prior_score,
                self.candidates[i].cost,
                -self.candidates[i].size,
                i,
            ),
        )
        self._valid_cache: Dict[int, List[int]] = {}
        self._greedy_cost_cache: Dict[int, float] = {}

    def _prior_score(self, size: int, cost: float, dim: int) -> float:
        efficiency = size / max(cost, 1.0)
        if self.prior == "size":
            return math.log2(size + 1.0)
        if self.prior == "efficiency":
            return efficiency
        # Balanced policy: prefer larger blocks, but penalize expensive controls.
        return 0.70 * math.log2(size + 1.0) + 0.30 * math.log1p(efficiency) - 0.015 * cost

    def valid_actions(self, A_mask: int, top_k: Optional[int] = None) -> List[int]:
        if A_mask in self._valid_cache:
            valid = self._valid_cache[A_mask]
        else:
            valid = [
                i
                for i in self.sorted_idx
                if self.candidates[i].mask != 0
                and (self.candidates[i].mask & A_mask) == self.candidates[i].mask
            ]
            self._valid_cache[A_mask] = valid
        if top_k is None:
            return list(valid)
        return list(valid[:top_k])

    def greedy_path(
        self,
        A_mask: int,
        top_k: int = 64,
        lookahead: bool = False,
    ) -> Tuple[List[int], float]:
        path: List[int] = []
        cost = 0.0
        seen = set()
        while A_mask:
            if A_mask in seen:
                # Monotone updates should prevent this, but keep a guard.
                break
            seen.add(A_mask)
            actions = self.valid_actions(A_mask, top_k=top_k)
            if not actions:
                break
            if lookahead:
                best = min(
                    actions,
                    key=lambda i: (
                        self.candidates[i].cost
                        + self.greedy_cost(A_mask ^ self.candidates[i].mask, top_k=top_k),
                        self.candidates[i].cost,
                        -self.candidates[i].size,
                        i,
                    ),
                )
            else:
                best = actions[0]
            path.append(best)
            cost += self.candidates[best].cost
            A_mask ^= self.candidates[best].mask
        return path, cost

    def greedy_cost(self, A_mask: int, top_k: int = 64) -> float:
        if A_mask in self._greedy_cost_cache:
            return self._greedy_cost_cache[A_mask]
        _, cost = self.greedy_path(A_mask, top_k=top_k, lookahead=False)
        self._greedy_cost_cache[A_mask] = cost
        return cost

    def build_circuit(self, path: Sequence[int]) -> QuantumCircuit:
        circ = QuantumCircuit(self.n + 1)
        for idx in path:
            circ.add_block(synth_block(self.candidates[idx].p, self.n))
        return circ


@dataclass
class EdgeStats:
    visits: int = 0
    q_cost: float = 0.0


class MCTSNode:
    __slots__ = ("A_mask", "actions", "children", "stats", "visits")

    def __init__(self, A_mask: int) -> None:
        self.A_mask = A_mask
        self.actions: Optional[List[int]] = None
        self.children: Dict[int, "MCTSNode"] = {}
        self.stats: Dict[int, EdgeStats] = {}
        self.visits = 0

    @property
    def expanded(self) -> bool:
        return self.actions is not None


def _softmax_priors(engine: BlockSearchEngine, actions: Sequence[int], temp: float = 1.0) -> Dict[int, float]:
    if not actions:
        return {}
    scores = [engine.candidates[i].prior_score / max(temp, 1e-6) for i in actions]
    m = max(scores)
    weights = [math.exp(s - m) for s in scores]
    z = sum(weights)
    return {a: w / z for a, w in zip(actions, weights)}


def policy_value_mcts_path(
    engine: BlockSearchEngine,
    A0: int,
    simulations_per_step: int = 96,
    expand_top_k: int = 24,
    c_puct: float = 1.25,
    value_top_k: int = 64,
    seed: int = 0,
) -> Tuple[List[int], float]:
    """Return a block path using PUCT MCTS and a greedy value estimate."""
    rng = random.Random(seed)
    root = MCTSNode(A0)
    path: List[int] = []
    total_cost = 0.0
    A_mask = A0

    def simulate(node: MCTSNode) -> float:
        if node.A_mask == 0:
            return 0.0
        node.visits += 1
        if not node.expanded:
            actions = engine.valid_actions(node.A_mask, top_k=expand_top_k)
            node.actions = actions
            for a in actions:
                node.stats[a] = EdgeStats()
            return engine.greedy_cost(node.A_mask, top_k=value_top_k)

        assert node.actions is not None
        if not node.actions:
            return engine.greedy_cost(node.A_mask, top_k=value_top_k)

        priors = _softmax_priors(engine, node.actions)
        sqrt_n = math.sqrt(max(node.visits, 1))

        def select_key(a: int) -> Tuple[float, float]:
            st = node.stats[a]
            q = st.q_cost if st.visits else engine.candidates[a].cost + engine.greedy_cost(
                node.A_mask ^ engine.candidates[a].mask, top_k=value_top_k
            )
            bonus = c_puct * priors.get(a, 0.0) * sqrt_n / (1 + st.visits)
            # Lower estimated cost is better; bonus encourages exploration.
            jitter = rng.random() * 1e-9
            return (q - bonus + jitter, engine.candidates[a].cost)

        action = min(node.actions, key=select_key)
        child = node.children.get(action)
        next_A = node.A_mask ^ engine.candidates[action].mask
        if child is None:
            child = MCTSNode(next_A)
            node.children[action] = child
        sample = engine.candidates[action].cost + simulate(child)
        st = node.stats[action]
        st.visits += 1
        st.q_cost += (sample - st.q_cost) / st.visits
        return sample

    while A_mask:
        for _ in range(simulations_per_step):
            simulate(root)
        if not root.expanded or not root.actions:
            greedy_suffix, suffix_cost = engine.greedy_path(A_mask, top_k=value_top_k)
            path.extend(greedy_suffix)
            total_cost += suffix_cost
            break
        assert root.actions is not None
        visited = [a for a in root.actions if root.stats[a].visits > 0]
        if not visited:
            visited = root.actions
        best = min(
            visited,
            key=lambda a: (
                root.stats[a].q_cost if root.stats[a].visits else float("inf"),
                -root.stats[a].visits,
                engine.candidates[a].cost,
                a,
            ),
        )
        path.append(best)
        total_cost += engine.candidates[best].cost
        A_mask ^= engine.candidates[best].mask
        root = root.children.get(best, MCTSNode(A_mask))
    return path, total_cost


def synthesize_greedy(
    bf: BooleanFunction,
    prior: str = "balanced",
    lookahead: bool = False,
) -> SearchResult:
    t0 = time.time()
    engine = BlockSearchEngine(bf.n, prior=prior)
    path, _ = engine.greedy_path(onset_mask(bf), lookahead=lookahead)
    circ = engine.build_circuit(path)
    return SearchResult(
        circuit=circ,
        path=path,
        cost=circuit_cost(circ),
        time_s=time.time() - t0,
        correct=verify_circuit(circ, bf),
        steps=len(path),
        method="pv_greedy_lookahead" if lookahead else "pv_greedy",
    )


def synthesize_pv_mcts(
    bf: BooleanFunction,
    prior: str = "balanced",
    simulations_per_step: int = 96,
    expand_top_k: int = 24,
    c_puct: float = 1.25,
    seed: int = 0,
) -> SearchResult:
    t0 = time.time()
    engine = BlockSearchEngine(bf.n, prior=prior)
    path, _ = policy_value_mcts_path(
        engine,
        onset_mask(bf),
        simulations_per_step=simulations_per_step,
        expand_top_k=expand_top_k,
        c_puct=c_puct,
        seed=seed,
    )
    circ = engine.build_circuit(path)
    return SearchResult(
        circuit=circ,
        path=path,
        cost=circuit_cost(circ),
        time_s=time.time() - t0,
        correct=verify_circuit(circ, bf),
        steps=len(path),
        method="pv_mcts",
    )

