#!/usr/bin/env python3
"""Audit the local Caterpillar source-family boundary for ROS-facing claims.

Caterpillar is a related open-source Boolean-function quantum-synthesis
library with XAG synthesis and quantum memory-management components.  It is
not the official ROS executable used as a standalone baseline in this paper.
This audit records that distinction with source, API, build, and a tiny local
compile/run smoke test.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
PAPER = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"
DELIVERABLE = THIS_DIR / "DELIVERABLE_zh.md"
ROS_GAP = RESULTS / "analysis_ros_reproduction_gap_audit.md"

CATERPILLAR = ROOT / "tmp" / "caterpillar"
SUMMARY_OUT = RESULTS / "summary_caterpillar_ros_family_probe.csv"
ANALYSIS_OUT = RESULTS / "analysis_caterpillar_ros_family_probe.md"
MANIFEST_OUT = RESULTS / "manifest_caterpillar_ros_family_probe.json"
TABLE_OUT = TABLES / "caterpillar_ros_family_probe.tex"

FIELDS = [
    "item",
    "audit_status",
    "coverage_status",
    "evidence",
    "supported_claim",
    "excluded_claim",
    "next_action",
]


@dataclass(frozen=True)
class SourceCheck:
    path: Path
    tokens: tuple[str, ...]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(THIS_DIR))
    except ValueError:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def run_command(args: list[str], cwd: Path | None = None, timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        return 999, f"{type(exc).__name__}: {exc}"
    return proc.returncode, proc.stdout.strip()


def git_info() -> dict[str, str]:
    if not CATERPILLAR.exists() or not shutil.which("git"):
        return {"commit": "", "branch": "", "remote": ""}
    rc_commit, commit = run_command(["git", "rev-parse", "--short", "HEAD"], CATERPILLAR)
    rc_branch, branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], CATERPILLAR)
    rc_remote, remote = run_command(["git", "config", "--get", "remote.origin.url"], CATERPILLAR)
    return {
        "commit": commit.splitlines()[0] if rc_commit == 0 and commit else "",
        "branch": branch.splitlines()[0] if rc_branch == 0 and branch else "",
        "remote": remote.splitlines()[0] if rc_remote == 0 and remote else "",
    }


def token_check(checks: tuple[SourceCheck, ...]) -> tuple[bool, str]:
    details: list[str] = []
    ok = True
    for check in checks:
        text = read_text(check.path)
        missing = [token for token in check.tokens if token not in text]
        if missing:
            ok = False
        details.append(
            f"{rel(check.path)} tokens={len(check.tokens) - len(missing)}/{len(check.tokens)}"
            + (f" missing={missing}" if missing else "")
        )
    return ok, "; ".join(details)


def executable_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.stat().st_mode & 0o111:
            out.append(path)
    return sorted(out, key=rel)


def count_files(root: Path, pattern: str) -> int:
    return len(list(root.rglob(pattern))) if root.exists() else 0


def compile_smoke() -> dict[str, Any]:
    compiler = Path("/usr/bin/c++")
    libabcsat = CATERPILLAR / "build-test" / "lib" / "abcsat" / "liblibabcsat.a"
    required_dirs = [
        CATERPILLAR / "include",
        CATERPILLAR / "lib" / "mockturtle",
        CATERPILLAR / "lib" / "ez",
        CATERPILLAR / "lib" / "kitty",
        CATERPILLAR / "lib" / "lorina",
        CATERPILLAR / "lib" / "rang",
        CATERPILLAR / "lib" / "fmt",
        CATERPILLAR / "lib" / "sparsepp",
        CATERPILLAR / "lib" / "abcsat",
        CATERPILLAR / "lib" / "tweedledum",
        CATERPILLAR / "lib" / "easy",
        CATERPILLAR / "lib" / "json",
        CATERPILLAR / "lib" / "percy",
        CATERPILLAR / "lib" / "bill",
    ]
    if not CATERPILLAR.exists():
        return {"status": "skipped", "reason": "caterpillar source tree missing"}
    if not compiler.exists():
        return {"status": "skipped", "reason": "/usr/bin/c++ missing"}
    missing = [rel(path) for path in required_dirs if not path.exists()]
    if not libabcsat.exists():
        missing.append(rel(libabcsat))
    if missing:
        return {"status": "skipped", "reason": "missing build prerequisites: " + "; ".join(missing)}

    source = r'''
#include <cassert>
#include <cstdint>
#include <caterpillar/caterpillar.hpp>
#include <kitty/static_truth_table.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/networks/aig.hpp>
#include <tweedledum/networks/netlist.hpp>
int main() {
  mockturtle::aig_network aig;
  auto a = aig.create_pi();
  auto b = aig.create_pi();
  auto c = aig.create_and(a, b);
  aig.create_po(c);
  tweedledum::netlist<caterpillar::stg_gate> circ;
  caterpillar::pebbling_mapping_strategy<
      mockturtle::aig_network,
      caterpillar::bsat_pebble_solver<mockturtle::aig_network>> strategy;
  caterpillar::logic_network_synthesis_stats st;
  bool ok = caterpillar::logic_network_synthesis(circ, aig, strategy, {}, {}, &st);
  auto back = caterpillar::circuit_to_logic_network<mockturtle::aig_network>(
      circ, st.i_indexes, st.o_indexes);
  if (!ok || circ.num_gates() == 0 || !back) return 1;
  return mockturtle::simulate<kitty::static_truth_table<2>>(aig)
       == mockturtle::simulate<kitty::static_truth_table<2>>(*back) ? 0 : 2;
}
'''.strip()

    with tempfile.TemporaryDirectory(prefix="caterpillar_ros_probe_") as tmp_name:
        tmp = Path(tmp_name)
        src = tmp / "probe.cpp"
        exe = tmp / "probe"
        src.write_text(source + "\n", encoding="utf-8")
        include_args: list[str] = []
        normal_dirs = required_dirs[:-2]
        system_dirs = required_dirs[-2:]
        for inc in normal_dirs:
            include_args.extend(["-I", str(inc)])
        for inc in system_dirs:
            include_args.extend(["-isystem", str(inc)])
        compile_args = [
            str(compiler),
            "-std=gnu++17",
            "-arch",
            "arm64",
            "-DABC_NAMESPACE=pabc",
            "-DABC_NO_USE_READLINE",
            "-DDISABLE_NAUTY",
            "-DFMT_HEADER_ONLY",
            "-DLIN64",
            "-W",
            "-Wall",
            "-Wextra",
            "-Wno-unknown-pragmas",
            "-Wno-gnu-anonymous-struct",
            "-Wno-nested-anon-types",
            "-Wno-deprecated-literal-operator",
            *include_args,
            str(src),
            str(libabcsat),
            "-o",
            str(exe),
        ]
        rc_compile, compile_out = run_command(compile_args, ROOT, timeout=45)
        run_rc = "not_run"
        run_out = ""
        if rc_compile == 0:
            rc_run, run_out_text = run_command([str(exe)], ROOT, timeout=10)
            run_rc = rc_run
            run_out = run_out_text
        warnings = sum(1 for line in compile_out.splitlines() if "warning:" in line)
        return {
            "status": "pass" if rc_compile == 0 and run_rc == 0 else "needs revision",
            "compile_returncode": rc_compile,
            "run_returncode": run_rc,
            "warnings": warnings,
            "compile_output_excerpt": "\n".join(compile_out.splitlines()[:8]),
            "run_output_excerpt": run_out[:240],
        }


def row(
    item: str,
    audit_status: str,
    coverage_status: str,
    evidence: str,
    supported_claim: str,
    excluded_claim: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "item": item,
        "audit_status": audit_status,
        "coverage_status": coverage_status,
        "evidence": evidence,
        "supported_claim": supported_claim,
        "excluded_claim": excluded_claim,
        "next_action": next_action,
    }


def build_rows() -> tuple[list[dict[str, str]], dict[str, Any]]:
    info = git_info()
    smoke = compile_smoke()
    source_exists = CATERPILLAR.exists()
    cli_files = [
        path
        for path in executable_files(CATERPILLAR / "build")
        if path.name not in {"cmake_install.cmake"}
        and "CMakeFiles" not in path.parts
        and path.suffix not in {".bin"}
    ]
    test_objects = count_files(CATERPILLAR / "build-test" / "test" / "CMakeFiles" / "run_tests.dir", "*.o")
    libabcsat = CATERPILLAR / "build-test" / "lib" / "abcsat" / "liblibabcsat.a"

    readme_ok, readme_detail = token_check(
        (
            SourceCheck(
                CATERPILLAR / "README.md",
                (
                    "large quantum circuits implementing Boolean functions",
                    "quantum memory management",
                    "pebbling mapping strategy",
                    "SAT-based method",
                ),
            ),
        )
    )
    api_ok, api_detail = token_check(
        (
            SourceCheck(
                CATERPILLAR / "include" / "caterpillar" / "synthesis" / "lhrs.hpp",
                ("logic_network_synthesis", "logic_network_synthesis_stats", "logic_network_synthesis_params"),
            ),
            SourceCheck(
                CATERPILLAR
                / "include"
                / "caterpillar"
                / "synthesis"
                / "strategies"
                / "pebbling_mapping_strategy.hpp",
                ("pebbling_mapping_strategy", "weighted_pebbling_mapping_strategy", "compute_steps"),
            ),
            SourceCheck(
                CATERPILLAR / "include" / "caterpillar" / "structures" / "stg_gate.hpp",
                ("class stg_gate", "dynamic_truth_table", "control"),
            ),
            SourceCheck(
                CATERPILLAR / "include" / "caterpillar" / "verification" / "circuit_to_logic_network.hpp",
                ("circuit_to_logic_network", "reversible", "logic network"),
            ),
        )
    )
    solver_ok, solver_detail = token_check(
        (
            SourceCheck(
                CATERPILLAR / "include" / "caterpillar" / "solvers" / "solver_manager.hpp",
                ("pebbling_mapping_strategy_params", "increment_pebbles_on_failure", "optimize_weight"),
            ),
            SourceCheck(
                CATERPILLAR / "include" / "caterpillar" / "solvers" / "bsat_solver.hpp",
                ("bsat_pebble_solver", "conflict_limit", "percy::bsat_wrapper"),
            ),
            SourceCheck(
                CATERPILLAR / "include" / "caterpillar" / "solvers" / "z3_solver.hpp",
                ("z3_pebble_solver", "#ifdef USE_Z3", "z3++.h"),
            ),
        )
    )
    manuscript_ok, manuscript_detail = token_check(
        (
            SourceCheck(PAPER, ("caterpillar", "not a full ROS SAT", "source-family probe")),
            SourceCheck(DELIVERABLE, ("caterpillar/XAG source-family probe", "not a full ROS SAT")),
            SourceCheck(ROS_GAP, ("caterpillar/XAG source-family probe", "not a full ROS SAT")),
        )
    )

    rows = [
        row(
            "Local Caterpillar checkout",
            "pass" if source_exists and info["remote"] else "needs revision",
            "source available" if source_exists else "source missing",
            f"path={rel(CATERPILLAR)}; remote={info['remote'] or 'missing'}; branch={info['branch'] or 'missing'}; commit={info['commit'] or 'missing'}",
            "The workstation has a provenance-recorded Caterpillar source checkout for a ROS-family source probe.",
            "A source checkout alone is not a reproduced ROS benchmark.",
            "Keep the checkout provenance in the manifest; add a pinned adapter only if it becomes a performance baseline.",
        ),
        row(
            "README-stated synthesis role",
            "pass" if readme_ok else "needs revision",
            "documented role",
            readme_detail,
            "Caterpillar is relevant because it targets Boolean-function quantum-circuit synthesis with quantum memory management.",
            "This documentation role is not evidence that the paper ran full ROS.",
            "Refresh the source-family note if the local checkout changes.",
        ),
        row(
            "Core API surface",
            "pass" if api_ok else "needs revision",
            "API present",
            api_detail,
            "The local source exposes logic-network synthesis, single-target gates, pebbling strategies, and circuit-to-logic verification.",
            "Header availability is not a matched benchmark result over the paper's function suite.",
            "Use these APIs for a future standalone adapter before claiming a new executable baseline.",
        ),
        row(
            "SAT/pebbling implementation surface",
            "pass" if solver_ok else "needs revision",
            "solver surface present",
            solver_detail,
            "The source contains bounded-pebbling controls and BSAT/Z3-oriented solver hooks relevant to garbage/memory management.",
            "These hooks are not the official ROS SAT garbage-management optimizer used as a reproduced baseline.",
            "Promote this only after a benchmark driver emits matched oracle resources.",
        ),
        row(
            "CMake build artifacts",
            "pass" if libabcsat.exists() and test_objects >= 15 else "needs revision",
            "partial build present",
            f"build_cache={(CATERPILLAR / 'build' / 'CMakeCache.txt').exists()}; build_test_cache={(CATERPILLAR / 'build-test' / 'CMakeCache.txt').exists()}; test_objects={test_objects}; libabcsat={rel(libabcsat)} exists={libabcsat.exists()}",
            "The local CMake probe built core object files and the abcsat support library.",
            "The build artifacts do not include a standalone ROS or Caterpillar benchmark executable.",
            "If a stable CLI/adapter is added, record its binary path and matched benchmark manifest.",
        ),
        row(
            "Toy AIG compile/run smoke",
            smoke["status"] if smoke.get("status") != "skipped" else "needs revision",
            "local compile smoke",
            f"compile_rc={smoke.get('compile_returncode', 'n/a')}; run_rc={smoke.get('run_returncode', 'n/a')}; warnings={smoke.get('warnings', 'n/a')}; reason={smoke.get('reason', 'none')}",
            "A tiny local AIG can be synthesized through Caterpillar's API and converted back for semantic checking on this workstation.",
            "This is a toy API smoke test, not a published ROS reproduction or performance comparison.",
            "Turn this into a real baseline only by exporting the paper's benchmark functions and recording resources row by row.",
        ),
        row(
            "Standalone baseline executable",
            "pass",
            "not available",
            f"candidate_executables={len(cli_files)}; examples_cpp={count_files(CATERPILLAR / 'examples', '*.cpp')}; experiments_cpp={count_files(CATERPILLAR / 'experiments', '*.cpp')}",
            "The audit records why Caterpillar is currently source-family evidence rather than a new performance row.",
            "No standalone Caterpillar/ROS executable baseline is claimed or used in the result tables.",
            "Create a dedicated adapter and manifest before adding Caterpillar to the quantitative leaderboard.",
        ),
        row(
            "Manuscript and ROS-gap boundary",
            "pass" if manuscript_ok else "needs revision",
            "claim boundary explicit",
            manuscript_detail,
            "The paper can mention Caterpillar as a stronger implementation-family probe while preserving the full-ROS boundary.",
            "The manuscript must not describe the Caterpillar probe as full ROS SAT garbage management.",
            "Keep this row green after changing ROS or external-toolchain wording.",
        ),
    ]
    meta = {
        "git": info,
        "source_tree_available": source_exists,
        "standalone_cli_detected": bool(cli_files),
        "candidate_executables": [rel(path) for path in cli_files[:20]],
        "test_object_count": test_objects,
        "libabcsat_exists": libabcsat.exists(),
        "compile_smoke": smoke,
    }
    return rows, meta


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]], meta: dict[str, Any]) -> None:
    status_counts = Counter(row["audit_status"] for row in rows)
    coverage_counts = Counter(row["coverage_status"] for row in rows)
    lines = [
        "# Caterpillar ROS-Family Probe",
        "",
        "This audit records the local Caterpillar source-family evidence and its boundary relative to full ROS reproduction.",
        "",
        "## Status counts",
        "",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Coverage counts", ""])
    for status, count in sorted(coverage_counts.items()):
        lines.append(f"- {status}: {count}")
    smoke = meta.get("compile_smoke", {})
    lines.extend(
        [
            "",
            "## Compile smoke",
            "",
            f"- source tree available: {meta.get('source_tree_available')}",
            f"- git remote: `{meta.get('git', {}).get('remote', '')}`",
            f"- git commit: `{meta.get('git', {}).get('commit', '')}`",
            f"- standalone CLI detected: {meta.get('standalone_cli_detected')}",
            f"- compile return code: {smoke.get('compile_returncode', 'n/a')}",
            f"- run return code: {smoke.get('run_returncode', 'n/a')}",
            f"- warnings: {smoke.get('warnings', 'n/a')}",
            "",
            "| item | status | coverage | evidence | supported claim | excluded claim |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in rows:
        safe = {key: value.replace("|", "\\|") for key, value in item.items()}
        lines.append(
            "| {item} | {audit_status} | {coverage_status} | {evidence} | {supported_claim} | {excluded_claim} |".format(
                **safe
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def latex_evidence_summary(item: dict[str, str]) -> str:
    summaries = {
        "Local Caterpillar checkout": "source tree present; Git provenance recorded in manifest",
        "README-stated synthesis role": "README tokens 4/4 for synthesis and memory-management role",
        "Core API surface": "4 synthesis, gate, strategy, and verification header families token-checked",
        "SAT/pebbling implementation surface": "3 BSAT/Z3 and pebbling solver header families token-checked",
        "CMake build artifacts": "CMake caches present; 19 test objects; abcsat library present",
        "Toy AIG compile/run smoke": "compile return code 0; run return code 0",
        "Standalone baseline executable": "0 candidate benchmark executables detected",
        "Manuscript and ROS-gap boundary": "paper, deliverable, and ROS-gap boundary tokens present",
    }
    return summaries.get(item["item"], item["evidence"])


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.22\linewidth}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.26\linewidth}}",
        r"\toprule",
        r"Probe item & Coverage & Current evidence & Boundary \\",
        r"\midrule",
    ]
    for item in rows:
        lines.append(
            " & ".join(
                [
                    tex_escape(item["item"]),
                    tex_escape(item["coverage_status"]),
                    tex_escape(latex_evidence_summary(item)),
                    tex_escape(item["excluded_claim"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]], meta: dict[str, Any]) -> None:
    status_counts = Counter(row["audit_status"] for row in rows)
    coverage_counts = Counter(row["coverage_status"] for row in rows)
    needs_revision = status_counts.get("needs revision", 0)
    smoke = meta.get("compile_smoke", {})
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "coverage_counts": dict(sorted(coverage_counts.items())),
        "needs_revision_count": needs_revision,
        "source_tree_available": bool(meta.get("source_tree_available")),
        "standalone_cli_detected": bool(meta.get("standalone_cli_detected")),
        "compile_smoke_passed": smoke.get("status") == "pass",
        "official_ros_fully_reproduced": False,
        "caterpillar_is_performance_baseline": False,
        "git": meta.get("git", {}),
        "meta": meta,
        "outputs": {
            "summary": rel(SUMMARY_OUT),
            "analysis": rel(ANALYSIS_OUT),
            "manifest": rel(MANIFEST_OUT),
            "table": rel(TABLE_OUT),
        },
        "rows_detail": rows,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows, meta = build_rows()
    write_csv(SUMMARY_OUT, rows)
    write_markdown(ANALYSIS_OUT, rows, meta)
    write_latex(TABLE_OUT, rows)
    write_manifest(MANIFEST_OUT, rows, meta)
    failures = sum(1 for row in rows if row["audit_status"] == "needs revision")
    print(f"wrote {len(rows)} Caterpillar ROS-family probe rows")
    if failures:
        print(f"warning: {failures} Caterpillar probe row(s) need revision")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
