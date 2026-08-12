"""Determinism and strict-number tests for XA contract encodings."""

from __future__ import annotations

import json
import math

import pytest

from src.contracts.codec import canonical_hex, canonical_json_bytes, canonical_json_text


def test_canonical_json_is_sorted_utf8_and_byte_stable() -> None:
    left = {"z": [3, 2, 1], "a": {"中文": True, "value": 1.25}}
    right = {"a": {"value": 1.25, "中文": True}, "z": [3, 2, 1]}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_bytes(left).endswith(b"\n")
    assert json.loads(canonical_json_text(left)) == left


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_canonical_json_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonical_json_bytes({"nested": [0.0, {"bad": value}]})


def test_canonical_json_requires_callers_to_sort_sets() -> None:
    with pytest.raises(TypeError, match="sets must be converted"):
        canonical_json_bytes({"terms": {1, 2}})


def test_canonical_hex_is_lowercase_and_padded() -> None:
    assert canonical_hex(0) == "0x0"
    assert canonical_hex(0xAF, min_nibbles=4) == "0x00af"
    with pytest.raises(ValueError):
        canonical_hex(-1)
    with pytest.raises(TypeError):
        canonical_hex(True)
