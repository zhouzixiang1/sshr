"""Cross-module test isolation for release-gated holdout imports."""

from __future__ import annotations

import sys

import pytest


_CRYPTO_MODULE = "src.benchmarks.crypto_oracles"


@pytest.fixture(scope="module", autouse=True)
def _isolate_e5_holdout_import_state(request: pytest.FixtureRequest):
    """Give E5 release-gate tests the fresh-process import state they specify."""

    if request.module.__name__.rsplit(".", 1)[-1] != "test_e5_external_crypto_holdout":
        yield
        return

    prior = {
        name: sys.modules.pop(name)
        for name in list(sys.modules)
        if name == _CRYPTO_MODULE or name.startswith(f"{_CRYPTO_MODULE}.")
    }
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name == _CRYPTO_MODULE or name.startswith(f"{_CRYPTO_MODULE}."):
                sys.modules.pop(name, None)
        sys.modules.update(prior)
