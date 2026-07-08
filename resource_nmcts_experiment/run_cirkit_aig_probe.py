#!/usr/bin/env python3
"""Run an official CirKit-shell AIG multiplicative-complexity probe.

This adapter is intentionally narrower than a RevKit/ROS reproduction.  It
uses ABC only to convert the exported BLIF benchmarks into AIGER and to verify
the Verilog that CirKit writes after AIG optimization.  The resource score is a
logic-layer proxy derived from CirKit's AIG multiplicative-complexity report.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from run_external_baselines import (
    DEFAULT_ABC_BIN,
    DEFAULT_WEIGHTS,
    abc_xag_cost,
    bool_from_row,
    display_path,
    load_manifest,
    verify_blif,
)


THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
DEFAULT_CIRKIT_BIN = ROOT / "tmp" / "cirkit" / "build" / "cli" / "cirkit"
DEFAULT_CIRKIT_ROOT = ROOT / "tmp" / "cirkit"
DEFAULT_FLOW = "cut_rewrite,resub"

TARGET_METHODS = [
    "and_resource_nmcts",
    "and_profile_resource_nmcts",
    "and_pareto_resource_nmcts",
    "and_fprm_polarity_archive",
    "and_fprm_linear_pair",
    "and_fprm_root_beam",
    "and_fprm_greedy",
    "and_affine_greedy",
    "and_direct_anf",
    "direct_anf",
    "and_esop_milp",
    "sshr_h",
]

AIG_STATS_RE = re.compile(r"AIG\s+i/o\s*=\s*(\d+)/(\d+)\s+gates\s*=\s*(\d+)\s+level\s*=\s*(\d+)")
MC_SIZE_RE = re.compile(r"mult\.\s+compl\.\s+size\s*=\s*(\d+)")
MC_DEPTH_RE = re.compile(r"mult\.\s+compl\.\s+depth\s*=\s*(\d+)")


@dataclass(frozen=True)
class CirKitTask:
    dataset: str
    row: dict[str, str]
    timeout: float
    abc_bin: Path
    cirkit_bin: Path
    flow: tuple[str, ...]
    cirkit_commit: str


def parse_labeled_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, path = value.split("=", 1)
    return label.strip(), Path(path.strip())


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else THIS_DIR / path


def parse_methods(value: str) -> list[str]:
    methods = [item.strip() for item in value.split(",") if item.strip()]
    return methods or TARGET_METHODS


def parse_flow(value: str) -> tuple[str, ...]:
    commands: list[str] = []
    mapping = {
        "cut_rewrite": "cut_rewrite -a",
        "resub": "resub -a",
        "lut_mapping4": "lut_mapping -a -k 4",
    }
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        commands.append(mapping.get(item, item))
    return tuple(commands)


def get_git_commit(path: Path) -> str:
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


def parse_cirkit_stats(text: str) -> dict[str, int]:
    aig_matches = list(AIG_STATS_RE.finditer(text))
    if not aig_matches:
        raise RuntimeError(f"CirKit output missing AIG stats: {text[-1000:]}")
    aig = aig_matches[-1]
    size = MC_SIZE_RE.search(text)
    depth = MC_DEPTH_RE.search(text)
    if size is None or depth is None:
        raise RuntimeError(f"CirKit output missing mccost stats: {text[-1000:]}")
    return {
        "aig_inputs": int(aig.group(1)),
        "aig_outputs": int(aig.group(2)),
        "aig_gates": int(aig.group(3)),
        "aig_level": int(aig.group(4)),
        "mc_size": int(size.group(1)),
        "mc_depth": int(depth.group(1)),
    }


def score_cost(cost) -> float:
    return cost.score(DEFAULT_WEIGHTS)


def run_abc_verify_verilog(abc_bin: Path, verilog: Path, out_blif: Path, bf, timeout: float) -> bool:
    command = f"read_verilog {verilog}; strash; write_blif {out_blif}; print_stats"
    proc = subprocess.run(
        [str(abc_bin), "-c", command],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(f"ABC Verilog verification conversion failed: {combined[-1200:]}")
    if not out_blif.exists():
        raise RuntimeError(f"ABC did not write verification BLIF: {combined[-1200:]}")
    return verify_blif(out_blif, bf)


def evaluate_task(task: CirKitTask) -> dict[str, object]:
    bf = bool_from_row(task.row)
    flow_label = ",".join(task.flow)
    base = {
        "dataset": task.dataset,
        "index": task.row.get("index", ""),
        "name": task.row["name"],
        "preset_name": task.row.get("preset_name", task.row["name"]),
        "n": bf.n,
        "anf_terms": task.row.get("anf_terms", ""),
        "method": "external_cirkit_aig_mc",
        "flow": flow_label,
        "source_manifest": task.row.get("_manifest_dir", ""),
        "cirkit_commit": task.cirkit_commit,
    }
    try:
        if not task.abc_bin.exists():
            raise FileNotFoundError(f"ABC binary not found: {task.abc_bin}")
        if not task.cirkit_bin.exists():
            raise FileNotFoundError(f"CirKit binary not found: {task.cirkit_bin}")
        rel_blif = task.row.get("blif")
        if not rel_blif:
            raise ValueError("manifest row has no BLIF path")
        blif = (Path(task.row["_manifest_abs_dir"]) / rel_blif).resolve()
        if not blif.exists():
            raise FileNotFoundError(f"BLIF file not found: {blif}")

        started = time.time()
        with tempfile.TemporaryDirectory(prefix="cirkit_aig_") as tmp_raw:
            tmp = Path(tmp_raw)
            aig = tmp / f"{task.row['name']}.aig"
            verilog = tmp / f"{task.row['name']}.cirkit.v"
            verify_out = tmp / f"{task.row['name']}.verify.blif"

            source_correct = verify_blif(blif, bf)
            if not source_correct:
                raise RuntimeError("exported source BLIF failed truth-table verification")

            abc_started = time.time()
            abc_command = f"read_blif {blif}; strash; write_aiger {aig}; print_stats"
            abc_proc = subprocess.run(
                [str(task.abc_bin), "-c", abc_command],
                text=True,
                capture_output=True,
                timeout=task.timeout,
                check=False,
            )
            abc_time = time.time() - abc_started
            abc_text = (abc_proc.stdout or "") + (abc_proc.stderr or "")
            if abc_proc.returncode != 0:
                raise RuntimeError(f"ABC BLIF-to-AIGER failed: {abc_text[-1200:]}")
            if not aig.exists():
                raise RuntimeError(f"ABC did not write AIGER: {abc_text[-1200:]}")

            cirkit_started = time.time()
            commands = [f"read_aiger --aig {aig}", *task.flow, "ps -a", "mccost -a", f"write_verilog -a {verilog}"]
            cirkit_proc = subprocess.run(
                [str(task.cirkit_bin), "-c", "; ".join(commands)],
                text=True,
                capture_output=True,
                timeout=task.timeout,
                check=False,
            )
            cirkit_time = time.time() - cirkit_started
            cirkit_text = (cirkit_proc.stdout or "") + (cirkit_proc.stderr or "")
            if cirkit_proc.returncode != 0:
                raise RuntimeError(f"CirKit failed with code {cirkit_proc.returncode}: {cirkit_text[-1600:]}")
            if not verilog.exists():
                raise RuntimeError(f"CirKit did not write Verilog: {cirkit_text[-1600:]}")
            stats = parse_cirkit_stats(cirkit_text)

            verify_started = time.time()
            verilog_correct = run_abc_verify_verilog(task.abc_bin, verilog, verify_out, bf, task.timeout)
            verify_time = time.time() - verify_started
            if not verilog_correct:
                raise RuntimeError("CirKit Verilog failed truth-table verification after ABC readback")

        cost = abc_xag_cost(stats["mc_size"], 0, 0, stats["mc_depth"], bf)
        elapsed = time.time() - started
        return {
            **base,
            "T": cost.T,
            "CNOT": cost.CNOT,
            "depth": cost.depth,
            "gates": cost.gates,
            "explicit_ancilla": cost.explicit_ancilla,
            "peak_ancilla": cost.peak_ancilla,
            "n_qubits": bf.n + 1 + cost.explicit_ancilla,
            "score": score_cost(cost),
            "correct": True,
            "source_blif_correct": source_correct,
            "verilog_correct": verilog_correct,
            "time_s": elapsed,
            "abc_time_s": abc_time,
            "cirkit_time_s": cirkit_time,
            "verify_time_s": verify_time,
            "abc_binary": display_path(task.abc_bin),
            "cirkit_binary": display_path(task.cirkit_bin),
            "skipped": "",
            "error": "",
            **stats,
        }
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
            "correct": "",
            "source_blif_correct": "",
            "verilog_correct": "",
            "time_s": "",
            "abc_time_s": "",
            "cirkit_time_s": "",
            "verify_time_s": "",
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
            "correct": "",
            "source_blif_correct": "",
            "verilog_correct": "",
            "time_s": "",
            "abc_time_s": "",
            "cirkit_time_s": "",
            "verify_time_s": "",
            "skipped": "",
            "error": repr(exc),
        }


def load_manifest_rows(inputs: list[str], min_n: int | None, max_n: int | None, limit: int | None) -> list[tuple[str, dict[str, str]]]:
    out: list[tuple[str, dict[str, str]]] = []
    for raw in inputs:
        label, path = parse_labeled_path(raw)
        path = resolve_path(path)
        for row in load_manifest(path):
            n = int(row["n"])
            if min_n is not None and n < min_n:
                continue
            if max_n is not None and n > max_n:
                continue
            out.append((label, row))
            if limit is not None and len(out) >= limit:
                return out
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    preferred = [
        "dataset",
        "index",
        "name",
        "preset_name",
        "n",
        "anf_terms",
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
        "correct",
        "source_blif_correct",
        "verilog_correct",
        "time_s",
        "abc_time_s",
        "cirkit_time_s",
        "verify_time_s",
        "aig_gates",
        "aig_level",
        "mc_size",
        "mc_depth",
        "cirkit_commit",
        "abc_binary",
        "cirkit_binary",
        "source_manifest",
        "skipped",
        "error",
    ]
    ordered = [key for key in preferred if key in fieldnames]
    ordered.extend(key for key in fieldnames if key not in ordered)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_internal(inputs: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for raw in inputs:
        label, path = parse_labeled_path(raw)
        path = resolve_path(path)
        for row in load_csv(path):
            if row.get("error") or row.get("skipped"):
                continue
            out: dict[str, object] = dict(row)
            out["dataset"] = label
            rows.append(out)
    return rows


def usable(row: dict[str, object]) -> bool:
    return not row.get("error") and not row.get("skipped") and str(row.get("correct")) == "True"


def by_dataset_name_method(rows: list[dict[str, object]]) -> dict[tuple[str, str], dict[str, dict[str, object]]]:
    out: dict[tuple[str, str], dict[str, dict[str, object]]] = {}
    for row in rows:
        dataset = str(row.get("dataset", ""))
        name = str(row.get("name", ""))
        method = str(row.get("method", ""))
        out.setdefault((dataset, name), {})[method] = row
    return out


def relative(new: float, base: float) -> float:
    return (new - base) / max(abs(base), 1.0)


def compare(
    joined: dict[tuple[str, str], dict[str, dict[str, object]]],
    target: str,
    baseline: str,
    metric: str,
) -> dict[str, object] | None:
    relatives: list[float] = []
    wins = losses = ties = 0
    by_n: dict[int, int] = {}
    for (_dataset, _name), methods in joined.items():
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
        try:
            n = int(methods[target].get("n", methods[baseline].get("n", -1)))
            by_n[n] = by_n.get(n, 0) + 1
        except Exception:
            pass
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
    external_rows = [row for row in raw_rows if usable(row)]
    joined = by_dataset_name_method(internal_rows + external_rows)
    out: list[dict[str, object]] = []
    for target in targets:
        for metric in ("score", "T", "CNOT", "depth", "peak_ancilla"):
            summary = compare(joined, target, "external_cirkit_aig_mc", metric)
            if summary:
                out.append(summary)
    return out


def write_analysis(path: Path, raw_rows: list[dict[str, object]], summaries: list[dict[str, object]], cirkit_root: Path, cirkit_bin: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = len(raw_rows)
    usable_count = sum(1 for row in raw_rows if usable(row))
    error_count = sum(1 for row in raw_rows if row.get("error"))
    timeout_count = sum(1 for row in raw_rows if "TimeoutExpired" in str(row.get("error", "")))
    correct_count = sum(1 for row in raw_rows if str(row.get("correct")) == "True")
    lines = [
        "# CirKit AIG Multiplicative-Complexity Probe",
        "",
        "Scope: ABC converts each exported BLIF into AIGER; official CirKit 3 shell reads the AIG, applies the selected AIG optimization flow, reports `mccost -a`, and writes Verilog that is read back by ABC for truth-table verification.",
        "",
        "This is a CirKit-shell AIG/MC probe, not legacy RevKit reversible synthesis, not the full ROS flow, and not hardware mapping.",
        "",
        f"- CirKit checkout: `{display_path(cirkit_root)}`",
        f"- CirKit commit: `{get_git_commit(cirkit_root)}`",
        f"- CirKit binary: `{display_path(cirkit_bin)}`",
        f"- rows attempted: {total}",
        f"- usable rows: {usable_count}",
        f"- correct rows: {correct_count}",
        f"- error rows: {error_count}",
        f"- timeout rows: {timeout_count}",
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
            "- The probe converts the previously built CirKit shell into a reproducible external baseline with row-level truth-table verification of the optimized Verilog readback.",
            "- The resource numbers are logic-layer AIG multiplicative-complexity proxies: `T=4*MC`, CNOT/depth/ancilla are derived through the same AND/XAG proxy used by other external logic-network probes.",
            "- The result should be claimed as evidence against an official CirKit AIG optimization and MC-count probe. It should not be described as a reproduced RevKit/ROS reversible-synthesis circuit or as a Clifford+T hardware-mapped result.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summaries: list[dict[str, object]], metric: str = "score") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [row for row in summaries if row["metric"] == metric]
    preferred = [
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
    order = {name: i for i, name in enumerate(preferred)}
    rows.sort(key=lambda row: order.get(str(row["target"]), 999))
    lines = [
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Target vs CirKit AIG/MC & Items & W/L/T & Mean $\\Delta$ \\\\",
        "\\midrule",
    ]
    for row in rows:
        label = str(row["target"]).replace("_", "\\_")
        mean_delta = f"{float(row['mean_relative']):+.2%}".replace("%", "\\%")
        lines.append(
            f"{label} & {row['items']} & {row['wins']}/{row['losses']}/{row['ties']} & "
            f"{mean_delta} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, args: argparse.Namespace, raw_rows: list[dict[str, object]], summaries: list[dict[str, object]], cirkit_commit: str) -> None:
    serializable_args = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in vars(args).items()
    }
    payload = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "script": Path(__file__).name,
        "argv": serializable_args,
        "cirkit_commit": cirkit_commit,
        "rows": len(raw_rows),
        "usable_rows": sum(1 for row in raw_rows if usable(row)),
        "summary_rows": len(summaries),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        action="append",
        default=None,
        help="labeled manifest path, e.g. traditional=benchmark_exports/.../manifest.json",
    )
    parser.add_argument(
        "--internal",
        action="append",
        default=None,
        help="labeled internal result CSV with matching dataset labels",
    )
    parser.add_argument("--min-n", type=int, default=None)
    parser.add_argument("--max-n", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--abc-bin", type=Path, default=DEFAULT_ABC_BIN)
    parser.add_argument("--cirkit-root", type=Path, default=DEFAULT_CIRKIT_ROOT)
    parser.add_argument("--cirkit-bin", type=Path, default=DEFAULT_CIRKIT_BIN)
    parser.add_argument("--flow", default=DEFAULT_FLOW)
    parser.add_argument("--targets", default=",".join(TARGET_METHODS))
    parser.add_argument("--out", type=Path, default=RESULTS / "raw_cirkit_aig_probe.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_cirkit_aig_probe.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_cirkit_aig_probe.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "cirkit_aig_probe.tex")
    parser.add_argument("--run-manifest", type=Path, default=RESULTS / "manifest_cirkit_aig_probe.json")
    args = parser.parse_args()
    if args.manifest is None:
        args.manifest = ["traditional=benchmark_exports/traditional_resource_external_seed42/manifest.json"]
    if args.internal is None:
        args.internal = ["traditional=results/raw_traditional_resource.csv"]

    args.abc_bin = resolve_path(args.abc_bin)
    args.cirkit_root = args.cirkit_root if args.cirkit_root.is_absolute() else ROOT / args.cirkit_root
    args.cirkit_bin = args.cirkit_bin if args.cirkit_bin.is_absolute() else ROOT / args.cirkit_bin
    args.out = resolve_path(args.out)
    args.summary = resolve_path(args.summary)
    args.analysis = resolve_path(args.analysis)
    args.latex_out = resolve_path(args.latex_out)
    args.run_manifest = resolve_path(args.run_manifest)
    flow = parse_flow(args.flow)
    cirkit_commit = get_git_commit(args.cirkit_root)

    manifest_rows = load_manifest_rows(args.manifest, args.min_n, args.max_n, args.limit)
    tasks = [
        CirKitTask(
            dataset=dataset,
            row=row,
            timeout=args.timeout,
            abc_bin=args.abc_bin,
            cirkit_bin=args.cirkit_bin,
            flow=flow,
            cirkit_commit=cirkit_commit,
        )
        for dataset, row in manifest_rows
    ]

    raw_rows: list[dict[str, object]] = []
    if args.workers <= 1:
        for i, task in enumerate(tasks, start=1):
            row = evaluate_task(task)
            raw_rows.append(row)
            print(f"[{i}/{len(tasks)}] {row['dataset']}:{row['name']} error={bool(row.get('error'))}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(evaluate_task, task) for task in tasks]
            for i, future in enumerate(as_completed(futures), start=1):
                row = future.result()
                raw_rows.append(row)
                print(f"[{i}/{len(tasks)}] {row['dataset']}:{row['name']} error={bool(row.get('error'))}", flush=True)

    raw_rows.sort(key=lambda row: (str(row.get("dataset", "")), int(row.get("n") or 0), str(row.get("name", ""))))
    write_csv(args.out, raw_rows)

    internal_rows = load_internal(args.internal)
    targets = parse_methods(args.targets)
    summaries = summarize(raw_rows, internal_rows, targets)
    write_csv(args.summary, summaries)
    write_analysis(args.analysis, raw_rows, summaries, args.cirkit_root, args.cirkit_bin)
    write_latex(args.latex_out, summaries)
    write_manifest(args.run_manifest, args, raw_rows, summaries, cirkit_commit)

    print(f"wrote {display_path(args.out)}")
    print(f"wrote {display_path(args.summary)}")
    print(f"wrote {display_path(args.analysis)}")
    print(f"wrote {display_path(args.latex_out)}")
    print(f"wrote {display_path(args.run_manifest)}")


if __name__ == "__main__":
    main()
