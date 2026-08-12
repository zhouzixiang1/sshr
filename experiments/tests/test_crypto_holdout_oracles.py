from __future__ import annotations

import hashlib

import pytest

from src.benchmarks.crypto_oracles import (
    CANONICAL_SUBSTITUTION_TABLE_ENCODING,
    CRYPTO_HOLDOUT_EXCLUSION_LABEL,
    CryptoOracleHoldoutAccessError,
    CryptoOracleVerificationError,
    UnsupportedCryptoOracleError,
    available_crypto_holdout_families,
    get_crypto_holdout_oracle_coordinate,
    get_crypto_holdout_oracle_coordinates,
    get_crypto_oracle_coordinates,
    get_crypto_oracle_family_spec,
    reconstruct_substitution_value,
    verify_crypto_holdout_oracle_family,
)


# Independent source transcriptions used by the tests.  These literals do not
# import the implementation's private tables, so every input is checked across
# the public coordinate API against the cited primary source.
NIST_SP_800_232_ASCON_SBOX = (
    0x04, 0x0B, 0x1F, 0x14, 0x1A, 0x15, 0x09, 0x02,
    0x1B, 0x05, 0x08, 0x12, 0x1D, 0x03, 0x06, 0x1C,
    0x1E, 0x13, 0x07, 0x0E, 0x00, 0x0D, 0x11, 0x18,
    0x10, 0x0C, 0x01, 0x19, 0x16, 0x0A, 0x0F, 0x17,
)

CHES_2007_PRESENT_SBOX = (
    0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD,
    0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2,
)

SOURCE_TABLES = {
    "ASCON": NIST_SP_800_232_ASCON_SBOX,
    "PRESENT": CHES_2007_PRESENT_SBOX,
}

EXPECTED_VECTOR_SHA256 = {
    "ASCON": "2f5f6885b68f1f6fafed2be6ab614346c48a8528b51f7b4bdf4a0c1b609df97d",
    "PRESENT": "8e63f8c394a1ee38340d3be6e9a33b7b8c86d752498720dc80c223b02562e959",
}

EXPECTED_COORDINATE_SHA256 = {
    "ASCON": (
        "2629f646e4e48c89d27a2fa15d806db1bb59721ec004c19415ae59ac2e72b48f",
        "80713771a1b2e8920d65ad892d27c8e2e8aba5874d587d4b24cf6cf074784ce7",
        "8a20f3428448f5e2bd8da3e9559cb7a3ae091759f4516e80cc65b8f616d6112d",
        "e511dae0b4fd7953dd2e564003d3ef3b86f560ece76e073391bc525e9a45a97d",
        "cac32e76240366ea1129102f26003cec2121742a1742f912da081106857743be",
    ),
    "PRESENT": (
        "4e970e8b7f2fb52a79c55db9c9dfaa44658eb64fd37e5ed9d3440a0905803e71",
        "b3311960f4cf52c6db4d5cbb9cf0d47915e3666175b91f3eb4e08bad9932865a",
        "651dfc9a16350c391f9b9f1e02afd433f951246a6fce4691301e3c463266bf71",
        "3def4ec7c4026dc026162cdf2279a16a8e9e9f5efdde0521ebbfd91f3d5fec83",
    ),
}


def _load_holdout(family: str):
    return get_crypto_holdout_oracle_coordinates(
        family,
        family_exclusion_label=CRYPTO_HOLDOUT_EXCLUSION_LABEL,
    )


def _anf_monomial_masks(values: list[int], width: int) -> tuple[int, ...]:
    coefficients = list(values)
    for bit in range(width):
        for mask in range(1 << width):
            if mask & (1 << bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << bit)]
    return tuple(mask for mask, coefficient in enumerate(coefficients) if coefficient)


def _maximum_ddt_entry(table: tuple[int, ...]) -> int:
    return max(
        sum((table[x] ^ table[x ^ input_difference]) == output_difference for x in range(len(table)))
        for input_difference in range(1, len(table))
        for output_difference in range(len(table))
    )


def _maximum_walsh_magnitude(table: tuple[int, ...], width: int) -> int:
    return max(
        abs(
            sum(
                1
                if ((input_mask & x).bit_count() ^ (output_mask & table[x]).bit_count()) & 1 == 0
                else -1
                for x in range(1 << width)
            )
        )
        for input_mask in range(1, 1 << width)
        for output_mask in range(1, 1 << width)
    )


def test_holdout_partition_is_explicit_and_general_loader_stays_blocked() -> None:
    specs = {spec.family: spec for spec in available_crypto_holdout_families()}
    assert set(specs) == {"ASCON", "PRESENT"}

    for family, spec in specs.items():
        assert not spec.supported
        assert spec.holdout_evaluation_supported
        assert not spec.training_access_allowed
        assert spec.benchmark_partition == "external_crypto_family_holdout"
        assert spec.family_exclusion_label == CRYPTO_HOLDOUT_EXCLUSION_LABEL
        assert spec.vector_truth_table_sha256 == EXPECTED_VECTOR_SHA256[family]

        with pytest.raises(UnsupportedCryptoOracleError):
            get_crypto_oracle_coordinates(family)
        with pytest.raises(CryptoOracleHoldoutAccessError, match="excluded"):
            get_crypto_holdout_oracle_coordinates(family)
        with pytest.raises(CryptoOracleHoldoutAccessError, match="excluded"):
            get_crypto_holdout_oracle_coordinates(
                family,
                family_exclusion_label="wrong_partition",
            )


@pytest.mark.parametrize("family", ["ASCON", "PRESENT"])
def test_all_inputs_reconstruct_the_independent_primary_source_table(family: str) -> None:
    table = SOURCE_TABLES[family]
    coordinates = _load_holdout(family)
    spec = get_crypto_oracle_family_spec(family)

    assert len(coordinates) == spec.output_width
    assert tuple(coordinate.output_bit for coordinate in coordinates) == tuple(
        range(spec.output_width)
    )
    assert [reconstruct_substitution_value(coordinates, x) for x in range(len(table))] == list(table)
    assert len(set(table)) == len(table)
    assert all(table[x] != x for x in range(len(table)))
    assert hashlib.sha256(bytes(table)).hexdigest() == EXPECTED_VECTOR_SHA256[family]
    assert "one unsigned byte" in CANONICAL_SUBSTITUTION_TABLE_ENCODING
    assert verify_crypto_holdout_oracle_family(
        family,
        coordinates=coordinates,
        family_exclusion_label=CRYPTO_HOLDOUT_EXCLUSION_LABEL,
    )


@pytest.mark.parametrize("family", ["ASCON", "PRESENT"])
def test_each_boolean_function_has_lsb_coordinate_semantics_and_frozen_hash(
    family: str,
) -> None:
    table = SOURCE_TABLES[family]
    coordinates = _load_holdout(family)

    assert tuple(coordinate.truth_table_sha256 for coordinate in coordinates) == (
        EXPECTED_COORDINATE_SHA256[family]
    )
    for output_bit, coordinate in enumerate(coordinates):
        assert coordinate.boolean_function.n == len(table).bit_length() - 1
        assert not coordinate.training_access_allowed
        assert coordinate.family_exclusion_label == CRYPTO_HOLDOUT_EXCLUSION_LABEL
        assert all(
            coordinate.evaluate(x) == ((table[x] >> output_bit) & 1)
            for x in range(len(table))
        )
        assert hashlib.sha256(coordinate.canonical_truth_table_bytes()).hexdigest() == (
            EXPECTED_COORDINATE_SHA256[family][output_bit]
        )
        coordinate.assert_valid()


def test_ascon_nist_bit_mapping_anchors_and_coordinate_equations() -> None:
    coordinates = _load_holdout("ASCON")
    reconstructed = [reconstruct_substitution_value(coordinates, x) for x in range(32)]
    assert {x: reconstructed[x] for x in (0x00, 0x01, 0x14, 0x1F)} == {
        0x00: 0x04,
        0x01: 0x0B,
        0x14: 0x00,
        0x1F: 0x17,
    }

    # LSB-indexed coordinate ANFs are NIST y4, y3, ..., y0 after the explicit
    # x_i <-> canonical bit (4-i) mapping recorded in the family provenance.
    expected_anf_masks = (
        (1, 2, 8, 9, 24),
        (1, 2, 4, 8, 16, 17, 18),
        (0, 1, 3, 4, 8),
        (1, 2, 4, 6, 8, 10, 12, 16),
        (2, 4, 8, 9, 12, 16, 24),
    )
    for output_bit, expected in enumerate(expected_anf_masks):
        values = [(value >> output_bit) & 1 for value in reconstructed]
        masks = _anf_monomial_masks(values, 5)
        assert masks == expected
        assert max(mask.bit_count() for mask in masks) == 2

    # Derived exhaustive property of the frozen standard table.
    assert _maximum_ddt_entry(NIST_SP_800_232_ASCON_SBOX) == 8


def test_present_original_paper_anchors_and_design_properties() -> None:
    coordinates = _load_holdout("PRESENT")
    reconstructed = [reconstruct_substitution_value(coordinates, x) for x in range(16)]
    assert {x: reconstructed[x] for x in (0x0, 0x1, 0x5, 0xF)} == {
        0x0: 0xC,
        0x1: 0x5,
        0x5: 0x0,
        0xF: 0x2,
    }

    # Section 4 of the original paper specifies differential bound 4, no
    # one-bit-to-one-bit differential, and maximum Walsh magnitude 8.
    assert _maximum_ddt_entry(CHES_2007_PRESENT_SBOX) == 4
    for input_difference in (1, 2, 4, 8):
        for x in range(16):
            output_difference = reconstructed[x] ^ reconstructed[x ^ input_difference]
            assert output_difference.bit_count() != 1
    assert _maximum_walsh_magnitude(CHES_2007_PRESENT_SBOX, 4) == 8


def test_single_coordinate_api_and_tamper_detection() -> None:
    coordinate = get_crypto_holdout_oracle_coordinate(
        "ASCON",
        0,
        family_exclusion_label=CRYPTO_HOLDOUT_EXCLUSION_LABEL,
    )
    assert all(
        coordinate.evaluate(x) == (NIST_SP_800_232_ASCON_SBOX[x] & 1)
        for x in range(32)
    )

    original = coordinate.boolean_function.truth_table
    coordinate.boolean_function.truth_table ^= 1 << 29
    try:
        with pytest.raises(CryptoOracleVerificationError, match="complete truth table"):
            coordinate.assert_valid()
    finally:
        coordinate.boolean_function.truth_table = original
