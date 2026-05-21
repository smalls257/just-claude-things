"""Smoke test — ensures pytest discovers the engine package."""
import convention_scan


def test_package_importable():
    assert hasattr(convention_scan, "__name__")
    assert convention_scan.__name__ == "convention_scan"
