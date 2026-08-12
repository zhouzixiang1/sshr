"""Provenance-carrying cryptographic Boolean-oracle benchmarks.

The synthesis engine consumes scalar :class:`BooleanFunction` objects, whereas
cryptographic substitutions are vector Boolean functions.  This module makes
that boundary explicit: one ``CryptoOracleCoordinate`` represents one output
bit and records enough metadata to reproduce and audit its complete truth
table.

AES is the only family exposed through the general benchmark loader.  ASCON
and PRESENT are frozen external-family hold-outs: their constants are audited,
but their coordinates can only be obtained from the explicit hold-out loader
after acknowledging the family-exclusion label.  This keeps existing training,
calibration, and model-selection code from silently expanding its data domain.
SM4 remains registered but unverified and unavailable from either loader.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
from typing import Final, Iterable

from src.sshr_lib.bool_func import BooleanFunction


CANONICAL_TRUTH_TABLE_ENCODING: Final[str] = (
    "Unsigned truth_table integer encoded in exactly ceil(2**input_width/8) "
    "bytes, little-endian; bit x is f(x). SHA-256 is over those bytes."
)

CANONICAL_SUBSTITUTION_TABLE_ENCODING: Final[str] = (
    "Forward substitution outputs S(0), S(1), ... as one unsigned byte each; "
    "SHA-256 is over that byte string."
)

CRYPTO_HOLDOUT_EXCLUSION_LABEL: Final[str] = (
    "external_crypto_family_holdout_excluded_from_training_calibration_"
    "and_model_selection"
)

_LSB_BIT_ORDER: Final[str] = (
    "x = sum(input_bit[i] * 2**i); coordinate 0 is the output LSB; "
    "truth-table bit x equals coordinate(x)"
)


class CryptoOracleVerificationError(ValueError):
    """Raised when a benchmark no longer matches its frozen truth-table hash."""


class UnsupportedCryptoOracleError(NotImplementedError):
    """Raised when a family is unavailable through the requested interface."""

    def __init__(self, spec: "CryptoOracleFamilySpec") -> None:
        self.spec = spec
        super().__init__(
            f"{spec.family} coordinate functions are unsupported: "
            f"{spec.unsupported_reason} Source contract: {spec.source}"
        )


class CryptoOracleHoldoutAccessError(PermissionError):
    """Raised unless an evaluation caller acknowledges the frozen exclusion."""


@dataclass(frozen=True)
class CryptoOracleFamilySpec:
    """Source and representation contract for a vector Boolean function."""

    family: str
    operation: str
    input_width: int
    output_width: int
    bit_order: str
    source: str
    provenance: str
    supported: bool
    unsupported_reason: str | None = None
    benchmark_partition: str = "development"
    training_access_allowed: bool = True
    holdout_evaluation_supported: bool = False
    family_exclusion_label: str | None = None
    vector_truth_table_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.input_width <= 0 or self.output_width <= 0:
            raise ValueError("input_width and output_width must be positive")
        if self.supported and self.unsupported_reason is not None:
            raise ValueError("a supported family cannot have unsupported_reason")
        if not self.supported and not self.unsupported_reason:
            raise ValueError("an unsupported family must state unsupported_reason")
        if self.holdout_evaluation_supported:
            if self.supported:
                raise ValueError("a hold-out family cannot use the general loader")
            if self.training_access_allowed:
                raise ValueError("a hold-out family cannot permit training access")
            if not self.family_exclusion_label:
                raise ValueError("a hold-out family requires a family-exclusion label")
            if not self.vector_truth_table_sha256:
                raise ValueError("a hold-out family requires a frozen vector-table SHA-256")
        if self.vector_truth_table_sha256 is not None:
            digest = self.vector_truth_table_sha256
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("vector_truth_table_sha256 must be lowercase SHA-256 hex")


@dataclass(frozen=True)
class CryptoOracleCoordinate:
    """One reproducible coordinate function from a cryptographic primitive."""

    family: str
    operation: str
    output_bit: int
    input_width: int
    output_width: int
    bit_order: str
    source: str
    provenance: str
    truth_table_sha256: str
    boolean_function: BooleanFunction
    benchmark_partition: str = "development"
    training_access_allowed: bool = True
    family_exclusion_label: str | None = None
    vector_truth_table_sha256: str | None = None

    def evaluate(self, x: int) -> int:
        if not 0 <= x < (1 << self.input_width):
            raise ValueError(f"input x={x} is outside the {self.input_width}-bit domain")
        return self.boolean_function.evaluate(x)

    def canonical_truth_table_bytes(self) -> bytes:
        byte_count = ((1 << self.input_width) + 7) // 8
        return int(self.boolean_function.truth_table).to_bytes(byte_count, "little")

    def assert_valid(self) -> None:
        """Recompute every output and verify the frozen complete-table SHA-256."""

        spec = get_crypto_oracle_family_spec(self.family)
        metadata = (
            self.operation,
            self.input_width,
            self.output_width,
            self.bit_order,
            self.source,
            self.provenance,
            self.benchmark_partition,
            self.training_access_allowed,
            self.family_exclusion_label,
            self.vector_truth_table_sha256,
        )
        expected_metadata = (
            spec.operation,
            spec.input_width,
            spec.output_width,
            spec.bit_order,
            spec.source,
            spec.provenance,
            spec.benchmark_partition,
            spec.training_access_allowed,
            spec.family_exclusion_label,
            spec.vector_truth_table_sha256,
        )
        if metadata != expected_metadata:
            raise CryptoOracleVerificationError(
                f"{self.family}[{self.output_bit}] provenance metadata differs "
                "from the registered family contract"
            )
        if self.boolean_function.n != self.input_width:
            raise CryptoOracleVerificationError(
                f"{self.family}[{self.output_bit}] has n={self.boolean_function.n}, "
                f"expected {self.input_width}"
            )
        if not 0 <= self.output_bit < self.output_width:
            raise CryptoOracleVerificationError("output_bit is outside the family width")

        expected_sha = _coordinate_sha256(self.family, self.output_bit)
        if self.truth_table_sha256 != expected_sha:
            raise CryptoOracleVerificationError(
                f"{self.family}[{self.output_bit}] frozen coordinate SHA-256 "
                "differs from the registered family contract"
            )

        recomputed = _audited_coordinate_truth_table(self.family, self.output_bit)
        if self.boolean_function.truth_table != recomputed:
            raise CryptoOracleVerificationError(
                f"{self.family}[{self.output_bit}] complete truth table does not "
                "match the standard evaluator"
            )
        actual_sha = hashlib.sha256(self.canonical_truth_table_bytes()).hexdigest()
        if actual_sha != self.truth_table_sha256:
            raise CryptoOracleVerificationError(
                f"{self.family}[{self.output_bit}] SHA-256 mismatch: "
                f"expected {self.truth_table_sha256}, got {actual_sha}"
            )


_AES_SOURCE: Final[str] = (
    "NIST FIPS 197-upd1 (2023), Advanced Encryption Standard, "
    "Section 5.1.1 and Table 4; https://doi.org/10.6028/NIST.FIPS.197-upd1"
)

_FAMILY_SPECS: Final[dict[str, CryptoOracleFamilySpec]] = {
    "AES": CryptoOracleFamilySpec(
        family="AES",
        operation="SubBytes forward S-box",
        input_width=8,
        output_width=8,
        bit_order=_LSB_BIT_ORDER,
        source=_AES_SOURCE,
        provenance=(
            "Generated from the FIPS 197 GF(2^8) multiplicative-inverse and "
            "affine-transform definition; frozen coordinate hashes below; "
            "known FIPS table anchors are checked during family verification."
        ),
        supported=True,
    ),
    "SM4": CryptoOracleFamilySpec(
        family="SM4",
        operation="nonlinear substitution S-box",
        input_width=8,
        output_width=8,
        bit_order=_LSB_BIT_ORDER,
        source=(
            "GB/T 32907-2016; public algorithm transcription: IETF RFC 8998, "
            "https://www.rfc-editor.org/rfc/rfc8998.html"
        ),
        provenance="Interface metadata only; no S-box constants are embedded.",
        supported=False,
        unsupported_reason=(
            "the standard table and an independent full-table checksum have "
            "not yet been audited in this repository"
        ),
        benchmark_partition="unverified_blocked",
        training_access_allowed=False,
    ),
    "PRESENT": CryptoOracleFamilySpec(
        family="PRESENT",
        operation="forward 4-bit substitution S-box",
        input_width=4,
        output_width=4,
        bit_order=_LSB_BIT_ORDER,
        source=(
            "Bogdanov et al., PRESENT: An Ultra-Lightweight Block Cipher, "
            "CHES 2007, Section 2.1 and Table 1; "
            "https://www.iacr.org/archive/ches2007/47270450/47270450.pdf; "
            "https://doi.org/10.1007/978-3-540-74735-2_31"
        ),
        provenance=(
            "Forward table transcribed from the original paper's Table 1. "
            "The paper numbers bits from zero with bit zero on the right and "
            "defines wi=b[4i+3]||...||b[4i], which agrees with the canonical "
            "integer/LSB coordinate convention used here. Audited 2026-08-12; "
            "only the forward S-box is registered (no inverse coordinates); "
            "coordinate and complete vector-table hashes are frozen below."
        ),
        supported=False,
        unsupported_reason=(
            "this audited external-family hold-out is deliberately blocked from "
            "the general/training loader; use the labelled evaluation-only loader"
        ),
        benchmark_partition="external_crypto_family_holdout",
        training_access_allowed=False,
        holdout_evaluation_supported=True,
        family_exclusion_label=CRYPTO_HOLDOUT_EXCLUSION_LABEL,
        vector_truth_table_sha256=(
            "8e63f8c394a1ee38340d3be6e9a33b7b8c86d752498720dc80c223b02562e959"
        ),
    ),
    "ASCON": CryptoOracleFamilySpec(
        family="ASCON",
        operation="forward 5-bit substitution S-box",
        input_width=5,
        output_width=5,
        bit_order=_LSB_BIT_ORDER,
        source=(
            "NIST SP 800-232 (2025), Ascon-Based Lightweight Cryptography "
            "Standards, Section 3.3 and Table 6; "
            "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/"
            "NIST.SP.800-232.pdf; https://doi.org/10.6028/NIST.SP.800-232"
        ),
        provenance=(
            "Forward table transcribed from NIST SP 800-232 Table 6 and "
            "cross-checked against its coordinate equations. NIST represents "
            "x=1 as (x0,...,x4)=(0,0,0,0,1); therefore canonical input bit i "
            "maps to NIST x[4-i], and canonical output bit i maps to NIST "
            "y[4-i]. Audited 2026-08-12; coordinate and complete vector-table "
            "hashes are frozen below. Only the standard's forward S-box is "
            "registered; no inverse coordinates are defined."
        ),
        supported=False,
        unsupported_reason=(
            "this audited external-family hold-out is deliberately blocked from "
            "the general/training loader; use the labelled evaluation-only loader"
        ),
        benchmark_partition="external_crypto_family_holdout",
        training_access_allowed=False,
        holdout_evaluation_supported=True,
        family_exclusion_label=CRYPTO_HOLDOUT_EXCLUSION_LABEL,
        vector_truth_table_sha256=(
            "2f5f6885b68f1f6fafed2be6ab614346c48a8528b51f7b4bdf4a0c1b609df97d"
        ),
    ),
}

_AES_COORDINATE_SHA256: Final[tuple[str, ...]] = (
    "1e9824b17f9c4881346ee92a37d0ff4efc5d44cadf9c1e558f78ae190d662a05",
    "ac7c564edb9b2693a5ecf17f055281babf6b97433394169f5448d5af6fc950c2",
    "8bb9df77d8e16f65c91cc9fce1b1368b9f23332f6eb41419cc7fbd0ce39e2f4c",
    "f1993d2d5719218ea7fe15a97b9c7f977c03863e923def799fc948f669bc613f",
    "793b6367e6dd9217673ed5a6aa0bda6faa78da85239f47061ffb470e41c6151f",
    "25bff3db1032e49ddfc2d9bc9d5d48c985b1779930865e47f3780ff950984994",
    "3e1685e8e7f2b9529edafc5fd6d96e1174d858091a180d379cd89147ec286256",
    "20b7cdfce4e67e25cb3b5dc4de26118f9b048c02981fa89ad1ceb54bd5274dd5",
)

_PRESENT_FORWARD_SBOX: Final[tuple[int, ...]] = (
    0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD,
    0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2,
)

_PRESENT_COORDINATE_SHA256: Final[tuple[str, ...]] = (
    "4e970e8b7f2fb52a79c55db9c9dfaa44658eb64fd37e5ed9d3440a0905803e71",
    "b3311960f4cf52c6db4d5cbb9cf0d47915e3666175b91f3eb4e08bad9932865a",
    "651dfc9a16350c391f9b9f1e02afd433f951246a6fce4691301e3c463266bf71",
    "3def4ec7c4026dc026162cdf2279a16a8e9e9f5efdde0521ebbfd91f3d5fec83",
)

_ASCON_FORWARD_SBOX: Final[tuple[int, ...]] = (
    0x04, 0x0B, 0x1F, 0x14, 0x1A, 0x15, 0x09, 0x02,
    0x1B, 0x05, 0x08, 0x12, 0x1D, 0x03, 0x06, 0x1C,
    0x1E, 0x13, 0x07, 0x0E, 0x00, 0x0D, 0x11, 0x18,
    0x10, 0x0C, 0x01, 0x19, 0x16, 0x0A, 0x0F, 0x17,
)

_ASCON_COORDINATE_SHA256: Final[tuple[str, ...]] = (
    "2629f646e4e48c89d27a2fa15d806db1bb59721ec004c19415ae59ac2e72b48f",
    "80713771a1b2e8920d65ad892d27c8e2e8aba5874d587d4b24cf6cf074784ce7",
    "8a20f3428448f5e2bd8da3e9559cb7a3ae091759f4516e80cc65b8f616d6112d",
    "e511dae0b4fd7953dd2e564003d3ef3b86f560ece76e073391bc525e9a45a97d",
    "cac32e76240366ea1129102f26003cec2121742a1742f912da081106857743be",
)

_FAMILY_COORDINATE_SHA256: Final[dict[str, tuple[str, ...]]] = {
    "AES": _AES_COORDINATE_SHA256,
    "ASCON": _ASCON_COORDINATE_SHA256,
    "PRESENT": _PRESENT_COORDINATE_SHA256,
}

_FAMILY_ANCHORS: Final[dict[str, dict[int, int]]] = {
    "AES": {0x00: 0x63, 0x53: 0xED, 0xFF: 0x16},
    "ASCON": {0x00: 0x04, 0x01: 0x0B, 0x14: 0x00, 0x1F: 0x17},
    "PRESENT": {0x0: 0xC, 0x1: 0x5, 0x5: 0x0, 0xF: 0x2},
}


def available_crypto_oracle_families() -> tuple[CryptoOracleFamilySpec, ...]:
    """Return all contracts, including explicitly unsupported families."""

    return tuple(_FAMILY_SPECS[name] for name in sorted(_FAMILY_SPECS))


def available_crypto_holdout_families() -> tuple[CryptoOracleFamilySpec, ...]:
    """Return audited external families reserved for final evaluation only."""

    return tuple(
        _FAMILY_SPECS[name]
        for name in sorted(_FAMILY_SPECS)
        if _FAMILY_SPECS[name].holdout_evaluation_supported
    )


def get_crypto_oracle_family_spec(family: str) -> CryptoOracleFamilySpec:
    key = _normalise_family(family)
    try:
        return _FAMILY_SPECS[key]
    except KeyError as exc:
        known = ", ".join(sorted(_FAMILY_SPECS))
        raise KeyError(f"unknown crypto-oracle family {family!r}; known: {known}") from exc


@lru_cache(maxsize=None)
def get_crypto_oracle_coordinates(family: str) -> tuple[CryptoOracleCoordinate, ...]:
    """Load and fully verify all scalar coordinates of ``family``."""

    spec = get_crypto_oracle_family_spec(family)
    if not spec.supported:
        raise UnsupportedCryptoOracleError(spec)

    if spec.family != "AES":  # Defensive: general support implies reviewed access.
        raise UnsupportedCryptoOracleError(spec)

    coordinates = _build_coordinates(spec)
    verify_crypto_oracle_family(spec.family, coordinates=coordinates)
    return coordinates


def get_crypto_oracle_coordinate(family: str, output_bit: int) -> CryptoOracleCoordinate:
    coordinates = get_crypto_oracle_coordinates(family)
    if not 0 <= output_bit < len(coordinates):
        raise ValueError(f"output_bit={output_bit} is outside [0, {len(coordinates)})")
    return coordinates[output_bit]


@lru_cache(maxsize=None)
def get_crypto_holdout_oracle_coordinates(
    family: str,
    *,
    family_exclusion_label: str | None = None,
) -> tuple[CryptoOracleCoordinate, ...]:
    """Load a frozen external-family hold-out after explicit acknowledgement.

    The general loader intentionally rejects these families.  Requiring the
    registered label makes an evaluation caller's exclusion contract visible
    in code and prevents accidental use by existing training/calibration paths.
    """

    spec = get_crypto_oracle_family_spec(family)
    _assert_holdout_access(spec, family_exclusion_label)
    coordinates = _build_coordinates(spec)
    verify_crypto_holdout_oracle_family(
        spec.family,
        coordinates=coordinates,
        family_exclusion_label=family_exclusion_label,
    )
    return coordinates


def get_crypto_holdout_oracle_coordinate(
    family: str,
    output_bit: int,
    *,
    family_exclusion_label: str | None = None,
) -> CryptoOracleCoordinate:
    coordinates = get_crypto_holdout_oracle_coordinates(
        family,
        family_exclusion_label=family_exclusion_label,
    )
    if not 0 <= output_bit < len(coordinates):
        raise ValueError(f"output_bit={output_bit} is outside [0, {len(coordinates)})")
    return coordinates[output_bit]


def reconstruct_substitution_value(
    coordinates: Iterable[CryptoOracleCoordinate], x: int
) -> int:
    """Recombine LSB-indexed scalar coordinates into one vector output."""

    items = tuple(coordinates)
    if not items:
        raise ValueError("at least one coordinate is required")
    return sum(coordinate.evaluate(x) << coordinate.output_bit for coordinate in items)


def verify_crypto_oracle_family(
    family: str,
    *,
    coordinates: Iterable[CryptoOracleCoordinate] | None = None,
) -> bool:
    """Exhaustively verify hashes and all vector outputs for a supported family."""

    spec = get_crypto_oracle_family_spec(family)
    if not spec.supported:
        raise UnsupportedCryptoOracleError(spec)
    items = tuple(coordinates) if coordinates is not None else get_crypto_oracle_coordinates(family)
    return _verify_audited_family(spec, items)


def verify_crypto_holdout_oracle_family(
    family: str,
    *,
    coordinates: Iterable[CryptoOracleCoordinate] | None = None,
    family_exclusion_label: str | None = None,
) -> bool:
    """Exhaustively verify one labelled, evaluation-only crypto hold-out."""

    spec = get_crypto_oracle_family_spec(family)
    _assert_holdout_access(spec, family_exclusion_label)
    items = (
        tuple(coordinates)
        if coordinates is not None
        else get_crypto_holdout_oracle_coordinates(
            family,
            family_exclusion_label=family_exclusion_label,
        )
    )
    return _verify_audited_family(spec, items)


def _build_coordinates(spec: CryptoOracleFamilySpec) -> tuple[CryptoOracleCoordinate, ...]:
    return tuple(
        CryptoOracleCoordinate(
            family=spec.family,
            operation=spec.operation,
            output_bit=output_bit,
            input_width=spec.input_width,
            output_width=spec.output_width,
            bit_order=spec.bit_order,
            source=spec.source,
            provenance=spec.provenance,
            truth_table_sha256=_coordinate_sha256(spec.family, output_bit),
            boolean_function=BooleanFunction(
                spec.input_width,
                _audited_coordinate_truth_table(spec.family, output_bit),
            ),
            benchmark_partition=spec.benchmark_partition,
            training_access_allowed=spec.training_access_allowed,
            family_exclusion_label=spec.family_exclusion_label,
            vector_truth_table_sha256=spec.vector_truth_table_sha256,
        )
        for output_bit in range(spec.output_width)
    )


def _verify_audited_family(
    spec: CryptoOracleFamilySpec,
    items: tuple[CryptoOracleCoordinate, ...],
) -> bool:
    if len(items) != spec.output_width:
        raise CryptoOracleVerificationError(
            f"{spec.family} requires {spec.output_width} coordinates, got {len(items)}"
        )
    if tuple(coordinate.output_bit for coordinate in items) != tuple(range(spec.output_width)):
        raise CryptoOracleVerificationError("coordinates must appear once in LSB-to-MSB order")
    for coordinate in items:
        if coordinate.family != spec.family:
            raise CryptoOracleVerificationError("mixed-family coordinate collection")
        coordinate.assert_valid()

    outputs: list[int] = []
    for x in range(1 << spec.input_width):
        reconstructed = reconstruct_substitution_value(items, x)
        expected = _evaluate_audited_substitution(spec.family, x)
        if reconstructed != expected:
            raise CryptoOracleVerificationError(
                f"{spec.family} vector mismatch at input 0x{x:x}: "
                f"expected 0x{expected:x}, got 0x{reconstructed:x}"
            )
        outputs.append(reconstructed)

    if spec.vector_truth_table_sha256 is not None:
        actual_vector_sha = hashlib.sha256(bytes(outputs)).hexdigest()
        if actual_vector_sha != spec.vector_truth_table_sha256:
            raise CryptoOracleVerificationError(
                f"{spec.family} vector-table SHA-256 mismatch: expected "
                f"{spec.vector_truth_table_sha256}, got {actual_vector_sha}"
            )

    if spec.holdout_evaluation_supported and len(set(outputs)) != len(outputs):
        raise CryptoOracleVerificationError(f"{spec.family} forward S-box is not bijective")

    for x, expected in _FAMILY_ANCHORS[spec.family].items():
        if outputs[x] != expected:
            raise CryptoOracleVerificationError(
                f"{spec.family} source-table anchor mismatch: "
                f"S({x:#04x}) != {expected:#04x}"
            )
    return True


def _normalise_family(family: str) -> str:
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string")
    return family.strip().upper().replace("-", "")


def _assert_holdout_access(
    spec: CryptoOracleFamilySpec,
    family_exclusion_label: str | None,
) -> None:
    if not spec.holdout_evaluation_supported:
        if not spec.supported:
            raise UnsupportedCryptoOracleError(spec)
        raise CryptoOracleHoldoutAccessError(
            f"{spec.family} is a development family, not an external-family hold-out"
        )
    if family_exclusion_label != spec.family_exclusion_label:
        raise CryptoOracleHoldoutAccessError(
            f"{spec.family} hold-out access requires family_exclusion_label="
            f"{spec.family_exclusion_label!r}; the family must remain excluded "
            "from training, calibration, and model selection"
        )


def _coordinate_sha256(family: str, output_bit: int) -> str:
    spec = get_crypto_oracle_family_spec(family)
    try:
        hashes = _FAMILY_COORDINATE_SHA256[spec.family]
    except KeyError as exc:
        raise UnsupportedCryptoOracleError(spec) from exc
    if not 0 <= output_bit < spec.output_width:
        raise ValueError(f"output_bit={output_bit} is outside [0, {spec.output_width})")
    if len(hashes) != spec.output_width:
        raise CryptoOracleVerificationError(
            f"{spec.family} coordinate-hash count differs from its output width"
        )
    return hashes[output_bit]


def _coordinate_truth_table(family: str, output_bit: int) -> int:
    spec = get_crypto_oracle_family_spec(family)
    if not spec.supported:
        raise UnsupportedCryptoOracleError(spec)
    return _audited_coordinate_truth_table(spec.family, output_bit)


def _audited_coordinate_truth_table(family: str, output_bit: int) -> int:
    spec = get_crypto_oracle_family_spec(family)
    _coordinate_sha256(spec.family, output_bit)
    if not 0 <= output_bit < spec.output_width:
        raise ValueError(f"output_bit={output_bit} is outside [0, {spec.output_width})")
    return sum(
        ((_evaluate_audited_substitution(spec.family, x) >> output_bit) & 1) << x
        for x in range(1 << spec.input_width)
    )


def _evaluate_substitution(family: str, x: int) -> int:
    spec = get_crypto_oracle_family_spec(family)
    if not spec.supported:
        raise UnsupportedCryptoOracleError(spec)
    return _evaluate_audited_substitution(spec.family, x)


def _evaluate_audited_substitution(family: str, x: int) -> int:
    spec = get_crypto_oracle_family_spec(family)
    if not 0 <= x < (1 << spec.input_width):
        raise ValueError(f"input x={x} is outside the {spec.input_width}-bit domain")
    if spec.family == "AES":
        return _aes_sbox_byte(x)
    if spec.family == "ASCON":
        return _ASCON_FORWARD_SBOX[x]
    if spec.family == "PRESENT":
        return _PRESENT_FORWARD_SBOX[x]
    raise UnsupportedCryptoOracleError(spec)


def _aes_sbox_byte(x: int) -> int:
    """Compute the FIPS 197 forward S-box from its field/affine definition."""

    if not 0 <= x <= 0xFF:
        raise ValueError("AES S-box input must be one byte")
    inverse = _gf256_pow(x, 254) if x else 0
    return (
        inverse
        ^ _rotate_left_byte(inverse, 1)
        ^ _rotate_left_byte(inverse, 2)
        ^ _rotate_left_byte(inverse, 3)
        ^ _rotate_left_byte(inverse, 4)
        ^ 0x63
    )


def _gf256_pow(base: int, exponent: int) -> int:
    result = 1
    while exponent:
        if exponent & 1:
            result = _gf256_multiply(result, base)
        base = _gf256_multiply(base, base)
        exponent >>= 1
    return result


def _gf256_multiply(a: int, b: int) -> int:
    """Multiply modulo x^8 + x^4 + x^3 + x + 1 (FIPS polynomial)."""

    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        high_bit = a & 0x80
        a = (a << 1) & 0xFF
        if high_bit:
            a ^= 0x1B
        b >>= 1
    return result


def _rotate_left_byte(value: int, amount: int) -> int:
    return ((value << amount) | (value >> (8 - amount))) & 0xFF
