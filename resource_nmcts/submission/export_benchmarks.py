#!/usr/bin/env python3
"""Export benchmark Boolean functions for external synthesis toolchains."""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJ_ROOT))


import argparse
import csv
import json
import re
from pathlib import Path
from typing import Iterable

from src.anf_utils import anf_monomials
from run_experiments import PRESETS, make_suite


THIS_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = THIS_DIR / "benchmark_exports"


def sanitize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "function"


def input_labels(n: int) -> list[str]:
    return [f"x{i}" for i in range(n)]


def bit_pattern(x: int, n: int) -> str:
    return "".join("1" if (x >> i) & 1 else "0" for i in range(n))


def truth_bits_lsb_first(bf) -> str:
    return "".join("1" if bf.evaluate(x) else "0" for x in range(1 << bf.n))


def write_pla(path: Path, name: str, bf) -> None:
    labels = input_labels(bf.n)
    lines = [
        f"# name {name}",
        f"# truth_table_hex {bf.truth_table:X}",
        f".i {bf.n}",
        ".o 1",
        ".ilb " + " ".join(labels),
        ".ob f",
        ".type fr",
    ]
    for x in range(1 << bf.n):
        if bf.evaluate(x):
            lines.append(f"{bit_pattern(x, bf.n)} 1")
    lines.append(".e")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blif(path: Path, name: str, bf) -> None:
    labels = input_labels(bf.n)
    lines = [
        f".model {name}",
        ".inputs " + " ".join(labels),
        ".outputs f",
        ".names " + " ".join(labels + ["f"]),
    ]
    for x in range(1 << bf.n):
        if bf.evaluate(x):
            lines.append(f"{bit_pattern(x, bf.n)} 1")
    lines.append(".end")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_truth(path: Path, name: str, bf) -> None:
    payload = {
        "name": name,
        "n": bf.n,
        "truth_table_hex": f"{bf.truth_table:X}",
        "bit_order": "LSB-first over integer assignments x0 + 2*x1 + ...",
        "truth_bits_lsb_first": truth_bits_lsb_first(bf),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def selected_formats(raw: str) -> set[str]:
    formats = {item.strip().lower() for item in raw.split(",") if item.strip()}
    valid = {"pla", "blif", "truth"}
    unknown = formats - valid
    if unknown:
        raise SystemExit(f"unknown export formats: {', '.join(sorted(unknown))}")
    return formats or valid


def export_suite(
    preset: str,
    seed: int,
    out_dir: Path,
    formats: Iterable[str],
    limit: int | None = None,
) -> dict:
    suite = make_suite(preset, seed)
    if limit is not None:
        suite = suite[: max(0, limit)]
    fmt = set(formats)
    out_dir.mkdir(parents=True, exist_ok=True)
    for subdir in fmt:
        (out_dir / subdir).mkdir(parents=True, exist_ok=True)

    rows = []
    seen_names: dict[str, int] = {}
    for index, (raw_name, bf) in enumerate(suite):
        base = sanitize_name(raw_name)
        count = seen_names.get(base, 0)
        seen_names[base] = count + 1
        name = base if count == 0 else f"{base}_{count}"
        terms = anf_monomials(bf)
        row = {
            "index": index,
            "name": name,
            "preset_name": raw_name,
            "n": bf.n,
            "truth_table_hex": f"{bf.truth_table:X}",
            "onset_size": len(bf.onset),
            "anf_terms": len(terms),
        }
        if "pla" in fmt:
            path = out_dir / "pla" / f"{name}.pla"
            write_pla(path, name, bf)
            row["pla"] = str(path.relative_to(out_dir))
        if "blif" in fmt:
            path = out_dir / "blif" / f"{name}.blif"
            write_blif(path, name, bf)
            row["blif"] = str(path.relative_to(out_dir))
        if "truth" in fmt:
            path = out_dir / "truth" / f"{name}.json"
            write_truth(path, name, bf)
            row["truth"] = str(path.relative_to(out_dir))
        rows.append(row)

    fieldnames = ["index", "name", "preset_name", "n", "truth_table_hex", "onset_size", "anf_terms", "pla", "blif", "truth"]
    with (out_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "preset": preset,
        "seed": seed,
        "functions": len(rows),
        "formats": sorted(fmt),
        "source_methods": PRESETS[preset]["methods"],
        "manifest": "manifest.csv",
    }
    (out_dir / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=sorted(PRESETS), default="large_resource_core")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--formats", default="pla,blif,truth", help="comma-separated subset: pla,blif,truth")
    parser.add_argument("--limit", type=int, default=None, help="export only the first N functions")
    args = parser.parse_args(argv)

    out_dir = args.out_dir or (DEFAULT_OUT / f"{args.preset}_seed{args.seed}")
    summary = export_suite(args.preset, args.seed, out_dir, selected_formats(args.formats), args.limit)
    print(f"wrote {out_dir}")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
