"""Shared path resolver for flat (payload) and layered (dev) layouts.
+Analysis scripts need to find project files that live in different subdirectories
depending on the layout: flat in the reviewer payload, or layered in the dev worktree.
"""
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
ROOT = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent


def find(name: str) -> Path:
    """Find a project file by name, searching ROOT and known subdirectories."""
    for d in (ROOT, ROOT / "submission", ROOT / "analysis", ROOT / "scripts", ROOT / "src"):
        p = d / name
        if p.exists():
            return p
    return ROOT / name
