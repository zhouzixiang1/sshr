#!/usr/bin/env python3
"""Minimal smoke checks for the block PV-MCTS implementation."""
from __future__ import annotations

import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SSHR_DIR = THIS_DIR.parent / "sshr"
for p in [THIS_DIR, SSHR_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from bool_func import BooleanFunction  # noqa: E402
from block_pv_mcts import synthesize_greedy, synthesize_pv_mcts  # noqa: E402


def main() -> int:
    for tt in [0x1, 0x5, 0x69, 0xB6]:
        bf = BooleanFunction(3, tt)
        for fn in [synthesize_greedy, synthesize_pv_mcts]:
            result = fn(bf)
            assert result.correct, (tt, fn.__name__, result.cost)
            assert result.cost >= 0
    print("smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
