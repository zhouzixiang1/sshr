from __future__ import annotations

import hashlib

import pytest

from src.benchmarks.crypto_oracles import (
    CANONICAL_TRUTH_TABLE_ENCODING,
    CryptoOracleVerificationError,
    UnsupportedCryptoOracleError,
    available_crypto_oracle_families,
    get_crypto_oracle_coordinate,
    get_crypto_oracle_coordinates,
    get_crypto_oracle_family_spec,
    reconstruct_substitution_value,
    verify_crypto_oracle_family,
)


EXPECTED_AES_COORDINATE_SHA256 = (
    "1e9824b17f9c4881346ee92a37d0ff4efc5d44cadf9c1e558f78ae190d662a05",
    "ac7c564edb9b2693a5ecf17f055281babf6b97433394169f5448d5af6fc950c2",
    "8bb9df77d8e16f65c91cc9fce1b1368b9f23332f6eb41419cc7fbd0ce39e2f4c",
    "f1993d2d5719218ea7fe15a97b9c7f977c03863e923def799fc948f669bc613f",
    "793b6367e6dd9217673ed5a6aa0bda6faa78da85239f47061ffb470e41c6151f",
    "25bff3db1032e49ddfc2d9bc9d5d48c985b1779930865e47f3780ff950984994",
    "3e1685e8e7f2b9529edafc5fd6d96e1174d858091a180d379cd89147ec286256",
    "20b7cdfce4e67e25cb3b5dc4de26118f9b048c02981fa89ad1ceb54bd5274dd5",
)


def test_aes_exposes_eight_auditable_boolean_functions() -> None:
    coordinates = get_crypto_oracle_coordinates("aes")

    assert len(coordinates) == 8
    assert [coordinate.output_bit for coordinate in coordinates] == list(range(8))
    assert all(coordinate.family == "AES" for coordinate in coordinates)
    assert all(coordinate.boolean_function.n == 8 for coordinate in coordinates)
    assert [coordinate.truth_table_sha256 for coordinate in coordinates] == list(
        EXPECTED_AES_COORDINATE_SHA256
    )
    assert all("FIPS 197" in coordinate.source for coordinate in coordinates)
    assert all("coordinate 0 is the output LSB" in coordinate.bit_order for coordinate in coordinates)


def test_aes_full_truth_tables_and_vector_outputs_are_verified() -> None:
    coordinates = get_crypto_oracle_coordinates("AES")

    assert verify_crypto_oracle_family("AES")
    for coordinate in coordinates:
        coordinate.assert_valid()
        assert len(coordinate.canonical_truth_table_bytes()) == 32
        assert hashlib.sha256(coordinate.canonical_truth_table_bytes()).hexdigest() == (
            coordinate.truth_table_sha256
        )

    # Full-domain reconstruction checks the coordinate convention, not merely
    # isolated example vectors.  A bijective result is required for the S-box.
    outputs = [reconstruct_substitution_value(coordinates, x) for x in range(256)]
    assert len(set(outputs)) == 256
    assert outputs[0x00] == 0x63
    assert outputs[0x53] == 0xED
    assert outputs[0xFF] == 0x16


def test_scalar_coordinate_matches_reconstructed_output_bit() -> None:
    coordinates = get_crypto_oracle_coordinates("AES")
    for bit in range(8):
        coordinate = get_crypto_oracle_coordinate("AES", bit)
        for x in range(256):
            value = reconstruct_substitution_value(coordinates, x)
            assert coordinate.evaluate(x) == ((value >> bit) & 1)


def test_family_specs_make_unsupported_provenance_explicit() -> None:
    specs = {spec.family: spec for spec in available_crypto_oracle_families()}
    assert set(specs) == {"AES", "SM4", "PRESENT", "ASCON"}
    assert specs["AES"].supported

    for family in ("SM4", "PRESENT", "ASCON"):
        spec = get_crypto_oracle_family_spec(family)
        assert not spec.supported
        assert spec.unsupported_reason
        assert spec.source.startswith(("GB/T", "Bogdanov", "NIST"))
        with pytest.raises(UnsupportedCryptoOracleError) as error:
            get_crypto_oracle_coordinates(family)
        assert error.value.spec == spec
        assert "unsupported" in str(error.value)


def test_tampered_complete_truth_table_fails_validation() -> None:
    coordinate = get_crypto_oracle_coordinate("AES", 0)
    original = coordinate.boolean_function.truth_table
    coordinate.boolean_function.truth_table ^= 1 << 137
    try:
        with pytest.raises(CryptoOracleVerificationError, match="complete truth table"):
            coordinate.assert_valid()
    finally:
        coordinate.boolean_function.truth_table = original


def test_invalid_family_bit_and_input_are_rejected() -> None:
    with pytest.raises(KeyError, match="unknown crypto-oracle family"):
        get_crypto_oracle_coordinates("unknown")
    with pytest.raises(ValueError, match="output_bit"):
        get_crypto_oracle_coordinate("AES", 8)
    with pytest.raises(ValueError, match="outside"):
        get_crypto_oracle_coordinate("AES", 0).evaluate(256)
    assert "little-endian" in CANONICAL_TRUTH_TABLE_ENCODING
