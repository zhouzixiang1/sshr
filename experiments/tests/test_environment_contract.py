#!/usr/bin/env python3
"""Keep the Conda entry point aligned with the frozen pip requirements."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = PROJECT_ROOT / "environment" / "requirements"
ENVIRONMENT = PROJECT_ROOT / "environment" / "environment.yml"


def _pins(path: Path) -> set[str]:
    pins: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and not line.startswith("-r"):
            assert "==" in line, f"requirement is not exactly pinned: {line}"
            pins.add(line)
    return pins


def _environment_pip_pins(text: str) -> set[str]:
    pins: set[str] = set()
    in_pip = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped == "- pip:":
            in_pip = True
            continue
        if in_pip and raw.startswith("      - "):
            pins.add(stripped[2:])
        elif in_pip and stripped and not raw.startswith("      "):
            in_pip = False
    return pins


def test_conda_environment_matches_frozen_dev_contract() -> None:
    text = ENVIRONMENT.read_text(encoding="utf-8")
    expected = _pins(REQUIREMENTS / "core.txt") | _pins(
        REQUIREMENTS / "dev.txt"
    )
    assert "name: xa202609" in text
    assert "- python=3.11.15" in text
    assert _environment_pip_pins(text) == expected
