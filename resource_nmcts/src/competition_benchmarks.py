"""Frozen Boolean-function suite for the XA-202609 competition experiments."""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.anf_utils import (
    anf_monomials,
    majority_function,
    parity_function,
    random_anf_function,
    random_truth_function,
    threshold_function,
)
from src.sshr_lib.bool_func import BooleanFunction


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AES_SOURCE = PROJECT_ROOT / "results" / "aes_sbox_functions.json"
SUITE_VERSION = "xa202609-final-v1"


def function_key(bf: BooleanFunction) -> str:
    """Content address for a Boolean function, independent of its display ID."""
    payload = {
        "n": int(bf.n),
        "truth_table_hex": format(int(bf.truth_table), f"0{max(1, (1 << bf.n) // 4)}x"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    family: str
    function: BooleanFunction
    generator: str
    generator_params: dict[str, Any]
    source: str

    @property
    def function_key(self) -> str:
        return function_key(self.function)

    def to_manifest(self) -> dict[str, Any]:
        bf = self.function
        width = max(1, (1 << bf.n) // 4)
        return {
            "case_id": self.case_id,
            "family": self.family,
            "n_inputs": int(bf.n),
            "truth_table_hex": f"0x{bf.truth_table:0{width}x}",
            "function_key": self.function_key,
            "anf_terms": len(anf_monomials(bf)),
            "onset_size": len(bf.onset),
            "generator": self.generator,
            "generator_params": self.generator_params,
            "source": self.source,
        }


def _and_function(n: int) -> BooleanFunction:
    return BooleanFunction(n, 1 << ((1 << n) - 1))


def _aes_component(bit: int) -> BooleanFunction:
    table = json.loads(AES_SOURCE.read_text(encoding="utf-8"))["sbox"]
    if len(table) != 256:
        raise ValueError("AES S-box source must contain 256 entries")
    truth_table = 0
    for x, value in enumerate(table):
        if (int(value) >> bit) & 1:
            truth_table |= 1 << x
    return BooleanFunction(8, truth_table)


def _random_truth_case(n: int, seed: int) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=f"randtt{n}_s{seed}",
        family="random_truth",
        function=random_truth_function(n, random.Random(seed)),
        generator="random_truth_function",
        generator_params={"seed": seed},
        source="project deterministic generator",
    )


def _random_anf_case(n: int, seed: int, term_prob: float, max_degree: int) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=f"randanf{n}_s{seed}",
        family="random_anf",
        function=random_anf_function(
            n,
            random.Random(seed),
            term_prob=term_prob,
            max_degree=max_degree,
        ),
        generator="random_anf_function",
        generator_params={
            "seed": seed,
            "term_prob": term_prob,
            "max_degree": max_degree,
        },
        source="project deterministic generator",
    )


def competition_suite() -> tuple[BenchmarkCase, ...]:
    """Return 30 content-distinct, deterministic cases with ``n <= 8``."""
    cases: list[BenchmarkCase] = [
        BenchmarkCase("and3", "structured", _and_function(3), "and", {"n": 3}, "analytic"),
        BenchmarkCase("and4", "structured", _and_function(4), "and", {"n": 4}, "analytic"),
        BenchmarkCase("parity4", "structured", parity_function(4), "parity", {"n": 4}, "analytic"),
        BenchmarkCase("parity6", "structured", parity_function(6), "parity", {"n": 6}, "analytic"),
        BenchmarkCase("maj3", "structured", majority_function(3), "majority", {"n": 3}, "analytic"),
        BenchmarkCase("maj5", "structured", majority_function(5), "majority", {"n": 5}, "analytic"),
        BenchmarkCase("maj7", "structured", majority_function(7), "majority", {"n": 7}, "analytic"),
        BenchmarkCase("thr5_t2", "structured", threshold_function(5, 2), "threshold", {"n": 5, "threshold": 2}, "analytic"),
        BenchmarkCase("thr6_t3", "structured", threshold_function(6, 3), "threshold", {"n": 6, "threshold": 3}, "analytic"),
        BenchmarkCase("thr7_t5", "structured", threshold_function(7, 5), "threshold", {"n": 7, "threshold": 5}, "analytic"),
    ]
    cases.extend(_random_truth_case(4, seed) for seed in (101, 103, 107, 109))
    cases.extend(_random_truth_case(5, seed) for seed in (113, 127, 131, 137))
    cases.extend(_random_truth_case(6, seed) for seed in (139, 149))
    cases.extend(
        [
            _random_anf_case(6, 151, 0.16, 3),
            _random_anf_case(6, 157, 0.24, 4),
            _random_anf_case(7, 163, 0.10, 3),
            _random_anf_case(7, 167, 0.16, 4),
            _random_anf_case(8, 173, 0.07, 3),
            _random_anf_case(8, 179, 0.11, 4),
        ]
    )
    for bit in (0, 2, 5, 7):
        cases.append(
            BenchmarkCase(
                case_id=f"aes_sbox_b{bit}",
                family="aes_sbox",
                function=_aes_component(bit),
                generator="aes_sbox_component",
                generator_params={"output_bit": bit},
                source="results/aes_sbox_functions.json",
            )
        )
    if len(cases) != 30:
        raise AssertionError(f"competition suite must contain 30 cases, got {len(cases)}")
    ids = [case.case_id for case in cases]
    keys = [case.function_key for case in cases]
    if len(set(ids)) != len(ids):
        raise AssertionError("duplicate benchmark case_id")
    if len(set(keys)) != len(keys):
        raise AssertionError("duplicate Boolean function in competition suite")
    return tuple(cases)


def suite_manifest() -> dict[str, Any]:
    cases = [case.to_manifest() for case in competition_suite()]
    content = {
        "suite_version": SUITE_VERSION,
        "case_count": len(cases),
        "function_key_algorithm": "sha256(canonical-json(n,truth_table_hex-without-0x))",
        "cases": cases,
    }
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {**content, "suite_id": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
