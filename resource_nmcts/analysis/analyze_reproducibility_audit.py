#!/usr/bin/env python3
"""Assemble a compute and artifact reproducibility audit for the paper.

The audit is intentionally descriptive.  It records the local compute envelope,
parallel-run provenance found in manifests, and the size of the result package.
It does not turn workstation wall times into a machine-independent performance
claim.
"""
from __future__ import annotations

import csv
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


THIS_DIR = Path(__file__).resolve().parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
FIGURES = THIS_DIR / "paper_latex" / "figures" / "submission_v36"


def run_text(args: list[str], timeout: int = 8) -> str:
    try:
        proc = subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return ""
    return proc.stdout.strip()


def sysctl_value(name: str) -> str:
    return run_text(["sysctl", "-n", name], timeout=3).splitlines()[0].strip()


def gib(bytes_text: str) -> float:
    try:
        return int(bytes_text) / (1024**3)
    except ValueError:
        return 0.0


def gpu_summary() -> str:
    text = run_text(["system_profiler", "SPDisplaysDataType"], timeout=12)
    chipset = ""
    cores = ""
    metal = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Chipset Model:"):
            chipset = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Total Number of Cores:"):
            cores = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Metal Support:"):
            metal = stripped.split(":", 1)[1].strip()
    parts = [part for part in [chipset, f"{cores} GPU cores" if cores else "", metal] if part]
    return ", ".join(parts) if parts else "GPU not detected"


def torch_summary() -> str:
    try:
        import torch  # type: ignore
    except Exception as exc:
        return f"PyTorch unavailable ({type(exc).__name__})"
    mps = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    cuda = bool(torch.cuda.is_available())
    return f"PyTorch {torch.__version__}; MPS={mps}; CUDA={cuda}"


def count_files(pattern: str, root: Path = THIS_DIR) -> int:
    return sum(1 for _ in root.glob(pattern))


def count_top_scripts() -> int:
    return sum(1 for _ in THIS_DIR.glob("run_*.py")) + sum(1 for _ in THIS_DIR.glob("train_*.py")) + sum(
        1 for _ in THIS_DIR.glob("analyze_*.py")
    )


def read_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def manifest_worker_stats() -> tuple[int, int, list[str]]:
    summaries: list[tuple[int, str, str]] = []
    for path in sorted(RESULTS.glob("manifest_*.json")):
        data = read_manifest(path)
        argv = data.get("argv", {}) if isinstance(data, dict) else {}
        workers = argv.get("workers", data.get("workers")) if isinstance(argv, dict) else data.get("workers")
        if workers in ("", None):
            continue
        try:
            workers_int = int(workers)
        except (TypeError, ValueError):
            continue
        rows = data.get(
            "usable_rows",
            data.get("verified_rows", data.get("sweep_rows", data.get("raw_rows", data.get("rows", "")))),
        )
        script = data.get("script") or path.name.removeprefix("manifest_").removesuffix(".json")
        summaries.append((workers_int, str(script), str(rows)))
    max_workers = max((item[0] for item in summaries), default=0)
    priority = [
        ("manifest_traditional_resource.json", "traditional resource"),
        ("manifest_revkit_cli_multiflow_traditional.json", "RevKit CLI"),
        ("manifest_ros_lut_proxy.json", "ROS-style LUT"),
        ("manifest_cirkit_aig_probe.json", "CirKit"),
        ("manifest_mockturtle_xag_probe.json", "mockturtle"),
    ]
    selected_text: list[str] = []
    for filename, label in priority:
        data = read_manifest(RESULTS / filename)
        argv = data.get("argv", {}) if isinstance(data, dict) else {}
        workers = argv.get("workers", data.get("workers")) if isinstance(argv, dict) else data.get("workers")
        rows = data.get(
            "usable_rows",
            data.get("verified_rows", data.get("sweep_rows", data.get("raw_rows", data.get("rows", "")))),
        )
        if workers not in ("", None):
            selected_text.append(f"{label} {int(workers)} workers/{rows} rows")
    return len(summaries), max_workers, selected_text


def external_commit_summary() -> str:
    names = {
        "manifest_mockturtle_xag_probe.json": ("mockturtle", "mockturtle_commit"),
        "manifest_cirkit_aig_probe.json": ("CirKit", "cirkit_commit"),
        "manifest_revkit_cli_multiflow_traditional.json": ("RevKit CLI", "revkit_commit"),
    }
    pieces: list[str] = []
    for filename, (label, key) in names.items():
        data = read_manifest(RESULTS / filename)
        value = str(data.get(key, ""))
        if value:
            pieces.append(f"{label} {value[:7]}")
    return "; ".join(pieces) if pieces else "No external commit hashes found"


def build_rows() -> list[dict[str, str]]:
    cpu = sysctl_value("machdep.cpu.brand_string") or platform.processor() or "unknown CPU"
    physical = sysctl_value("hw.physicalcpu") or "?"
    logical = sysctl_value("hw.logicalcpu") or "?"
    memory = gib(sysctl_value("hw.memsize"))
    worker_manifests, max_workers, selected_workers = manifest_worker_stats()
    figure_panels = count_files("*.pdf", FIGURES)
    figure_assets = count_files("*.pdf", FIGURES) + count_files("*.png", FIGURES) + count_files("*.svg", FIGURES)

    return [
        {
            "aspect": "Host compute envelope",
            "evidence": (
                f"{cpu}; {physical} physical/{logical} logical CPU cores; "
                f"{memory:.1f} GiB RAM; {gpu_summary()}; Python {sys.version.split()[0]}"
            ),
            "boundary": "Workstation context for reproducibility; not a hardware-mapping result.",
        },
        {
            "aspect": "Learning accelerator",
            "evidence": torch_summary(),
            "boundary": "GPU/MPS is available for neural training; synthesis resources remain logical-layer estimates.",
        },
        {
            "aspect": "Parallel-run provenance",
            "evidence": (
                f"{worker_manifests} manifests record worker counts; max workers={max_workers}; "
                + "; ".join(selected_workers)
            ),
            "boundary": "Wall times are machine-dependent and are not claimed as portable speedups.",
        },
        {
            "aspect": "Artifact coverage",
            "evidence": (
                f"{count_top_scripts()} top-level run/train/analyze scripts; "
                f"{count_files('raw_*.csv', RESULTS)} raw CSVs; "
                f"{count_files('summary_*.csv', RESULTS)} summaries; "
                f"{count_files('manifest_*.json', RESULTS)} manifests; "
                f"{count_files('*.tex', TABLES)} paper tables; "
                f"{figure_panels} figure panels ({figure_assets} PDF/PNG/SVG assets)"
            ),
            "boundary": "Counts describe the current artifact package, not independent datasets.",
        },
        {
            "aspect": "External-tool provenance",
            "evidence": external_commit_summary(),
            "boundary": "Toolchain rows are logic-level probes or exact-oracle reversible probes, not full hardware flows.",
        },
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["aspect", "evidence", "boundary"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Reproducibility and Compute Audit",
        "",
        "This audit records the local compute envelope, manifest-level parallelism, artifact counts, and external-tool provenance.",
        "",
        "| aspect | evidence | boundary |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['aspect']} | {row['evidence']} | {row['boundary']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("MPS=True", r"MPS=True")
    text = text.replace("CUDA=False", r"CUDA=False")
    return text


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.45\linewidth}>{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Aspect & Evidence & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join([tex_escape(row["aspect"]), tex_escape(row["evidence"]), tex_escape(row["boundary"])])
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "rows": len(rows),
        "outputs": {
            "summary": str(RESULTS / "summary_reproducibility_audit.csv"),
            "analysis": str(RESULTS / "analysis_reproducibility_audit.md"),
            "table": str(TABLES / "reproducibility_audit.tex"),
        },
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RESULTS / "summary_reproducibility_audit.csv", rows)
    write_markdown(RESULTS / "analysis_reproducibility_audit.md", rows)
    write_latex(TABLES / "reproducibility_audit.tex", rows)
    write_manifest(RESULTS / "manifest_reproducibility_audit.json", rows)
    print(f"wrote {len(rows)} reproducibility audit rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
