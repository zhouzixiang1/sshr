#!/usr/bin/env python3
"""Audit local external-toolchain readiness for oracle-synthesis baselines.

The audit is deliberately stricter than checking whether a command exists in
PATH.  Some relevant tools are C++ libraries rather than binaries, and RevKit
3.x is primarily a Python package backed by C++ dependencies.  The report
therefore separates four questions:

1. Is a local executable, Python module, or source checkout available?
2. Are basic build prerequisites available?
3. Are the upstream repositories reachable from this workstation?
4. What exact install/probe command should be run next?
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
ROOT = THIS_DIR.parent
RESULTS = THIS_DIR / "results"
ENV_BIN = Path("/opt/anaconda3/envs/mcts-qoracle/bin")
ENV_PYTHON = ENV_BIN / "python"
MOCKTURTLE_ADAPTER_SRC = THIS_DIR / "tools" / "mockturtle_blif_xag_stats.cpp"
MOCKTURTLE_PROBE_ANALYSIS = RESULTS / "analysis_mockturtle_xag_probe.md"
CIRKIT_AIG_PROBE_ANALYSIS = RESULTS / "analysis_cirkit_aig_probe.md"
REVKIT_CLI_PROBE_ANALYSIS = RESULTS / "analysis_revkit_cli_multiflow_traditional.md"


BUILD_PREREQS = [
    {
        "name": "git",
        "commands": ["git"],
        "version_args": ["--version"],
        "required_for": "fetching mockturtle/RevKit/CirKit sources",
    },
    {
        "name": "cmake",
        "commands": [str(ENV_BIN / "cmake"), "cmake"],
        "version_args": ["--version"],
        "required_for": "building RevKit/CirKit-style C++ toolchains",
    },
    {
        "name": "C++17 compiler",
        "commands": ["clang++", "g++"],
        "version_args": ["--version"],
        "required_for": "building mockturtle/RevKit dependencies",
    },
    {
        "name": "Python/pip",
        "commands": [str(ENV_PYTHON)],
        "version_args": ["-m", "pip", "--version"],
        "required_for": "probing RevKit 3.x Python package installation",
    },
]


TOOLS = [
    {
        "name": "ABC",
        "kind": "binary",
        "paths": [ROOT / "tmp" / "abc" / "abc"],
        "commands": ["abc"],
        "role": "implemented AIG/XAG/LUT/ESOP external estimates",
        "source_url": "https://github.com/berkeley-abc/abc",
        "remote": "https://github.com/berkeley-abc/abc.git",
        "branches": ["master"],
        "install": ["already vendored under tmp/abc/abc in this project"],
    },
    {
        "name": "mockturtle",
        "kind": "cxx_header_library",
        "paths": [ROOT / "tmp" / "mockturtle", ROOT / "external" / "mockturtle"],
        "commands": [],
        "modules": [],
        "role": "official-header KLUT-to-XAG probe adapter; full ROS flow remains separate",
        "source_url": "https://github.com/lsils/mockturtle",
        "remote": "https://github.com/lsils/mockturtle.git",
        "branches": ["master"],
        "install": [
            "git clone --recursive https://github.com/lsils/mockturtle.git tmp/mockturtle",
            "/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/run_mockturtle_xag_probe.py --workers 4 --timeout 20",
        ],
    },
    {
        "name": "RevKit",
        "kind": "binary_or_python",
        "paths": [ROOT / "tmp" / "revkit", ROOT / "external" / "revkit"],
        "commands": ["revkit", "revkit.py"],
        "modules": ["revkit"],
        "role": "Python oracle_synth phase-netlist baseline adapter",
        "source_url": "https://github.com/msoeken/revkit",
        "remote": "https://github.com/msoeken/revkit.git",
        "branches": ["develop", "master"],
        "install": [
            "/opt/anaconda3/envs/mcts-qoracle/bin/python -m pip install 'git+https://github.com/msoeken/revkit@develop'",
            "or: git clone -b develop https://github.com/msoeken/revkit tmp/revkit && cd tmp/revkit && make devbuild",
        ],
    },
    {
        "name": "CirKit 3 shell",
        "kind": "binary_or_source",
        "paths": [ROOT / "tmp" / "cirkit" / "build" / "cli" / "cirkit", ROOT / "tmp" / "cirkit"],
        "commands": [],
        "modules": [],
        "role": "official CirKit shell for AIG/LUT optimization probes; not legacy RevKit reversible synthesis",
        "source_url": "https://github.com/msoeken/cirkit",
        "remote": "https://github.com/msoeken/cirkit.git",
        "branches": ["cirkit3", "master"],
        "install": [
            "git clone --recursive https://github.com/msoeken/cirkit.git tmp/cirkit",
            "cd tmp/cirkit && mkdir -p build && cd build && cmake .. && cmake --build . --target cirkit --parallel 8",
            "/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/run_cirkit_aig_probe.py --workers 8 --timeout 45",
        ],
    },
    {
        "name": "RevKit CLI / CirKit legacy",
        "kind": "binary_or_source",
        "paths": [
            ROOT / "tmp" / "cirkit_legacy" / "build" / "programs" / "revkit",
            ROOT / "tmp" / "cirkit_legacy",
            ROOT / "tmp" / "cirkit" / "build" / "cli" / "revkit",
        ],
        "commands": [],
        "modules": [],
        "role": "legacy command-line reversible synthesis flow for exact oracle-permutation baselines",
        "source_url": "https://github.com/msoeken/cirkit",
        "remote": "https://github.com/msoeken/cirkit.git",
        "branches": ["master", "develop"],
        "install": [
            "git -C tmp/cirkit worktree add ../cirkit_legacy origin/develop && git -C tmp/cirkit_legacy submodule update --init --recursive",
            "cd tmp/cirkit_legacy && mkdir -p build && cd build && cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -Denable_cirkit-addon-reversible=ON .. && cmake --build . --target revkit --parallel 8",
            "/opt/anaconda3/envs/mcts-qoracle/bin/python resource_nmcts_experiment/run_revkit_cli_probe.py --workers 8 --timeout 20 --flow tbs=tbs --flow dbs=dbs --flow rms=rms",
        ],
    },
    {
        "name": "caterpillar",
        "kind": "cxx_source_library",
        "paths": [
            ROOT / "tmp" / "caterpillar",
            ROOT / "tmp" / "caterpillar" / "build" / "CMakeCache.txt",
            ROOT / "tmp" / "caterpillar" / "build-test" / "lib" / "abcsat" / "liblibabcsat.a",
        ],
        "commands": [],
        "modules": [],
        "role": "open-source LSI quantum Boolean synthesis library with XAG synthesis and SAT-based pebbling components; source/build probe only, not standalone ROS CLI",
        "source_url": "https://github.com/gmeuli/caterpillar",
        "remote": "https://github.com/gmeuli/caterpillar.git",
        "branches": ["master"],
        "install": [
            "git clone --depth 1 https://github.com/gmeuli/caterpillar.git tmp/caterpillar",
            "cmake -S tmp/caterpillar -B tmp/caterpillar/build -DCATERPILLAR_TEST=OFF -DCATERPILLAR_EXAMPLES=ON -DCATERPILLAR_EXPERIMENTS=OFF && cmake --build tmp/caterpillar/build --parallel 8",
            "optional test probe: cmake -S tmp/caterpillar -B tmp/caterpillar/build-test -DCATERPILLAR_TEST=ON -DCATERPILLAR_EXAMPLES=OFF -DCATERPILLAR_EXPERIMENTS=OFF && cmake --build tmp/caterpillar/build-test --parallel 8",
        ],
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


def command_version(command: str, version_args: list[str]) -> tuple[str, str] | None:
    found = shutil.which(command)
    if not found and Path(command).is_file():
        found = command
    if not found:
        return None
    try:
        proc = subprocess.run(
            [found, *version_args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=8,
        )
    except Exception as exc:
        return found, f"probe failed: {exc!r}"
    first = next((line.strip() for line in proc.stdout.splitlines() if line.strip()), "")
    return found, first[:160]


def probe_prereq(spec: dict) -> dict:
    hits: list[tuple[str, str]] = []
    for command in spec["commands"]:
        result = command_version(command, spec["version_args"])
        if result is not None:
            hits.append(result)
    return {
        "name": spec["name"],
        "required_for": spec["required_for"],
        "available": bool(hits),
        "hits": hits,
    }


def git_remote_heads(remote: str, branches: list[str]) -> list[dict[str, str]]:
    if not shutil.which("git"):
        return [{"branch": branch, "status": "git missing", "commit": ""} for branch in branches]
    out: list[dict[str, str]] = []
    for branch in branches:
        try:
            proc = subprocess.run(
                ["git", "ls-remote", "--heads", remote, branch],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=12,
            )
        except Exception as exc:
            out.append({"branch": branch, "status": f"probe failed: {exc!r}", "commit": ""})
            continue
        text = (proc.stdout or "").strip()
        if proc.returncode == 0 and text:
            commit = text.split()[0]
            out.append({"branch": branch, "status": "reachable", "commit": commit})
        elif proc.returncode == 0:
            out.append({"branch": branch, "status": "missing branch", "commit": ""})
        else:
            out.append({"branch": branch, "status": f"git failed: {text[-160:]}", "commit": ""})
    return out


def find_tool(tool: dict) -> dict:
    hits: list[tuple[str, str, str]] = []
    for path in tool.get("paths", []):
        path = Path(path)
        if path.exists() and path.is_file():
            if os.access(path, os.X_OK):
                probe = binary_version(path)
            else:
                probe = "local file exists"
            hits.append(("file", str(path), probe))
        elif path.exists() and path.is_dir():
            hits.append(("source", str(path), "local source checkout exists"))
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
        "kind": tool["kind"],
        "role": tool["role"],
        "source_url": tool.get("source_url", ""),
        "remote": tool.get("remote", ""),
        "install": tool.get("install", []),
        "available": bool(hits),
        "hits": hits,
        "remote_heads": git_remote_heads(tool["remote"], tool.get("branches", [])) if tool.get("remote") else [],
    }


def write_markdown(prereqs: list[dict], results: list[dict], out: Path) -> None:
    missing_prereqs = [item["name"] for item in prereqs if not item["available"]]
    availability = {item["name"]: item["available"] for item in results}
    mockturtle_adapter_ready = MOCKTURTLE_ADAPTER_SRC.exists() and MOCKTURTLE_PROBE_ANALYSIS.exists()
    cirkit_aig_probe_ready = CIRKIT_AIG_PROBE_ANALYSIS.exists()
    revkit_cli_probe_ready = REVKIT_CLI_PROBE_ANALYSIS.exists()
    lines = [
        "# External Toolchain Readiness",
        "",
        "This audit checks whether the current workstation can run external",
        "logic/reversible-synthesis baselines beyond the in-repository ABC path.",
        "It distinguishes local availability from upstream source reachability",
        "and build prerequisites, because mockturtle is a C++ library and",
        "RevKit 3.x is a Python package backed by C++ code.",
        "",
        "## Build Prerequisites",
        "",
        "| prerequisite | status | detected command/path | probe | needed for |",
        "|---|---|---|---|---|",
    ]
    for item in prereqs:
        if item["hits"]:
            for idx, (path, version) in enumerate(item["hits"]):
                status = "available" if idx == 0 else "available (additional)"
                lines.append(f"| {item['name']} | {status} | `{path}` | {version} | {item['required_for']} |")
        else:
            lines.append(f"| {item['name']} | missing |  | not found | {item['required_for']} |")
    lines.extend(
        [
            "",
            "## Tool Availability",
            "",
            "| tool | kind | local status | role | detected path/module | probe |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in results:
        if item["hits"]:
            for idx, (source, target, version) in enumerate(item["hits"]):
                status = "available" if idx == 0 else "available (additional)"
                lines.append(
                    f"| {item['name']} | {item['kind']} | {status} | {item['role']} | `{source}: {target}` | {version} |"
                )
        else:
            lines.append(
                f"| {item['name']} | {item['kind']} | missing | {item['role']} |  | not found in configured paths, PATH, or Python modules |"
            )

    lines.extend(
        [
            "",
            "## Upstream Source Reachability",
            "",
            "| tool | source | branch | status | commit |",
            "|---|---|---|---|---|",
        ]
    )
    for item in results:
        if not item["remote_heads"]:
            continue
        for head in item["remote_heads"]:
            lines.append(
                f"| {item['name']} | <{item['source_url']}> | {head['branch']} | {head['status']} | `{head['commit']}` |"
            )

    lines.extend(
        [
            "",
            "## Reproduction Commands to Try Next",
            "",
        ]
    )
    for item in results:
        if not item["install"]:
            continue
        lines.append(f"### {item['name']}")
        lines.append("")
        for command in item["install"]:
            lines.append(f"- `{command}`")
        lines.append("")

    if missing_prereqs:
        prereq_sentence = ", ".join(missing_prereqs)
        blocker = f"Current local build blocker(s): {prereq_sentence}."
    else:
        blocker = "No basic build prerequisite blocker was detected."
    lines.extend(["## Interpretation", ""])
    lines.append(
        "- ABC is already usable through the bundled `tmp/abc/abc` binary and is the basis of the current AIG/XAG/LUT/ESOP export baselines."
    )
    lines.append(f"- {blocker}")
    if availability.get("mockturtle"):
        if mockturtle_adapter_ready:
            lines.append(
                "- mockturtle source and the project KLUT-to-XAG adapter are available; `run_mockturtle_xag_probe.py` has produced a reproducible official-header probe. This is still not the full official ROS flow."
            )
        else:
            lines.append(
                "- mockturtle source is present locally, but the project KLUT-to-XAG adapter or its probe output is not yet available."
            )
    else:
        lines.append(
            "- mockturtle upstream is checked as a C++ source dependency rather than a binary; a reproduced mockturtle baseline still requires a local checkout and a project adapter."
        )
    if availability.get("RevKit"):
        lines.append(
            "- RevKit Python API is locally available and can support an API-level `oracle_synth` baseline; this is distinct from the legacy RevKit/CirKit CLI flow."
        )
    else:
        lines.append(
            "- RevKit Python API is not locally available; a reproduced RevKit API comparison still requires installation."
        )
    if availability.get("CirKit 3 shell"):
        if cirkit_aig_probe_ready:
            lines.append(
                "- CirKit 3 shell is locally available and `run_cirkit_aig_probe.py` has produced a reproducible AIG/multiplicative-complexity probe. This is not legacy RevKit reversible synthesis or full ROS."
            )
        else:
            lines.append(
                "- CirKit 3 shell is locally available, but the AIG/multiplicative-complexity probe output has not yet been generated."
            )
    else:
        lines.append("- CirKit 3 shell is not locally available; AIG/LUT shell probes still require a checkout and build.")
    if availability.get("RevKit CLI / CirKit legacy"):
        if revkit_cli_probe_ready:
            lines.append(
                "- RevKit/CirKit legacy CLI is locally available and `run_revkit_cli_probe.py` has produced a reproducible reversible-synthesis CLI portfolio probe on exact oracle permutations."
            )
        else:
            lines.append("- RevKit/CirKit legacy CLI is locally available for command-line reversible-synthesis probes.")
    else:
        lines.append("- RevKit/CirKit legacy CLI is not yet available, so legacy command-line reversible-synthesis reproduction remains pending.")
    if availability.get("caterpillar"):
        lines.append(
            "- caterpillar source is locally available as the open-source LSI quantum Boolean synthesis library cited by the XAG compilation line. It exposes XAG synthesis and SAT-based pebbling/memory-management components, but no standalone ROS executable was detected in this checkout."
        )
        lines.append(
            "- The local caterpillar minimal CMake probe configured successfully; the optional all-test build is environment-sensitive on this macOS/AppleClang toolchain because the bundled Catch2 trap uses an x86 `int $3` inline-assembly mnemonic."
        )
    else:
        lines.append(
            "- caterpillar is reachable upstream but not locally available; this prevents using it as a source-family probe for ROS/XAG memory-management components on this workstation."
        )
    lines.extend(
        [
            "- This audit is intentionally environment-specific; rerun it after installing external tools before claiming reproduced external reversible-toolchain results.",
            "",
            "## Primary References / Tool Sources",
            "",
            "- mockturtle: <https://github.com/lsils/mockturtle>",
            "- RevKit: <https://github.com/msoeken/revkit>",
            "- RevKit/CirKit legacy CLI: <https://msoeken.github.io/revkit.html>",
            "- caterpillar: <https://github.com/gmeuli/caterpillar>",
            "- Back-end-aware fault-tolerant oracle synthesis: <https://dl.acm.org/doi/10.1145/3658617.3697776>",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=RESULTS / "analysis_toolchain_readiness.md")
    parser.add_argument("--json-out", type=Path, default=RESULTS / "toolchain_readiness.json")
    args = parser.parse_args()
    prereqs = [probe_prereq(item) for item in BUILD_PREREQS]
    results = [find_tool(tool) for tool in TOOLS]
    write_markdown(prereqs, results, args.out)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps({"build_prerequisites": prereqs, "tools": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
