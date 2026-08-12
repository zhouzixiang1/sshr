"""Run-level provenance manifest for XA experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.contracts.codec import canonical_json_bytes


EXPERIMENT_MANIFEST_SCHEMA = "xa.experiment-manifest.v1"


@dataclass(frozen=True)
class ExperimentManifest:
    run_id: str
    track: str
    experiment: str
    status: str
    created_at_utc: str
    source: dict[str, Any]
    environment: dict[str, Any]
    command: dict[str, Any]
    dataset: dict[str, Any]
    config: dict[str, Any]
    model: dict[str, Any] | None
    variants: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    counts: dict[str, Any]
    timing: dict[str, Any]
    claim_boundary: str
    schema_version: str = EXPERIMENT_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != EXPERIMENT_MANIFEST_SCHEMA:
            raise ValueError(f"unsupported experiment manifest schema: {self.schema_version!r}")
        if self.status not in {"planned", "running", "complete", "failed"}:
            raise ValueError(f"unsupported experiment status: {self.status!r}")
        if not self.run_id or "/" in self.run_id or "\\" in self.run_id:
            raise ValueError("run_id must be a non-empty path-safe identifier")
        canonical_json_bytes(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
