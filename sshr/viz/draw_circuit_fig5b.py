"""
Draw quantum circuit diagrams in the style of SSHR paper Fig 5b.

For a given BooleanFunction, synthesise with SSHR-H, SSHR-I, and SSHR-MCTS,
then draw the resulting circuits side-by-side with colour-coded parallelotope blocks.

Usage:
    python draw_circuit_fig5b.py              # default: n=4 f=0x46B9 (paper example)
    python draw_circuit_fig5b.py --tt 0x96    # n=3 f=0x96
    python draw_circuit_fig5b.py --n 4 --tt 0x46B9 --output circuits.png
"""
from __future__ import annotations
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Rectangle, FancyArrow
import numpy as np
from typing import List, Tuple, Optional

from bool_func import BooleanFunction, QuantumCircuit, Gate, mct_cost


# ── Palette for block colouring ────────────────────────────────────────────
BLOCK_COLORS = [
    '#FFE0B2', '#E3F2FD', '#F3E5F5', '#E8F5E9', '#FFF9C4',
    '#FCE4EC', '#E0F7FA', '#F1F8E9', '#EDE7F6', '#FBE9E7',
]

# ── Gate geometry ──────────────────────────────────────────────────────────
WIRE_SPACING = 0.8      # vertical spacing between wires
GATE_SLOT_W  = 0.55     # horizontal width per gate slot
LEFT_MARGIN  = 1.0      # space for wire labels
RIGHT_MARGIN = 0.3
TOP_MARGIN   = 0.5
BOT_MARGIN   = 0.7      # space for cost label at bottom


def wire_y(qubit_idx: int, n_qubits: int) -> float:
    """Y coordinate for qubit wire (0=output at bottom)."""
    return (n_qubits - 1 - qubit_idx) * WIRE_SPACING


def _draw_cnot(ax, x: float, ctrl_y: float, tgt_y: float,
               color: str = 'steelblue', lw: float = 1.5):
    ax.plot([x, x], [min(ctrl_y, tgt_y), max(ctrl_y, tgt_y)],
            color=color, lw=lw, zorder=3)
    c = Circle((x, ctrl_y), 0.09, color=color, zorder=4)
    ax.add_patch(c)
    # ⊕ symbol for target
    r = 0.18
    c2 = Circle((x, tgt_y), r, color='white', ec=color, lw=lw, zorder=4)
    ax.add_patch(c2)
    ax.plot([x - r, x + r], [tgt_y, tgt_y], color=color, lw=lw, zorder=5)
    ax.plot([x, x], [tgt_y - r, tgt_y + r], color=color, lw=lw, zorder=5)


def _draw_mct(ax, x: float, ctrl_ys: List[float], tgt_y: float,
              color: str = 'darkorange', lw: float = 2.0):
    all_ys = list(ctrl_ys) + [tgt_y]
    ax.plot([x, x], [min(all_ys), max(all_ys)], color=color, lw=lw, zorder=3)
    for cy in ctrl_ys:
        c = Circle((x, cy), 0.10, color=color, zorder=4)
        ax.add_patch(c)
    r = 0.20
    c2 = Circle((x, tgt_y), r, color='white', ec=color, lw=lw + 0.5, zorder=4)
    ax.add_patch(c2)
    ax.plot([x - r, x + r], [tgt_y, tgt_y], color=color, lw=lw, zorder=5)
    ax.plot([x, x], [tgt_y - r, tgt_y + r], color=color, lw=lw, zorder=5)


def _draw_x_gate(ax, x: float, y: float, color: str = '#2e7d32', lw: float = 2.0):
    r = 0.19
    c = Circle((x, y), r, color='white', ec=color, lw=lw, zorder=4)
    ax.add_patch(c)
    d = r * 0.65
    ax.plot([x - d, x + d], [y - d, y + d], color=color, lw=lw, zorder=5)
    ax.plot([x - d, x + d], [y + d, y - d], color=color, lw=lw, zorder=5)


def gate_x_positions(gates: List[Gate], n_qubits: int) -> List[float]:
    """
    Assign horizontal slots to gates, packing non-overlapping gates together.
    Returns x-position for each gate.
    """
    # Simple sequential assignment (no overlap detection — straightforward for display)
    xs = []
    x = 0.0
    for _ in gates:
        xs.append(x)
        x += 1.0
    return xs


def draw_circuit(
    ax,
    circ: QuantumCircuit,
    n: int,
    block_boundaries: List[int],  # start gate-index for each block
    title: str,
    cost_label: str,
):
    """
    Draw the circuit on `ax`.

    block_boundaries[k] = index of the first gate belonging to block k.
    Blocks are coloured alternately.
    """
    n_qubits = n + 1
    gates = circ.gates

    # Compute qubit label heights
    wire_ys = [wire_y(q, n_qubits) for q in range(n_qubits)]
    total_slots = len(gates) + 1  # +1 for small padding at end
    width = LEFT_MARGIN + total_slots * GATE_SLOT_W + RIGHT_MARGIN
    height = n_qubits * WIRE_SPACING + TOP_MARGIN + BOT_MARGIN

    ax.set_xlim(-LEFT_MARGIN, width - LEFT_MARGIN)
    ax.set_ylim(-BOT_MARGIN, height - BOT_MARGIN)
    ax.set_aspect('equal')
    ax.axis('off')

    # Shade background blocks
    boundaries = list(block_boundaries) + [len(gates)]
    for k, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        if start >= end:
            continue
        col = BLOCK_COLORS[k % len(BLOCK_COLORS)]
        x0 = start * GATE_SLOT_W - 0.05
        x1 = end * GATE_SLOT_W + 0.05
        rect = Rectangle(
            (x0, wire_ys[-1] - 0.35), x1 - x0,
            (wire_ys[0] + 0.35) - (wire_ys[-1] - 0.35),
            linewidth=1.5, edgecolor=col, facecolor=col, alpha=0.6, zorder=0,
        )
        ax.add_patch(rect)
        ax.text((x0 + x1) / 2, wire_ys[0] + 0.42, f'B{k+1}',
                ha='center', va='bottom', fontsize=7, color='gray', style='italic')

    # Draw wires
    wire_end = total_slots * GATE_SLOT_W
    for q in range(n_qubits):
        wy = wire_y(q, n_qubits)
        ax.plot([-0.05, wire_end], [wy, wy], color='black', lw=1.2, zorder=1)
        lbl = f'q{q}' if q < n else 'out'
        ax.text(-0.15, wy, lbl, ha='right', va='center', fontsize=9, fontweight='bold')

    # Draw gates
    for gi, g in enumerate(gates):
        x = gi * GATE_SLOT_W + GATE_SLOT_W / 2
        if g.type == 'X':
            wy = wire_y(g.target, n_qubits)
            _draw_x_gate(ax, x, wy)
        elif g.type == 'CNOT':
            cy = wire_y(g.controls[0], n_qubits)
            ty = wire_y(g.target, n_qubits)
            _draw_cnot(ax, x, cy, ty)
        elif g.type == 'MCT':
            ctrl_ys = [wire_y(c, n_qubits) for c in g.controls]
            ty = wire_y(g.target, n_qubits)
            _draw_mct(ax, x, ctrl_ys, ty)

    # Title and cost label
    ax.set_title(title, fontsize=11, fontweight='bold', pad=4)
    ax.text(wire_end / 2, -BOT_MARGIN + 0.1, cost_label,
            ha='center', va='bottom', fontsize=9, color='navy',
            bbox=dict(boxstyle='round', facecolor='#E8EAF6', edgecolor='navy', alpha=0.7))


def synth_with_blocks(method_fn, bf, **kwargs):
    """
    Run synthesis method and return (circuit, block_boundaries).
    We intercept synth_block calls to record block start indices.
    """
    # Monkey-patch: wrap QuantumCircuit.add_block to record boundaries
    boundaries = []
    original_add_block = QuantumCircuit.add_block

    def tracking_add_block(self, other):
        boundaries.append(len(self.gates))
        original_add_block(self, other)

    QuantumCircuit.add_block = tracking_add_block
    try:
        circ = method_fn(bf, **kwargs)
    finally:
        QuantumCircuit.add_block = original_add_block

    return circ, boundaries


def compute_cost_label(circ: QuantumCircuit) -> str:
    T, C, anc = 0, 0, 0
    for g in circ.gates:
        if g.type == 'MCT':
            c = mct_cost(len(g.controls))
            T += c['T']; C += c['CNOT']; anc = max(anc, c['ancilla'])
        elif g.type == 'CNOT':
            C += 1
    return f'T={T}  CNOT={C}  Anc={anc}  |gates|={len(circ.gates)}'


def make_figure(bf: BooleanFunction, output_path: str = 'circuit_fig5b.png'):
    from sshr_h import sshr_h
    from sshr_mcts import sshr_mcts
    try:
        from sshr_i import sshr_i
        has_ilp = True
    except Exception:
        has_ilp = False

    n = bf.n
    methods = []
    methods.append(('SSHR-H', sshr_h, {}))
    methods.append(('SSHR-MCTS\n(iter=2000)', sshr_mcts,
                     {'n_iterations': 2000, 'time_limit': 60.0, 'seed': 42}))
    if has_ilp:
        methods.append(('SSHR-I\n(optimal)', sshr_i,
                        {'objective': 'cnot', 'timeout': 120}))

    n_methods = len(methods)
    fig, axes = plt.subplots(1, n_methods,
                             figsize=(7 * n_methods, max(4, n * 0.8 + 2)))
    fig.suptitle(
        f'Quantum Circuit Synthesis Comparison\n'
        f'f = 0x{bf.truth_table:0{(1<<n)//4}X}  (n={n}, on-set size={len(bf.onset)})',
        fontsize=13, fontweight='bold', y=1.01,
    )
    if n_methods == 1:
        axes = [axes]

    for ax, (label, fn, kw) in zip(axes, methods):
        print(f'  Synthesising with {label.split(chr(10))[0]}...', flush=True)
        circ, boundaries = synth_with_blocks(fn, bf, **kw)
        cost_label = compute_cost_label(circ)
        draw_circuit(ax, circ, n, boundaries, label, cost_label)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f'Saved: {output_path}')
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=4)
    parser.add_argument('--tt', default='0x46B9')
    parser.add_argument('--output', default='circuit_fig5b.png')
    args = parser.parse_args()

    tt = int(args.tt, 16) if args.tt.startswith('0x') else int(args.tt)
    bf = BooleanFunction(args.n, tt)
    print(f'Function: n={args.n}, tt=0x{tt:X}, onset={bf.onset}')
    make_figure(bf, output_path=args.output)


if __name__ == '__main__':
    main()
