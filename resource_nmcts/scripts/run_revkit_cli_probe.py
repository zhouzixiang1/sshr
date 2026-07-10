#!/usr/bin/env python3
"""Run a legacy RevKit CLI reversible-synthesis baseline.

This adapter turns each Boolean function into the exact reversible oracle
permutation ``(x,y) -> (x, y xor f(x))`` and runs the legacy RevKit shell on
that reversible specification.  The default flow is transformation-based
synthesis (``tbs``).  Unlike the RevKit Python ``oracle_synth`` adapter, this
is a bit-flip reversible-circuit baseline rather than an Rz-phase netlist.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable

from run_external_baselines import DEFAULT_WEIGHTS, display_path

ROOT = Path(__file__).resolve().parents[1]
THIS_DIR = Path(__file__).resolve().parent
SSHR_DIR = ROOT / "sshr"
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
DEFAULT_REVKIT_BIN = ROOT / "tmp" / "cirkit_legacy" / "build" / "programs" / "revkit"
DEFAULT_REVKIT_ROOT = ROOT / "tmp" / "cirkit_legacy"

TARGET_METHODS = [
    "and_resource_nmcts",
    "and_profile_resource_nmcts",
    "and_pareto_resource_nmcts",
    "and_fprm_polarity_archive",
    "and_fprm_linear_pair",
    "and_fprm_root_beam",
    "and_direct_anf",
    "direct_anf",
    "and_esop_milp",
    "sshr_h",
]

PS_INT_RE = {
    "lines": re.compile(r"^Lines:\s*(\d+)\s*$", re.MULTILINE),
    "gates": re.compile(r"^Gates:\s*(\d+)\s*$", re.MULTILINE),
    "t_count": re.compile(r"^T-count:\s*(\d+)\s*$", re.MULTILINE),
    "logic_qubits": re.compile(r"^Logic qubits:\s*(\d+)\s*$", re.MULTILINE),
}


@dataclass(frozen=True)
class RevKitCliTask:
    name: str
    n: int
    truth_table_hex: str
    flow_name: str
    flow_command: str
    timeout: float
    revkit_bin: Path
    revkit_commit: str


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_tasks(path: Path, max_n: int | None, limit: int | None) -> list[dict[str, str]]:
    rows = load_csv(path)
    by_name: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        if not row.get("truth_table_hex"):
            continue
        n = int(row["n"])
        if max_n is not None and n > max_n:
            continue
        by_name.setdefault(row["name"], row)
    tasks = sorted(by_name.values(), key=lambda item: (int(item["n"]), item["name"]))
    if limit is not None:
        return tasks[:limit]
    return tasks


def parse_flows(items: list[str] | None) -> list[tuple[str, str]]:
    if not items:
        return [("tbs", "tbs")]
    flows: list[tuple[str, str]] = []
    for item in items:
        if "=" in item:
            name, command = item.split("=", 1)
            flows.append((name.strip(), command.strip()))
        else:
            name = item.strip().replace(" ", "_").replace("-", "_")
            flows.append((name, item.strip()))
    return [(name, command) for name, command in flows if name and command]


def parse_methods(value: str) -> list[str]:
    methods = [item.strip() for item in value.split(",") if item.strip()]
    return methods or TARGET_METHODS


def git_commit(path: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "unknown"


def oracle_permutation(n: int, truth: int) -> list[int]:
    size = 1 << (n + 1)
    mask = (1 << n) - 1
    perm: list[int] = []
    for value in range(size):
        x = value & mask
        y = (value >> n) & 1
        f = (truth >> x) & 1
        perm.append(x | ((y ^ f) << n))
    if sorted(perm) != list(range(size)):
        raise ValueError("generated oracle mapping is not a permutation")
    return perm


def parse_ps_values(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, pattern in PS_INT_RE.items():
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"RevKit output missing {key}: {text[-1200:]}")
        out[key] = int(match.group(1))
    return out


def parse_gate_distribution(text: str) -> dict[str, dict[int, int]]:
    lines = text.splitlines()
    controls: list[int] | None = None
    distribution: dict[str, dict[int, int]] = {}
    for line in lines:
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 3:
            continue
        if parts[0] == "controls":
            controls = [int(part) for part in parts[1:-1] if part and part != "total"]
            continue
        if controls is None:
            continue
        label = parts[0].lower().replace("-", "_").replace(" ", "_")
        values = [int(part) for part in parts[1:-1]]
        if len(values) == len(controls):
            distribution[label] = {control: value for control, value in zip(controls, values)}
    return distribution


def mct_standard_cost(controls: int) -> tuple[int, int]:
    """Return (CNOT, depth proxy) for one MCT gate under the project table."""
    if controls <= 0:
        return 0, 1
    if controls == 1:
        return 1, 1
    if str(SSHR_DIR) not in sys.path:
        sys.path.insert(0, str(SSHR_DIR))
    from src.sshr_lib.bool_func import mct_cost  # noqa: PLC0415

    cost = mct_cost(controls)
    cnot = int(cost["CNOT"])
    return cnot, max(1, cnot)


def estimate_cnot_depth(distribution: dict[str, dict[int, int]], total_gates: int) -> tuple[int, int, int]:
    cnot = 0
    depth = 0
    accounted = 0
    for controls, count in distribution.get("toffoli", {}).items():
        gate_cnot, gate_depth = mct_standard_cost(controls)
        cnot += gate_cnot * count
        depth += gate_depth * count
        accounted += count
    for controls, count in distribution.get("fredkin", {}).items():
        # A controlled-SWAP can be decomposed into three controlled-X style gates
        # at the same control size plus one target.  RevKit TBS did not emit
        # Fredkin gates in our probes, but keep a conservative parser path.
        gate_cnot, gate_depth = mct_standard_cost(max(1, controls + 1))
        cnot += 3 * gate_cnot * count
        depth += 3 * gate_depth * count
        accounted += count
    unknown = max(0, total_gates - accounted)
    depth += unknown
    return cnot, depth, unknown


def score(row: dict[str, object]) -> float:
    return (
        DEFAULT_WEIGHTS["t"] * float(row["T"])
        + DEFAULT_WEIGHTS["cnot"] * float(row["CNOT"])
        + DEFAULT_WEIGHTS["depth"] * float(row["depth"])
        + DEFAULT_WEIGHTS["gates"] * float(row["gates"])
        + DEFAULT_WEIGHTS["ancilla"] * float(row["peak_ancilla"])
    )


def run_task(task: RevKitCliTask) -> dict[str, object]:
    started = time.time()
    base = {
        "name": task.name,
        "n": task.n,
        "truth_table_hex": task.truth_table_hex,
        "method": f"external_revkit_cli_{task.flow_name}",
        "flow": task.flow_command,
        "revkit_commit": task.revkit_commit,
    }
    try:
        if not task.revkit_bin.exists():
            raise FileNotFoundError(f"RevKit binary not found: {task.revkit_bin}")
        truth = int(task.truth_table_hex, 16)
        perm = oracle_permutation(task.n, truth)
        command = (
            f"read_spec -p \"{' '.join(map(str, perm))}\"; "
            f"{task.flow_command}; ps -c; gates"
        )
        proc = subprocess.run(
            [str(task.revkit_bin), "-c", command],
            text=True,
            capture_output=True,
            timeout=task.timeout,
            check=False,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(f"RevKit failed with code {proc.returncode}: {text[-1600:]}")
        values = parse_ps_values(text)
        distribution = parse_gate_distribution(text)
        cnot, depth, unknown = estimate_cnot_depth(distribution, values["gates"])
        explicit = max(0, values["lines"] - (task.n + 1))
        peak = max(0, values["logic_qubits"] - (task.n + 1), explicit)
        row: dict[str, object] = {
            **base,
            "T": values["t_count"],
            "CNOT": cnot,
            "depth": depth,
            "gates": values["gates"],
            "explicit_ancilla": explicit,
            "peak_ancilla": peak,
            "n_qubits": values["logic_qubits"],
            "revkit_lines": values["lines"],
            "revkit_logic_qubits": values["logic_qubits"],
            "revkit_t_count": values["t_count"],
            "unknown_gates": unknown,
            "toffoli_distribution": json.dumps(distribution.get("toffoli", {}), sort_keys=True),
            "correct": True,
            "permutation_checked": True,
            "time_s": time.time() - started,
            "skipped": "",
            "error": "",
        }
        row["score"] = score(row)
        return row
    except subprocess.TimeoutExpired as exc:
        return {
            **base,
            "T": "",
            "CNOT": "",
            "depth": "",
            "gates": "",
            "explicit_ancilla": "",
            "peak_ancilla": "",
            "n_qubits": "",
            "score": "",
            "revkit_lines": "",
            "revkit_logic_qubits": "",
            "revkit_t_count": "",
            "unknown_gates": "",
            "toffoli_distribution": "",
            "correct": "",
            "permutation_checked": "",
            "time_s": time.time() - started,
            "skipped": "",
            "error": f"TimeoutExpired({exc.timeout})",
        }
    except Exception as exc:
        return {
            **base,
            "T": "",
            "CNOT": "",
            "depth": "",
            "gates": "",
            "explicit_ancilla": "",
            "peak_ancilla": "",
            "n_qubits": "",
            "score": "",
            "revkit_lines": "",
            "revkit_logic_qubits": "",
            "revkit_t_count": "",
            "unknown_gates": "",
            "toffoli_distribution": "",
            "correct": "",
            "permutation_checked": "",
            "time_s": time.time() - started,
            "skipped": "",
            "error": repr(exc),
        }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preferred = [
        "name",
        "n",
        "method",
        "flow",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "revkit_lines",
        "revkit_logic_qubits",
        "revkit_t_count",
        "unknown_gates",
        "time_s",
        "correct",
        "permutation_checked",
        "toffoli_distribution",
        "skipped",
        "error",
        "truth_table_hex",
        "revkit_commit",
    ]
    fieldnames = sorted({key for row in rows for key in row})
    ordered = [key for key in preferred if key in fieldnames]
    ordered.extend(key for key in fieldnames if key not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def usable(row: dict[str, object]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def by_name_method(rows: Iterable[dict[str, object]]) -> dict[str, dict[str, dict[str, object]]]:
    out: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        out.setdefault(str(row["name"]), {})[str(row["method"])] = row
    return out


def relative(new: float, base: float) -> float:
    return (new - base) / max(abs(base), 1.0)


def compare(
    joined: dict[str, dict[str, dict[str, object]]],
    target: str,
    baseline: str,
    metric: str,
) -> dict[str, object] | None:
    relatives: list[float] = []
    wins = losses = ties = 0
    by_n: dict[int, int] = {}
    for methods in joined.values():
        if target not in methods or baseline not in methods:
            continue
        try:
            new = float(methods[target][metric])
            old = float(methods[baseline][metric])
        except (KeyError, TypeError, ValueError):
            continue
        if new < old:
            wins += 1
        elif new > old:
            losses += 1
        else:
            ties += 1
        relatives.append(relative(new, old))
        n = int(methods[target].get("n", methods[baseline].get("n", -1)))
        by_n[n] = by_n.get(n, 0) + 1
    if not relatives:
        return None
    return {
        "target": target,
        "baseline": baseline,
        "metric": metric,
        "items": len(relatives),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_relative": statistics.mean(relatives),
        "median_relative": statistics.median(relatives),
        "by_n": ";".join(f"{n}:{count}" for n, count in sorted(by_n.items())),
    }


def summarize(raw_rows: list[dict[str, object]], internal_rows: list[dict[str, object]], targets: list[str]) -> list[dict[str, object]]:
    joined = by_name_method(internal_rows)
    for name, methods in by_name_method(raw_rows).items():
        joined.setdefault(name, {}).update(methods)
    baselines = sorted({row["method"] for row in raw_rows if usable(row)})
    out: list[dict[str, object]] = []
    for baseline in baselines:
        for target in targets:
            for metric in ("score", "T", "CNOT", "depth", "peak_ancilla"):
                item = compare(joined, target, str(baseline), metric)
                if item is not None:
                    out.append(item)
    return out


def add_best_score_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        if usable(row) and str(row.get("method", "")) != "external_revkit_cli_best_score":
            grouped.setdefault(str(row["name"]), []).append(row)
    best_rows: list[dict[str, object]] = []
    for name, subset in grouped.items():
        if len({str(row["method"]) for row in subset}) <= 1:
            continue
        best = min(subset, key=lambda row: float(row["score"]))
        out = dict(best)
        out["method"] = "external_revkit_cli_best_score"
        out["selected_method"] = best["method"]
        out["flow"] = f"best_score:{best.get('flow', '')}"
        best_rows.append(out)
    return best_rows


def write_summary_csv(path: Path, summaries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "target",
                "baseline",
                "metric",
                "items",
                "wins",
                "losses",
                "ties",
                "mean_relative",
                "median_relative",
                "by_n",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summaries)


def write_analysis(
    path: Path,
    rows: list[dict[str, object]],
    summaries: list[dict[str, object]],
    args: argparse.Namespace,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    direct_rows = [row for row in rows if row.get("method") != "external_revkit_cli_best_score"]
    best_rows = [row for row in rows if row.get("method") == "external_revkit_cli_best_score"]
    usable_rows = [row for row in direct_rows if usable(row)]
    errors = [row for row in direct_rows if row.get("error")]
    timeouts = [row for row in direct_rows if "TimeoutExpired" in str(row.get("error", ""))]
    times = [float(row.get("time_s") or 0.0) for row in direct_rows]
    lines = [
        "# RevKit CLI Reversible Baseline",
        "",
        "Scope: each Boolean function is embedded as the exact reversible oracle permutation `(x,y)->(x,y xor f(x))`; legacy RevKit CLI reads that SPEC permutation and runs the configured reversible synthesis flow.  The default run uses `tbs`.",
        "",
        "This is a legacy RevKit/CirKit command-line reversible-synthesis probe.  It is logic-layer only and does not include hardware mapping.",
        "",
        f"- RevKit binary: `{display_path(args.revkit_bin)}`",
        f"- RevKit root: `{display_path(args.revkit_root)}`",
        f"- RevKit commit: `{git_commit(args.revkit_root)}`",
        f"- CLI flow rows attempted: {len(direct_rows)}",
        f"- usable CLI flow rows: {len(usable_rows)}",
        f"- synthetic best-score portfolio rows: {len(best_rows)}",
        f"- error CLI flow rows: {len(errors)}",
        f"- timeout CLI flow rows: {len(timeouts)}",
        f"- median time: {statistics.median(times) if times else 0.0:.4f} s",
        f"- max time: {max(times, default=0.0):.4f} s",
        "",
        "## Comparisons",
        "",
        "| Target | Baseline | Metric | Items | W/L/T | Mean relative | Median relative |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['target']} | {row['baseline']} | {row['metric']} | {row['items']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | "
            f"{float(row['mean_relative']):+.2%} | {float(row['median_relative']):+.2%} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This probe removes the previous boundary that legacy RevKit CLI was unavailable locally: the CLI was built from the legacy `develop` branch and exercised on exact reversible oracle specifications.",
            "- `T` is RevKit's own Maslov-style T-count from `ps -c`; CNOT and depth are derived from the Toffoli control distribution using the project's MCT cost table.",
            "- `peak_ancilla` is derived from RevKit logic qubits relative to the `n+1` oracle lines, so this comparison focuses on logical line usage rather than hardware routing or magic-state factories.",
            "- Successful rows are checked for oracle-permutation bijectivity before invoking RevKit.  RevKit synthesis correctness is delegated to `read_spec` plus the deterministic synthesis command accepting the exact permutation.",
        ]
    )
    if errors:
        lines.extend(["", "## Error Samples", ""])
        for row in errors[:10]:
            lines.append(f"- {row.get('name')} `{row.get('method')}`: {row.get('error')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summaries: list[dict[str, object]], metric: str = "score") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    baselines = {str(row["baseline"]) for row in summaries}
    baseline = "external_revkit_cli_best_score" if "external_revkit_cli_best_score" in baselines else "external_revkit_cli_tbs"
    rows = [row for row in summaries if row["metric"] == metric and row["baseline"] == baseline]
    order = {name: index for index, name in enumerate(TARGET_METHODS)}
    rows.sort(key=lambda row: order.get(str(row["target"]), 999))
    baseline_labels = {
        "external_revkit_cli_best_score": "RevKit CLI best-score",
        "external_revkit_cli_tbs": "RevKit CLI TBS",
        "external_revkit_cli_dbs": "RevKit CLI DBS",
        "external_revkit_cli_rms": "RevKit CLI RMS",
    }
    baseline_label = baseline_labels.get(baseline, baseline.replace("_", "\\_"))
    lines = [
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        f"Target vs {baseline_label} & Items & W/L/T & Mean $\\Delta$ \\\\",
        "\\midrule",
    ]
    for row in rows:
        label = str(row["target"]).replace("_", "\\_")
        mean_delta = f"{float(row['mean_relative']):+.2%}".replace("%", "\\%")
        lines.append(f"{label} & {row['items']} & {row['wins']}/{row['losses']}/{row['ties']} & {mean_delta} \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, args: argparse.Namespace, rows: list[dict[str, object]], summaries: list[dict[str, object]]) -> None:
    payload = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "script": Path(__file__).name,
        "argv": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "revkit_commit": git_commit(args.revkit_root),
        "rows": len(rows),
        "usable_rows": sum(1 for row in rows if usable(row)),
        "summary_rows": len(summaries),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RESULTS / "raw_traditional_resource.csv")
    parser.add_argument("--max-n", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--flow", action="append", default=None, help="flow as name=command; default is tbs")
    parser.add_argument("--targets", default=",".join(TARGET_METHODS))
    parser.add_argument("--revkit-bin", type=Path, default=DEFAULT_REVKIT_BIN)
    parser.add_argument("--revkit-root", type=Path, default=DEFAULT_REVKIT_ROOT)
    parser.add_argument("--raw-out", type=Path, default=RESULTS / "raw_revkit_cli_tbs_traditional.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_revkit_cli_tbs_traditional.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_revkit_cli_tbs_traditional.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "revkit_cli_tbs_traditional.tex")
    parser.add_argument("--run-manifest", type=Path, default=RESULTS / "manifest_revkit_cli_tbs_traditional.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    args.input = args.input if args.input.is_absolute() else THIS_DIR / args.input
    args.raw_out = args.raw_out if args.raw_out.is_absolute() else THIS_DIR / args.raw_out
    args.summary = args.summary if args.summary.is_absolute() else THIS_DIR / args.summary
    args.analysis = args.analysis if args.analysis.is_absolute() else THIS_DIR / args.analysis
    args.latex_out = args.latex_out if args.latex_out.is_absolute() else THIS_DIR / args.latex_out
    args.run_manifest = args.run_manifest if args.run_manifest.is_absolute() else THIS_DIR / args.run_manifest
    args.revkit_bin = args.revkit_bin if args.revkit_bin.is_absolute() else ROOT / args.revkit_bin
    args.revkit_root = args.revkit_root if args.revkit_root.is_absolute() else ROOT / args.revkit_root

    base_rows = load_tasks(args.input, args.max_n, args.limit)
    flows = parse_flows(args.flow)
    revkit_commit = git_commit(args.revkit_root)
    tasks = [
        RevKitCliTask(
            name=row["name"],
            n=int(row["n"]),
            truth_table_hex=row["truth_table_hex"],
            flow_name=flow_name,
            flow_command=flow_command,
            timeout=args.timeout,
            revkit_bin=args.revkit_bin,
            revkit_commit=revkit_commit,
        )
        for row in base_rows
        for flow_name, flow_command in flows
    ]

    rows: list[dict[str, object]] = []
    if args.workers <= 1:
        for task in tasks:
            rows.append(run_task(task))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_task, task): task for task in tasks}
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda item: (int(item["n"]), str(item["name"]), str(item["method"])))

    internal_rows = [dict(row) for row in load_csv(args.input) if not row.get("error") and not row.get("skipped")]
    targets = parse_methods(args.targets)
    rows.extend(add_best_score_rows(rows))
    rows.sort(key=lambda item: (int(item["n"]), str(item["name"]), str(item["method"])))
    summaries = summarize(rows, internal_rows, targets)
    write_csv(args.raw_out, rows)
    write_summary_csv(args.summary, summaries)
    write_analysis(args.analysis, rows, summaries, args)
    write_latex(args.latex_out, summaries)
    write_manifest(args.run_manifest, args, rows, summaries)
    print(f"wrote {args.raw_out}")
    print(f"wrote {args.summary}")
    print(f"wrote {args.analysis}")
    print(f"wrote {args.latex_out}")
    print(f"wrote {args.run_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
