#!/usr/bin/env python3
"""Run external/cross-tool Boolean-oracle baselines on exported benchmarks.

This script intentionally consumes the files produced by ``export_benchmarks.py``
instead of calling the in-harness experiment preset directly.  That keeps the
baseline path close to future XAG/ROS/mockturtle integrations: every backend
sees the same exported truth table manifest.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
SSHR_DIR = ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))

from bool_func import BooleanFunction, QuantumCircuit, mct_cost_rp  # noqa: E402
from sshr_h import sshr_h  # noqa: E402

try:
    from sshr_i import sshr_i  # noqa: E402
except Exception:  # pragma: no cover - reported per row when used
    sshr_i = None


DEFAULT_RESULTS = THIS_DIR / "results"
DEFAULT_WEIGHTS = {"t": 1.0, "cnot": 0.04, "depth": 0.015, "gates": 0.01, "ancilla": 2.0}


@dataclass(frozen=True)
class Cost:
    T: int = 0
    CNOT: int = 0
    gates: int = 0
    depth: int = 0
    explicit_ancilla: int = 0
    peak_ancilla: int = 0

    def score(self, weights: dict[str, float]) -> float:
        return (
            weights["t"] * self.T
            + weights["cnot"] * self.CNOT
            + weights["depth"] * self.depth
            + weights["gates"] * self.gates
            + weights["ancilla"] * self.peak_ancilla
        )


def anf_term_count(bf: BooleanFunction) -> int:
    coeff = [(bf.truth_table >> i) & 1 for i in range(1 << bf.n)]
    for bit in range(bf.n):
        step = 1 << bit
        for mask in range(1 << bf.n):
            if mask & step:
                coeff[mask] ^= coeff[mask ^ step]
    return sum(coeff)


def circuit_cost(circ: QuantumCircuit, n_inputs: int) -> Cost:
    t_count = 0
    cnot_count = 0
    depth = 0
    helper_peak = 0
    for gate in circ.gates:
        if gate.type == "X":
            depth += 1
        elif gate.type == "CNOT":
            cnot_count += 1
            depth += 1
        elif gate.type == "MCT":
            cost = mct_cost_rp(len(gate.controls))
            t_count += int(cost["T"])
            cnot_count += int(cost["CNOT"])
            depth += max(1, int(cost["CNOT"]))
            helper_peak = max(helper_peak, int(cost.get("ancilla", 0)))
    explicit = max(0, circ.n_qubits - (n_inputs + 1))
    return Cost(
        T=t_count,
        CNOT=cnot_count,
        gates=len(circ.gates),
        depth=depth,
        explicit_ancilla=explicit,
        peak_ancilla=explicit + helper_peak,
    )


def verify_oracle(circ: QuantumCircuit, bf: BooleanFunction) -> bool:
    if circ.n_qubits < bf.n + 1:
        return False
    out = bf.n
    for x in range(1 << bf.n):
        prefix = [(x >> i) & 1 for i in range(bf.n)]
        expected = bf.evaluate(x)
        for y in (0, 1):
            bits = prefix + [y] + [0] * max(0, circ.n_qubits - (bf.n + 1))
            got = circ.simulate(bits)[out]
            if got != (y ^ expected):
                return False
    return True


def resolve_manifest(path: Path) -> Path:
    if path.name.endswith(".json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifest = payload.get("manifest")
        if not manifest:
            raise SystemExit(f"manifest JSON has no manifest field: {path}")
        return (path.parent / manifest).resolve()
    return path.resolve()


def load_manifest(path: Path) -> list[dict]:
    manifest = resolve_manifest(path)
    with manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["_manifest_dir"] = display_path(manifest.parent)
    return rows


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(THIS_DIR))
    except ValueError:
        return str(path)


def parse_methods(raw: str) -> list[str]:
    methods = [item.strip() for item in raw.split(",") if item.strip()]
    valid = {"external_sshr_h", "external_sshr_i_cnot", "external_sshr_i_t"}
    unknown = sorted(set(methods) - valid)
    if unknown:
        raise SystemExit(f"unknown external methods: {', '.join(unknown)}")
    return methods or sorted(valid)


def bool_from_row(row: dict) -> BooleanFunction:
    return BooleanFunction(int(row["n"]), int(str(row["truth_table_hex"]), 16))


def synthesize_external(method: str, bf: BooleanFunction, timeout: float) -> QuantumCircuit:
    if method == "external_sshr_h":
        return sshr_h(bf)
    if method == "external_sshr_i_cnot":
        if sshr_i is None:
            raise RuntimeError("sshr_i backend could not be imported")
        return sshr_i(bf, objective="cnot", timeout=timeout, try_complement=True)
    if method == "external_sshr_i_t":
        if sshr_i is None:
            raise RuntimeError("sshr_i backend could not be imported")
        return sshr_i(bf, objective="t", timeout=timeout, try_complement=True)
    raise ValueError(method)


def run_one(task: tuple[dict, str, float, int, dict[str, float]]) -> dict:
    row, method, timeout, max_ilp_n, weights = task
    bf = bool_from_row(row)
    base = {
        "index": row.get("index", ""),
        "name": row["name"],
        "preset_name": row.get("preset_name", row["name"]),
        "n": bf.n,
        "truth_table_hex": f"{bf.truth_table:X}",
        "onset_size": len(bf.onset),
        "anf_terms": anf_term_count(bf),
        "method": method,
        "source_manifest": row.get("_manifest_dir", ""),
    }
    if method.startswith("external_sshr_i") and bf.n > max_ilp_n:
        return {**base, "skipped": f"SSHR-I capped at n<={max_ilp_n}", "error": ""}
    try:
        start = time.time()
        circ = synthesize_external(method, bf, timeout)
        elapsed = time.time() - start
        cost = circuit_cost(circ, bf.n)
        return {
            **base,
            **asdict(cost),
            "score": cost.score(weights),
            "time_s": elapsed,
            "correct": verify_oracle(circ, bf),
            "gates": len(circ.gates),
            "n_qubits": circ.n_qubits,
            "skipped": "",
            "error": "",
        }
    except Exception as exc:
        return {**base, "correct": False, "skipped": "", "error": repr(exc)}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        if row.get("error") or row.get("skipped"):
            continue
        groups.setdefault((str(row["method"]), int(row["n"])), []).append(row)
    out = []
    for (method, n), items in sorted(groups.items()):
        def vals(key: str) -> list[float]:
            return [float(row[key]) for row in items if row.get(key) not in {None, ""}]

        out.append(
            {
                "method": method,
                "n": n,
                "functions": len(items),
                "correct": sum(1 for row in items if str(row.get("correct")) == "True"),
                "total_T": int(sum(vals("T"))),
                "total_CNOT": int(sum(vals("CNOT"))),
                "mean_score": statistics.mean(vals("score")) if vals("score") else float("nan"),
                "mean_depth": statistics.mean(vals("depth")) if vals("depth") else float("nan"),
                "mean_peak_ancilla": statistics.mean(vals("peak_ancilla")) if vals("peak_ancilla") else float("nan"),
                "mean_time_s": statistics.mean(vals("time_s")) if vals("time_s") else float("nan"),
            }
        )
    return out


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True, help="manifest.csv or manifest.json from export_benchmarks.py")
    parser.add_argument("--methods", default="external_sshr_h,external_sshr_i_cnot,external_sshr_i_t")
    parser.add_argument("--out", type=Path, default=DEFAULT_RESULTS / "raw_external_baselines.csv")
    parser.add_argument("--summary", type=Path, default=DEFAULT_RESULTS / "summary_external_baselines.csv")
    parser.add_argument("--run-manifest", type=Path, default=DEFAULT_RESULTS / "manifest_external_baselines.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-n", type=int, default=None)
    parser.add_argument("--max-ilp-n", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30.0, help="per SSHR-I call time limit")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    weights = dict(DEFAULT_WEIGHTS)
    manifest_rows = load_manifest(args.manifest)
    if args.max_n is not None:
        manifest_rows = [row for row in manifest_rows if int(row["n"]) <= args.max_n]
    if args.limit is not None:
        manifest_rows = manifest_rows[: max(0, args.limit)]
    methods = parse_methods(args.methods)
    tasks = [(row, method, args.timeout, args.max_ilp_n, weights) for row in manifest_rows for method in methods]

    rows: list[dict] = []
    if args.resume and args.out.exists():
        with args.out.open(newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
        done = {(row.get("name"), row.get("method")) for row in rows}
        tasks = [task for task in tasks if (task[0]["name"], task[1]) not in done]
        print(f"resuming from {len(rows)} rows; remaining {len(tasks)}", flush=True)

    start = time.time()
    if args.workers <= 1:
        for i, task in enumerate(tasks, 1):
            rows.append(run_one(task))
            if i % 20 == 0:
                write_csv(args.out, rows)
                print(f"{i}/{len(tasks)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_one, task) for task in tasks]
            for i, future in enumerate(as_completed(futures), 1):
                rows.append(future.result())
                if i % 20 == 0:
                    write_csv(args.out, rows)
                    print(f"{i}/{len(tasks)}", flush=True)

    write_csv(args.out, rows)
    summary = summarize(rows)
    write_csv(args.summary, summary)
    args.run_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.run_manifest.write_text(
        json.dumps(
            {
                "source_manifest": display_path(resolve_manifest(args.manifest)),
                "methods": methods,
                "functions": len(manifest_rows),
                "rows": len(rows),
                "new_tasks": len(tasks),
                "max_n": args.max_n,
                "max_ilp_n": args.max_ilp_n,
                "timeout": args.timeout,
                "workers": args.workers,
                "elapsed_s": time.time() - start,
                "raw": str(args.out),
                "summary": str(args.summary),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out}")
    print(f"wrote {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
