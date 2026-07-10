#!/usr/bin/env python3
"""Source-derived Clifford+T rotation-sequence smoke audit.

The phase/Rz branch is primarily a logical phase-parity cost model.  This
audit adds a deliberately bounded sanity check: it extracts representative
non-Clifford Rz angles from the already verified affine phase spectra, emits
short Clifford+T gate strings with an internal matrix beam search, and verifies
the global-phase-invariant single-qubit approximation error.

This is not Ross--Selinger gridsynth, not an optimal T-count claim, not a
replacement for high-precision approximate synthesis, and not hardware mapping.
It only demonstrates that the symbolic Rz targets used by the phase branch can
be connected to concrete Clifford+T sequences under a coarse smoke tolerance.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence

import numpy as np


THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
SSHR_DIR = ROOT / "sshr"
if str(SSHR_DIR) not in sys.path:
    sys.path.insert(0, str(SSHR_DIR))
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

try:
    from affine_search import transform_function
    from anf_utils import anf_monomials, shifted_function
    from src.sshr_lib.bool_func import BooleanFunction
    from run_phase_parity_affine_search import translate_affine_shifted_angles
    from run_phase_parity_baseline import is_clifford_angle, is_t_like_angle, normalize_angle_pi

    PHASE_RECONSTRUCTION_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - exercised by extracted payload smoke.
    transform_function = None
    anf_monomials = None
    shifted_function = None
    BooleanFunction = None
    translate_affine_shifted_angles = None
    PHASE_RECONSTRUCTION_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


RESULTS = THIS_DIR / "results"
TABLES = THIS_DIR / "paper_latex" / "tables"
RAW_OUT = RESULTS / "raw_phase_rotation_sequence_smoke_audit.csv"
SUMMARY_OUT = RESULTS / "summary_phase_rotation_sequence_smoke_audit.csv"
ANALYSIS_OUT = RESULTS / "analysis_phase_rotation_sequence_smoke_audit.md"
MANIFEST_OUT = RESULTS / "manifest_phase_rotation_sequence_smoke_audit.json"
TABLE_OUT = TABLES / "phase_rotation_sequence_smoke_audit.tex"

PHASE_SOURCES = (
    RESULTS / "raw_phase_parity_affine.csv",
    RESULTS / "raw_phase_parity_affine_wide128.csv",
    RESULTS / "raw_phase_affine_policy_rank_diverse.csv",
)

TARGETS = (
    ("freq01-den8-15", Fraction(15, 8)),
    ("freq02-den8-1", Fraction(1, 8)),
    ("freq03-den32-57", Fraction(57, 32)),
    ("freq04-den32-61", Fraction(61, 32)),
    ("freq05-den32-19", Fraction(19, 32)),
    ("freq06-den32-59", Fraction(59, 32)),
    ("freq07-den32-3", Fraction(3, 32)),
    ("freq08-den32-1", Fraction(1, 32)),
    ("freq09-den16-31", Fraction(31, 16)),
    ("freq10-den32-63", Fraction(63, 32)),
    ("freq11-den32-13", Fraction(13, 32)),
    ("freq12-den32-17", Fraction(17, 32)),
    ("freq13-den16-1", Fraction(1, 16)),
    ("freq14-den32-15", Fraction(15, 32)),
    ("freq15-den8-3", Fraction(3, 8)),
    ("freq16-den16-3", Fraction(3, 16)),
    ("freq17-den16-29", Fraction(29, 16)),
    ("freq18-den32-11", Fraction(11, 32)),
    ("freq19-den32-21", Fraction(21, 32)),
    ("freq20-den8-13", Fraction(13, 8)),
)

SMOKE_EPSILON = 0.125
TIGHT_EPSILON = 0.05
BEAM_WIDTH = 2500
MAX_SEQUENCE_LENGTH = 24
ROUND_DIGITS = 9
FIELDS = [
    "target_id",
    "angle_pi",
    "denominator",
    "source_count",
    "source_file",
    "source_name",
    "source_method",
    "source_split",
    "source_n",
    "source_parity_mask_hex",
    "backend",
    "beam_width",
    "max_sequence_length",
    "sequence",
    "sequence_length",
    "t_count",
    "achieved_error",
    "smoke_epsilon",
    "smoke_pass",
    "tight_epsilon",
    "tight_pass",
    "status",
]

SQRT2 = math.sqrt(2.0)
GATE_MATRICES: dict[str, np.ndarray] = {
    "H": np.array([[1, 1], [1, -1]], dtype=complex) / SQRT2,
    "T": np.diag([1.0 + 0.0j, np.exp(1j * math.pi / 4.0)]),
    "Td": np.diag([1.0 + 0.0j, np.exp(-1j * math.pi / 4.0)]),
    "S": np.diag([1.0 + 0.0j, 1.0j]),
    "Sd": np.diag([1.0 + 0.0j, -1.0j]),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Z": np.diag([1.0 + 0.0j, -1.0 + 0.0j]),
}
INVERSE_PAIRS = {
    ("H", "H"),
    ("T", "Td"),
    ("Td", "T"),
    ("S", "Sd"),
    ("Sd", "S"),
    ("X", "X"),
    ("Z", "Z"),
}


@dataclass(frozen=True)
class AngleExample:
    source_file: str
    name: str
    method: str
    split: str
    n: int
    parity_mask: int


@dataclass(frozen=True)
class SearchNode:
    error: float
    sequence: tuple[str, ...]
    unitary: np.ndarray
    t_count: int


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_transform_rows(value: str) -> tuple[int, ...]:
    return tuple(int(item, 16) for item in value.split(";") if item)


def usable_phase_row(path: Path, row: dict[str, str]) -> bool:
    if row.get("error") or row.get("skipped"):
        return False
    if not row.get("truth_table_hex") or not row.get("transform_rows_hex") or not row.get("polarity"):
        return False
    if "tperrz30" not in row.get("method", ""):
        return False
    if path.name == "raw_phase_affine_policy_rank_diverse.csv" and row.get("split") != "test_n6":
        return False
    verified = row.get("verified_up_to_global_phase", "").strip().lower()
    return verified not in {"false", "0"}


def reconstruct_angles(row: dict[str, str]) -> dict[int, Fraction]:
    if not all((transform_function, anf_monomials, shifted_function, BooleanFunction, translate_affine_shifted_angles)):
        raise RuntimeError(f"phase reconstruction imports unavailable: {PHASE_RECONSTRUCTION_IMPORT_ERROR}")
    n = int(row["n"])
    truth = int(row["truth_table_hex"], 16)
    rows = parse_transform_rows(row["transform_rows_hex"])
    polarity = int(row["polarity"])
    transformed = transform_function(BooleanFunction(n, truth), rows)
    shifted = shifted_function(transformed, polarity)
    terms = anf_monomials(shifted)
    _, _, angles = translate_affine_shifted_angles(terms, rows, polarity)
    return angles


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass"}


def normalize_existing_row(row: dict[str, str]) -> dict[str, object]:
    angle = Fraction(row["angle_pi"])
    raw_sequence = row.get("sequence", "I").strip()
    sequence = tuple(gate for gate in raw_sequence.split() if gate and gate != "I")
    verified_error = global_phase_error(sequence_unitary(sequence), target_unitary(angle))
    smoke_epsilon = float(row.get("smoke_epsilon") or SMOKE_EPSILON)
    tight_epsilon = float(row.get("tight_epsilon") or TIGHT_EPSILON)
    smoke_pass = verified_error <= smoke_epsilon
    tight_pass = verified_error <= tight_epsilon
    out: dict[str, object] = {field: row.get(field, "") for field in FIELDS}
    out.update(
        {
            "denominator": int(row.get("denominator") or angle.denominator),
            "source_count": int(row.get("source_count") or 0),
            "source_n": int(row.get("source_n") or 0) if row.get("source_n") else "",
            "beam_width": int(row.get("beam_width") or BEAM_WIDTH),
            "max_sequence_length": int(row.get("max_sequence_length") or MAX_SEQUENCE_LENGTH),
            "sequence": raw_sequence or "I",
            "sequence_length": len(sequence),
            "t_count": sum(1 for gate in sequence if gate in {"T", "Td"}),
            "achieved_error": verified_error,
            "smoke_epsilon": smoke_epsilon,
            "smoke_pass": smoke_pass,
            "tight_epsilon": tight_epsilon,
            "tight_pass": tight_pass,
            "status": "pass" if smoke_pass and int(row.get("source_count") or 0) > 0 else "needs revision",
        }
    )
    return out


def fallback_rows_from_packaged_raw() -> list[dict[str, object]]:
    if not RAW_OUT.exists():
        return [
            {
                "target_id": "fallback-missing-raw",
                "angle_pi": "0",
                "denominator": 1,
                "source_count": 0,
                "source_file": "",
                "source_name": "",
                "source_method": "",
                "source_split": "",
                "source_n": "",
                "source_parity_mask_hex": "",
                "backend": "packaged_raw_sequence_verification",
                "beam_width": BEAM_WIDTH,
                "max_sequence_length": MAX_SEQUENCE_LENGTH,
                "sequence": "I",
                "sequence_length": 0,
                "t_count": 0,
                "achieved_error": 0.0,
                "smoke_epsilon": SMOKE_EPSILON,
                "smoke_pass": False,
                "tight_epsilon": TIGHT_EPSILON,
                "tight_pass": False,
                "status": "needs revision",
            }
        ]
    rows = [normalize_existing_row(row) for row in read_csv(RAW_OUT)]
    return rows


def collect_angle_support() -> tuple[Counter[Fraction], dict[Fraction, AngleExample]]:
    counts: Counter[Fraction] = Counter()
    examples: dict[Fraction, AngleExample] = {}
    for path in PHASE_SOURCES:
        for row in read_csv(path):
            if not usable_phase_row(path, row):
                continue
            for mask, raw_angle in reconstruct_angles(row).items():
                angle = normalize_angle_pi(raw_angle)
                if is_clifford_angle(angle) or is_t_like_angle(angle):
                    continue
                counts[angle] += 1
                examples.setdefault(
                    angle,
                    AngleExample(
                        source_file=path.name,
                        name=row["name"],
                        method=row.get("method", ""),
                        split=row.get("split", "traditional"),
                        n=int(row["n"]),
                        parity_mask=int(mask),
                    ),
                )
    return counts, examples


def target_unitary(angle_pi: Fraction) -> np.ndarray:
    theta = math.pi * float(angle_pi)
    return np.diag([np.exp(-0.5j * theta), np.exp(0.5j * theta)])


def sequence_unitary(sequence: Sequence[str]) -> np.ndarray:
    unitary = np.eye(2, dtype=complex)
    for gate in sequence:
        unitary = GATE_MATRICES[gate] @ unitary
    return unitary


def global_phase_error(candidate: np.ndarray, target: np.ndarray) -> float:
    overlap = abs(np.trace(candidate.conj().T @ target)) / 2.0
    bounded = min(1.0, max(0.0, float(overlap)))
    return math.sqrt(max(0.0, 1.0 - bounded))


def matrix_key(unitary: np.ndarray) -> tuple[float, ...]:
    rounded = np.round(unitary.real, ROUND_DIGITS).ravel().tolist() + np.round(unitary.imag, ROUND_DIGITS).ravel().tolist()
    return tuple(float(item) for item in rounded)


def beam_synthesize(angle_pi: Fraction) -> SearchNode:
    target = target_unitary(angle_pi)
    identity = np.eye(2, dtype=complex)
    beam = [SearchNode(global_phase_error(identity, target), tuple(), identity, 0)]
    best = beam[0]

    for _ in range(MAX_SEQUENCE_LENGTH):
        candidates: list[SearchNode] = []
        seen: set[tuple[float, ...]] = set()
        for node in beam:
            last = node.sequence[-1] if node.sequence else None
            for gate, gate_matrix in GATE_MATRICES.items():
                if last is not None and (last, gate) in INVERSE_PAIRS:
                    continue
                unitary = gate_matrix @ node.unitary
                key = matrix_key(unitary)
                if key in seen:
                    continue
                seen.add(key)
                sequence = node.sequence + (gate,)
                t_count = node.t_count + (1 if gate in {"T", "Td"} else 0)
                candidates.append(SearchNode(global_phase_error(unitary, target), sequence, unitary, t_count))
        candidates.sort(key=lambda item: (item.error, item.t_count, len(item.sequence), " ".join(item.sequence)))
        beam = candidates[:BEAM_WIDTH]
        if beam and beam[0].error < best.error:
            best = beam[0]
    return best


def build_rows() -> list[dict[str, object]]:
    if PHASE_RECONSTRUCTION_IMPORT_ERROR:
        return fallback_rows_from_packaged_raw()

    counts, examples = collect_angle_support()
    rows: list[dict[str, object]] = []
    for target_id, angle in TARGETS:
        example = examples.get(angle)
        if example is None:
            rows.append(
                {
                    "target_id": target_id,
                    "angle_pi": str(angle),
                    "denominator": angle.denominator,
                    "source_count": 0,
                    "source_file": "",
                    "source_name": "",
                    "source_method": "",
                    "source_split": "",
                    "source_n": "",
                    "source_parity_mask_hex": "",
                    "backend": "internal_matrix_beam",
                    "beam_width": BEAM_WIDTH,
                    "max_sequence_length": MAX_SEQUENCE_LENGTH,
                    "sequence": "",
                    "sequence_length": 0,
                    "t_count": 0,
                    "achieved_error": float("nan"),
                    "smoke_epsilon": SMOKE_EPSILON,
                    "smoke_pass": False,
                    "tight_epsilon": TIGHT_EPSILON,
                    "tight_pass": False,
                    "status": "needs revision",
                }
            )
            continue

        best = beam_synthesize(angle)
        recomputed = sequence_unitary(best.sequence)
        verified_error = global_phase_error(recomputed, target_unitary(angle))
        smoke_pass = verified_error <= SMOKE_EPSILON
        tight_pass = verified_error <= TIGHT_EPSILON
        rows.append(
            {
                "target_id": target_id,
                "angle_pi": str(angle),
                "denominator": angle.denominator,
                "source_count": counts[angle],
                "source_file": example.source_file,
                "source_name": example.name,
                "source_method": example.method,
                "source_split": example.split,
                "source_n": example.n,
                "source_parity_mask_hex": hex(example.parity_mask),
                "backend": "internal_matrix_beam",
                "beam_width": BEAM_WIDTH,
                "max_sequence_length": MAX_SEQUENCE_LENGTH,
                "sequence": " ".join(best.sequence) if best.sequence else "I",
                "sequence_length": len(best.sequence),
                "t_count": best.t_count,
                "achieved_error": verified_error,
                "smoke_epsilon": SMOKE_EPSILON,
                "smoke_pass": smoke_pass,
                "tight_epsilon": TIGHT_EPSILON,
                "tight_pass": tight_pass,
                "status": "pass" if smoke_pass else "needs revision",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt_error(value: object) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "nan"


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    pass_rows = [row for row in rows if row["status"] == "pass"]
    tight_rows = [row for row in rows if row["tight_pass"] is True]
    max_error = max(float(row["achieved_error"]) for row in pass_rows) if pass_rows else float("nan")
    mean_error = statistics.mean(float(row["achieved_error"]) for row in pass_rows) if pass_rows else float("nan")
    lines = [
        "# Phase Rotation-Sequence Smoke Audit",
        "",
        "This audit extracts representative non-Clifford Rz angles from the verified affine phase spectra",
        "and emits concrete single-qubit Clifford+T gate strings with an internal matrix beam search.",
        "The distance metric is global-phase-invariant:",
        "`sqrt(1 - |Tr(U_seq^dagger U_target)|/2)`.",
        "",
        "This is a coarse sequence-level smoke test.  It is not Ross--Selinger gridsynth,",
        "not optimal T-count synthesis, not a high-precision compiler, and not hardware mapping.",
        "",
        f"- target angles: {len(rows)}",
        "- target selection: top-20 most frequent non-Clifford/non-T-like angles in the verified phase-search outputs",
        f"- smoke epsilon: {SMOKE_EPSILON}",
        f"- smoke passes: {len(pass_rows)}/{len(rows)}",
        f"- tight epsilon: {TIGHT_EPSILON}",
        f"- tight passes: {len(tight_rows)}/{len(rows)}",
        f"- max achieved error among smoke passes: {max_error:.6f}",
        f"- mean achieved error among smoke passes: {mean_error:.6f}",
        "",
        "| target | angle/pi | support | sequence length | T count | error | smoke pass | sequence |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {target} | {angle} | {support} | {length} | {t_count} | {error} | {smoke} | `{sequence}` |".format(
                target=row["target_id"],
                angle=row["angle_pi"],
                support=row["source_count"],
                length=row["sequence_length"],
                t_count=row["t_count"],
                error=fmt_error(row["achieved_error"]),
                smoke="yes" if row["smoke_pass"] else "no",
                sequence=row["sequence"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The 20 target angles are the most frequent non-Clifford/non-T-like angles in the existing phase-search outputs; this is not a synthetic rotation-only benchmark.",
            "- The bounded beam search closes part of the previous evidence gap by emitting actual Clifford+T strings for source-derived Rz targets.",
            "- The coarse tolerance and non-optimal sequences mean the manuscript should still keep the phase/Rz branch as a logical proxy and cite Ross--Selinger only for the precision-sensitivity model.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedleft\arraybackslash}p{0.12\linewidth}>{\raggedleft\arraybackslash}X}",
        r"\toprule",
        r"Target & Angle/$\pi$ & Support & Len. & $T$ & Error \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            "{} & {} & {} & {} & {} & {} \\\\".format(
                str(row["target_id"]).replace("_", r"\_"),
                str(row["angle_pi"]),
                row["source_count"],
                row["sequence_length"],
                row["t_count"],
                fmt_error(row["achieved_error"]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    pass_count = sum(1 for row in rows if row["status"] == "pass")
    tight_pass_count = sum(1 for row in rows if row["tight_pass"] is True)
    errors = [float(row["achieved_error"]) for row in rows if row["status"] == "pass"]
    data = {
        "script": Path(__file__).name,
        "python": sys.version.split()[0],
        "backend": "packaged_raw_sequence_verification" if PHASE_RECONSTRUCTION_IMPORT_ERROR else "internal_matrix_beam",
        "phase_reconstruction_import_error": PHASE_RECONSTRUCTION_IMPORT_ERROR,
        "gate_set": sorted(GATE_MATRICES),
        "beam_width": BEAM_WIDTH,
        "max_sequence_length": MAX_SEQUENCE_LENGTH,
        "rows": len(rows),
        "target_angles": [str(angle) for _, angle in TARGETS],
        "target_denominators": sorted({angle.denominator for _, angle in TARGETS}),
        "smoke_epsilon": SMOKE_EPSILON,
        "smoke_pass_count": pass_count,
        "tight_epsilon": TIGHT_EPSILON,
        "tight_pass_count": tight_pass_count,
        "max_achieved_error": max(errors) if errors else None,
        "mean_achieved_error": statistics.mean(errors) if errors else None,
        "status_counts": {
            status: sum(1 for row in rows if row["status"] == status)
            for status in sorted({str(row["status"]) for row in rows})
        },
        "needs_revision_count": len(rows) - pass_count,
        "sources": [str(path.relative_to(THIS_DIR)) for path in PHASE_SOURCES],
        "outputs": {
            "raw": "results/raw_phase_rotation_sequence_smoke_audit.csv",
            "summary": "results/summary_phase_rotation_sequence_smoke_audit.csv",
            "analysis": "results/analysis_phase_rotation_sequence_smoke_audit.md",
            "manifest": "results/manifest_phase_rotation_sequence_smoke_audit.json",
            "table": "paper_latex/tables/phase_rotation_sequence_smoke_audit.tex",
        },
        "boundary": "Coarse internal sequence smoke only; not Ross-Selinger gridsynth, optimal T-count synthesis, hardware mapping, routing, or native-gate scheduling.",
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_csv(RAW_OUT, rows)
    write_csv(SUMMARY_OUT, rows)
    write_markdown(ANALYSIS_OUT, rows)
    write_latex(TABLE_OUT, rows)
    write_manifest(MANIFEST_OUT, rows)
    print(f"wrote {len(rows)} phase rotation-sequence smoke rows")
    return 1 if any(row["status"] != "pass" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
