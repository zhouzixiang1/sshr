"""Versioned, deterministic contracts for XA-202609 experiment evidence.

The contract layer is intentionally independent of search policy choices.  It
turns in-memory synthesis objects into stable records and provides a small
checksum-verified artifact bundle format for experiments and submission QA.
"""

from .artifacts import (
    ArtifactBundleWriter,
    ArtifactRef,
    BundleVerification,
    verify_bundle,
)
from .codec import (
    canonical_hex,
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_file,
)
from .experiment import ExperimentManifest
from .search import PlanNodeTrace, PlanTrace
from .synthesis import DetailedSynthesisResult

__all__ = [
    "ArtifactBundleWriter",
    "ArtifactRef",
    "BundleVerification",
    "DetailedSynthesisResult",
    "ExperimentManifest",
    "PlanNodeTrace",
    "PlanTrace",
    "canonical_hex",
    "canonical_json_bytes",
    "canonical_json_text",
    "sha256_bytes",
    "sha256_file",
    "verify_bundle",
]
