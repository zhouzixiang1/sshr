"""Photonic capability boundary for logical Boolean-oracle circuits.

This module deliberately does *not* lower X/CNOT/MCT into fictional photonic
gates.  A real photonic backend must first fix an encoding, resource-state
family, measurement/feed-forward semantics, loss and detector model, and the
allowed heralding/postselection contract.  The current project has none of
those calibrated inputs, so only a machine-readable interface boundary is
provided.
"""

from __future__ import annotations

from copy import deepcopy


EVIDENCE_STRENGTH = "interface-boundary-only"
CLAIM_BOUNDARY = (
    "Capability and unsupported-boundary declaration only. No photonic gate "
    "mapping, resource-state synthesis, measurement/feed-forward schedule, "
    "loss-aware success probability, calibrated simulation, real hardware "
    "execution, speedup, or quantum-advantage claim is provided."
)


class PhotonicUnsupportedError(NotImplementedError):
    """Raised when a caller requests an unimplemented photonic compilation."""


_CAPABILITY = {
    "schema_version": "xa.photonic-capability.v1",
    "route_id": "photonic",
    "route_kind": "boundary_only",
    "adapter_status": "unsupported_pending_backend_contract",
    "executable": False,
    "hardware_execution": False,
    "evidence_strength": EVIDENCE_STRENGTH,
    "accepted_logical_ir": "logical-x-cnot-mct",
    "required_backend_contract": {
        "encoding": {
            "must_select_exactly_one": True,
            "candidates_not_selected": ["dual_rail", "single_rail", "time_bin"],
            "current_selection": None,
        },
        "resource_state": {
            "required": True,
            "current_family": None,
            "must_declare_generation_and_verification": True,
        },
        "measurement_and_feed_forward": {
            "required": True,
            "measurement_basis_schedule": None,
            "feed_forward_latency_model": None,
            "detector_contract": None,
        },
        "loss_model": {
            "required": True,
            "source_efficiency": None,
            "transmission_loss": None,
            "interference_visibility": None,
            "detector_efficiency": None,
            "dark_count_rate": None,
        },
        "heralding_and_postselection": {
            "must_be_explicit": True,
            "success_event_definition": None,
            "postselection_policy": None,
        },
    },
    "currently_supported": [
        "logical IR intake contract declaration",
        "backend prerequisite schema",
        "unsupported-scope fail-closed error",
    ],
    "currently_unsupported": [
        "logical X/CNOT/MCT to photonic operation lowering",
        "resource-state synthesis and consumption accounting",
        "measurement pattern and adaptive feed-forward scheduling",
        "loss-aware or detector-aware execution simulation",
        "heralding or postselection success-probability estimation",
        "calibrated device execution",
    ],
    "claim_boundary": CLAIM_BOUNDARY,
}


def photonic_capability_record() -> dict[str, object]:
    """Return a detached deterministic capability/boundary record."""

    return deepcopy(_CAPABILITY)


def compile_photonic(*_args: object, **_kwargs: object) -> None:
    """Fail closed until a concrete photonic backend contract is supplied."""

    raise PhotonicUnsupportedError(CLAIM_BOUNDARY)


__all__ = [
    "CLAIM_BOUNDARY",
    "EVIDENCE_STRENGTH",
    "PhotonicUnsupportedError",
    "compile_photonic",
    "photonic_capability_record",
]
