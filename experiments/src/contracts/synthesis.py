"""Versioned detailed synthesis result used by XA experiment runners."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.contracts.codec import canonical_json_bytes
from src.contracts.search import PlanTrace


DETAILED_SYNTHESIS_SCHEMA = "xa.detailed-synthesis-result.v1"
LOGICAL_COST_SEMANTICS = "logical-resource-proxy-v1"
LOGICAL_CLAIM_BOUNDARY = (
    "The recorded resource cost is a logical X/CNOT/MCT-layer proxy. It is not "
    "a native-gate, routed, noisy-simulator, or hardware-execution cost."
)


@dataclass(frozen=True)
class DetailedSynthesisResult:
    requested_method: str
    effective_method: str
    seed: int
    input: dict[str, Any]
    effective_config: dict[str, Any]
    model: dict[str, Any] | None
    summary: dict[str, Any]
    plan_trace: PlanTrace | None
    plan_unavailable_reason: str | None
    logical_ir: dict[str, Any]
    logical_qasm3: str
    qasm_metadata: dict[str, Any]
    verification: dict[str, Any]
    transform: dict[str, Any] | None = None
    cost_semantics: str = LOGICAL_COST_SEMANTICS
    claim_boundary: str = LOGICAL_CLAIM_BOUNDARY
    schema_version: str = DETAILED_SYNTHESIS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DETAILED_SYNTHESIS_SCHEMA:
            raise ValueError(f"unsupported detailed synthesis schema: {self.schema_version!r}")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if self.plan_trace is None and not self.plan_unavailable_reason:
            raise ValueError("plan_unavailable_reason is required when plan_trace is absent")
        if self.plan_trace is not None and self.plan_unavailable_reason is not None:
            raise ValueError("plan_unavailable_reason must be None when plan_trace is present")
        if not self.logical_qasm3.startswith("OPENQASM 3.0;"):
            raise ValueError("logical_qasm3 must contain an OpenQASM 3 program")
        # Serialize once during construction so NaN/Inf and unstable containers
        # fail at the producer boundary instead of later in the evidence writer.
        canonical_json_bytes(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "requested_method": self.requested_method,
            "effective_method": self.effective_method,
            "seed": self.seed,
            "input": self.input,
            "effective_config": self.effective_config,
            "model": self.model,
            "summary": self.summary,
            "plan_trace": self.plan_trace.to_dict() if self.plan_trace else None,
            "plan_unavailable_reason": self.plan_unavailable_reason,
            "logical_ir": self.logical_ir,
            "logical_qasm3": self.logical_qasm3,
            "qasm_metadata": self.qasm_metadata,
            "verification": self.verification,
            "transform": self.transform,
            "cost_semantics": self.cost_semantics,
            "claim_boundary": self.claim_boundary,
        }

    @staticmethod
    def dataclass_record(value: object) -> dict[str, Any]:
        """Convert a dataclass such as SearchConfig/SynthesisResult to a record."""

        try:
            return asdict(value)  # type: ignore[arg-type]
        except TypeError as exc:
            raise TypeError("value must be a dataclass instance") from exc
