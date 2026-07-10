#!/usr/bin/env python3
"""Run external/cross-tool Boolean-oracle baselines on exported benchmarks.

This script intentionally consumes the files produced by ``export_benchmarks.py``
instead of calling the in-harness experiment preset directly.  That keeps the
baseline path close to future ROS/mockturtle integrations: every backend sees
the same exported truth table manifest.
"""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJ_ROOT))


import argparse
import csv
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent  # resource_nmcts/ project root

from src.sshr_lib.bool_func import BooleanFunction, QuantumCircuit, mct_cost_rp  # noqa: E402
from src.sshr_lib.sshr_h import sshr_h  # noqa: E402

try:
    from src.sshr_lib.sshr_i import sshr_i  # noqa: E402
except Exception:  # pragma: no cover - reported per row when used
    sshr_i = None


DEFAULT_RESULTS = THIS_DIR / "results"
DEFAULT_WEIGHTS = {"t": 1.0, "cnot": 0.04, "depth": 0.015, "gates": 0.01, "ancilla": 2.0}
_EXT_TOOLS = ROOT.parent / "_archive" / "external-tools" / "tmp"
DEFAULT_ABC_BIN = _EXT_TOOLS / "abc" / "abc"
DEFAULT_ABC_SCRIPT = "strash; balance; rewrite; refactor; rewrite -z; balance"
DEFAULT_ABC_ESOP_SCRIPT = "strash; &get"
DEFAULT_ABC_XAG_SCRIPT = "&get; &st -m -L 1"
DEFAULT_ABC_LUT_SCRIPT = "strash; if -K 4"
ABC_STATS_RE = re.compile(r"and\s*=\s*(\d+)\s+lev\s*=\s*(\d+)")
ESOP_STATS_RE = re.compile(r"Final\s+statistics:\s+Cubes\s*=\s*(\d+)\s+Literals\s*=\s*(\d+)\s+QCost\s*=\s*(\d+)")
XAG_NODE_RE = re.compile(r"\b(?:and|nod)\s*=\s*(\d+)\s+lev\s*=\s*(\d+)")
XAG_STATS_RE = re.compile(
    r"XOR/MUX stats:\s*xor\s*=\s*(\d+).*?mux\s*=\s*(\d+).*?and\s*=\s*(\d+).*?obj\s*=\s*(\d+)",
    re.DOTALL,
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass(frozen=True)
class Cost:
    T: int = 0
    CNOT: int = 0
    gates: int = 0
    depth: int = 0
    explicit_ancilla: int = 0
    peak_ancilla: int = 0

    def score(self, weights: dict[str, float]) -> float:
        return (
            weights["t"] * self.T
            + weights["cnot"] * self.CNOT
            + weights["depth"] * self.depth
            + weights["gates"] * self.gates
            + weights["ancilla"] * self.peak_ancilla
        )


@dataclass(frozen=True)
class BddNode:
    var: int
    low: int
    high: int


@dataclass(frozen=True)
class BddNetwork:
    root: int
    nodes: dict[int, BddNode]
    order: tuple[int, ...]


def anf_term_count(bf: BooleanFunction) -> int:
    coeff = [(bf.truth_table >> i) & 1 for i in range(1 << bf.n)]
    for bit in range(bf.n):
        step = 1 << bit
        for mask in range(1 << bf.n):
            if mask & step:
                coeff[mask] ^= coeff[mask ^ step]
    return sum(coeff)


def circuit_cost(circ: QuantumCircuit, n_inputs: int) -> Cost:
    t_count = 0
    cnot_count = 0
    depth = 0
    helper_peak = 0
    for gate in circ.gates:
        if gate.type == "X":
            depth += 1
        elif gate.type == "CNOT":
            cnot_count += 1
            depth += 1
        elif gate.type == "MCT":
            cost = mct_cost_rp(len(gate.controls))
            t_count += int(cost["T"])
            cnot_count += int(cost["CNOT"])
            depth += max(1, int(cost["CNOT"]))
            helper_peak = max(helper_peak, int(cost.get("ancilla", 0)))
    explicit = max(0, circ.n_qubits - (n_inputs + 1))
    return Cost(
        T=t_count,
        CNOT=cnot_count,
        gates=len(circ.gates),
        depth=depth,
        explicit_ancilla=explicit,
        peak_ancilla=explicit + helper_peak,
    )


def verify_oracle(circ: QuantumCircuit, bf: BooleanFunction) -> bool:
    if circ.n_qubits < bf.n + 1:
        return False
    out = bf.n
    for x in range(1 << bf.n):
        prefix = [(x >> i) & 1 for i in range(bf.n)]
        expected = bf.evaluate(x)
        for y in (0, 1):
            bits = prefix + [y] + [0] * max(0, circ.n_qubits - (bf.n + 1))
            got = circ.simulate(bits)[out]
            if got != (y ^ expected):
                return False
    return True


def resolve_manifest(path: Path) -> Path:
    if path.name.endswith(".json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest = payload.get("manifest")
        if not manifest:
            raise SystemExit(f"manifest JSON has no manifest field: {path}")
        return (path.parent / manifest).resolve()
    return path.resolve()


def load_manifest(path: Path) -> list[dict]:
    manifest = resolve_manifest(path)
    with manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["_manifest_dir"] = display_path(manifest.parent)
        row["_manifest_abs_dir"] = str(manifest.parent)
    return rows


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(THIS_DIR))
    except ValueError:
        return str(path)


def parse_methods(raw: str) -> list[str]:
    methods = [item.strip() for item in raw.split(",") if item.strip()]
    valid = {
        "external_sshr_h",
        "external_sshr_i_cnot",
        "external_sshr_i_t",
        "external_abc_aig",
        "external_abc_esop",
        "external_abc_lut",
        "external_abc_xag",
        "external_bdd",
    }
    unknown = sorted(set(methods) - valid)
    if unknown:
        raise SystemExit(f"unknown external methods: {', '.join(unknown)}")
    return methods or sorted(valid)


def bool_from_row(row: dict) -> BooleanFunction:
    return BooleanFunction(int(row["n"]), int(str(row["truth_table_hex"]), 16))


@dataclass(frozen=True)
class BlifNode:
    inputs: tuple[str, ...]
    output: str
    cover: tuple[tuple[str, int], ...]


def blif_logical_lines(text: str) -> Iterable[str]:
    pending = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        if pending:
            line = pending + line
            pending = ""
        yield line.strip()
    if pending:
        yield pending.strip()


def parse_blif(path: Path) -> tuple[list[str], str, list[BlifNode]]:
    inputs: list[str] = []
    outputs: list[str] = []
    nodes: list[BlifNode] = []
    current_names: list[str] | None = None
    current_cover: list[tuple[str, int]] = []

    def flush_current() -> None:
        nonlocal current_names, current_cover
        if current_names is None:
            return
        if not current_names:
            raise ValueError(f"malformed .names in {path}")
        nodes.append(
            BlifNode(
                inputs=tuple(current_names[:-1]),
                output=current_names[-1],
                cover=tuple(current_cover),
            )
        )
        current_names = None
        current_cover = []

    for line in blif_logical_lines(path.read_text(encoding="utf-8")):
        if line.startswith("."):
            flush_current()
            parts = line.split()
            directive = parts[0]
            if directive == ".inputs":
                inputs.extend(parts[1:])
            elif directive == ".outputs":
                outputs.extend(parts[1:])
            elif directive == ".names":
                current_names = parts[1:]
                current_cover = []
            elif directive == ".end":
                break
            continue

        if current_names is None:
            raise ValueError(f"cover row outside .names in {path}: {line}")
        parts = line.split()
        if len(current_names) == 1:
            value = int(parts[-1]) if parts else 0
            current_cover.append(("", value))
        else:
            pattern = parts[0]
            value = int(parts[1]) if len(parts) > 1 else 1
            current_cover.append((pattern, value))
    flush_current()
    if len(outputs) != 1:
        raise ValueError(f"expected one BLIF output in {path}, got {outputs}")
    return inputs, outputs[0], nodes


def input_label_index(label: str) -> int:
    for prefix in ("x", "pi"):
        if label.startswith(prefix) and label[len(prefix) :].isdigit():
            return int(label[len(prefix) :])
    raise ValueError(f"unsupported input label: {label}")


def eval_blif(inputs: list[str], output: str, nodes: list[BlifNode], x: int) -> int:
    values: dict[str, int] = {}
    for label in inputs:
        values[label] = (x >> input_label_index(label)) & 1
    pending = list(nodes)
    while pending:
        next_pending = []
        progressed = False
        for node in pending:
            if any(name not in values for name in node.inputs):
                next_pending.append(node)
                continue
            if not node.inputs:
                value = node.cover[-1][1] if node.cover else 0
            else:
                values_in_cover = {out_value for _pattern, out_value in node.cover}
                # ABC may emit off-set covers; then the unlisted minterms default to 1.
                value = 1 if values_in_cover == {0} else 0
                bits = "".join(str(values[name]) for name in node.inputs)
                for pattern, out_value in node.cover:
                    if len(pattern) != len(bits):
                        continue
                    if all(p == "-" or p == b for p, b in zip(pattern, bits)):
                        value = out_value
                        break
            values[node.output] = value
            progressed = True
        if not progressed:
            missing = sorted({name for node in next_pending for name in node.inputs if name not in values})
            raise ValueError(f"BLIF nodes are not resolvable; missing fanins: {missing[:8]}")
        pending = next_pending
    if output not in values:
        raise ValueError(f"BLIF output {output} was not driven")
    return values[output]


def _all_truth_bits(n: int) -> int:
    return (1 << (1 << n)) - 1


def _input_truth_masks(labels: list[str], n: int) -> dict[str, int]:
    masks = {label: 0 for label in labels}
    for x in range(1 << n):
        bit = 1 << x
        for label in labels:
            if (x >> input_label_index(label)) & 1:
                masks[label] |= bit
    return masks


def _pattern_mask(pattern: str, input_masks: tuple[int, ...], all_bits: int) -> int:
    mask = all_bits
    for ch, input_mask in zip(pattern, input_masks):
        if ch == "1":
            mask &= input_mask
        elif ch == "0":
            mask &= all_bits ^ input_mask
        elif ch == "-":
            continue
        else:
            raise ValueError(f"unsupported BLIF pattern character: {ch}")
    return mask


def blif_truth_table(inputs: list[str], output: str, nodes: list[BlifNode], n: int) -> int:
    values = _input_truth_masks(inputs, n)
    all_bits = _all_truth_bits(n)
    pending = list(nodes)
    while pending:
        next_pending = []
        progressed = False
        for node in pending:
            if any(name not in values for name in node.inputs):
                next_pending.append(node)
                continue
            if not node.inputs:
                values[node.output] = all_bits if node.cover and node.cover[-1][1] else 0
                progressed = True
                continue

            values_in_cover = {out_value for _pattern, out_value in node.cover}
            # ABC sometimes emits off-set covers; then the unlisted minterms default to 1.
            value = all_bits if values_in_cover == {0} else 0
            input_masks = tuple(values[name] for name in node.inputs)
            for pattern, out_value in node.cover:
                if len(pattern) != len(input_masks):
                    continue
                mask = _pattern_mask(pattern, input_masks, all_bits)
                if out_value:
                    value |= mask
                else:
                    value &= all_bits ^ mask
            values[node.output] = value & all_bits
            progressed = True
        if not progressed:
            missing = sorted({name for node in next_pending for name in node.inputs if name not in values})
            raise ValueError(f"BLIF nodes are not resolvable; missing fanins: {missing[:8]}")
        pending = next_pending
    if output not in values:
        raise ValueError(f"BLIF output {output} was not driven")
    return values[output]


def verify_blif(path: Path, bf: BooleanFunction) -> bool:
    inputs, output, nodes = parse_blif(path)
    if len(inputs) != bf.n:
        return False
    return blif_truth_table(inputs, output, nodes, bf.n) == bf.truth_table


def _cover_local_truth(input_count: int, cover: tuple[tuple[str, int], ...]) -> int:
    if input_count == 0:
        return 1 if cover and cover[-1][1] else 0
    values_in_cover = {out_value for _pattern, out_value in cover}
    default = 1 if values_in_cover == {0} else 0
    truth = 0
    for x in range(1 << input_count):
        value = default
        bits = "".join(str((x >> i) & 1) for i in range(input_count))
        for pattern, out_value in cover:
            if len(pattern) != input_count:
                continue
            if all(p == "-" or p == b for p, b in zip(pattern, bits)):
                value = out_value
                break
        if value:
            truth |= 1 << x
    return truth


def _anf_terms_from_truth(truth: int, input_count: int) -> list[int]:
    coeff = [(truth >> i) & 1 for i in range(1 << input_count)]
    for bit in range(input_count):
        step = 1 << bit
        for mask in range(1 << input_count):
            if mask & step:
                coeff[mask] ^= coeff[mask ^ step]
    return [mask for mask, value in enumerate(coeff) if value]


def blif_lut_network_cost(inputs: list[str], output: str, nodes: list[BlifNode], bf: BooleanFunction) -> Cost:
    """Estimate a BLIF LUT network as compute-output-uncompute local ANF nodes."""
    if output not in {node.output for node in nodes}:
        output_cnot, output_gate = output_toggle_cost(bf)
        return Cost(CNOT=output_cnot, gates=output_gate, depth=output_gate)

    compute_t = compute_cnot = compute_gates = compute_depth = 0
    helper_peak = 0
    for node in nodes:
        truth = _cover_local_truth(len(node.inputs), node.cover)
        for term in _anf_terms_from_truth(truth, len(node.inputs)):
            cost = _logical_and_gate_cost(int(term).bit_count())
            compute_t += cost.T
            compute_cnot += cost.CNOT
            compute_gates += cost.gates
            compute_depth += cost.depth
            helper_peak = max(helper_peak, cost.peak_ancilla)

    output_cnot, output_gate = output_toggle_cost(bf)
    explicit = len(nodes)
    return Cost(
        T=2 * compute_t,
        CNOT=2 * compute_cnot + output_cnot,
        gates=2 * compute_gates + output_gate,
        depth=2 * compute_depth + output_gate,
        explicit_ancilla=explicit,
        peak_ancilla=explicit + helper_peak,
    )


def abc_bennett_cost(and_count: int, level: int, bf: BooleanFunction) -> Cost:
    all_ones = (1 << (1 << bf.n)) - 1
    if bf.truth_table == 0:
        output_cnot = 0
        output_gate = 0
    elif bf.truth_table == all_ones:
        output_cnot = 0
        output_gate = 1
    else:
        output_cnot = 1
        output_gate = 1
    return Cost(
        T=4 * and_count,
        CNOT=10 * and_count + output_cnot,
        gates=4 * and_count + output_gate,
        depth=10 * level + output_gate,
        explicit_ancilla=and_count,
        peak_ancilla=and_count,
    )


def output_toggle_cost(bf: BooleanFunction) -> tuple[int, int]:
    all_ones = (1 << (1 << bf.n)) - 1
    if bf.truth_table in {0, all_ones}:
        return 0, int(bf.truth_table == all_ones)
    return 1, 1


def abc_xag_cost(and_count: int, xor_count: int, mux_count: int, level: int, bf: BooleanFunction) -> Cost:
    output_cnot, output_gate = output_toggle_cost(bf)
    # Count a MUX as one nonlinear selection plus two XOR-class linear updates.
    nonlinear = and_count + mux_count
    linear = xor_count + 2 * mux_count
    return Cost(
        T=4 * nonlinear,
        CNOT=6 * nonlinear + 2 * linear + output_cnot,
        gates=2 * nonlinear + 2 * linear + output_gate,
        depth=6 * level + output_gate,
        explicit_ancilla=nonlinear + linear,
        peak_ancilla=nonlinear + linear,
    )


def _reordered_truth_table(bf: BooleanFunction, order: tuple[int, ...]) -> int:
    local = 0
    for local_idx in range(1 << bf.n):
        original_idx = 0
        for pos, var in enumerate(order):
            if (local_idx >> pos) & 1:
                original_idx |= 1 << var
        if (bf.truth_table >> original_idx) & 1:
            local |= 1 << local_idx
    return local


def _split_local_truth(tt: int, remaining_vars: int) -> tuple[int, int]:
    low = 0
    high = 0
    for rest_idx in range(1 << (remaining_vars - 1)):
        low_bit = 1 << (2 * rest_idx)
        high_bit = 1 << (2 * rest_idx + 1)
        if tt & low_bit:
            low |= 1 << rest_idx
        if tt & high_bit:
            high |= 1 << rest_idx
    return low, high


def build_robdd_for_order(bf: BooleanFunction, order: tuple[int, ...]) -> BddNetwork:
    if len(order) != bf.n or set(order) != set(range(bf.n)):
        raise ValueError(f"invalid BDD order for n={bf.n}: {order}")
    local_truth = _reordered_truth_table(bf, order)
    unique: dict[tuple[int, int, int], int] = {}
    memo: dict[tuple[int, int], int] = {}
    nodes: dict[int, BddNode] = {}
    next_id = 2

    def build(level: int, tt: int) -> int:
        nonlocal next_id
        remaining = bf.n - level
        full_mask = (1 << (1 << remaining)) - 1
        if tt == 0:
            return 0
        if tt == full_mask:
            return 1
        if remaining == 0:
            return 1 if tt & 1 else 0
        key = (level, tt)
        if key in memo:
            return memo[key]
        low, high = _split_local_truth(tt, remaining)
        low_id = build(level + 1, low)
        high_id = build(level + 1, high)
        if low_id == high_id:
            memo[key] = low_id
            return low_id
        node_key = (order[level], low_id, high_id)
        node_id = unique.get(node_key)
        if node_id is None:
            node_id = next_id
            next_id += 1
            unique[node_key] = node_id
            nodes[node_id] = BddNode(var=order[level], low=low_id, high=high_id)
        memo[key] = node_id
        return node_id

    return BddNetwork(root=build(0, local_truth), nodes=nodes, order=order)


def eval_bdd(network: BddNetwork, x: int) -> int:
    node_id = network.root
    while node_id not in {0, 1}:
        node = network.nodes[node_id]
        node_id = node.high if ((x >> node.var) & 1) else node.low
    return node_id


def verify_bdd(network: BddNetwork, bf: BooleanFunction) -> bool:
    for x in range(1 << bf.n):
        if eval_bdd(network, x) != bf.evaluate(x):
            return False
    return True


def _variable_influences(bf: BooleanFunction) -> list[tuple[int, int]]:
    influences = []
    for var in range(bf.n):
        count = 0
        step = 1 << var
        for x in range(1 << bf.n):
            if x & step:
                continue
            count += ((bf.truth_table >> x) ^ (bf.truth_table >> (x | step))) & 1
        influences.append((count, var))
    return influences


def candidate_bdd_orders(bf: BooleanFunction, seed: int, max_orders: int) -> list[tuple[int, ...]]:
    if bf.n == 0:
        return [()]
    influences = _variable_influences(bf)
    descending = tuple(var for _count, var in sorted(influences, key=lambda item: (-item[0], item[1])))
    ascending = tuple(var for _count, var in sorted(influences, key=lambda item: (item[0], item[1])))
    natural = tuple(range(bf.n))
    reverse = tuple(reversed(natural))
    high_low = tuple(var for pair in zip(descending, reversed(descending)) for var in pair)
    high_low = tuple(dict.fromkeys(high_low))

    orders: list[tuple[int, ...]] = []

    def add(order: tuple[int, ...]) -> None:
        if len(orders) >= max_orders:
            return
        if len(order) == bf.n and order not in orders:
            orders.append(order)

    for order in (natural, reverse, descending, ascending, high_low):
        add(order)

    import random

    rng = random.Random(seed)
    attempts = 0
    max_attempts = max(10, 20 * max_orders)
    while len(orders) < max_orders and attempts < max_attempts:
        attempts += 1
        order_list = list(range(bf.n))
        rng.shuffle(order_list)
        add(tuple(order_list))
    return orders


def _bdd_branch_compute_cost(child: int, inverted_control: bool) -> Cost:
    if child == 0:
        return Cost()
    wraps = 2 if inverted_control else 0
    if child == 1:
        return Cost(CNOT=1, gates=1 + wraps, depth=1 + wraps)
    and_cost = Cost(T=4, CNOT=7, gates=3, depth=7)
    return Cost(
        T=and_cost.T,
        CNOT=and_cost.CNOT,
        gates=and_cost.gates + wraps,
        depth=and_cost.depth + wraps,
    )


def _add_cost(a: Cost, b: Cost) -> Cost:
    return Cost(
        T=a.T + b.T,
        CNOT=a.CNOT + b.CNOT,
        gates=a.gates + b.gates,
        depth=a.depth + b.depth,
        explicit_ancilla=max(a.explicit_ancilla, b.explicit_ancilla),
        peak_ancilla=max(a.peak_ancilla, b.peak_ancilla),
    )


def bdd_cost(network: BddNetwork, bf: BooleanFunction) -> Cost:
    if network.root == 0:
        return Cost()
    if network.root == 1:
        return Cost(gates=1, depth=1)

    compute = Cost()
    for node in network.nodes.values():
        node_cost = _add_cost(
            _bdd_branch_compute_cost(node.low, inverted_control=True),
            _bdd_branch_compute_cost(node.high, inverted_control=False),
        )
        compute = _add_cost(compute, node_cost)
    output_cnot, output_gate = output_toggle_cost(bf)
    node_count = len(network.nodes)
    return Cost(
        T=2 * compute.T,
        CNOT=2 * compute.CNOT + output_cnot,
        gates=2 * compute.gates + output_gate,
        depth=2 * compute.depth + output_gate,
        explicit_ancilla=node_count,
        peak_ancilla=node_count,
    )


def run_bdd(row: dict, bf: BooleanFunction, weights: dict[str, float], max_orders: int) -> tuple[Cost, dict]:
    best: tuple[float, Cost, BddNetwork, int] | None = None
    orders = candidate_bdd_orders(bf, seed=int(row.get("index") or 0), max_orders=max(1, max_orders))
    for order in orders:
        network = build_robdd_for_order(bf, order)
        cost = bdd_cost(network, bf)
        score = cost.score(weights)
        if best is None or (score, len(network.nodes), order) < (best[0], len(best[2].nodes), best[2].order):
            best = (score, cost, network, len(orders))
    if best is None:
        raise RuntimeError("BDD order generation produced no candidates")
    _score, cost, network, order_count = best
    correct = verify_bdd(network, bf)
    return cost, {
        "correct": correct,
        "bdd_nodes": len(network.nodes),
        "bdd_root": network.root,
        "bdd_order": " ".join(str(var) for var in network.order),
        "bdd_orders_evaluated": order_count,
    }


@dataclass(frozen=True)
class EsopCube:
    pattern: str

    @property
    def controls(self) -> int:
        return sum(ch in {"0", "1"} for ch in self.pattern)

    @property
    def zeros(self) -> int:
        return self.pattern.count("0")

    def matches(self, x: int) -> bool:
        for i, ch in enumerate(self.pattern):
            if ch == "-":
                continue
            if ((x >> i) & 1) != int(ch):
                return False
        return True


def parse_esop_pla(path: Path) -> list[EsopCube]:
    cubes: list[EsopCube] = []
    n_inputs: int | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(".i"):
            parts = line.split()
            if len(parts) >= 2:
                n_inputs = int(parts[1])
            continue
        if line.startswith("."):
            continue
        parts = line.split()
        if not parts:
            continue
        pattern = parts[0]
        output = parts[1] if len(parts) > 1 else "1"
        if output != "1":
            continue
        if n_inputs is not None and len(pattern) != n_inputs:
            raise ValueError(f"ESOP cube width mismatch in {path}: {pattern}")
        if any(ch not in {"0", "1", "-"} for ch in pattern):
            raise ValueError(f"unsupported ESOP cube pattern in {path}: {pattern}")
        cubes.append(EsopCube(pattern))
    return cubes


def verify_esop(cubes: list[EsopCube], bf: BooleanFunction) -> bool:
    all_bits = _all_truth_bits(bf.n)
    input_masks = _input_truth_masks([f"x{i}" for i in range(bf.n)], bf.n)
    masks = tuple(input_masks[f"x{i}"] for i in range(bf.n))
    value = 0
    for cube in cubes:
        if len(cube.pattern) != bf.n:
            return False
        value ^= _pattern_mask(cube.pattern, masks, all_bits)
    return value == bf.truth_table


def _logical_and_gate_cost(controls: int) -> Cost:
    if controls <= 0:
        return Cost(gates=1, depth=1)
    if controls == 1:
        return Cost(CNOT=1, gates=1, depth=1)
    ands = controls - 1
    temp = max(0, controls - 2)
    return Cost(
        T=4 * ands,
        CNOT=6 * ands + 1,
        gates=2 * ands + 1,
        depth=6 * ands + 1,
        peak_ancilla=temp,
    )


def esop_logical_and_cost(cubes: list[EsopCube]) -> Cost:
    total = Cost()
    for cube in cubes:
        base = _logical_and_gate_cost(cube.controls)
        wrap = 2 * cube.zeros
        total = Cost(
            T=total.T + base.T,
            CNOT=total.CNOT + base.CNOT,
            gates=total.gates + base.gates + wrap,
            depth=total.depth + base.depth + wrap,
            explicit_ancilla=max(total.explicit_ancilla, base.explicit_ancilla),
            peak_ancilla=max(total.peak_ancilla, base.peak_ancilla),
        )
    return total


def parse_abc_stats(output: str) -> tuple[int, int]:
    clean = ANSI_RE.sub("", output)
    matches = ABC_STATS_RE.findall(clean)
    if not matches:
        raise RuntimeError(f"could not parse ABC stats from output: {clean[-500:]}")
    and_count, level = matches[-1]
    return int(and_count), int(level)


def parse_esop_stats(output: str) -> tuple[int | None, int | None, int | None]:
    clean = ANSI_RE.sub("", output)
    matches = ESOP_STATS_RE.findall(clean)
    if not matches:
        return None, None, None
    cubes, literals, qcost = matches[-1]
    return int(cubes), int(literals), int(qcost)


def parse_xag_stats(output: str) -> tuple[int, int, int, int, int]:
    clean = ANSI_RE.sub("", output)
    node_matches = XAG_NODE_RE.findall(clean)
    stat_matches = XAG_STATS_RE.findall(clean)
    if not node_matches or not stat_matches:
        raise RuntimeError(f"could not parse ABC-XAG stats from output: {clean[-800:]}")
    _nodes, level = node_matches[-1]
    xor_count, mux_count, and_count, obj_count = stat_matches[-1]
    return int(and_count), int(xor_count), int(mux_count), int(obj_count), int(level)


def run_abc_aig(
    row: dict,
    bf: BooleanFunction,
    timeout: float,
    abc_bin: Path,
    abc_script: str,
) -> tuple[Cost, dict]:
    if not abc_bin.exists():
        raise FileNotFoundError(f"ABC binary not found: {abc_bin}")
    rel_blif = row.get("blif")
    if not rel_blif:
        raise ValueError("manifest row has no BLIF path")
    blif = (Path(row["_manifest_abs_dir"]) / rel_blif).resolve()
    if not blif.exists():
        raise FileNotFoundError(f"BLIF file not found: {blif}")

    with tempfile.TemporaryDirectory(prefix="abc_aig_") as tmp:
        opt_blif = Path(tmp) / f"{row['name']}.abc.blif"
        command = (
            f"read_blif {blif}; {abc_script}; "
            f"write_blif {opt_blif}; print_stats"
        )
        proc = subprocess.run(
            [str(abc_bin), "-c", command],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(f"ABC failed with code {proc.returncode}: {combined[-1000:]}")
        and_count, level = parse_abc_stats(combined)
        correct = verify_blif(opt_blif, bf)
    cost = abc_bennett_cost(and_count, level, bf)
    return cost, {
        "correct": correct,
        "abc_and": and_count,
        "abc_level": level,
        "abc_script": abc_script,
        "abc_binary": display_path(abc_bin),
    }


def run_abc_xag(
    row: dict,
    bf: BooleanFunction,
    timeout: float,
    abc_bin: Path,
    abc_script: str,
) -> tuple[Cost, dict]:
    if not abc_bin.exists():
        raise FileNotFoundError(f"ABC binary not found: {abc_bin}")
    rel_blif = row.get("blif")
    if not rel_blif:
        raise ValueError("manifest row has no BLIF path")
    blif = (Path(row["_manifest_abs_dir"]) / rel_blif).resolve()
    if not blif.exists():
        raise FileNotFoundError(f"BLIF file not found: {blif}")

    with tempfile.TemporaryDirectory(prefix="abc_xag_") as tmp:
        opt_blif = Path(tmp) / f"{row['name']}.abc_xag.blif"
        command = f"read_blif {blif}; {abc_script}; &ps -m -x; &put; write_blif {opt_blif}"
        proc = subprocess.run(
            [str(abc_bin), "-c", command],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(f"ABC-XAG failed with code {proc.returncode}: {combined[-1000:]}")
        if not opt_blif.exists():
            raise RuntimeError(f"ABC-XAG did not write BLIF file: {combined[-1000:]}")
        and_count, xor_count, mux_count, obj_count, level = parse_xag_stats(combined)
        correct = verify_blif(opt_blif, bf)
    cost = abc_xag_cost(and_count, xor_count, mux_count, level, bf)
    return cost, {
        "correct": correct,
        "abc_xag_and": and_count,
        "abc_xag_xor": xor_count,
        "abc_xag_mux": mux_count,
        "abc_xag_obj": obj_count,
        "abc_xag_level": level,
        "abc_script": abc_script,
        "abc_binary": display_path(abc_bin),
    }


def run_abc_lut(
    row: dict,
    bf: BooleanFunction,
    timeout: float,
    abc_bin: Path,
    abc_script: str,
) -> tuple[Cost, dict]:
    if not abc_bin.exists():
        raise FileNotFoundError(f"ABC binary not found: {abc_bin}")
    rel_blif = row.get("blif")
    if not rel_blif:
        raise ValueError("manifest row has no BLIF path")
    blif = (Path(row["_manifest_abs_dir"]) / rel_blif).resolve()
    if not blif.exists():
        raise FileNotFoundError(f"BLIF file not found: {blif}")

    with tempfile.TemporaryDirectory(prefix="abc_lut_") as tmp:
        opt_blif = Path(tmp) / f"{row['name']}.abc_lut.blif"
        command = f"read_blif {blif}; {abc_script}; write_blif {opt_blif}; print_stats"
        proc = subprocess.run(
            [str(abc_bin), "-c", command],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(f"ABC-LUT failed with code {proc.returncode}: {combined[-1000:]}")
        if not opt_blif.exists():
            raise RuntimeError(f"ABC-LUT did not write BLIF file: {combined[-1000:]}")
        inputs, output, nodes = parse_blif(opt_blif)
        if len(inputs) != bf.n:
            raise RuntimeError(f"ABC-LUT BLIF input count mismatch: {len(inputs)} != {bf.n}")
        correct = blif_truth_table(inputs, output, nodes, bf.n) == bf.truth_table
    cost = blif_lut_network_cost(inputs, output, nodes, bf)
    return cost, {
        "correct": correct,
        "abc_lut_nodes": len(nodes),
        "abc_lut_max_fanin": max((len(node.inputs) for node in nodes), default=0),
        "abc_script": abc_script,
        "abc_binary": display_path(abc_bin),
    }


def run_abc_esop(
    row: dict,
    bf: BooleanFunction,
    timeout: float,
    abc_bin: Path,
    abc_script: str,
) -> tuple[Cost, dict]:
    if not abc_bin.exists():
        raise FileNotFoundError(f"ABC binary not found: {abc_bin}")
    rel_blif = row.get("blif")
    if not rel_blif:
        raise ValueError("manifest row has no BLIF path")
    blif = (Path(row["_manifest_abs_dir"]) / rel_blif).resolve()
    if not blif.exists():
        raise FileNotFoundError(f"BLIF file not found: {blif}")

    with tempfile.TemporaryDirectory(prefix="abc_esop_") as tmp:
        esop_path = Path(tmp) / f"{row['name']}.esop.pla"
        command = f"read_blif {blif}; {abc_script}; &exorcism -q {esop_path}"
        proc = subprocess.run(
            [str(abc_bin), "-c", command],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(f"ABC exorcism failed with code {proc.returncode}: {combined[-1000:]}")
        if not esop_path.exists():
            raise RuntimeError(f"ABC exorcism did not write ESOP file: {combined[-1000:]}")
        cubes = parse_esop_pla(esop_path)
        correct = verify_esop(cubes, bf)
        final_cubes, final_literals, qcost = parse_esop_stats(esop_path.read_text(encoding="utf-8"))
    cost = esop_logical_and_cost(cubes)
    return cost, {
        "correct": correct,
        "abc_esop_cubes": len(cubes),
        "abc_esop_reported_cubes": final_cubes if final_cubes is not None else "",
        "abc_esop_literals": final_literals if final_literals is not None else "",
        "abc_esop_qcost": qcost if qcost is not None else "",
        "abc_script": abc_script,
        "abc_binary": display_path(abc_bin),
    }


def synthesize_external(method: str, bf: BooleanFunction, timeout: float) -> QuantumCircuit:
    if method == "external_sshr_h":
        return sshr_h(bf)
    if method == "external_sshr_i_cnot":
        if sshr_i is None:
            raise RuntimeError("sshr_i backend could not be imported")
        return sshr_i(bf, objective="cnot", timeout=timeout, try_complement=True)
    if method == "external_sshr_i_t":
        if sshr_i is None:
            raise RuntimeError("sshr_i backend could not be imported")
        return sshr_i(bf, objective="t", timeout=timeout, try_complement=True)
    raise ValueError(method)


def run_one(task: tuple[dict, str, float, int, int, int, int, int, int, int, dict[str, float], Path, str, str, str, str]) -> dict:
    (
        row,
        method,
        timeout,
        max_ilp_n,
        max_abc_n,
        max_esop_n,
        max_xag_n,
        max_lut_n,
        max_bdd_n,
        bdd_orders,
        weights,
        abc_bin,
        abc_script,
        abc_esop_script,
        abc_xag_script,
        abc_lut_script,
    ) = task
    bf = bool_from_row(row)
    base = {
        "index": row.get("index", ""),
        "name": row["name"],
        "preset_name": row.get("preset_name", row["name"]),
        "n": bf.n,
        "truth_table_hex": f"{bf.truth_table:X}",
        "onset_size": len(bf.onset),
        "anf_terms": anf_term_count(bf),
        "method": method,
        "source_manifest": row.get("_manifest_dir", ""),
    }
    if method.startswith("external_sshr_i") and bf.n > max_ilp_n:
        return {**base, "skipped": f"SSHR-I capped at n<={max_ilp_n}", "error": ""}
    if method == "external_abc_aig" and bf.n > max_abc_n:
        return {**base, "skipped": f"ABC-AIG capped at n<={max_abc_n}", "error": ""}
    if method == "external_abc_esop" and bf.n > max_esop_n:
        return {**base, "skipped": f"ABC-ESOP capped at n<={max_esop_n}", "error": ""}
    if method == "external_abc_xag" and bf.n > max_xag_n:
        return {**base, "skipped": f"ABC-XAG capped at n<={max_xag_n}", "error": ""}
    if method == "external_abc_lut" and bf.n > max_lut_n:
        return {**base, "skipped": f"ABC-LUT capped at n<={max_lut_n}", "error": ""}
    if method == "external_bdd" and bf.n > max_bdd_n:
        return {**base, "skipped": f"BDD capped at n<={max_bdd_n}", "error": ""}
    try:
        start = time.time()
        if method == "external_abc_aig":
            cost, extra = run_abc_aig(row, bf, timeout, abc_bin, abc_script)
            elapsed = time.time() - start
            correct = extra.pop("correct")
            n_qubits = bf.n + 1 + cost.explicit_ancilla
            gates = cost.gates
        elif method == "external_abc_esop":
            cost, extra = run_abc_esop(row, bf, timeout, abc_bin, abc_esop_script)
            elapsed = time.time() - start
            correct = extra.pop("correct")
            n_qubits = bf.n + 1 + cost.explicit_ancilla
            gates = cost.gates
        elif method == "external_abc_xag":
            cost, extra = run_abc_xag(row, bf, timeout, abc_bin, abc_xag_script)
            elapsed = time.time() - start
            correct = extra.pop("correct")
            n_qubits = bf.n + 1 + cost.explicit_ancilla
            gates = cost.gates
        elif method == "external_abc_lut":
            cost, extra = run_abc_lut(row, bf, timeout, abc_bin, abc_lut_script)
            elapsed = time.time() - start
            correct = extra.pop("correct")
            n_qubits = bf.n + 1 + cost.explicit_ancilla
            gates = cost.gates
        elif method == "external_bdd":
            cost, extra = run_bdd(row, bf, weights, bdd_orders)
            elapsed = time.time() - start
            correct = extra.pop("correct")
            n_qubits = bf.n + 1 + cost.explicit_ancilla
            gates = cost.gates
        else:
            circ = synthesize_external(method, bf, timeout)
            elapsed = time.time() - start
            cost = circuit_cost(circ, bf.n)
            extra = {}
            correct = verify_oracle(circ, bf)
            n_qubits = circ.n_qubits
            gates = len(circ.gates)
        return {
            **base,
            **asdict(cost),
            "score": cost.score(weights),
            "time_s": elapsed,
            "correct": correct,
            "gates": gates,
            "n_qubits": n_qubits,
            **extra,
            "skipped": "",
            "error": "",
        }
    except Exception as exc:
        return {**base, "correct": False, "skipped": "", "error": repr(exc)}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        groups.setdefault((str(row["method"]), int(row["n"])), []).append(row)
    out = []
    for (method, n), items in sorted(groups.items()):
        def vals(key: str) -> list[float]:
            return [float(row[key]) for row in items if row.get(key) not in {None, ""}]

        out.append(
            {
                "method": method,
                "n": n,
                "functions": len(items),
                "correct": sum(1 for row in items if str(row.get("correct")) == "True"),
                "total_T": int(sum(vals("T"))),
                "total_CNOT": int(sum(vals("CNOT"))),
                "mean_score": statistics.mean(vals("score")) if vals("score") else float("nan"),
                "mean_depth": statistics.mean(vals("depth")) if vals("depth") else float("nan"),
                "mean_peak_ancilla": statistics.mean(vals("peak_ancilla")) if vals("peak_ancilla") else float("nan"),
                "mean_time_s": statistics.mean(vals("time_s")) if vals("time_s") else float("nan"),
            }
        )
    return out


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True, help="manifest.csv or manifest.json from export_benchmarks.py")
    parser.add_argument("--methods", default="external_sshr_h,external_sshr_i_cnot,external_sshr_i_t")
    parser.add_argument("--out", type=Path, default=DEFAULT_RESULTS / "raw_external_baselines.csv")
    parser.add_argument("--summary", type=Path, default=DEFAULT_RESULTS / "summary_external_baselines.csv")
    parser.add_argument("--run-manifest", type=Path, default=DEFAULT_RESULTS / "manifest_external_baselines.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--min-n", type=int, default=None)
    parser.add_argument("--max-n", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0, help="function offset after n filters")
    parser.add_argument("--count", type=int, default=None, help="function count after n filters")
    parser.add_argument("--max-ilp-n", type=int, default=4)
    parser.add_argument("--max-abc-n", type=int, default=15)
    parser.add_argument("--max-esop-n", type=int, default=8)
    parser.add_argument("--max-xag-n", type=int, default=15)
    parser.add_argument("--max-lut-n", type=int, default=15)
    parser.add_argument("--max-bdd-n", type=int, default=15)
    parser.add_argument("--bdd-orders", type=int, default=8)
    parser.add_argument("--abc-bin", type=Path, default=DEFAULT_ABC_BIN)
    parser.add_argument("--abc-script", default=DEFAULT_ABC_SCRIPT)
    parser.add_argument("--abc-esop-script", default=DEFAULT_ABC_ESOP_SCRIPT)
    parser.add_argument("--abc-xag-script", default=DEFAULT_ABC_XAG_SCRIPT)
    parser.add_argument("--abc-lut-script", default=DEFAULT_ABC_LUT_SCRIPT)
    parser.add_argument("--timeout", type=float, default=30.0, help="per SSHR-I call time limit")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--replace-methods", action="store_true", help="drop existing rows for selected methods before a resume run")
    args = parser.parse_args(list(argv) if argv is not None else None)

    weights = dict(DEFAULT_WEIGHTS)
    manifest_rows = load_manifest(args.manifest)
    if args.min_n is not None:
        manifest_rows = [row for row in manifest_rows if int(row["n"]) >= args.min_n]
    if args.max_n is not None:
        manifest_rows = [row for row in manifest_rows if int(row["n"]) <= args.max_n]
    if args.offset:
        manifest_rows = manifest_rows[max(0, args.offset) :]
    if args.count is not None:
        manifest_rows = manifest_rows[: max(0, args.count)]
    if args.limit is not None:
        manifest_rows = manifest_rows[: max(0, args.limit)]
    methods = parse_methods(args.methods)
    tasks = [
        (
            row,
            method,
            args.timeout,
            args.max_ilp_n,
            args.max_abc_n,
            args.max_esop_n,
            args.max_xag_n,
            args.max_lut_n,
            args.max_bdd_n,
            args.bdd_orders,
            weights,
            args.abc_bin,
            args.abc_script,
            args.abc_esop_script,
            args.abc_xag_script,
            args.abc_lut_script,
        )
        for row in manifest_rows
        for method in methods
    ]

    rows: list[dict] = []
    existing_rows = 0
    if args.resume and args.out.exists():
        with args.out.open(newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
        if args.replace_methods:
            replace_set = set(methods)
            rows = [row for row in rows if row.get("method") not in replace_set]
        existing_rows = len(rows)
        done = {(row.get("name"), row.get("method")) for row in rows}
        tasks = [task for task in tasks if (task[0]["name"], task[1]) not in done]
        print(f"resuming from {len(rows)} rows; remaining {len(tasks)}", flush=True)

    start = time.time()
    if args.workers <= 1:
        for i, task in enumerate(tasks, 1):
            rows.append(run_one(task))
            if i % 20 == 0:
                write_csv(args.out, rows)
                print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_one, task) for task in tasks]
            for i, future in enumerate(as_completed(futures), 1):
                rows.append(future.result())
                if i % 20 == 0:
                    write_csv(args.out, rows)
                    print(f"{i}/{len(tasks)}", flush=True)

    write_csv(args.out, rows)
    summary = summarize(rows)
    write_csv(args.summary, summary)
    args.run_manifest.parent.mkdir(parents=True, exist_ok=True)
    previous_manifest = {}
    if args.resume and args.run_manifest.exists():
        try:
            previous_manifest = json.loads(args.run_manifest.read_text(encoding="utf-8"))
        except Exception:
            previous_manifest = {}
    report_max_ilp_n = (
        args.max_ilp_n
        if any(method.startswith("external_sshr_i") for method in methods)
        else previous_manifest.get("max_ilp_n", args.max_ilp_n)
    )
    report_max_abc_n = (
        args.max_abc_n
        if "external_abc_aig" in methods
        else previous_manifest.get("max_abc_n", args.max_abc_n)
    )
    report_max_esop_n = (
        args.max_esop_n
        if "external_abc_esop" in methods
        else previous_manifest.get("max_esop_n", args.max_esop_n)
    )
    report_max_xag_n = (
        args.max_xag_n
        if "external_abc_xag" in methods
        else previous_manifest.get("max_xag_n", args.max_xag_n)
    )
    report_max_lut_n = (
        args.max_lut_n
        if "external_abc_lut" in methods
        else previous_manifest.get("max_lut_n", args.max_lut_n)
    )
    report_max_bdd_n = (
        args.max_bdd_n
        if "external_bdd" in methods
        else previous_manifest.get("max_bdd_n", args.max_bdd_n)
    )
    args.run_manifest.write_text(
        json.dumps(
            {
                "source_manifest": display_path(resolve_manifest(args.manifest)),
                "methods": sorted({str(row.get("method", "")) for row in rows if row.get("method")}),
                "last_run_methods": methods,
                "functions": len(manifest_rows),
                "rows": len(rows),
                "resume": args.resume,
                "existing_rows": existing_rows,
                "new_tasks": len(tasks),
                "max_n": args.max_n,
                "min_n": args.min_n,
                "offset": args.offset,
                "count": args.count,
                "max_ilp_n": report_max_ilp_n,
                "max_abc_n": report_max_abc_n,
                "max_esop_n": report_max_esop_n,
                "max_xag_n": report_max_xag_n,
                "max_lut_n": report_max_lut_n,
                "max_bdd_n": report_max_bdd_n,
                "bdd_orders": args.bdd_orders,
                "abc_binary": display_path(args.abc_bin),
                "abc_script": args.abc_script,
                "abc_esop_script": args.abc_esop_script,
                "abc_xag_script": args.abc_xag_script,
                "abc_lut_script": args.abc_lut_script,
                "timeout": args.timeout,
                "workers": args.workers,
                "elapsed_s": time.time() - start,
                "raw": str(args.out),
                "summary": str(args.summary),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    print(f"wrote {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
