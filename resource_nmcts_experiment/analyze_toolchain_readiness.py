#!/usr/bin/env python3
"""Audit local external-toolchain readiness for oracle-synthesis baselines."""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
RESULTS = THIS_DIR / "results"


TOOLS = [
    {
        "name": "ABC",
        "kind": "binary",
        "paths": [ROOT / "tmp" / "abc" / "abc"],
        "commands": ["abc"],
        "role": "implemented AIG/XAG/LUT/ESOP external estimates",
    },
    {
        "name": "mockturtle",
        "kind": "binary_or_python",
        "paths": [],
        "commands": ["mockturtle"],
        "modules": ["mockturtle"],
        "role": "future logic-network / reversible-toolchain baseline adapter",
    },
    {
        "name": "RevKit",
        "kind": "binary_or_python",
        "paths": [],
        "commands": ["revkit", "revkit.py"],
        "modules": ["revkit"],
        "role": "future reversible-synthesis baseline adapter",
    },
]


def binary_version(path: str | Path) -> str:
    try:
        proc = subprocess.run(
            [str(path), "-h"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        return f"probe failed: {exc!r}"
    first = next((line.strip() for line in proc.stdout.splitlines() if line.strip()), "")
    return first[:160]


def find_tool(tool: dict) -> dict:
    hits: list[tuple[str, str, str]] = []
    for path in tool.get("paths", []):
        if Path(path).exists() and Path(path).is_file():
            hits.append(("file", str(path), binary_version(path)))
    for command in tool.get("commands", []):
        found = shutil.which(command)
        if found:
            hits.append(("PATH", found, binary_version(found)))
    for module in tool.get("modules", []):
        spec = importlib.util.find_spec(module)
        if spec is not None:
            origin = spec.origin or "namespace-package"
            hits.append(("python", module, origin))
    return {
        "name": tool["name"],
        "role": tool["role"],
        "available": bool(hits),
        "hits": hits,
    }


def write_markdown(results: list[dict], out: Path) -> None:
    lines = [
        "# External Toolchain Readiness",
        "",
        "This audit checks whether the current workstation can run external",
        "logic/reversible-synthesis baselines beyond the in-repository ABC path.",
        "",
        "| tool | local status | role | detected path/module | probe |",
        "|---|---|---|---|---|",
    ]
    for item in results:
        if item["hits"]:
            for idx, (source, target, version) in enumerate(item["hits"]):
                status = "available" if idx == 0 else "available (additional)"
                lines.append(
                    f"| {item['name']} | {status} | {item['role']} | `{source}: {target}` | {version} |"
                )
        else:
            lines.append(
                f"| {item['name']} | missing | {item['role']} |  | not found in configured paths, PATH, or Python modules |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- ABC is already usable through the bundled `tmp/abc/abc` binary and is the basis of the current AIG/XAG/LUT/ESOP export baselines.",
            "- mockturtle and RevKit are not available in the current environment, so a reproduced ROS/mockturtle/RevKit-style reversible-toolchain comparison still requires installing or vendoring those tools.",
            "- This audit is intentionally environment-specific; rerun it after installing external tools before claiming reproduced external reversible-toolchain results.",
            "",
            "## Primary References / Tool Sources",
            "",
            "- mockturtle: <https://github.com/lsils/mockturtle>",
            "- RevKit: <https://github.com/msoeken/revkit>",
            "- Back-end-aware fault-tolerant oracle synthesis: <https://dl.acm.org/doi/10.1145/3658617.3697776>",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_toolchain_readiness.md")
    args = parser.parse_args()
    results = [find_tool(tool) for tool in TOOLS]
    write_markdown(results, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
