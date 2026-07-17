#!/usr/bin/env python3
"""Audit function-level diversity behind the benchmark comparisons.

The suite-composition audit records which benchmark families are present.  This
audit asks the next reviewer question: whether the compared functions are
structurally varied enough to make the comparisons meaningful.  It is a
descriptive, post-hoc audit over existing raw CSVs; it does not rerun synthesis
or expand large truth tables.
"""
from __future__ import annotations

# --- project root bootstrap (so this script runs standalone) ---
import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = _Path(__file__).resolve().parent.parent
if str(_PROJ_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJ_ROOT))


import csv
import json
import re
import statistics
import sys
from collections import Counter

from src.anf_utils import anf_monomials
from src.sshr_lib.bool_func import BooleanFunction


_THIS_FILE = Path(__file__).resolve()
THIS_DIR = _THIS_FILE.parent if (_THIS_FILE.parent / "results").exists() else _THIS_FILE.parent.parent
RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
AUTHOR_TEX = THIS_DIR / "paper_latex" / "resource_nmcts_submission_v1.tex"

SUMMARY = RESULTS / "summary_benchmark_function_diversity_audit.csv"
ANALYSIS = RESULTS / "analysis_benchmark_function_diversity_audit.md"
MANIFEST = RESULTS / "manifest_benchmark_function_diversity_audit.json"
TABLE = TABLES / "benchmark_function_diversity_audit.tex"

TRADITIONAL = RESULTS / "raw_traditional_resource.csv"
STG = RESULTS / "raw_stg_published_benchmark.csv"


def rel(path: Path) -> str:
    return str(path.relative_to(THIS_DIR))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def verified(row: dict[str, str]) -> bool:
    if row.get("status"):
        return row["status"] == "pass"
    checks = [field for field in ("truth_verified", "anf_verified", "circuit_anf_verified") if field in row]
    if checks:
        return all(truthy(row.get(field)) for field in checks) and not truthy(row.get("skipped"))
    if row.get("correct"):
        return truthy(row.get("correct")) and not truthy(row.get("skipped")) and not row.get("error")
    return False


def int_field(row: dict[str, str], *fields: str) -> int | None:
    for field in fields:
        value = str(row.get(field, "")).strip()
        if re.fullmatch(r"\d+", value):
            return int(value)
    return None


def n_scope(values: list[int]) -> str:
    if not values:
        return "not applicable"
    ordered = sorted(set(values))
    if len(ordered) == 1:
        return f"n={ordered[0]}"
    return f"n={ordered[0]}--{ordered[-1]}"


def minmax_text(values: list[int], label: str = "") -> str:
    if not values:
        return "not recorded"
    prefix = f"{label} " if label else ""
    return f"{prefix}{min(values)}--{max(values)}"


def family(name: str) -> str:
    if name.startswith("stg_"):
        return "published STG"
    if name.startswith("parity"):
        return "parity/affine"
    if name.startswith(("majority", "threshold")):
        return "threshold/majority"
    if name.startswith(("adder", "mul", "mux")):
        return "arithmetic/mux"
    if name.startswith("anf_"):
        return "generated random ANF"
    if name.startswith("terms_") or name.startswith("truth_bridge_"):
        return "generated term set"
    return "random truth-table"


def density_bucket(value: float) -> str:
    if value < 0.25:
        return "sparse"
    if value > 0.75:
        return "dense"
    return "balanced"


def compact_counts(counter: Counter[str], limit: int = 5) -> str:
    if not counter:
        return "not recorded"
    parts = [f"{key}={counter[key]}" for key in sorted(counter)]
    if len(parts) <= limit:
        return "; ".join(parts)
    head = parts[: limit - 1]
    head.append(f"other={sum(counter[key] for key in sorted(counter)[limit - 1:])}")
    return "; ".join(head)


def truth_table_signatures(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    by_key: dict[tuple[str, int, str], dict[str, str]] = {}
    for row in rows:
        if not row.get("truth_table_hex"):
            continue
        n = int_field(row, "n")
        if n is None:
            continue
        key = (row.get("name", ""), n, row["truth_table_hex"])
        by_key.setdefault(key, row)
    return list(by_key.values())


def exact_truth_summary(label: str, role: str, path: Path, route: str, boundary: str) -> dict[str, str]:
    raw_rows = read_csv(path)
    signatures = truth_table_signatures(path)
    ns: list[int] = []
    degrees: list[int] = []
    terms: list[int] = []
    densities: list[float] = []
    families: Counter[str] = Counter()
    density_counts: Counter[str] = Counter()

    for row in signatures:
        n = int(row["n"])
        truth = int(row["truth_table_hex"], 16)
        monomials = anf_monomials(BooleanFunction(n, truth))
        degree = max((mask.bit_count() for mask in monomials), default=0)
        term_count = len(monomials)
        density = truth.bit_count() / float(1 << n)
        ns.append(n)
        degrees.append(degree)
        terms.append(term_count)
        densities.append(density)
        families[family(row.get("name", ""))] += 1
        density_counts[density_bucket(density)] += 1

    verified_rows = sum(1 for row in raw_rows if verified(row))
    status = "pass" if path.exists() and signatures and verified_rows else "needs revision"
    return {
        "slice": label,
        "role": role,
        "abstraction": "stored truth table",
        "items": str(len(signatures)),
        "raw_rows": str(len(raw_rows)),
        "verified_rows": str(verified_rows),
        "n_scope": n_scope(ns),
        "family_or_profile_coverage": compact_counts(families),
        "density_coverage": compact_counts(density_counts),
        "degree_coverage": minmax_text(degrees, "degree"),
        "anf_or_term_count_range": minmax_text(terms, "ANF terms"),
        "verification_route": route,
        "boundary": boundary,
        "status": status,
        "source_files": rel(path) if path.exists() else rel(path),
    }


def collect(patterns: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in RESULTS.glob(pattern) if path.is_file())
    return sorted(set(files), key=rel)


def signature_key(row: dict[str, str], source: Path) -> str:
    name = row.get("name") or row.get("preset_name") or row.get("target_id") or row.get("index") or ""
    n = row.get("n") or row.get("source_n") or ""
    profile = row.get("profile") or row.get("dataset") or row.get("method") or ""
    return "|".join([source.name, name, n, profile])


def term_summary(
    label: str,
    role: str,
    patterns: tuple[str, ...],
    abstraction: str,
    route: str,
    boundary: str,
) -> dict[str, str]:
    files = collect(patterns)
    rows: list[tuple[Path, dict[str, str]]] = []
    for path in files:
        rows.extend((path, row) for row in read_csv(path))

    ns: list[int] = []
    term_counts: list[int] = []
    families: Counter[str] = Counter()
    signatures: set[str] = set()
    verified_rows = 0
    for path, row in rows:
        signatures.add(signature_key(row, path))
        n = int_field(row, "n", "source_n")
        if n is not None:
            ns.append(n)
        term_count = int_field(row, "term_count", "terms", "anf_terms")
        if term_count is not None:
            term_counts.append(term_count)
        label_value = row.get("profile") or row.get("dataset") or family(row.get("name", ""))
        if label_value:
            families[label_value] += 1
        if verified(row):
            verified_rows += 1

    status = "pass" if files and rows and verified_rows else "needs revision"
    return {
        "slice": label,
        "role": role,
        "abstraction": abstraction,
        "items": str(len(signatures)),
        "raw_rows": str(len(rows)),
        "verified_rows": str(verified_rows),
        "n_scope": n_scope(ns),
        "family_or_profile_coverage": compact_counts(families),
        "density_coverage": "not stored for symbolic rows",
        "degree_coverage": "not expanded for large-n rows",
        "anf_or_term_count_range": minmax_text(term_counts, "terms"),
        "verification_route": route,
        "boundary": boundary,
        "status": status,
        "source_files": "; ".join(rel(path) for path in files),
    }


def build_rows() -> list[dict[str, str]]:
    return [
        exact_truth_summary(
            "Matched n<=6 truth-table core",
            "primary same-task diversity check",
            TRADITIONAL,
            "complete truth-table correctness rows and exact ANF feature extraction",
            "The density distribution is intentionally reported; these rows are structurally varied but not a distributional sample of all Boolean functions.",
        ),
        exact_truth_summary(
            "Published STG optimum counterpoint",
            "tiny-function optimum boundary",
            STG,
            "stored public n=4/5 truth tables plus Resource-NMCTS correctness checks",
            "This slice validates a hard small-function counterpoint rather than a headline victory over precomputed optimum libraries.",
        ),
        term_summary(
            "External high-dimensional ANF/network probes",
            "external-tool structure stress",
            (
                "raw_highdim_resource.csv",
                "raw_highdim_scale_resource.csv",
                "raw_mega_highdim_resource.csv",
                "raw_ultra_highdim_resource.csv",
                "raw_external_highdim_resource.csv",
                "raw_external_highdim_scale_resource.csv",
                "raw_external_mega_highdim_resource.csv",
                "raw_external_ultra_highdim_resource.csv",
                "raw_mockturtle_xag_highdim_probe.csv",
                "raw_cirkit_aig_highdim_probe.csv",
            ),
            "symbolic ANF plus exported logic-network probes",
            "ANF, BDD/ABC, XAG, and AIG/MC correctness checks where available",
            "These rows stress external toolchains but remain logical-network proxies rather than reversible hardware mapping.",
        ),
        term_summary(
            "Large symbolic term-set stress",
            "large-n scalability diversity check",
            ("raw_screen_scale*_terms.csv",),
            "symbolic generated term sets",
            "symbolic ANF and emitted-circuit ANF checks",
            "This is large-dimensional search evidence, not exhaustive truth-table enumeration.",
        ),
        term_summary(
            "Complete truth-table bridge slices",
            "large-n semantic bridge",
            ("raw_truth_bridge*_terms.csv", "raw_schedule_truth_bridge*_terms.csv"),
            "generated term sets with complete truth-table construction",
            "complete truth-table construction plus plan and emitted-circuit ANF checks",
            "Bridge slices are deliberately narrow because truth tables grow exponentially.",
        ),
    ]


def latex_escape(text: str) -> str:
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
    text = text.replace("<=", r"$\leq$")
    text = text.replace(">=", r"$\geq$")
    return text


def latex_cell(text: str) -> str:
    escaped = latex_escape(text)
    replacements = {
        "Resource-NMCTS": r"\method{}",
        "ANF": r"\anf{}",
        "n=3--6": r"$n=3$--$6$",
        "n=4--5": r"$n=4$--$5$",
        "n=14--18": r"$n=14$--$18$",
        "n=20--64": r"$n=20$--$64$",
        "n=21--30": r"$n=21$--$30$",
    }
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    escaped = re.sub(r"n=(\d+)--(\d+)", r"$n=\1$--$\2$", escaped)
    return escaped


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Benchmark Function Diversity Audit",
        "",
        "This audit records structural diversity behind the paper's comparison targets.  It is descriptive and post-hoc over existing raw CSVs.",
        "",
        "## Status counts",
        "",
    ]
    for status in sorted(counts):
        lines.append(f"- {status}: {counts[status]}")
    lines.extend(
        [
            "",
            "| slice | role | abstraction | items | raw rows | verified rows | n scope | family/profile coverage | density coverage | degree coverage | term range | boundary | status |",
            "|---|---|---|---:|---:|---:|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {slice} | {role} | {abstraction} | {items} | {raw_rows} | {verified_rows} | {n_scope} | {family_or_profile_coverage} | {density_coverage} | {degree_coverage} | {anf_or_term_count_range} | {boundary} | {status} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The small truth-table core contains named affine, threshold/majority, arithmetic/mux, and random truth-table families, with exact ANF degree and term-count measurements.",
            "- Most small truth-table rows are balanced-density functions; that fact is recorded as a boundary rather than hidden as representativeness.",
            "- The large-n rows add symbolic and bridge-verified search stress, but they do not become exhaustive large-n Boolean-function coverage.",
            "",
            "## Source files",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- **{row['slice']}**: `{row['source_files']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedleft\arraybackslash}p{0.08\linewidth}>{\raggedright\arraybackslash}p{0.08\linewidth}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{0.22\linewidth}}",
        r"\toprule",
        r"Slice & Items & Scope & Diversity evidence & Boundary \\",
        r"\midrule",
    ]
    for row in rows:
        term_text = f"{row['family_or_profile_coverage']}; {row['degree_coverage']}; {row['anf_or_term_count_range']}"
        if row["density_coverage"] != "not stored for symbolic rows":
            term_text += f"; density {row['density_coverage']}"
        boundary = {
            "Matched n<=6 truth-table core": "structurally varied, not a distributional Boolean-function sample",
            "Published STG optimum counterpoint": "small optimum-library boundary",
            "External high-dimensional ANF/network probes": "logical-network proxy, not reversible hardware mapping",
            "Large symbolic term-set stress": "large-n symbolic search evidence, not exhaustive truth tables",
            "Complete truth-table bridge slices": "narrow bridge because truth tables grow exponentially",
        }.get(row["slice"], row["boundary"])
        lines.append(
            "{} & {}/{} & {} & {} & {} \\\\".format(
                latex_cell(row["slice"]),
                row["items"],
                row["raw_rows"],
                latex_cell(row["n_scope"]),
                latex_cell(term_text),
                latex_cell(boundary),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row["status"] for row in rows)
    author_text = read_text(AUTHOR_TEX)
    exact_core = next(row for row in rows if row["slice"] == "Matched n<=6 truth-table core")
    bridge = next(row for row in rows if row["slice"] == "Complete truth-table bridge slices")
    large = next(row for row in rows if row["slice"] == "Large symbolic term-set stress")
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "rows": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "needs_revision_count": counts.get("needs revision", 0),
        "exact_truth_table_core_items": int(exact_core["items"]),
        "exact_truth_table_core_families": exact_core["family_or_profile_coverage"],
        "bridge_n_scope": bridge["n_scope"],
        "large_symbolic_n_scope": large["n_scope"],
        "n_scopes": sorted({row["n_scope"] for row in rows}),
        "table": rel(TABLE),
        "table_anchor_present": "tab:benchmark-function-diversity-audit" in author_text,
        "source_files": sorted({source for row in rows for source in row["source_files"].split("; ") if source}),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(SUMMARY, rows)
    write_markdown(ANALYSIS, rows)
    write_latex(TABLE, rows)
    write_manifest(MANIFEST, rows)
    print(f"wrote {rel(SUMMARY)}")
    print(f"wrote {rel(ANALYSIS)}")
    print(f"wrote {rel(MANIFEST)}")
    print(f"wrote {rel(TABLE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
