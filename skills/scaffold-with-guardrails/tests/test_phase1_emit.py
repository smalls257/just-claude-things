"""Smoke tests for phase1_emit.py.

Heavyweight tests (dotnet build, semgrep) live in the bats e2e gate.
These pytest tests just verify the emitter's structure and its extraction
of the canonical Program.cs body from scaffold.md — without invoking dotnet.
"""
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))


def test_phase1_emit_module_importable():
    """Emitter relies on `dotnet new`. This test verifies the module imports
    cleanly and exposes the expected callables — we don't actually invoke
    emit() (that needs a real dotnet SDK and ~60s)."""
    import phase1_emit  # noqa: PLC0415

    assert callable(phase1_emit.emit)
    assert callable(phase1_emit._extract_canonical_program_cs)


def test_phase1_emit_extracts_program_cs_with_markers():
    """The canonical Program.cs extracted from scaffold.md must contain the
    convention markers baked in during Task 9 (post-X2 fix).

    If scaffold.md drifts and someone removes a marker or renames the block,
    this test catches it before the e2e bats gate has to run dotnet build to
    find out.
    """
    import phase1_emit  # noqa: PLC0415

    body = phase1_emit._extract_canonical_program_cs()
    for layer in ("logging", "observability", "auth", "data", "http-outbound"):
        assert f"// {{{{CONVENTION:{layer}}}}}" in body, (
            f"canonical Program.cs body missing builder-time marker for '{layer}'"
        )
    assert "// {{CONVENTION:middleware}}" in body, (
        "canonical Program.cs body missing middleware marker"
    )


def test_phase1_emit_program_cs_has_database_options_binding():
    """Program.cs must bind DatabaseOptions so emit() can write a matching
    DatabaseOptions.cs that actually compiles.  If the canonical block stops
    referencing DatabaseOptions, this fires before a full dotnet build is needed.
    """
    import phase1_emit  # noqa: PLC0415

    body = phase1_emit._extract_canonical_program_cs()
    assert "DatabaseOptions" in body, (
        "canonical Program.cs must reference DatabaseOptions (ValidateOnStart triad)"
    )
    assert "AddOptions<DatabaseOptions>" in body or "DatabaseOptions.SectionName" in body, (
        "canonical Program.cs must use the AddOptions<DatabaseOptions>().Bind().ValidateOnStart() triad"
    )


def test_phase1_emit_skill_root_templates_exist():
    """The emitter derives SKILL_ROOT from __file__; the templates it copies
    must all be present. Missing any one would cause a silent FileNotFoundError
    on emit() — verify them statically so the failure is caught early with a
    clear message (not a cryptic OSError mid-run).
    """
    import phase1_emit  # noqa: PLC0415

    for fname in (
        "global.json",
        "Directory.Build.props",
        "Directory.Packages.props",
        "coverlet.runsettings",
        "gitignore",
        "scaffold.md",
    ):
        p = phase1_emit.TEMPLATES / fname
        assert p.exists(), f"Required template file missing: {p}"
