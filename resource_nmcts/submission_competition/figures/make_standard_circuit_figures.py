#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate standards-compliant, traceable circuit figures for XA-202609.

Unlike the earlier contact-sheet draft, this generator separates logical and
physical evidence, labels Oracle wire roles explicitly, folds long circuits,
and draws line art as editable matplotlib vectors.  Every logical glyph comes
from ``synthesize_artifact()``; no circuit is reconstructed from reported
metrics.

Run from ``resource_nmcts/`` with the mcts-qoracle interpreter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch  # noqa: F401 -- import before Qiskit on this Windows host

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch
import pandas as pd
import qiskit
import qiskit_aer

from src.anf_utils import (
    anf_monomials,
    majority_function,
    random_anf_function,
    random_truth_function,
    threshold_function,
)
from src.factor_plan import SearchConfig, verify_oracle
from src.hardware_map import (
    CompileConfig,
    compile_for_target,
    make_cx_line_target,
    verify_oracle_aer,
)
from src.resource_model import ResourceWeights
from src.sshr_lib.bool_func import BooleanFunction, QuantumCircuit as EngineCircuit
from src.synthesizers import synthesize_artifact

OUTDIR = ROOT / "submission_competition" / "figures"
MODEL = ROOT / "models" / "action_scorer.pt"

INK = "#182432"
WIRE = "#445466"
BLUE = "#1358B0"
ORANGE = "#D9652B"
GREEN = "#167B64"
GREY = "#6E7A86"
GRID = "#CDD6DF"
LIGHT_BLUE = "#EAF2FB"
LIGHT_GREY = "#F3F5F7"

MM = 1 / 25.4

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Arial", "SimHei", "DejaVu Sans"],
        "font.size": 7,
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


@dataclass(frozen=True)
class DrawOp:
    name: str
    controls: tuple[int, ...]
    target: int
    parameter: float | None = None


def figure_config() -> SearchConfig:
    return SearchConfig(
        weights=ResourceWeights(t=1.0, cnot=0.04, depth=0.015, gates=0.01, ancilla=2.0),
        max_factor_ancilla=3,
        max_factor_size=4,
        candidate_top_k=12,
        mcts_simulations=24,
        neural_mcts_simulations=32,
        max_polarities=8,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _save(fig: plt.Figure, stem: str, *, dpi: int = 600) -> list[str]:
    outputs: list[str] = []
    for suffix in ("svg", "pdf", "png"):
        path = OUTDIR / f"{stem}.{suffix}"
        # Preserve the declared 183 mm competition-page width exactly; all
        # artists are laid out inside explicit margins, so tight cropping is
        # unnecessary and would silently change the final publication size.
        kwargs = {}
        if suffix == "png":
            kwargs["dpi"] = dpi
        fig.savefig(path, **kwargs)
        outputs.append(str(path.relative_to(ROOT)))
    plt.close(fig)
    return outputs


def _engine_ops(circuit: EngineCircuit) -> list[DrawOp]:
    return [
        DrawOp(gate.type.lower(), tuple(gate.controls), int(gate.target))
        for gate in circuit.gates
    ]


def _native_ops(circuit) -> list[DrawOp]:
    operations: list[DrawOp] = []
    for instruction in circuit.data:
        name = instruction.operation.name.lower()
        qubits = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        if name == "cx":
            operations.append(DrawOp(name, (qubits[0],), qubits[1]))
        elif len(qubits) == 1:
            parameter = None
            if instruction.operation.params:
                try:
                    parameter = float(instruction.operation.params[0])
                except (TypeError, ValueError):
                    parameter = None
            operations.append(DrawOp(name, (), qubits[0], parameter))
        elif len(qubits) == 2:
            operations.append(DrawOp(name, (qubits[0],), qubits[1]))
        else:
            raise ValueError(f"unsupported native instruction for figure: {instruction}")
    return operations


def _oracle_wire_labels(n_inputs: int, n_qubits: int) -> tuple[list[str], list[str]]:
    if n_qubits < n_inputs + 1:
        raise ValueError("Oracle circuit has no output wire")
    left: list[str] = []
    right: list[str] = []
    for index in range(n_qubits):
        if index < n_inputs:
            left.append(rf"$x_{{{index}}}$  $|x_{{{index}}}\rangle$")
            right.append(rf"$|x_{{{index}}}\rangle$")
        elif index == n_inputs:
            left.append(r"$y$  $|y\rangle$")
            right.append(r"$|y\oplus f(x)\rangle$")
        else:
            ancilla = index - n_inputs - 1
            left.append(rf"$a_{{{ancilla}}}$  $|0\rangle$")
            right.append(r"$|0\rangle$")
    return left, right


def _logical_role(index: int, n_inputs: int) -> str:
    if index < n_inputs:
        return rf"x_{{{index}}}"
    if index == n_inputs:
        return "y"
    return rf"a_{{{index - n_inputs - 1}}}"


def _physical_wire_labels(mapped, n_inputs: int) -> tuple[list[str], list[str], list[int], list[int]]:
    n_physical = mapped.num_qubits
    if mapped.layout is None:
        initial_by_logical = list(range(n_physical))
        final_by_logical = list(range(n_physical))
    else:
        initial_by_logical = list(mapped.layout.initial_index_layout(filter_ancillas=True))
        final_by_logical = list(mapped.layout.final_index_layout(filter_ancillas=True))
    initial_role_at = {physical: logical for logical, physical in enumerate(initial_by_logical)}
    final_role_at = {physical: logical for logical, physical in enumerate(final_by_logical)}
    left: list[str] = []
    right: list[str] = []
    for physical in range(n_physical):
        logical_in = initial_role_at.get(physical)
        logical_out = final_role_at.get(physical)
        in_role = _logical_role(logical_in, n_inputs) if logical_in is not None else "0"
        out_role = _logical_role(logical_out, n_inputs) if logical_out is not None else "0"
        if logical_in is not None and logical_in == n_inputs:
            in_state = r"|y\rangle"
        elif logical_in is not None and logical_in < n_inputs:
            in_state = rf"|x_{{{logical_in}}}\rangle"
        else:
            in_state = r"|0\rangle"
        if logical_out is not None and logical_out == n_inputs:
            out_state = r"|y\oplus f(x)\rangle"
        elif logical_out is not None and logical_out < n_inputs:
            out_state = rf"|x_{{{logical_out}}}\rangle"
        else:
            out_state = r"|0\rangle"
        left.append(rf"$p_{{{physical}}}\!:\!{in_role}$  ${in_state}$")
        right.append(rf"$p_{{{physical}}}\!:\!{out_role}$  ${out_state}$")
    return left, right, initial_by_logical, final_by_logical


def _angle_label(value: float | None) -> str:
    if value is None:
        return ""
    fraction = Fraction(value / math.pi).limit_denominator(16)
    if abs(float(fraction) - value / math.pi) > 1e-7:
        return f"{value:.2f}"
    numerator, denominator = fraction.numerator, fraction.denominator
    if numerator == 0:
        return "0"
    sign = "−" if numerator < 0 else ""
    numerator = abs(numerator)
    if denominator == 1:
        coefficient = "" if numerator == 1 else str(numerator)
        return f"{sign}{coefficient}π"
    coefficient = "" if numerator == 1 else str(numerator)
    return f"{sign}{coefficient}π/{denominator}"


def _draw_target(ax: plt.Axes, x: float, y: float, color: str) -> None:
    radius = 0.165
    ax.add_patch(Circle((x, y), radius, facecolor="white", edgecolor=color, lw=1.15, zorder=4))
    ax.plot([x - 0.105, x + 0.105], [y, y], color=color, lw=1.05, zorder=5)
    ax.plot([x, x], [y - 0.105, y + 0.105], color=color, lw=1.05, zorder=5)


def _draw_box(ax: plt.Axes, x: float, y: float, label: str, color: str, *, width: float = 0.50) -> None:
    box = FancyBboxPatch(
        (x - width / 2, y - 0.23),
        width,
        0.46,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        facecolor="white",
        edgecolor=color,
        linewidth=1.0,
        zorder=4,
    )
    ax.add_patch(box)
    ax.text(x, y, label, ha="center", va="center", fontsize=5.6, color=color, zorder=5)


def draw_folded_circuit(
    ax: plt.Axes,
    operations: Sequence[DrawOp],
    left_labels: Sequence[str],
    right_labels: Sequence[str],
    *,
    max_columns: int,
    gate_color: str = BLUE,
    label_size: float = 5.8,
    show_time_arrow: bool = True,
) -> None:
    """Draw a complete gate sequence with explicit fold continuity markers."""
    n_qubits = len(left_labels)
    if n_qubits != len(right_labels):
        raise ValueError("left/right wire label count differs")
    if not operations:
        raise ValueError("cannot draw an empty circuit")
    segments = math.ceil(len(operations) / max_columns)
    wire_step = 1.0
    segment_gap = 1.65
    segment_height = (n_qubits - 1) * wire_step + segment_gap
    x_wire_start = 3.05
    x_first_gate = x_wire_start + 0.55
    x_wire_end = x_first_gate + max_columns - 0.25
    total_height = segments * segment_height

    ax.set_xlim(0.0, x_wire_end + 3.3)
    ax.set_ylim(-0.45, total_height + 0.55)
    ax.axis("off")

    for segment in range(segments):
        start = segment * max_columns
        stop = min(len(operations), start + max_columns)
        segment_ops = operations[start:stop]
        top = total_height - segment * segment_height - 0.65
        y_positions = [top - index * wire_step for index in range(n_qubits)]
        is_first = segment == 0
        is_last = segment == segments - 1

        for wire, y in enumerate(y_positions):
            ax.plot([x_wire_start, x_wire_end], [y, y], color=WIRE, lw=0.82, zorder=1)
            short_label = left_labels[wire].split("  ")[0]
            displayed_left = left_labels[wire] if is_first else short_label
            ax.text(
                x_wire_start - 0.20,
                y,
                displayed_left,
                ha="right",
                va="center",
                fontsize=label_size,
                color=INK,
            )
            if is_last:
                ax.text(
                    x_wire_end + 0.20,
                    y,
                    right_labels[wire],
                    ha="left",
                    va="center",
                    fontsize=label_size,
                    color=INK,
                )

        if not is_last:
            ax.text(x_wire_end + 0.04, sum(y_positions) / n_qubits, "»", ha="left", va="center", fontsize=10, color=GREY)
        ax.text(
            0.10,
            top + 0.05,
            f"段 {segment + 1}/{segments} · 门 {start + 1}–{stop}",
            ha="left",
            va="center",
            fontsize=5.4,
            color=GREY,
        )

        for local_index, operation in enumerate(segment_ops):
            x = x_first_gate + local_index
            target_y = y_positions[operation.target]
            if operation.controls:
                involved = list(operation.controls) + [operation.target]
                ax.plot(
                    [x, x],
                    [min(y_positions[index] for index in involved), max(y_positions[index] for index in involved)],
                    color=gate_color,
                    lw=0.95,
                    zorder=2,
                )
                for control in operation.controls:
                    ax.add_patch(Circle((x, y_positions[control]), 0.075, facecolor=gate_color, edgecolor=gate_color, zorder=4))

            if operation.name in {"cnot", "mct", "cx"}:
                _draw_target(ax, x, target_y, gate_color)
            elif operation.name == "x":
                _draw_box(ax, x, target_y, "X", gate_color)
            elif operation.name == "sx":
                _draw_box(ax, x, target_y, "√X", gate_color)
            elif operation.name == "rz":
                _draw_box(ax, x, target_y, f"Rz\n{_angle_label(operation.parameter)}", gate_color, width=0.58)
            else:
                _draw_box(ax, x, target_y, operation.name.upper(), gate_color, width=0.60)

    if show_time_arrow:
        first_top = total_height - 0.65
        arrow_y = first_top + 0.52
        ax.annotate(
            "",
            xy=(x_wire_end, arrow_y),
            xytext=(x_wire_start, arrow_y),
            arrowprops={"arrowstyle": "->", "lw": 0.75, "color": GREY},
        )
        ax.text(x_wire_end + 0.08, arrow_y, "$t$", ha="left", va="center", fontsize=6.2, color=GREY)


def _panel_title(ax: plt.Axes, label: str, title: str, subtitle: str = "", *, accent: str = INK) -> None:
    ax.axis("off")
    ax.text(0.0, 0.58, label, transform=ax.transAxes, fontsize=8.5, fontweight="bold", color=INK, va="center")
    ax.text(0.045, 0.58, title, transform=ax.transAxes, fontsize=8.1, fontweight="bold", color=accent, va="center")
    if subtitle:
        ax.text(1.0, 0.58, subtitle, transform=ax.transAxes, fontsize=6.2, color=GREY, ha="right", va="center")
    ax.plot([0.0, 1.0], [0.08, 0.08], transform=ax.transAxes, color=GRID, lw=0.7, clip_on=False)


def _reduction(baseline: float, proposed: float) -> float:
    return 100.0 * (baseline - proposed) / baseline


def _worked_data(seed: int) -> tuple[BooleanFunction, dict[str, dict], dict[str, tuple]]:
    bf = majority_function(3)
    config = figure_config()
    model_path = str(MODEL) if MODEL.exists() else None
    target_spec = make_cx_line_target(4, bidirectional=True)
    compile_config = CompileConfig(
        optimization_level=1,
        layout_method="trivial",
        routing_method="sabre",
        seed_transpiler=seed,
        hls_ancilla_budget=0,
    )
    rows: dict[str, dict] = {}
    circuits: dict[str, tuple] = {}
    for method in ("direct_anf", "resource_nmcts"):
        artifact = synthesize_artifact(
            method,
            bf,
            config,
            seed=seed,
            model_path=model_path if method == "resource_nmcts" else None,
        )
        circuit = artifact.circuit
        symbolic_ok = bool(verify_oracle(circuit, bf))
        aer = verify_oracle_aer(bf, circuit)
        mapped_artifact = compile_for_target(
            circuit,
            target_spec,
            compile_config,
            bf=bf,
        )
        logical = mapped_artifact.logical
        mapped = mapped_artifact.mapped
        mapped_verification = mapped_artifact.verification
        if mapped_verification is None:
            raise RuntimeError(f"mapped verification missing for {method}")
        metrics = mapped_artifact.metrics
        if not (symbolic_ok and aer.ok and mapped_verification.ok):
            raise RuntimeError(f"worked-example verification failed for {method}")
        row = {
            "figure_group": "worked_example",
            "instance": "maj3",
            "method": method,
            "selected_method": artifact.selected_method,
            "seed": seed,
            "n_inputs": bf.n,
            "truth_table_hex": f"0x{bf.truth_table:02X}",
            "anf_terms": len(anf_monomials(bf)),
            "logic_gate_count": len(circuit.gates),
            "logic_qubits": circuit.n_qubits,
            "logic_T_est": artifact.result.cost.T,
            "logic_CNOT_est": artifact.result.cost.CNOT,
            "logic_depth_est": artifact.result.cost.depth,
            "symbolic_verified": symbolic_ok,
            "aer_verified": bool(aer.ok),
            "aer_basis_states": aer.evaluated,
            "aer_mismatches": aer.mismatches,
            "target_id": target_spec.target_id,
            "target_hash": target_spec.config_hash(),
            "compile_config_hash": compile_config.config_hash(),
            "native_basis": "cx,rz,sx,x",
            "mapped_gate_count": metrics.gates,
            "mapped_depth": metrics.depth,
            "mapped_twoq_count": metrics.twoq_count,
            "mapped_twoq_depth": metrics.twoq_depth,
            "routing_gate_delta": metrics.routing_gate_delta,
            "routing_depth_delta": metrics.routing_depth_delta,
            "routing_twoq_delta": metrics.routing_twoq_delta,
            "target_violations": metrics.unsupported_instructions,
            "mapped_oracle_verified": mapped_verification.ok,
            "mapped_verification_mode": mapped_verification.mode,
            "mapped_verification_cases": mapped_verification.evaluated,
            "mapped_max_leakage": mapped_verification.max_leakage,
            "mapped_max_phase_error": mapped_verification.max_phase_error,
        }
        rows[method] = row
        circuits[method] = (circuit, logical, mapped, mapped_artifact)
    return bf, rows, circuits


def make_logical_figure(bf: BooleanFunction, rows: dict[str, dict], circuits: dict[str, tuple]) -> list[str]:
    direct = rows["direct_anf"]
    ours = rows["resource_nmcts"]
    direct_circuit = circuits["direct_anf"][0]
    ours_circuit = circuits["resource_nmcts"][0]

    fig = plt.figure(figsize=(183 * MM, 192 * MM))
    outer = fig.add_gridspec(7, 1, height_ratios=[0.72, 1.45, 0.35, 1.55, 0.35, 1.75, 1.05], hspace=0.08)

    title_ax = fig.add_subplot(outer[0])
    title_ax.axis("off")
    title_ax.text(
        0.0,
        0.78,
        "maj3 单实例：同一 Boolean Oracle 的逻辑线路与资源配对比较",
        fontsize=11.0,
        fontweight="bold",
        color=INK,
        va="center",
    )
    title_ax.text(
        0.0,
        0.18,
        "结论：在功能等价约束下，Resource-NMCTS 用仿射复用降低 T/CNOT/深度；本图不把单例收益归因于神经先验。",
        fontsize=6.4,
        color=GREY,
        va="center",
    )

    contract = fig.add_subplot(outer[1])
    contract.axis("off")
    contract.text(0.0, 0.96, "a", fontsize=8.5, fontweight="bold", color=INK, va="top")
    contract.text(0.05, 0.96, "Oracle 功能契约", fontsize=8.1, fontweight="bold", color=INK, va="top")
    contract.text(0.05, 0.67, r"$f(x_0,x_1,x_2)=x_0x_1\oplus x_0x_2\oplus x_1x_2$", fontsize=9.2, color=BLUE)
    contract.text(0.05, 0.38, r"$U_f: |x\rangle|y\rangle\mapsto|x\rangle|y\oplus f(x)\rangle$", fontsize=8.4, color=INK)
    contract.text(0.05, 0.12, "真值表 0xE8 · ON-set = {3, 5, 6, 7}", fontsize=6.6, color=GREY)
    table_rows = []
    for value in range(8):
        bits = [(value >> index) & 1 for index in range(3)]
        table_rows.append([*bits, bf.evaluate(value)])
    table = contract.table(
        cellText=table_rows,
        colLabels=[r"$x_0$", r"$x_1$", r"$x_2$", "$f$"],
        cellLoc="center",
        colLoc="center",
        bbox=[0.69, 0.02, 0.30, 0.92],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(5.4)
    for (row, _column), cell in table.get_celld().items():
        cell.set_linewidth(0.45)
        cell.set_edgecolor(GRID)
        cell.set_facecolor(LIGHT_BLUE if row == 0 else "white")

    head_b = fig.add_subplot(outer[2])
    _panel_title(
        head_b,
        "b",
        f"Direct-ANF 基线：{sum(op.name == 'mct' for op in _engine_ops(direct_circuit))} 个多控 X",
        f"T={direct['logic_T_est']} · CNOT={direct['logic_CNOT_est']} · depth={direct['logic_depth_est']}",
        accent=GREY,
    )
    ax_b = fig.add_subplot(outer[3])
    left, right = _oracle_wire_labels(bf.n, direct_circuit.n_qubits)
    draw_folded_circuit(ax_b, _engine_ops(direct_circuit), left, right, max_columns=10, gate_color=GREY)

    head_c = fig.add_subplot(outer[4])
    _panel_title(
        head_c,
        "c",
        f"Resource-NMCTS：真实获胜线路（{ours['selected_method']}）",
        f"T={ours['logic_T_est']} · CNOT={ours['logic_CNOT_est']} · depth={ours['logic_depth_est']}",
        accent=BLUE,
    )
    ax_c = fig.add_subplot(outer[5])
    left, right = _oracle_wire_labels(bf.n, ours_circuit.n_qubits)
    draw_folded_circuit(ax_c, _engine_ops(ours_circuit), left, right, max_columns=10, gate_color=BLUE)

    metrics = fig.add_subplot(outer[6])
    metrics.axis("off")
    metrics.text(0.0, 0.95, "d", fontsize=8.5, fontweight="bold", color=INK, va="top")
    metrics.text(0.05, 0.95, "同实例逻辑资源（项目成本模型）", fontsize=8.1, fontweight="bold", color=INK, va="top")
    cell_text = []
    for field, label in (
        ("logic_T_est", "T-count"),
        ("logic_CNOT_est", "CNOT-count"),
        ("logic_depth_est", "逻辑深度"),
    ):
        cell_text.append(
            [
                label,
                direct[field],
                ours[field],
                f"−{_reduction(direct[field], ours[field]):.1f}%",
            ]
        )
    metric_table = metrics.table(
        cellText=cell_text,
        colLabels=["指标", "Direct-ANF", "Resource-NMCTS", "相对降低"],
        cellLoc="center",
        colLoc="center",
        bbox=[0.05, 0.10, 0.73, 0.68],
    )
    metric_table.auto_set_font_size(False)
    metric_table.set_fontsize(6.2)
    for (row, column), cell in metric_table.get_celld().items():
        cell.set_linewidth(0.55)
        cell.set_edgecolor(GRID)
        if row == 0:
            cell.set_facecolor(LIGHT_GREY)
            cell.set_text_props(weight="bold", color=INK)
        elif column == 3:
            cell.set_text_props(color=GREEN, weight="bold")
    metrics.text(0.82, 0.63, "验证", fontsize=7.0, fontweight="bold", color=INK)
    metrics.text(0.82, 0.43, "通过 · 符号验证", fontsize=6.4, color=GREEN)
    metrics.text(0.82, 0.25, f"通过 · Aer y=0: {ours['aer_basis_states']}/{ours['aer_basis_states']}", fontsize=6.4, color=GREEN)
    metrics.text(0.82, 0.07, "通过 · 0 mismatch", fontsize=6.4, color=GREEN)

    fig.subplots_adjust(top=0.985, bottom=0.025, left=0.025, right=0.985)
    return _save(fig, "F0_standard_oracle_comparison")


def _layout_text(layout: Sequence[int], n_inputs: int) -> str:
    roles = []
    for logical, physical in enumerate(layout):
        role = _logical_role(logical, n_inputs).replace("_{", "").replace("}", "")
        roles.append(f"{role}→p{physical}")
    return ", ".join(roles)


def _draw_line_topology(
    ax: plt.Axes,
    initial_direct: Sequence[int],
    final_direct: Sequence[int],
    initial_ours: Sequence[int],
    final_ours: Sequence[int],
    n_inputs: int,
) -> None:
    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.text(0.0, 0.92, "a", transform=ax.transAxes, fontsize=8.5, fontweight="bold", color=INK, va="top")
    ax.text(0.05, 0.92, "四比特最近邻线性拓扑代理与布局", transform=ax.transAxes, fontsize=8.1, fontweight="bold", color=INK, va="top")
    xs = [0.25, 0.42, 0.59, 0.76]
    y = 0.54
    for left, right in zip(xs[:-1], xs[1:]):
        ax.plot([left, right], [y, y], color=WIRE, lw=1.2, transform=ax.transAxes)
    ax.scatter(xs, [y] * len(xs), s=310, facecolors="white", edgecolors=BLUE, linewidths=1.2, transform=ax.transAxes, zorder=3)
    for index, x in enumerate(xs):
        ax.text(x, y, f"p{index}", transform=ax.transAxes, ha="center", va="center", fontsize=6.1, color=INK)
    if list(initial_direct) != list(initial_ours):
        raise AssertionError("paired mapping must use the same initial logical-to-physical layout")
    ax.text(
        0.05,
        0.27,
        f"共同初始布局：{_layout_text(initial_direct, n_inputs)}",
        transform=ax.transAxes,
        fontsize=5.9,
        color=GREY,
    )
    ax.text(
        0.05,
        0.08,
        f"Direct 末端：{_layout_text(final_direct, n_inputs)}",
        transform=ax.transAxes,
        fontsize=5.9,
        color=GREY,
    )
    ax.text(
        0.52,
        0.08,
        f"NMCTS 末端：{_layout_text(final_ours, n_inputs)}",
        transform=ax.transAxes,
        fontsize=5.9,
        color=GREY,
    )
    ax.text(0.99, 0.86, "合成拓扑代理；非具体芯片后端", transform=ax.transAxes, fontsize=5.8, color=ORANGE, ha="right", va="top")


def make_hardware_figure(bf: BooleanFunction, rows: dict[str, dict], circuits: dict[str, tuple], seed: int) -> list[str]:
    direct = rows["direct_anf"]
    ours = rows["resource_nmcts"]
    direct_mapped = circuits["direct_anf"][2]
    ours_mapped = circuits["resource_nmcts"][2]
    direct_left, direct_right, direct_initial, direct_final = _physical_wire_labels(direct_mapped, bf.n)
    ours_left, ours_right, ours_initial, ours_final = _physical_wire_labels(ours_mapped, bf.n)

    fig = plt.figure(figsize=(183 * MM, 254 * MM))
    outer = fig.add_gridspec(
        7,
        1,
        height_ratios=[0.56, 1.12, 0.30, 3.85, 0.30, 2.95, 1.18],
        hspace=0.07,
    )
    title = fig.add_subplot(outer[0])
    title.axis("off")
    title.text(
        0.0,
        0.76,
        "maj3 单实例：最近邻拓扑上的完整原生门线路配对比较",
        fontsize=11.0,
        fontweight="bold",
        color=INK,
    )
    title.text(
        0.0,
        0.15,
        "逻辑层与物理层分图报告；长线路按严格门序折行，段号给出连续范围。",
        fontsize=6.4,
        color=GREY,
    )

    topology = fig.add_subplot(outer[1])
    _draw_line_topology(
        topology,
        direct_initial,
        direct_final,
        ours_initial,
        ours_final,
        bf.n,
    )

    direct_head = fig.add_subplot(outer[2])
    _panel_title(
        direct_head,
        "b",
        "Direct-ANF 经固定初始布局 + SABRE 路由后的完整线路",
        f"basis=cx,rz,sx,x · seed={seed} · {direct['mapped_gate_count']} gates",
        accent=GREY,
    )
    direct_ax = fig.add_subplot(outer[3])
    draw_folded_circuit(
        direct_ax,
        _native_ops(direct_mapped),
        direct_left,
        direct_right,
        max_columns=17,
        gate_color=GREY,
        label_size=5.5,
    )

    ours_head = fig.add_subplot(outer[4])
    _panel_title(
        ours_head,
        "c",
        "Resource-NMCTS 经相同设置映射后的完整线路",
        f"basis=cx,rz,sx,x · seed={seed} · {ours['mapped_gate_count']} gates",
        accent=BLUE,
    )
    ours_ax = fig.add_subplot(outer[5])
    draw_folded_circuit(
        ours_ax,
        _native_ops(ours_mapped),
        ours_left,
        ours_right,
        max_columns=17,
        gate_color=BLUE,
        label_size=5.5,
    )

    metrics = fig.add_subplot(outer[6])
    metrics.axis("off")
    metrics.text(0.0, 0.94, "d", fontsize=8.5, fontweight="bold", color=INK, va="top")
    metrics.text(0.05, 0.94, "映射层配对结果与验证边界", fontsize=8.1, fontweight="bold", color=INK, va="top")
    table_rows = []
    for field, label in (
        ("mapped_gate_count", "原生总门数"),
        ("mapped_twoq_count", "CX 数"),
        ("mapped_depth", "映射深度"),
    ):
        table_rows.append([label, direct[field], ours[field], f"−{_reduction(direct[field], ours[field]):.1f}%"])
    table = metrics.table(
        cellText=table_rows,
        colLabels=["指标", "Direct-ANF", "Resource-NMCTS", "相对降低"],
        cellLoc="center",
        colLoc="center",
        bbox=[0.05, 0.08, 0.66, 0.68],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(6.0)
    for (row, column), cell in table.get_celld().items():
        cell.set_linewidth(0.55)
        cell.set_edgecolor(GRID)
        if row == 0:
            cell.set_facecolor(LIGHT_GREY)
            cell.set_text_props(weight="bold", color=INK)
        elif column == 3:
            cell.set_text_props(color=GREEN, weight="bold")
    metrics.text(0.75, 0.68, "通过 · 两条线路目标边违规：0", fontsize=6.1, color=GREEN)
    metrics.text(
        0.75,
        0.48,
        f"通过 · 完整 (x,y) + 相位：{ours['mapped_verification_cases']}/{ours['mapped_verification_cases']}",
        fontsize=6.1,
        color=GREEN,
    )
    metrics.text(0.75, 0.28, f"Qiskit {qiskit.__version__}", fontsize=5.9, color=GREY)
    metrics.text(0.75, 0.10, "不含校准/噪声，不能外推真实芯片保真度", fontsize=5.6, color=ORANGE)

    fig.subplots_adjust(top=0.985, bottom=0.025, left=0.025, right=0.985)
    return _save(fig, "F1_standard_hardware_mapping")


def _gallery_specs() -> list[tuple[str, str, BooleanFunction]]:
    return [
        ("maj5", "5 输入多数表决", majority_function(5)),
        ("thr6_t2", "6 输入阈值函数（至少 2 个 1）", threshold_function(6, 2)),
        ("thr7_t4", "7 输入阈值函数（至少 4 个 1）", threshold_function(7, 4)),
        ("randtt5_s3", "5 输入随机真值表（seed 3）", random_truth_function(5, random.Random(3))),
        ("randtt5_s17", "5 输入随机真值表（seed 17）", random_truth_function(5, random.Random(17))),
        ("randanf6_s23", "6 输入随机 ANF（seed 23）", random_anf_function(6, random.Random(23))),
    ]


def _gallery_rows(seed: int) -> tuple[list[dict], list[tuple[str, BooleanFunction, EngineCircuit, dict]]]:
    config = figure_config()
    model_path = str(MODEL) if MODEL.exists() else None
    rows: list[dict] = []
    items: list[tuple[str, BooleanFunction, EngineCircuit, dict]] = []
    for fid, label, bf in _gallery_specs():
        artifact = synthesize_artifact("resource_nmcts", bf, config, seed=seed, model_path=model_path)
        circuit = artifact.circuit
        symbolic_ok = bool(verify_oracle(circuit, bf))
        aer = verify_oracle_aer(bf, circuit)
        if not (symbolic_ok and aer.ok):
            raise RuntimeError(f"gallery verification failed for {fid}")
        row = {
            "figure_group": "gallery",
            "instance": fid,
            "function": label,
            "method": "resource_nmcts",
            "selected_method": artifact.selected_method,
            "seed": seed,
            "n_inputs": bf.n,
            "truth_table_hex": hex(bf.truth_table),
            "anf_terms": len(anf_monomials(bf)),
            "logic_gate_count": len(circuit.gates),
            "logic_qubits": circuit.n_qubits,
            "logic_T_est": artifact.result.cost.T,
            "logic_CNOT_est": artifact.result.cost.CNOT,
            "logic_depth_est": artifact.result.cost.depth,
            "symbolic_verified": symbolic_ok,
            "aer_verified": bool(aer.ok),
            "aer_basis_states": aer.evaluated,
            "aer_mismatches": aer.mismatches,
        }
        rows.append(row)
        items.append((label, bf, circuit, row))
    return rows, items


def _gallery_page(items: Sequence[tuple[str, BooleanFunction, EngineCircuit, dict]], stem: str, title: str) -> list[str]:
    fig = plt.figure(figsize=(183 * MM, 254 * MM))
    outer = fig.add_gridspec(7, 1, height_ratios=[0.65, 0.34, 1.65, 0.34, 1.85, 0.34, 2.05], hspace=0.06)
    heading = fig.add_subplot(outer[0])
    heading.axis("off")
    heading.text(0.0, 0.74, title, fontsize=10.5, fontweight="bold", color=INK)
    heading.text(
        0.0,
        0.16,
        "所有线路均由公开综合产物 API 生成；数据线、输出线与辅助线显式标注，折行不省略任何门。",
        fontsize=6.2,
        color=GREY,
    )
    for index, (label, bf, circuit, row) in enumerate(items):
        head = fig.add_subplot(outer[1 + 2 * index])
        _panel_title(
            head,
            chr(ord("a") + index),
            label,
            f"winner={row['selected_method']} · gates={row['logic_gate_count']} · T={row['logic_T_est']} · CNOT={row['logic_CNOT_est']} · Aer {row['aer_basis_states']}/{row['aer_basis_states']}",
            accent=BLUE,
        )
        ax = fig.add_subplot(outer[2 + 2 * index])
        left, right = _oracle_wire_labels(bf.n, circuit.n_qubits)
        draw_folded_circuit(
            ax,
            _engine_ops(circuit),
            left,
            right,
            max_columns=18,
            gate_color=BLUE,
            label_size=5.1,
            show_time_arrow=False,
        )
    fig.subplots_adjust(top=0.985, bottom=0.02, left=0.02, right=0.985)
    return _save(fig, stem)


def make_gallery(seed: int) -> tuple[list[dict], list[str]]:
    rows, items = _gallery_rows(seed)
    outputs = _gallery_page(
        items[:3],
        "A1a_standard_circuit_gallery_structured",
        "程序生成的 Oracle 线路实例 I：结构化函数",
    )
    outputs.extend(
        _gallery_page(
            items[3:],
            "A1b_standard_circuit_gallery_randomized",
            "程序生成的 Oracle 线路实例 II：随机函数",
        )
    )
    return rows, outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-gallery", action="store_true")
    args = parser.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    bf, worked_rows, circuits = _worked_data(args.seed)
    artifacts = make_logical_figure(bf, worked_rows, circuits)
    artifacts.extend(make_hardware_figure(bf, worked_rows, circuits, args.seed))
    records = list(worked_rows.values())
    if not args.skip_gallery:
        gallery_rows, gallery_artifacts = make_gallery(args.seed)
        records.extend(gallery_rows)
        artifacts.extend(gallery_artifacts)

    source_path = OUTDIR / "standard_circuit_figure_source.csv"
    pd.DataFrame(records).to_csv(source_path, index=False, encoding="utf-8-sig")
    artifacts.append(str(source_path.relative_to(ROOT)))

    manifest = {
        "purpose": "XA-202609 standards-compliant circuit figures",
        "contract": "submission_competition/figures/CIRCUIT_FIGURE_CONTRACT.md",
        "generator": str(Path(__file__).resolve().relative_to(ROOT)),
        "seed": args.seed,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "qiskit": qiskit.__version__,
        "qiskit_aer": qiskit_aer.__version__,
        "model": str(MODEL.relative_to(ROOT)) if MODEL.exists() else None,
        "model_sha256": _sha256(MODEL) if MODEL.exists() else None,
        "source_api": "src.synthesizers.synthesize_artifact",
        "logical_verifier": "src.factor_plan.verify_oracle",
        "aer_verifier": "src.hardware_map.verify_oracle_aer",
        "topology_compiler": "src.hardware_map.compile_for_target",
        "mapped_verifier": "src.hardware_map.verify_mapped_oracle",
        "mapping_note": "explicit four-qubit CX line target; trivial initial layout + SABRE routing; not a calibrated backend",
        "all_rows_verified": all(
            bool(row.get("symbolic_verified")) and bool(row.get("aer_verified"))
            for row in records
        ),
        "artifacts": artifacts,
    }
    manifest_path = OUTDIR / "standard_circuit_figure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(pd.DataFrame(records).to_string(index=False))
    print("\nGenerated:")
    for artifact in artifacts + [str(manifest_path.relative_to(ROOT))]:
        print(f"  {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
