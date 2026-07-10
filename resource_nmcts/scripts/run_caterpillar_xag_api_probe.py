#!/usr/bin/env python3
"""Run a bounded Caterpillar XAG API performance probe.

This is not the official ROS executable.  It uses the local Caterpillar source
checkout as an implementation-family probe: each traditional n<=6 Boolean
function is converted into an ANF-XAG network, synthesized through Caterpillar's
logic-network API, verified by Caterpillar's circuit-to-logic-network path, and
reported with the same logical resource columns as the main manuscript.
"""
from __future__ import annotations

import csv
import json
import argparse
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
THIS_DIR = Path(__file__).resolve().parent
from src.sshr_lib.bool_func import BooleanFunction  # noqa: E402
from src.anf_utils import anf_monomials  # noqa: E402
from run_external_baselines import DEFAULT_WEIGHTS  # noqa: E402


CATERPILLAR = ROOT / "tmp" / "caterpillar"
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
INPUT = RESULTS / "raw_traditional_resource.csv"
RAW_OUT = RESULTS / "raw_caterpillar_xag_api_probe.csv"
BEST_OUT = RESULTS / "raw_caterpillar_xag_api_best.csv"
SUMMARY_OUT = RESULTS / "summary_caterpillar_xag_api_probe.csv"
ANALYSIS_OUT = RESULTS / "analysis_caterpillar_xag_api_probe.md"
MANIFEST_OUT = RESULTS / "manifest_caterpillar_xag_api_probe.json"
TABLE_OUT = TABLES / "caterpillar_xag_api_probe.tex"

STRATEGIES = (
    "xag_lowt",
    "xag_fast_lowt",
    "xag_lowd",
)

FIELDS = [
    "dataset",
    "index",
    "name",
    "n",
    "anf_terms",
    "method",
    "strategy",
    "T",
    "CNOT",
    "depth",
    "t_depth_proxy",
    "gates",
    "explicit_ancilla",
    "peak_ancilla",
    "n_qubits",
    "score",
    "correct",
    "time_s",
    "xag_gates",
    "xag_and",
    "xag_xor",
    "xag_depth",
    "caterpillar_commit",
    "source",
    "skipped",
    "error",
    "truth_table_hex",
]


@dataclass(frozen=True)
class Task:
    dataset: str
    index: int
    name: str
    n: int
    truth_table_hex: str
    anf_terms: tuple[int, ...]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(THIS_DIR))
    except ValueError:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)


def run_command(args: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
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
    return proc.returncode, proc.stdout


def git_commit(root: Path) -> str:
    if not root.exists() or not shutil.which("git"):
        return "unknown"
    rc, out = run_command(["git", "rev-parse", "--short", "HEAD"], root, timeout=20)
    return out.strip().splitlines()[0] if rc == 0 and out.strip() else "unknown"


def load_tasks(path: Path) -> list[Task]:
    seen: set[tuple[str, int, str]] = set()
    tasks: list[Task] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("skipped") or row.get("correct") == "False":
                continue
            if not row.get("truth_table_hex"):
                continue
            key = (row["name"], int(row["n"]), row["truth_table_hex"])
            if key in seen:
                continue
            seen.add(key)
            n = int(row["n"])
            bf = BooleanFunction(n, int(row["truth_table_hex"], 16))
            terms = tuple(sorted(anf_monomials(bf)))
            tasks.append(
                Task(
                    dataset="traditional",
                    index=len(tasks),
                    name=row["name"],
                    n=n,
                    truth_table_hex=row["truth_table_hex"],
                    anf_terms=terms,
                )
            )
    return tasks


def cxx_string(value: str) -> str:
    return json.dumps(value)


def cxx_source(tasks: list[Task], commit: str) -> str:
    task_rows = []
    for task in tasks:
        terms = ", ".join(str(term) for term in task.anf_terms)
        task_rows.append(
            "  {"
            + ", ".join(
                [
                    cxx_string(task.dataset),
                    str(task.index),
                    cxx_string(task.name),
                    str(task.n),
                    cxx_string(task.truth_table_hex),
                    "{" + terms + "}",
                ]
            )
            + "}"
        )
    tasks_literal = ",\n".join(task_rows)
    strategies_literal = ", ".join(f'"{name}"' for name in STRATEGIES)
    return f"""
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include <caterpillar/caterpillar.hpp>
#include <caterpillar/details/utils.hpp>
#include <kitty/dynamic_truth_table.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/views/depth_view.hpp>
#include <mockturtle/networks/xag.hpp>
#include <tweedledum/networks/netlist.hpp>

struct Task {{
  std::string dataset;
  uint32_t index;
  std::string name;
  uint32_t n;
  std::string truth_hex;
  std::vector<uint32_t> terms;
}};

struct Result {{
  Task task;
  std::string strategy;
  uint32_t T = 0;
  uint32_t CNOT = 0;
  uint32_t depth = 0;
  uint32_t t_depth = 0;
  uint32_t gates = 0;
  uint32_t explicit_ancilla = 0;
  uint32_t peak_ancilla = 0;
  uint32_t n_qubits = 0;
  double time_s = 0.0;
  uint32_t xag_gates = 0;
  uint32_t xag_and = 0;
  uint32_t xag_xor = 0;
  uint32_t xag_depth = 0;
  bool correct = false;
  std::string skipped;
  std::string error;
}};

static std::vector<Task> tasks = {{
{tasks_literal}
}};

static std::vector<std::string> strategies = {{{strategies_literal}}};

mockturtle::xag_network build_xag(Task const& task) {{
  mockturtle::xag_network xag;
  std::vector<mockturtle::xag_network::signal> pis;
  for (uint32_t i = 0; i < task.n; ++i) {{
    pis.push_back(xag.create_pi());
  }}
  std::vector<mockturtle::xag_network::signal> term_signals;
  for (auto mask : task.terms) {{
    if (mask == 0) {{
      term_signals.push_back(xag.get_constant(true));
      continue;
    }}
    std::vector<mockturtle::xag_network::signal> factors;
    for (uint32_t bit = 0; bit < task.n; ++bit) {{
      if ((mask >> bit) & 1u) {{
        factors.push_back(pis[bit]);
      }}
    }}
    term_signals.push_back(xag.create_nary_and(factors));
  }}
  auto output = term_signals.empty() ? xag.get_constant(false) : xag.create_nary_xor(term_signals);
  xag.create_po(output);
  return xag;
}}

uint32_t gate_depth(tweedledum::netlist<caterpillar::stg_gate> const& circ) {{
  std::vector<uint32_t> depths(circ.num_qubits(), 0u);
  circ.foreach_cgate([&](auto const& node) {{
    std::vector<uint32_t> touched;
    node.gate.foreach_control([&](auto const& q) {{ touched.push_back(q.index()); }});
    node.gate.foreach_target([&](auto const& q) {{ touched.push_back(q.index()); }});
    uint32_t next_depth = 0u;
    for (auto q : touched) {{
      if (q < depths.size()) {{
        next_depth = std::max(next_depth, depths[q]);
      }}
    }}
    ++next_depth;
    for (auto q : touched) {{
      if (q < depths.size()) {{
        depths[q] = next_depth;
      }}
    }}
  }});
  return depths.empty() ? 0u : *std::max_element(depths.begin(), depths.end());
}}

std::tuple<uint32_t, uint32_t, uint32_t, uint32_t> xag_counts(mockturtle::xag_network const& xag) {{
  uint32_t gates = 0u;
  uint32_t ands = 0u;
  uint32_t xors = 0u;
  xag.foreach_gate([&](auto const& n) {{
    ++gates;
    if (xag.is_and(n)) {{
      ++ands;
    }} else if (xag.is_xor(n)) {{
      ++xors;
    }}
  }});
  mockturtle::depth_view<mockturtle::xag_network> depth_xag{{xag}};
  return {{gates, ands, xors, depth_xag.depth()}};
}}

template<class Strategy>
Result run_one_with_strategy(Task const& task, std::string const& strategy_name, bool low_depth_stats) {{
  Result out;
  out.task = task;
  out.strategy = strategy_name;
  auto started = std::chrono::steady_clock::now();
  try {{
    auto xag = build_xag(task);
    auto [xag_gates, xag_and, xag_xor, xag_depth] = xag_counts(xag);
    out.xag_gates = xag_gates;
    out.xag_and = xag_and;
    out.xag_xor = xag_xor;
    out.xag_depth = xag_depth;

    tweedledum::netlist<caterpillar::stg_gate> qnet;
    caterpillar::logic_network_synthesis_stats st;
    caterpillar::logic_network_synthesis_params ps;
    Strategy strategy;
    bool ok = caterpillar::logic_network_synthesis(qnet, xag, strategy, {{}}, ps, &st);
    if (!ok) {{
      out.skipped = "strategy_failed";
    }} else {{
      auto ntk = caterpillar::circuit_to_logic_network<mockturtle::xag_network,
          tweedledum::netlist<caterpillar::stg_gate>>(qnet, st.i_indexes, st.o_indexes);
      if (ntk) {{
        auto tt_xag = mockturtle::simulate<kitty::dynamic_truth_table>(xag, {{task.n}});
        auto tt_ntk = mockturtle::simulate<kitty::dynamic_truth_table>(*ntk, {{task.n}});
        out.correct = (tt_xag == tt_ntk);
      }}
      auto [CNOT, T_count, T_depth] = caterpillar::detail::qc_stats(qnet, low_depth_stats);
      out.T = T_count;
      out.CNOT = CNOT;
      out.t_depth = T_depth;
      out.depth = gate_depth(qnet);
      out.gates = qnet.num_gates();
      out.n_qubits = qnet.num_qubits();
      out.explicit_ancilla = st.required_ancillae;
      out.peak_ancilla = qnet.num_qubits() > task.n + 1u ? qnet.num_qubits() - (task.n + 1u) : 0u;
    }}
  }} catch (std::exception const& ex) {{
    out.error = ex.what();
  }} catch (...) {{
    out.error = "unknown_exception";
  }}
  auto stopped = std::chrono::steady_clock::now();
  out.time_s = std::chrono::duration<double>(stopped - started).count();
  return out;
}}

Result run_one(Task const& task, std::string const& strategy) {{
  if (strategy == "xag_lowt") {{
    return run_one_with_strategy<caterpillar::xag_mapping_strategy>(task, strategy, false);
  }}
  if (strategy == "xag_fast_lowt") {{
    return run_one_with_strategy<caterpillar::xag_fast_lowt_mapping_strategy>(task, strategy, false);
  }}
  return run_one_with_strategy<caterpillar::xag_low_depth_mapping_strategy>(task, strategy, true);
}}

double score(Result const& row) {{
  return 1.0 * row.T + 0.04 * row.CNOT + 0.015 * row.depth + 0.01 * row.gates + 2.0 * row.peak_ancilla;
}}

std::string csv_escape(std::string const& text) {{
  bool quote = text.find_first_of(",\\n\\r\\\"") != std::string::npos;
  if (!quote) {{
    return text;
  }}
  std::string out = "\\\"";
  for (char c : text) {{
    if (c == '\\\"') {{
      out += "\\\"\\\"";
    }} else {{
      out += c;
    }}
  }}
  out += "\\\"";
  return out;
}}

int main() {{
  std::cout
    << "dataset,index,name,n,anf_terms,method,strategy,T,CNOT,depth,t_depth_proxy,gates,"
    << "explicit_ancilla,peak_ancilla,n_qubits,score,correct,time_s,xag_gates,xag_and,"
    << "xag_xor,xag_depth,caterpillar_commit,source,skipped,error,truth_table_hex\\n";
  for (auto const& task : tasks) {{
    for (auto const& strategy : strategies) {{
      auto row = run_one(task, strategy);
      std::cout
        << csv_escape(row.task.dataset) << ","
        << row.task.index << ","
        << csv_escape(row.task.name) << ","
        << row.task.n << ","
        << row.task.terms.size() << ","
        << "external_caterpillar_xag_api" << ","
        << csv_escape(row.strategy) << ","
        << row.T << ","
        << row.CNOT << ","
        << row.depth << ","
        << row.t_depth << ","
        << row.gates << ","
        << row.explicit_ancilla << ","
        << row.peak_ancilla << ","
        << row.n_qubits << ","
        << score(row) << ","
        << (row.correct ? "True" : "False") << ","
        << row.time_s << ","
        << row.xag_gates << ","
        << row.xag_and << ","
        << row.xag_xor << ","
        << row.xag_depth << ","
        << csv_escape({cxx_string(commit)}) << ","
        << "anf_xag_api" << ","
        << csv_escape(row.skipped) << ","
        << csv_escape(row.error) << ","
        << csv_escape(row.task.truth_hex)
        << "\\n";
    }}
  }}
  return 0;
}}
""".strip() + "\n"


def build_and_run_tool(tasks: list[Task], commit: str, timeout: int) -> list[dict[str, str]]:
    compiler = Path("/usr/bin/c++")
    libabcsat = CATERPILLAR / "build-test" / "lib" / "abcsat" / "liblibabcsat.a"
    include_dirs = [
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
    missing = [path for path in [CATERPILLAR, compiler, libabcsat, *include_dirs] if not path.exists()]
    if missing:
        raise FileNotFoundError("missing Caterpillar prerequisites: " + "; ".join(rel(path) for path in missing))
    with tempfile.TemporaryDirectory(prefix="caterpillar_xag_api_") as tmp_name:
        tmp = Path(tmp_name)
        source = tmp / "caterpillar_xag_api_probe.cpp"
        exe = tmp / "caterpillar_xag_api_probe"
        source.write_text(cxx_source(tasks, commit), encoding="utf-8")
        cmd = [
            str(compiler),
            "-std=gnu++17",
            "-O2",
            "-DNDEBUG",
            "-arch",
            "arm64",
            "-DABC_NAMESPACE=pabc",
            "-DABC_NO_USE_READLINE",
            "-DDISABLE_NAUTY",
            "-DFMT_HEADER_ONLY",
            "-DLIN64",
            "-w",
        ]
        for include_dir in include_dirs[:-2]:
            cmd.extend(["-I", str(include_dir)])
        for include_dir in include_dirs[-2:]:
            cmd.extend(["-isystem", str(include_dir)])
        cmd.extend([str(source), str(libabcsat), "-o", str(exe)])
        rc, out = run_command(cmd, ROOT, timeout=timeout)
        if rc != 0:
            raise RuntimeError("Caterpillar XAG API probe compile failed:\n" + out[-4000:])
        rc, out = run_command([str(exe)], ROOT, timeout=timeout)
        if rc != 0:
            raise RuntimeError("Caterpillar XAG API probe run failed:\n" + out[-4000:])
    return list(csv.DictReader(out.splitlines()))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0.0)
    except ValueError:
        return 0.0


def wlt(target: dict[str, dict[str, str]], baseline: dict[str, dict[str, str]], metric: str) -> tuple[int, int, int, float]:
    wins = losses = ties = 0
    rels: list[float] = []
    for name in sorted(set(target) & set(baseline)):
        tv = f(target[name], metric)
        bv = f(baseline[name], metric)
        if abs(tv - bv) <= 1e-9:
            ties += 1
        elif tv < bv:
            wins += 1
        else:
            losses += 1
        rels.append((tv - bv) / max(abs(bv), 1.0) * 100.0)
    mean_rel = statistics.mean(rels) if rels else 0.0
    return wins, losses, ties, mean_rel


def normalize_timing(raw_rows: list[dict[str, str]]) -> None:
    """Keep tracked probe artifacts deterministic unless profiling is explicit."""
    for row in raw_rows:
        row["time_s"] = "0.0"


def summarize(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_strategy: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        by_strategy[row["strategy"]].append(row)
    summary: list[dict[str, str]] = []
    for strategy, rows in sorted(by_strategy.items()):
        ok_rows = [row for row in rows if row["correct"] == "True" and not row["skipped"] and not row["error"]]
        status = "pass" if len(ok_rows) == len(rows) else "needs revision"
        summary.append(
            {
                "item": strategy,
                "status": status,
                "rows": str(len(rows)),
                "correct_rows": str(len(ok_rows)),
                "mean_T": f"{statistics.mean(f(row, 'T') for row in ok_rows):.4f}" if ok_rows else "nan",
                "mean_CNOT": f"{statistics.mean(f(row, 'CNOT') for row in ok_rows):.4f}" if ok_rows else "nan",
                "mean_depth": f"{statistics.mean(f(row, 'depth') for row in ok_rows):.4f}" if ok_rows else "nan",
                "mean_peak_ancilla": f"{statistics.mean(f(row, 'peak_ancilla') for row in ok_rows):.4f}" if ok_rows else "nan",
                "mean_score": f"{statistics.mean(f(row, 'score') for row in ok_rows):.4f}" if ok_rows else "nan",
                "mean_time_s": f"{statistics.mean(f(row, 'time_s') for row in ok_rows):.6f}" if ok_rows else "nan",
            }
        )
    best_by_function: dict[str, dict[str, str]] = {}
    for row in raw_rows:
        if row["correct"] != "True" or row["skipped"] or row["error"]:
            continue
        current = best_by_function.get(row["name"])
        if current is None or (f(row, "score"), f(row, "T"), f(row, "CNOT")) < (
            f(current, "score"),
            f(current, "T"),
            f(current, "CNOT"),
        ):
            best_by_function[row["name"]] = row
    if best_by_function:
        rows = list(best_by_function.values())
        summary.append(
            {
                "item": "best_of_caterpillar_xag_api",
                "status": "pass",
                "rows": str(len(rows)),
                "correct_rows": str(len(rows)),
                "mean_T": f"{statistics.mean(f(row, 'T') for row in rows):.4f}",
                "mean_CNOT": f"{statistics.mean(f(row, 'CNOT') for row in rows):.4f}",
                "mean_depth": f"{statistics.mean(f(row, 'depth') for row in rows):.4f}",
                "mean_peak_ancilla": f"{statistics.mean(f(row, 'peak_ancilla') for row in rows):.4f}",
                "mean_score": f"{statistics.mean(f(row, 'score') for row in rows):.4f}",
                "mean_time_s": f"{statistics.mean(f(row, 'time_s') for row in rows):.6f}",
            }
        )
    return summary


def best_rows(raw_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    best: dict[str, dict[str, str]] = {}
    for row in raw_rows:
        if row.get("correct") != "True" or row.get("skipped") or row.get("error"):
            continue
        cur = best.get(row["name"])
        if cur is None or (f(row, "score"), f(row, "T"), f(row, "CNOT")) < (
            f(cur, "score"),
            f(cur, "T"),
            f(cur, "CNOT"),
        ):
            best[row["name"]] = row
    return best


def best_row_list(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name, row in sorted(best_rows(raw_rows).items()):
        copied = dict(row)
        copied["method"] = "external_caterpillar_xag_api_best"
        copied["strategy"] = f"best:{row.get('strategy', '')}"
        rows.append(copied)
    return rows


def load_baseline(method: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with INPUT.open(newline="", encoding="utf-8") as f_in:
        for row in csv.DictReader(f_in):
            if row.get("method") == method and row.get("correct") == "True":
                out[row["name"]] = row
    return out


def write_analysis(
    path: Path,
    raw_rows: list[dict[str, str]],
    summary: list[dict[str, str]],
    commit: str,
    timing_mode: str,
) -> None:
    status_counts = Counter(row["status"] for row in summary)
    best = best_rows(raw_rows)
    baselines = {
        "and_pareto_resource_nmcts": load_baseline("and_pareto_resource_nmcts"),
        "and_resource_nmcts": load_baseline("and_resource_nmcts"),
        "and_direct_anf": load_baseline("and_direct_anf"),
        "sshr_h": load_baseline("sshr_h"),
    }
    lines = [
        "# Caterpillar XAG API Probe",
        "",
        "This bounded probe runs Caterpillar's logic-network synthesis API on the same traditional n<=6 truth-table functions used by the main small-function experiment.",
        "",
        "It is a real Caterpillar API performance probe over ANF-XAG inputs, but it is still not the official ROS SAT garbage-management flow.",
        "",
        "## Status counts",
        "",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            f"- Caterpillar checkout: `{rel(CATERPILLAR)}`",
            f"- Caterpillar commit: `{commit}`",
            f"- input rows: `{rel(INPUT)}`",
            f"- raw probe rows: {len(raw_rows)}",
            f"- unique functions covered by best-of-Caterpillar: {len(best)}",
            f"- timing mode: `{timing_mode}`",
            "",
            "## Strategy Summary",
            "",
            "| item | status | rows | correct rows | mean T | mean CNOT | mean depth | mean peak ancilla | mean score | mean time s |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary:
        lines.append(
            "| {item} | {status} | {rows} | {correct_rows} | {mean_T} | {mean_CNOT} | {mean_depth} | {mean_peak_ancilla} | {mean_score} | {mean_time_s} |".format(
                **row
            )
        )
    lines.extend(["", "## Matched Comparison", ""])
    lines.append("| baseline | metric | W/L/T for Caterpillar best | mean relative delta |")
    lines.append("|---|---|---:|---:|")
    for baseline_name, baseline in baselines.items():
        for metric in ("score", "T", "CNOT", "depth", "peak_ancilla"):
            wins, losses, ties, mean_rel = wlt(best, baseline, metric)
            lines.append(f"| {baseline_name} | {metric} | {wins}/{losses}/{ties} | {mean_rel:+.2f}% |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Supported claim: Caterpillar can now be cited as a bounded, verified API-level implementation-family counterpoint on the same traditional function names.",
            "- Timing note: tracked outputs normalize wall-clock timings to zero by default so the rebuild and payload hash remain deterministic; rerun with `--measure-time` only for local profiling.",
            "- Excluded claim: these rows do not reproduce full ROS SAT garbage management, LUT mapping, reversible emission, routing, or hardware mapping.",
        ]
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


def write_latex(path: Path, summary: list[dict[str, str]], raw_rows: list[dict[str, str]]) -> None:
    best = best_rows(raw_rows)
    pareto = load_baseline("and_pareto_resource_nmcts")
    direct = load_baseline("and_direct_anf")
    rows = [row for row in summary if row["item"] in {"xag_lowt", "xag_fast_lowt", "xag_lowd", "best_of_caterpillar_xag_api"}]
    labels = {
        "xag_fast_lowt": "fast low-T",
        "xag_lowd": "low-depth",
        "xag_lowt": "low-T",
        "best_of_caterpillar_xag_api": "best API",
    }
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth}rrrr>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Caterpillar API row & Rows & Correct & Mean $T$ & Mean score & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        if row["item"] == "best_of_caterpillar_xag_api":
            p_w, p_l, p_t, p_rel = wlt(best, pareto, "score")
            d_w, d_l, d_t, d_rel = wlt(best, direct, "score")
            boundary = f"score vs Pareto {p_w}/{p_l}/{p_t}, {p_rel:+.1f}%; vs direct {d_w}/{d_l}/{d_t}, {d_rel:+.1f}%"
        else:
            boundary = "verified ANF-XAG input; not ROS"
        lines.append(
            " & ".join(
                [
                    tex_escape(labels.get(row["item"], row["item"])),
                    row["rows"],
                    row["correct_rows"],
                    row["mean_T"],
                    row["mean_score"],
                    tex_escape(boundary),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(
    path: Path,
    tasks: list[Task],
    raw_rows: list[dict[str, str]],
    summary: list[dict[str, str]],
    commit: str,
    timing_mode: str,
) -> None:
    needs_revision = sum(1 for row in summary if row["status"] == "needs revision")
    best = best_rows(raw_rows)
    pareto = load_baseline("and_pareto_resource_nmcts")
    score_wlt = wlt(best, pareto, "score")
    pareto_score_wlt = wlt(pareto, best, "score")
    cnot_wlt = wlt(pareto, best, "CNOT")
    data = {
        "script": Path(__file__).name,
        "caterpillar_path": rel(CATERPILLAR),
        "caterpillar_commit": commit,
        "input": rel(INPUT),
        "tasks": len(tasks),
        "strategies": list(STRATEGIES),
        "raw_rows": len(raw_rows),
        "timing_mode": timing_mode,
        "best_raw_rows": len(best),
        "summary_rows": len(summary),
        "correct_rows": sum(1 for row in raw_rows if row["correct"] == "True"),
        "needs_revision_count": needs_revision,
        "best_functions": len(best),
        "score_wlt_vs_pareto": f"{score_wlt[0]}/{score_wlt[1]}/{score_wlt[2]}",
        "score_mean_relative_vs_pareto_pct": score_wlt[3],
        "pareto_score_wlt_vs_caterpillar": f"{pareto_score_wlt[0]}/{pareto_score_wlt[1]}/{pareto_score_wlt[2]}",
        "pareto_score_mean_relative_vs_caterpillar_pct": pareto_score_wlt[3],
        "pareto_cnot_wlt_vs_caterpillar": f"{cnot_wlt[0]}/{cnot_wlt[1]}/{cnot_wlt[2]}",
        "pareto_cnot_mean_relative_vs_caterpillar_pct": cnot_wlt[3],
        "official_ros_fully_reproduced": False,
        "caterpillar_is_performance_baseline": True,
        "caterpillar_api_input": "ANF-XAG",
        "weights": DEFAULT_WEIGHTS,
        "outputs": {
            "raw": rel(RAW_OUT),
            "best_raw": rel(BEST_OUT),
            "summary": rel(SUMMARY_OUT),
            "analysis": rel(ANALYSIS_OUT),
            "manifest": rel(MANIFEST_OUT),
            "table": rel(TABLE_OUT),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--measure-time",
        action="store_true",
        help=(
            "keep measured wall-clock timings in generated CSV/Markdown outputs. "
            "The default normalizes time_s to zero for deterministic tracked artifacts."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = load_tasks(INPUT)
    commit = git_commit(CATERPILLAR)
    raw_rows = build_and_run_tool(tasks, commit, timeout=240)
    timing_mode = "measured_wall_clock" if args.measure_time else "normalized_zero"
    if not args.measure_time:
        normalize_timing(raw_rows)
    best_raw_rows = best_row_list(raw_rows)
    summary = summarize(raw_rows)
    write_csv(RAW_OUT, raw_rows, FIELDS)
    write_csv(BEST_OUT, best_raw_rows, FIELDS)
    write_csv(
        SUMMARY_OUT,
        summary,
        [
            "item",
            "status",
            "rows",
            "correct_rows",
            "mean_T",
            "mean_CNOT",
            "mean_depth",
            "mean_peak_ancilla",
            "mean_score",
            "mean_time_s",
        ],
    )
    write_analysis(ANALYSIS_OUT, raw_rows, summary, commit, timing_mode)
    write_latex(TABLE_OUT, summary, raw_rows)
    write_manifest(MANIFEST_OUT, tasks, raw_rows, summary, commit, timing_mode)
    print(f"wrote {len(raw_rows)} Caterpillar XAG API probe rows")


if __name__ == "__main__":
    main()
