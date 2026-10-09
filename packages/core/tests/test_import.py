"""Smoke test to verify that kairos_core imports successfully."""

import kairos_core


def test_kairos_core_imports() -> None:
    """Verify that kairos_core package can be imported and exposes version metadata."""
    assert hasattr(kairos_core, "__version__")
    assert kairos_core.__version__ == "0.1.0"
