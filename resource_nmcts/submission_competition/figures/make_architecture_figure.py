#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the traceable XA-202609 end-to-end system architecture figure.

The figure is intentionally schematic: it documents the implemented evidence
flow and its compute/epistemic boundaries, but reports no performance effect.
Run from ``resource_nmcts/`` with the mcts-qoracle interpreter.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "submission_competition" / "figures"
STEM = "F2_system_architecture"
SOURCE_PATH = OUTDIR / "architecture_figure_source.json"
MANIFEST_PATH = OUTDIR / "architecture_figure_manifest.json"
CONTRACT_PATH = OUTDIR / "FIGURE_CONTRACT_ARCHITECTURE.md"
ENVIRONMENT_PATH = ROOT / "submission_competition" / "environment_manifest.json"

WIDTH_MM = 183.0
HEIGHT_MM = 105.0
MM = 1.0 / 25.4

# Restrained, color-blind-tolerant semantics: blue=implemented flow,
# green=passed evidence, amber=boundary/caution, grey=neutral/control.
INK = "#172532"
MUTED = "#5F6D79"
WIRE = "#6C7A86"
BLUE = "#175AA6"
BLUE_DARK = "#124478"
BLUE_LIGHT = "#EAF2FA"
TEAL = "#177A72"
TEAL_LIGHT = "#E8F5F2"
GREEN = "#2A7C5F"
GREEN_LIGHT = "#EAF5EF"
AMBER = "#B56A1F"
AMBER_LIGHT = "#FFF3E4"
RED = "#A44B43"
GREY = "#6D7984"
GREY_LIGHT = "#F2F5F7"
PANEL = "#FBFCFD"
GRID = "#C9D2D9"
WHITE = "#FFFFFF"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _resolved_font() -> tuple[str, list[str]]:
    preferred = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
    installed = {item.name for item in font_manager.fontManager.ttflist}
    for candidate in preferred:
        if candidate in installed:
            return candidate, preferred
    return "DejaVu Sans", preferred


RESOLVED_FONT, FONT_FALLBACK = _resolved_font()

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": FONT_FALLBACK,
        "font.size": 6.2,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
    }
)


def build_source() -> dict[str, Any]:
    """Build the machine-readable evidence map used to draw the figure."""
    evidence_roles = {
        "src/competition_benchmarks.py": "frozen benchmark definitions and function identities",
        "src/synthesizers.py": "public SynthesisArtifact API and portfolio selection",
        "src/neural_policy.py": "learned, uniform, and random prior scorers",
        "src/hardware_map.py": "Qiskit conversion, topology mapping, and exact mapped verification",
        "scripts/run_hardware_validation.py": "synthesis-once/map-many experiment runner",
        "src/hardware_validation_ingest.py": "validated JSONL ingestion and failure preservation",
        "src/experiment_db.py": "append-only DuckDB schema, attempts, verification, and provenance",
    }
    evidence = []
    for relative_path, role in evidence_roles.items():
        path = ROOT / relative_path
        if not path.exists():
            raise FileNotFoundError(f"required architecture evidence missing: {path}")
        evidence.append(
            {
                "path": relative_path,
                "role": role,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )

    if not ENVIRONMENT_PATH.exists():
        raise FileNotFoundError(f"environment manifest missing: {ENVIRONMENT_PATH}")
    environment = json.loads(ENVIRONMENT_PATH.read_text(encoding="utf-8"))
    devices = environment.get("gpu", {}).get("devices", [])
    gpu_name = devices[0].get("name") if devices else "not detected"
    aer_devices = environment.get("aer", {}).get("available_devices", [])

    source = {
        "schema_version": 1,
        "figure_id": STEM,
        "competition": "XA-202609",
        "core_conclusion": (
            "The implemented system closes the loop from ablatable candidate ranking through "
            "executable circuit artifacts and topology-aware compilation to exact verification "
            "and append-only evidence archival; learned-prior gain is not assumed."
        ),
        "archetype": "schematic-led composite",
        "dimensions_mm": {"width": WIDTH_MM, "height": HEIGHT_MM},
        "panels": {
            "a": {
                "title": "端到端主流程",
                "nodes": [
                    {
                        "id": "input",
                        "title": "Boolean 函数",
                        "detail": ["冻结 benchmark", "真值表 + 函数哈希"],
                    },
                    {
                        "id": "candidates",
                        "title": "候选综合",
                        "detail": ["ANF / FPRM", "affine / Direct"],
                    },
                    {
                        "id": "search",
                        "title": "搜索与排序",
                        "detail": ["heuristic / MCTS", "learned prior 可消融"],
                    },
                    {
                        "id": "artifact",
                        "title": "SynthesisArtifact",
                        "detail": ["真实 gate list", "winner + 逻辑资源"],
                    },
                    {
                        "id": "mapping",
                        "title": "拓扑约束编译",
                        "detail": ["Qiskit Target", "layout + SABRE"],
                    },
                    {
                        "id": "native",
                        "title": "原生门线路",
                        "detail": ["native basis", "物理比特 + 耦合边"],
                    },
                ],
                "controls": ["heuristic", "uniform", "random", "learned prior"],
                "control_policy": "same search budget; learned prior can be disabled",
                "claim_boundary": (
                    "Portfolio-level gains must not be attributed to the learned prior without "
                    "matched ablation evidence."
                ),
            },
            "b": {
                "title": "验证与证据闭环",
                "verification_gates": [
                    {"id": "truth", "title": "符号真值", "detail": "全输入逻辑检查"},
                    {"id": "logical", "title": "逻辑线路", "detail": "artifact 一致性"},
                    {"id": "target", "title": "原生门/耦合", "detail": "Target 合法性"},
                    {"id": "exact", "title": "精确 (x,y)", "detail": "相位·辅助位·泄漏"},
                ],
                "pass_sink": ["append-only JSONL", "DuckDB typed facts"],
                "failure_policy": "Failures remain as status/error evidence in the audit trail.",
            },
            "c": {
                "title": "算力分工与外推边界",
                "compute": [
                    {
                        "role": "model",
                        "device": gpu_name,
                        "runtime": f"PyTorch {environment.get('key_packages', {}).get('torch', 'unknown')}",
                        "work": "模型训练 / 批推理",
                    },
                    {
                        "role": "verification",
                        "device": f"Aer device={','.join(aer_devices) or 'unknown'}",
                        "runtime": f"Qiskit Aer {environment.get('key_packages', {}).get('qiskit-aer', 'unknown')}",
                        "work": "无噪声精确验证",
                    },
                ],
                "boundary": (
                    "Synthetic Target is a topology/basis proxy, not a calibrated device; "
                    "no real-hardware fidelity or noise claim is made."
                ),
            },
        },
        "environment_snapshot": {
            "path": _relative(ENVIRONMENT_PATH),
            "sha256": _sha256(ENVIRONMENT_PATH),
            "captured_at_utc": environment.get("captured_at_utc"),
            "environment_name": environment.get("environment_name"),
            "python": environment.get("python", {}).get("version"),
            "gpu_name": gpu_name,
            "torch_cuda_available": environment.get("gpu", {}).get("torch_cuda_available"),
            "aer_available_devices": aer_devices,
        },
        "evidence_files": evidence,
        "claim_policy": {
            "performance_statistics_in_figure": False,
            "learned_prior_independent_gain_claimed": False,
            "aer_gpu_claimed": False,
            "real_hardware_execution_claimed": False,
            "noise_awareness_claimed": False,
        },
    }
    SOURCE_PATH.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    return source


def _round_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    face: str = WHITE,
    edge: str = GRID,
    linewidth: float = 0.8,
    radius: float = 0.012,
    linestyle: str = "-",
    zorder: int = 2,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle=f"round,pad=0.004,rounding_size={radius}",
        facecolor=face,
        edgecolor=edge,
        linewidth=linewidth,
        linestyle=linestyle,
        transform=ax.transAxes,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = WIRE,
    linewidth: float = 1.0,
    linestyle: str = "-",
    mutation_scale: float = 8.0,
    zorder: int = 4,
    connectionstyle: str = "arc3",
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=mutation_scale,
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            connectionstyle=connectionstyle,
            transform=ax.transAxes,
            zorder=zorder,
        )
    )


def _panel_frame(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    letter: str,
    title: str,
) -> None:
    _round_box(ax, x, y, width, height, face=PANEL, edge=GRID, linewidth=0.8, radius=0.010, zorder=0)
    ax.text(x + 0.014, y + height - 0.026, letter, transform=ax.transAxes, fontsize=8.6,
            fontweight="bold", color=INK, va="top", zorder=6)
    ax.text(x + 0.043, y + height - 0.026, title, transform=ax.transAxes, fontsize=7.5,
            fontweight="bold", color=INK, va="top", zorder=6)


def _truth_icon(ax: plt.Axes, x: float, y: float, color: str) -> None:
    size = 0.026
    for row in range(2):
        for col in range(2):
            ax.add_patch(
                Rectangle(
                    (x + col * size, y + row * size),
                    size - 0.002,
                    size - 0.002,
                    facecolor=BLUE_LIGHT if (row + col) % 2 else WHITE,
                    edgecolor=color,
                    linewidth=0.45,
                    transform=ax.transAxes,
                    zorder=5,
                )
            )


def _candidate_icon(ax: plt.Axes, x: float, y: float, color: str) -> None:
    labels = ("A", "F", "L", "D")
    for index, label in enumerate(labels):
        cx = x + (index % 2) * 0.034
        cy = y + (index // 2) * 0.029
        _round_box(ax, cx, cy, 0.027, 0.021, face=WHITE, edge=color, linewidth=0.6, radius=0.003, zorder=5)
        ax.text(cx + 0.0135, cy + 0.0105, label, transform=ax.transAxes, fontsize=6.0,
                ha="center", va="center", color=color, fontweight="bold", zorder=6)


def _tree_icon(ax: plt.Axes, x: float, y: float, color: str) -> None:
    root = (x + 0.031, y + 0.052)
    children = [(x + 0.008, y + 0.020), (x + 0.031, y + 0.020), (x + 0.054, y + 0.020)]
    for child in children:
        ax.plot([root[0], child[0]], [root[1], child[1]], color=color, lw=0.7,
                transform=ax.transAxes, zorder=5)
    for point in [root, *children]:
        ax.add_patch(Circle(point, 0.0045, facecolor=WHITE, edgecolor=color,
                            linewidth=0.7, transform=ax.transAxes, zorder=6))


def _artifact_icon(ax: plt.Axes, x: float, y: float, color: str) -> None:
    ax.add_patch(Rectangle((x, y), 0.052, 0.058, facecolor=WHITE, edgecolor=color,
                           linewidth=0.7, transform=ax.transAxes, zorder=5))
    for offset, width in ((0.044, 0.033), (0.032, 0.041), (0.020, 0.028), (0.008, 0.038)):
        ax.plot([x + 0.008, x + 0.008 + width], [y + offset, y + offset],
                color=color, lw=0.7, transform=ax.transAxes, zorder=6)


def _topology_icon(ax: plt.Axes, x: float, y: float, color: str) -> None:
    points = [(x + 0.005, y + 0.015), (x + 0.028, y + 0.049),
              (x + 0.055, y + 0.038), (x + 0.066, y + 0.008)]
    for left, right in zip(points[:-1], points[1:]):
        ax.plot([left[0], right[0]], [left[1], right[1]], color=color, lw=0.9,
                transform=ax.transAxes, zorder=5)
    for point in points:
        ax.add_patch(Circle(point, 0.005, facecolor=WHITE, edgecolor=color,
                            linewidth=0.8, transform=ax.transAxes, zorder=6))


def _circuit_icon(ax: plt.Axes, x: float, y: float, color: str) -> None:
    for offset in (0.011, 0.030, 0.049):
        ax.plot([x, x + 0.070], [y + offset, y + offset], color=WIRE, lw=0.6,
                transform=ax.transAxes, zorder=5)
    ax.plot([x + 0.026, x + 0.026], [y + 0.011, y + 0.049], color=color, lw=0.8,
            transform=ax.transAxes, zorder=6)
    ax.add_patch(Circle((x + 0.026, y + 0.049), 0.0038, facecolor=color,
                        edgecolor=color, transform=ax.transAxes, zorder=7))
    ax.add_patch(Circle((x + 0.026, y + 0.011), 0.007, facecolor=WHITE,
                        edgecolor=color, linewidth=0.8, transform=ax.transAxes, zorder=7))
    ax.plot([x + 0.019, x + 0.033], [y + 0.011, y + 0.011], color=color, lw=0.7,
            transform=ax.transAxes, zorder=8)
    ax.plot([x + 0.026, x + 0.026], [y + 0.004, y + 0.018], color=color, lw=0.7,
            transform=ax.transAxes, zorder=8)
    _round_box(ax, x + 0.048, y + 0.022, 0.017, 0.017, face=BLUE_LIGHT,
               edge=color, linewidth=0.6, radius=0.002, zorder=6)


def _draw_process_node(
    ax: plt.Axes,
    node: dict[str, Any],
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
    icon,
) -> None:
    _round_box(ax, x, y, width, height, face=WHITE, edge=color, linewidth=1.0, radius=0.009, zorder=2)
    ax.add_patch(Rectangle((x, y + height - 0.031), width, 0.031, facecolor=color,
                           edgecolor="none", transform=ax.transAxes, zorder=3))
    ax.text(x + width / 2, y + height - 0.0155, node["title"], transform=ax.transAxes,
            fontsize=6.5, fontweight="bold", color=WHITE, ha="center", va="center", zorder=6)
    icon_x = x + width / 2 - 0.032
    icon_y = y + 0.057
    icon(ax, icon_x, icon_y, color)
    ax.text(x + width / 2, y + 0.038, node["detail"][0], transform=ax.transAxes,
            fontsize=6.0, color=INK, ha="center", va="center", zorder=6)
    ax.text(x + width / 2, y + 0.018, node["detail"][1], transform=ax.transAxes,
            fontsize=6.0, color=MUTED, ha="center", va="center", zorder=6)


def _draw_panel_a(ax: plt.Axes, source: dict[str, Any]) -> None:
    x, y, width, height = 0.018, 0.435, 0.964, 0.455
    _panel_frame(ax, x, y, width, height, "a", "端到端主流程：从冻结函数到可执行原生门线路")

    # Same-budget ablation ribbon sits above the search node and is linked by
    # a dashed control arrow, separating control conditions from the data flow.
    ribbon_x, ribbon_y, ribbon_w, ribbon_h = 0.264, 0.790, 0.392, 0.050
    _round_box(ax, ribbon_x, ribbon_y, ribbon_w, ribbon_h, face=GREY_LIGHT,
               edge=GREY, linewidth=0.7, radius=0.007, linestyle="--", zorder=2)
    ax.text(ribbon_x + 0.012, ribbon_y + ribbon_h / 2,
            "统一预算消融  heuristic  |  uniform  |  random  |  learned prior（可关闭）",
            transform=ax.transAxes, fontsize=6.0, color=INK, va="center", zorder=6)

    note_x, note_y, note_w, note_h = 0.672, 0.790, 0.285, 0.050
    _round_box(ax, note_x, note_y, note_w, note_h, face=AMBER_LIGHT,
               edge=AMBER, linewidth=0.7, radius=0.007, zorder=2)
    ax.text(note_x + 0.012, note_y + note_h / 2,
            "审计边界：当前不主张 learned prior 的独立增益",
            transform=ax.transAxes, fontsize=6.0, color=AMBER, va="center", zorder=6)

    nodes = source["panels"]["a"]["nodes"]
    xs = [0.040, 0.196, 0.352, 0.508, 0.664, 0.820]
    node_w, node_y, node_h = 0.130, 0.535, 0.205
    colors = [BLUE, BLUE, TEAL, BLUE_DARK, TEAL, BLUE]
    icons = [_truth_icon, _candidate_icon, _tree_icon, _artifact_icon, _topology_icon, _circuit_icon]
    for index, (node, node_x, color, icon) in enumerate(zip(nodes, xs, colors, icons)):
        _draw_process_node(ax, node, node_x, node_y, node_w, node_h, color, icon)
        if index < len(nodes) - 1:
            _arrow(ax, (node_x + node_w + 0.003, node_y + 0.104),
                   (xs[index + 1] - 0.006, node_y + 0.104), color=WIRE, linewidth=0.9)

    # Control enters ranking only; this is visually distinct from the solid
    # artifact/compilation data flow.
    _arrow(ax, (0.430, ribbon_y), (0.417, node_y + node_h + 0.005),
           color=GREY, linewidth=0.8, linestyle="--", mutation_scale=7)

    ax.text(0.105, 0.500, "冻结输入", transform=ax.transAxes, fontsize=6.0,
            color=MUTED, ha="center", va="center")
    ax.text(0.417, 0.500, "候选排序信号", transform=ax.transAxes, fontsize=6.0,
            color=MUTED, ha="center", va="center")
    ax.text(0.573, 0.500, "公共 artifact API", transform=ax.transAxes, fontsize=6.0,
            color=MUTED, ha="center", va="center")
    ax.text(0.885, 0.500, "线路进入逐级验证", transform=ax.transAxes, fontsize=6.0,
            color=GREEN, ha="center", va="center", fontweight="bold")


def _gate_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    title: str,
    detail: str,
    index: int,
) -> None:
    _round_box(ax, x, y, width, 0.112, face=WHITE, edge=GREEN,
               linewidth=0.85, radius=0.007, zorder=2)
    ax.add_patch(Circle((x + 0.018, y + 0.088), 0.010, facecolor=GREEN,
                        edgecolor=GREEN, transform=ax.transAxes, zorder=5))
    ax.text(x + 0.018, y + 0.088, str(index), transform=ax.transAxes,
            fontsize=6.0, color=WHITE, ha="center", va="center", fontweight="bold", zorder=6)
    ax.text(x + 0.035, y + 0.087, title, transform=ax.transAxes, fontsize=6.2,
            color=INK, ha="left", va="center", fontweight="bold", zorder=6)
    ax.text(x + width / 2, y + 0.038, detail, transform=ax.transAxes, fontsize=6.0,
            color=MUTED, ha="center", va="center", zorder=6)


def _database_icon(ax: plt.Axes, x: float, y: float, width: float, height: float) -> None:
    body_h = height - 0.018
    ax.add_patch(Rectangle((x, y + 0.009), width, body_h, facecolor=BLUE_LIGHT,
                           edgecolor=BLUE, linewidth=0.8, transform=ax.transAxes, zorder=3))
    ax.add_patch(Ellipse((x + width / 2, y + height - 0.009), width, 0.018,
                         facecolor=WHITE, edgecolor=BLUE, linewidth=0.8,
                         transform=ax.transAxes, zorder=4))
    ax.add_patch(Ellipse((x + width / 2, y + 0.009), width, 0.018,
                         facecolor=BLUE_LIGHT, edgecolor=BLUE, linewidth=0.8,
                         transform=ax.transAxes, zorder=4))


def _draw_panel_b(ax: plt.Axes, source: dict[str, Any]) -> None:
    x, y, width, height = 0.018, 0.047, 0.625, 0.355
    _panel_frame(ax, x, y, width, height, "b", "四级验证门控与 append-only 证据闭环")
    gates = source["panels"]["b"]["verification_gates"]
    gate_xs = [0.040, 0.159, 0.278, 0.397]
    gate_y, gate_w = 0.194, 0.102
    for index, (gate, gate_x) in enumerate(zip(gates, gate_xs), start=1):
        _gate_box(ax, gate_x, gate_y, gate_w, gate["title"], gate["detail"], index)
        if index < len(gates):
            _arrow(ax, (gate_x + gate_w + 0.002, gate_y + 0.056),
                   (gate_xs[index] - 0.005, gate_y + 0.056), color=GREEN,
                   linewidth=0.85, mutation_scale=7)

    # Verified facts are archived as raw JSONL plus typed DuckDB evidence.
    sink_x, sink_y = 0.535, 0.176
    _database_icon(ax, sink_x, sink_y, 0.078, 0.130)
    ax.text(sink_x + 0.039, sink_y + 0.079, "JSONL", transform=ax.transAxes,
            fontsize=6.0, color=BLUE_DARK, ha="center", va="center", fontweight="bold", zorder=6)
    ax.text(sink_x + 0.039, sink_y + 0.052, "+ DuckDB", transform=ax.transAxes,
            fontsize=6.0, color=BLUE_DARK, ha="center", va="center", fontweight="bold", zorder=6)
    ax.text(sink_x + 0.039, sink_y + 0.027, "typed facts", transform=ax.transAxes,
            fontsize=6.0, color=MUTED, ha="center", va="center", zorder=6)
    _arrow(ax, (0.501, gate_y + 0.056), (sink_x - 0.005, gate_y + 0.056),
           color=GREEN, linewidth=1.0, mutation_scale=8)
    ax.text(0.517, gate_y + 0.074, "通过", transform=ax.transAxes,
            fontsize=6.0, color=GREEN, ha="center", va="bottom", fontweight="bold")

    # Failure is a preserved audit branch, not silently discarded evidence.
    _arrow(ax, (0.448, gate_y - 0.005), (0.448, 0.132), color=RED,
           linewidth=0.8, linestyle="--", mutation_scale=7)
    _round_box(ax, 0.235, 0.078, 0.378, 0.054, face=AMBER_LIGHT, edge=AMBER,
               linewidth=0.7, radius=0.006, zorder=2)
    ax.text(0.424, 0.105, "任一级失败/超时均保留：status · error · source hash · attempt",
            transform=ax.transAxes, fontsize=6.0, color=AMBER, ha="center", va="center", zorder=6)
    ax.text(0.056, 0.116, "门控原则", transform=ax.transAxes, fontsize=6.2,
            color=INK, ha="left", va="center", fontweight="bold")
    ax.text(0.056, 0.090, "仅匹配且通过的事实进入比较",
            transform=ax.transAxes, fontsize=6.0, color=MUTED, ha="left", va="center")


def _compute_card(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    tag: str,
    title: str,
    line1: str,
    line2: str,
    color: str,
    face: str,
) -> None:
    _round_box(ax, x, y, width, height, face=face, edge=color,
               linewidth=0.9, radius=0.008, zorder=2)
    _round_box(ax, x + 0.010, y + height - 0.036, 0.046, 0.024, face=color,
               edge=color, linewidth=0.6, radius=0.004, zorder=3)
    ax.text(x + 0.033, y + height - 0.024, tag, transform=ax.transAxes,
            fontsize=6.0, color=WHITE, ha="center", va="center", fontweight="bold", zorder=6)
    ax.text(x + 0.065, y + height - 0.024, title, transform=ax.transAxes,
            fontsize=6.2, color=INK, ha="left", va="center", fontweight="bold", zorder=6)
    ax.text(x + 0.014, y + 0.050, line1, transform=ax.transAxes,
            fontsize=6.0, color=INK, ha="left", va="center", zorder=6)
    ax.text(x + 0.014, y + 0.022, line2, transform=ax.transAxes,
            fontsize=6.0, color=MUTED, ha="left", va="center", zorder=6)


def _draw_panel_c(ax: plt.Axes, source: dict[str, Any]) -> None:
    x, y, width, height = 0.657, 0.047, 0.325, 0.355
    _panel_frame(ax, x, y, width, height, "c", "算力分工与外推边界")
    compute = source["panels"]["c"]["compute"]
    _compute_card(
        ax, 0.677, 0.193, 0.136, 0.116,
        tag="GPU", title="RTX 5090",
        line1="PyTorch / CUDA",
        line2="模型训练 · 批推理",
        color=BLUE, face=BLUE_LIGHT,
    )
    aer_device = compute[1]["device"].replace("Aer device=", "")
    _compute_card(
        ax, 0.829, 0.193, 0.133, 0.116,
        tag="CPU", title=f"Aer {aer_device}",
        line1="无噪声 statevector",
        line2="精确验证 · 分批限额",
        color=TEAL, face=TEAL_LIGHT,
    )
    ax.text(0.819, 0.250, "≠", transform=ax.transAxes, fontsize=9.0,
            color=AMBER, ha="center", va="center", fontweight="bold")
    _round_box(ax, 0.677, 0.078, 0.285, 0.078, face=AMBER_LIGHT, edge=AMBER,
               linewidth=0.8, radius=0.007, zorder=2)
    ax.text(0.690, 0.132, "Synthetic Target ≠ 真机", transform=ax.transAxes,
            fontsize=6.2, color=AMBER, ha="left", va="center", fontweight="bold", zorder=6)
    ax.text(0.690, 0.103, "仅代理拓扑/原生门；不含校准、噪声与保真度",
            transform=ax.transAxes, fontsize=6.0, color=AMBER, ha="left", va="center", zorder=6)


def render(source: dict[str, Any]) -> list[Path]:
    fig = plt.figure(figsize=(WIDTH_MM * MM, HEIGHT_MM * MM))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    ax.text(0.018, 0.968,
            "图 1 | Resource-NMCTS：从可消融候选排序到可审计硬件编译的闭环",
            transform=ax.transAxes, fontsize=10.2, color=INK, fontweight="bold", va="top")
    ax.text(0.018, 0.925,
            "系统证据链已实现；learned prior 是可关闭的排序信号，其独立增益须由匹配消融另证。",
            transform=ax.transAxes, fontsize=6.3, color=MUTED, va="top")
    ax.text(0.982, 0.968, "IMPLEMENTED  ·  TRACEABLE  ·  ABLATABLE",
            transform=ax.transAxes, fontsize=6.0, color=BLUE, fontweight="bold",
            ha="right", va="top")

    _draw_panel_a(ax, source)
    _draw_panel_b(ax, source)
    _draw_panel_c(ax, source)

    outputs: list[Path] = []
    for suffix in ("svg", "pdf", "png"):
        path = OUTDIR / f"{STEM}.{suffix}"
        kwargs: dict[str, Any] = {}
        if suffix == "png":
            kwargs["dpi"] = 600
        fig.savefig(path, **kwargs)
        outputs.append(path)
    plt.close(fig)
    return outputs


def _svg_qa(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    images = len(re.findall(r"<image(?:\s|>)", text))
    text_nodes = len(re.findall(r"<text(?:\s|>)", text))
    return {
        "embedded_image_elements": images,
        "text_elements": text_nodes,
        "editable_text_pass": images == 0 and text_nodes > 0,
    }


def _pdf_qa(path: Path) -> dict[str, Any]:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - dependency is captured explicitly
        raise RuntimeError("PyMuPDF is required for single-page/size QA") from exc
    document = fitz.open(path)
    if len(document) != 1:
        return {"pages": len(document), "single_page_pass": False}
    rect = document[0].rect
    width_mm = rect.width * 25.4 / 72.0
    height_mm = rect.height * 25.4 / 72.0
    return {
        "pages": 1,
        "width_mm": round(width_mm, 3),
        "height_mm": round(height_mm, 3),
        "single_page_pass": True,
        "declared_size_pass": abs(width_mm - WIDTH_MM) < 0.15 and abs(height_mm - HEIGHT_MM) < 0.15,
    }


def _png_qa(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required for PNG preview QA") from exc
    with Image.open(path) as image:
        dpi = image.info.get("dpi")
        return {
            "pixels": [image.width, image.height],
            "dpi_metadata": [round(float(value), 2) for value in dpi] if dpi else None,
            "preview_pass": image.width >= 4300 and image.height >= 2470,
        }


def write_manifest(source: dict[str, Any], outputs: Iterable[Path]) -> dict[str, Any]:
    output_paths = list(outputs)
    by_suffix = {path.suffix.lower(): path for path in output_paths}
    qa = {
        "svg": _svg_qa(by_suffix[".svg"]),
        "pdf": _pdf_qa(by_suffix[".pdf"]),
        "png": _png_qa(by_suffix[".png"]),
    }
    if not qa["svg"]["editable_text_pass"]:
        raise RuntimeError("SVG QA failed: raster content found or editable text missing")
    if not qa["pdf"].get("single_page_pass") or not qa["pdf"].get("declared_size_pass"):
        raise RuntimeError("PDF QA failed: output is not one 183 mm x 105 mm page")
    if not qa["png"]["preview_pass"]:
        raise RuntimeError("PNG QA failed: preview is not 600 dpi at the declared size")

    manifest = {
        "schema_version": 1,
        "figure_id": STEM,
        "purpose": "XA-202609 traceable end-to-end system architecture",
        "contract": _relative(CONTRACT_PATH),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "generator": _relative(Path(__file__)),
        "generator_sha256": _sha256(Path(__file__)),
        "source_data": _relative(SOURCE_PATH),
        "source_data_sha256": _sha256(SOURCE_PATH),
        "backend": "Python/matplotlib only",
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "dimensions_mm": source["dimensions_mm"],
        "font_policy": {
            "requested_fallback": FONT_FALLBACK,
            "resolved_primary": RESOLVED_FONT,
            "minimum_figure_label_pt": 6.0,
            "svg_fonttype": "none",
            "pdf_fonttype": 42,
        },
        "claim_policy": source["claim_policy"],
        "outputs": [
            {
                "path": _relative(path),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in output_paths
        ],
        "qa": qa,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    source = build_source()
    outputs = render(source)
    manifest = write_manifest(source, outputs)
    print(f"font: {RESOLVED_FONT}")
    print(f"source: {_relative(SOURCE_PATH)}")
    for path in outputs:
        print(f"output: {_relative(path)} ({path.stat().st_size} bytes)")
    print(f"manifest: {_relative(MANIFEST_PATH)}")
    print(json.dumps(manifest["qa"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
