#!/usr/bin/env python3
"""Run an official mockturtle KLUT-to-XAG resynthesis probe.

This is a reproducible external-toolchain adapter, not the official ROS flow.
Each exported benchmark BLIF is first mapped by ABC into K<=4 LUTs, then read by
mockturtle's BLIF reader and resynthesized into an XAG using
``xag_npn_resynthesis``.  The resulting XAG AND/XOR/depth counts are translated
into this project's logic-level oracle resource proxy.
"""
from __future__ import annotations

import argparse
import csv
import json
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
DEFAULT_MOCKTURTLE_ROOT = ROOT / "tmp" / "mockturtle"
DEFAULT_TOOL_SRC = THIS_DIR / "tools" / "mockturtle_blif_xag_stats.cpp"
DEFAULT_TOOL_BIN = ROOT / "tmp" / "bin" / "mockturtle_blif_xag_stats"

TARGET_METHODS = [
    "and_resource_nmcts",
    "and_pareto_resource_nmcts",
    "and_fprm_polarity_archive",
    "and_direct_anf",
    "direct_anf",
    "and_esop_milp",
    "sshr_h",
]


@dataclass(frozen=True)
class MockturtleTask:
    dataset: str
    row: dict[str, str]
    k: int
    timeout: float
    abc_bin: Path
    tool_bin: Path
    mockturtle_commit: str


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


def get_mockturtle_commit(mockturtle_root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(mockturtle_root), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "unknown"


def build_tool(
    mockturtle_root: Path,
    tool_src: Path,
    tool_bin: Path,
    cxx: str,
    rebuild: bool,
) -> None:
    if not mockturtle_root.exists():
        raise FileNotFoundError(f"mockturtle checkout not found: {mockturtle_root}")
    if not tool_src.exists():
        raise FileNotFoundError(f"mockturtle stats source not found: {tool_src}")
    if (
        tool_bin.exists()
        and not rebuild
        and tool_bin.stat().st_mtime >= tool_src.stat().st_mtime
    ):
        return

    tool_bin.parent.mkdir(parents=True, exist_ok=True)
    include_dirs = [
        mockturtle_root / "include",
        mockturtle_root / "lib" / "kitty",
        mockturtle_root / "lib" / "lorina",
        mockturtle_root / "lib" / "fmt",
        mockturtle_root / "lib" / "parallel_hashmap",
        mockturtle_root / "lib" / "percy",
        mockturtle_root / "lib" / "rang",
        mockturtle_root / "lib" / "bill",
        mockturtle_root / "lib" / "json",
    ]
    cmd = [
        cxx,
        "-std=c++17",
        "-O2",
        "-DNDEBUG",
        "-DFMT_HEADER_ONLY",
        "-w",
    ]
    for include_dir in include_dirs:
        cmd.extend(["-I", str(include_dir)])
    cmd.extend(["-o", str(tool_bin), str(tool_src)])
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        combined = (proc.stdout or "") + (proc.stderr or "")
        raise RuntimeError(f"failed to build mockturtle stats tool: {combined[-4000:]}")


def parse_key_values(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = int(value.strip())
    return out


def score_cost(cost) -> float:
    return cost.score(DEFAULT_WEIGHTS)


def evaluate_task(task: MockturtleTask) -> dict[str, object]:
    bf = bool_from_row(task.row)
    base = {
        "dataset": task.dataset,
        "index": task.row.get("index", ""),
        "name": task.row["name"],
        "preset_name": task.row.get("preset_name", task.row["name"]),
        "n": bf.n,
        "anf_terms": task.row.get("anf_terms", ""),
        "method": "external_mockturtle_xag_k4",
        "selected_k": task.k,
        "source_manifest": task.row.get("_manifest_dir", ""),
        "abc_script": f"strash; if -K {task.k}",
        "mockturtle_commit": task.mockturtle_commit,
    }
    try:
        if not task.abc_bin.exists():
            raise FileNotFoundError(f"ABC binary not found: {task.abc_bin}")
        rel_blif = task.row.get("blif")
        if not rel_blif:
            raise ValueError("manifest row has no BLIF path")
        blif = (Path(task.row["_manifest_abs_dir"]) / rel_blif).resolve()
        if not blif.exists():
            raise FileNotFoundError(f"BLIF file not found: {blif}")

        started = time.time()
        with tempfile.TemporaryDirectory(prefix="mockturtle_xag_") as tmp:
            opt_blif = Path(tmp) / f"{task.row['name']}.abc_k{task.k}.blif"
            abc_started = time.time()
            abc_command = f"read_blif {blif}; strash; if -K {task.k}; write_blif {opt_blif}; print_stats"
            abc_proc = subprocess.run(
                [str(task.abc_bin), "-c", abc_command],
                text=True,
                capture_output=True,
                timeout=task.timeout,
                check=False,
            )
            abc_time = time.time() - abc_started
            combined = (abc_proc.stdout or "") + (abc_proc.stderr or "")
            if abc_proc.returncode != 0:
                raise RuntimeError(f"ABC failed with code {abc_proc.returncode}: {combined[-1000:]}")
            if not opt_blif.exists():
                raise RuntimeError(f"ABC did not write BLIF: {combined[-1000:]}")
            blif_correct = verify_blif(opt_blif, bf)
            if not blif_correct:
                raise RuntimeError("ABC mapped BLIF failed truth-table verification")

            mock_started = time.time()
            mock_proc = subprocess.run(
                [str(task.tool_bin), str(opt_blif)],
                text=True,
                capture_output=True,
                timeout=task.timeout,
                check=False,
            )
            mock_time = time.time() - mock_started
            mock_combined = (mock_proc.stdout or "") + (mock_proc.stderr or "")
            if mock_proc.returncode != 0:
                raise RuntimeError(f"mockturtle stats failed with code {mock_proc.returncode}: {mock_combined[-1000:]}")
            stats = parse_key_values(mock_proc.stdout or "")
            for key in ("xag_and", "xag_xor", "xag_depth"):
                if key not in stats:
                    raise RuntimeError(f"mockturtle output missing {key}: {mock_combined[-1000:]}")

        cost = abc_xag_cost(stats["xag_and"], stats["xag_xor"], 0, stats["xag_depth"], bf)
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
            "abc_blif_correct": True,
            "time_s": elapsed,
            "abc_time_s": abc_time,
            "mockturtle_time_s": mock_time,
            "error": "",
            "skipped": "",
            **stats,
            "abc_binary": display_path(task.abc_bin),
            "mockturtle_tool": display_path(task.tool_bin),
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
            "abc_blif_correct": "",
            "time_s": "",
            "abc_time_s": "",
            "mockturtle_time_s": "",
            "error": f"TimeoutExpired({exc.timeout})",
            "skipped": "",
        }
    except Exception as exc:  # pragma: no cover - row-level report
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
            "abc_blif_correct": "",
            "time_s": "",
            "abc_time_s": "",
            "mockturtle_time_s": "",
            "error": repr(exc),
            "skipped": "",
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
        "selected_k",
        "T",
        "CNOT",
        "depth",
        "gates",
        "explicit_ancilla",
        "peak_ancilla",
        "n_qubits",
        "score",
        "correct",
        "abc_blif_correct",
        "time_s",
        "abc_time_s",
        "mockturtle_time_s",
        "klut_gates",
        "klut_depth",
        "xag_gates",
        "xag_and",
        "xag_xor",
        "xag_depth",
        "xag_other",
        "mockturtle_commit",
        "abc_script",
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
            summary = compare(joined, target, "external_mockturtle_xag_k4", metric)
            if summary:
                out.append(summary)
    return out


def write_analysis(path: Path, raw_rows: list[dict[str, object]], summaries: list[dict[str, object]], mockturtle_root: Path, tool_bin: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = len(raw_rows)
    usable_count = sum(1 for row in raw_rows if usable(row))
    error_count = sum(1 for row in raw_rows if row.get("error"))
    timeout_count = sum(1 for row in raw_rows if "TimeoutExpired" in str(row.get("error", "")))
    correct_count = sum(1 for row in raw_rows if str(row.get("correct")) == "True")
    lines = [
        "# Mockturtle XAG Probe Analysis",
        "",
        "Scope: ABC maps each exported BLIF with `strash; if -K 4`; official mockturtle then reads the mapped BLIF as a KLUT network and applies `xag_npn_resynthesis` to produce XAG counts.",
        "",
        "This is a mockturtle adapter/probe, not the official ROS flow and not hardware mapping.",
        "",
        f"- mockturtle checkout: `{display_path(mockturtle_root)}`",
        f"- mockturtle commit: `{get_mockturtle_commit(mockturtle_root)}`",
        f"- stats tool: `{display_path(tool_bin)}`",
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
            "- The probe removes the previous `mockturtle is reachable but not adapted` gap: the local checkout now builds a small official-header C++ adapter and runs on exported benchmark BLIFs.",
            "- The resource numbers are still logic-level proxy costs derived from XAG AND/XOR/depth counts; they are not a Clifford+T emission, not a reversible garbage-management flow, and not a routed hardware result.",
            "- If Resource-NMCTS wins under this baseline, the claim should be written as evidence against an official mockturtle KLUT-to-XAG resynthesis probe, not as a full ROS reproduction.",
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
        "Target vs mockturtle XAG K4 & Items & W/L/T & Mean $\\Delta$ \\\\",
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


def write_manifest(path: Path, args: argparse.Namespace, raw_rows: list[dict[str, object]], summaries: list[dict[str, object]], mockturtle_commit: str) -> None:
    serializable_args = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in vars(args).items()
    }
    payload = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "script": Path(__file__).name,
        "argv": serializable_args,
        "mockturtle_commit": mockturtle_commit,
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
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--abc-bin", type=Path, default=DEFAULT_ABC_BIN)
    parser.add_argument("--mockturtle-root", type=Path, default=DEFAULT_MOCKTURTLE_ROOT)
    parser.add_argument("--tool-src", type=Path, default=DEFAULT_TOOL_SRC)
    parser.add_argument("--tool-bin", type=Path, default=DEFAULT_TOOL_BIN)
    parser.add_argument("--cxx", default="clang++")
    parser.add_argument("--rebuild-tool", action="store_true")
    parser.add_argument("--targets", default=",".join(TARGET_METHODS))
    parser.add_argument("--out", type=Path, default=RESULTS / "raw_mockturtle_xag_probe.csv")
    parser.add_argument("--summary", type=Path, default=RESULTS / "summary_mockturtle_xag_probe.csv")
    parser.add_argument("--analysis", type=Path, default=RESULTS / "analysis_mockturtle_xag_probe.md")
    parser.add_argument("--latex-out", type=Path, default=TABLES / "mockturtle_xag_probe.tex")
    parser.add_argument("--run-manifest", type=Path, default=RESULTS / "manifest_mockturtle_xag_probe.json")
    args = parser.parse_args()
    if args.manifest is None:
        args.manifest = ["traditional=benchmark_exports/traditional_resource_external_seed42/manifest.json"]
    if args.internal is None:
        args.internal = ["traditional=results/raw_traditional_resource.csv"]

    args.abc_bin = resolve_path(args.abc_bin)
    args.mockturtle_root = args.mockturtle_root if args.mockturtle_root.is_absolute() else ROOT / args.mockturtle_root
    args.tool_src = resolve_path(args.tool_src)
    args.tool_bin = args.tool_bin if args.tool_bin.is_absolute() else ROOT / args.tool_bin
    args.out = resolve_path(args.out)
    args.summary = resolve_path(args.summary)
    args.analysis = resolve_path(args.analysis)
    args.latex_out = resolve_path(args.latex_out)
    args.run_manifest = resolve_path(args.run_manifest)

    build_tool(args.mockturtle_root, args.tool_src, args.tool_bin, args.cxx, args.rebuild_tool)
    mockturtle_commit = get_mockturtle_commit(args.mockturtle_root)

    manifest_rows = load_manifest_rows(args.manifest, args.min_n, args.max_n, args.limit)
    tasks = [
        MockturtleTask(
            dataset=dataset,
            row=row,
            k=args.k,
            timeout=args.timeout,
            abc_bin=args.abc_bin,
            tool_bin=args.tool_bin,
            mockturtle_commit=mockturtle_commit,
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
    write_analysis(args.analysis, raw_rows, summaries, args.mockturtle_root, args.tool_bin)
    write_latex(args.latex_out, summaries)
    write_manifest(args.run_manifest, args, raw_rows, summaries, mockturtle_commit)

    print(f"wrote {display_path(args.out)}")
    print(f"wrote {display_path(args.summary)}")
    print(f"wrote {display_path(args.analysis)}")
    print(f"wrote {display_path(args.latex_out)}")
    print(f"wrote {display_path(args.run_manifest)}")


if __name__ == "__main__":
    main()
