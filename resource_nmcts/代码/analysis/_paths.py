"""Shared path resolver for flat (payload), layered (dev), and reorg'd (文本/代码/结果/模型) layouts.

Analysis scripts need to find project files that live in different subdirectories
depending on the layout:
  * flat: everything at the payload root (scripts beside results/)
  * layered (pre-2026-08-13): results/ paper_latex/ models/ src/ ... all siblings at ROOT
  * reorg'd (2026-08-13+): 文本/ 代码/ 结果/ 模型/ siblings; results under 结果/, etc.
"""
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()


def _resolve_root() -> Path:
    """Walk up from this file until we find the project root.

    Recognised anchors (in priority order):
      * a directory containing 文本/  -> reorg'd resource_nmcts/ root
      * a directory containing results/ -> layered/payload root
    """
    d = _THIS_FILE.parent
    while d != d.parent:
        if (d / "文本").is_dir():
            return d
        if (d / "results").is_dir():
            return d
        d = d.parent
    # fallback: assume this file is at <root>/analysis/_paths.py
    return _THIS_FILE.parent.parent


ROOT = _resolve_root()
# In the reorg'd layout, results/paper_latex/models live under sibling categories.
REORG = (ROOT / "文本").is_dir()
RESULTS = (ROOT / "结果" / "results") if REORG else (ROOT / "results")
PAPER_LATEX = (ROOT / "文本" / "paper_latex") if REORG else (ROOT / "paper_latex")
MODELS = (ROOT / "模型" / "models") if REORG else (ROOT / "models")


def find(name: str) -> Path:
    """Find a project file by name, searching ROOT and known subdirectories."""
    # Search dirs across both layouts: reorg'd categories first, then legacy siblings.
    candidates = []
    if REORG:
        candidates += [
            RESULTS, PAPER_LATEX, MODELS,
            ROOT / "结果" / "submission_package",
            ROOT / "结果" / "benchmark_exports",
            ROOT / "代码" / "submission", ROOT / "代码" / "analysis",
            ROOT / "代码" / "scripts", ROOT / "代码" / "src",
            ROOT / "代码" / "tests", ROOT / "代码" / "tools",
            ROOT / "代码",
            ROOT,
        ]
    else:
        candidates += [ROOT, ROOT / "submission", ROOT / "analysis", ROOT / "scripts", ROOT / "src"]
    for d in candidates:
        p = d / name
        if p.exists():
            return p
    return ROOT / name
