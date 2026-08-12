"""Canonical encodings shared by experiment and synthesis contracts."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def canonical_hex(value: int, *, min_nibbles: int = 1) -> str:
    """Encode a non-negative integer as a lower-case, zero-padded hex string."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("canonical_hex value must be an integer")
    if value < 0:
        raise ValueError("canonical_hex value must be non-negative")
    if isinstance(min_nibbles, bool) or not isinstance(min_nibbles, int):
        raise TypeError("min_nibbles must be an integer")
    if min_nibbles < 1:
        raise ValueError("min_nibbles must be positive")
    return f"0x{value:0{min_nibbles}x}"


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise TypeError("sets must be converted to a stable sequence before encoding")
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _reject_non_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite float at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{path}[{index}]")


def canonical_json_text(value: Any) -> str:
    """Return deterministic UTF-8 JSON text with strict finite-number checks."""

    plain = _plain(value)
    _reject_non_finite(plain)
    return json.dumps(
        plain,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_json_bytes(value: Any) -> bytes:
    return (canonical_json_text(value) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
