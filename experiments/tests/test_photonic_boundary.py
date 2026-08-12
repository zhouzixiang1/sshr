"""Fail-closed contracts for the photonic capability boundary."""

from __future__ import annotations

import pytest

from src.hardware.photonic import (
    PhotonicUnsupportedError,
    compile_photonic,
    photonic_capability_record,
)


def test_photonic_capability_is_explicit_deterministic_and_non_executable() -> None:
    first = photonic_capability_record()
    second = photonic_capability_record()

    assert first == second
    assert first is not second
    assert first["route_kind"] == "boundary_only"
    assert first["executable"] is False
    assert first["hardware_execution"] is False
    assert first["evidence_strength"] == "interface-boundary-only"
    contract = first["required_backend_contract"]
    assert contract["encoding"]["current_selection"] is None
    assert contract["resource_state"]["current_family"] is None
    assert contract["measurement_and_feed_forward"]["measurement_basis_schedule"] is None
    assert contract["loss_model"]["detector_efficiency"] is None
    assert contract["heralding_and_postselection"]["success_event_definition"] is None
    assert len(first["currently_unsupported"]) >= 6
    assert "No photonic gate mapping" in first["claim_boundary"]


def test_photonic_compile_attempt_fails_closed_without_fake_gate_mapping() -> None:
    with pytest.raises(PhotonicUnsupportedError, match="Capability and unsupported"):
        compile_photonic(object())
