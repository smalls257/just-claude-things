from pathlib import Path
from convention_scan.card_renderer import render_card, CardInput
from convention_scan.package_resolver import Package
from convention_scan.extractor import Region


def test_card_matches_golden_snapshot():
    inp = CardInput(
        detector_id="auth-jwt-bearer",
        display="JWT bearer auth",
        source_path="src/Auth/JwtExtensions.cs",
        region=Region(file_path="src/Auth/JwtExtensions.cs", start_line=12, end_line=45,
                      text="public static class JwtExtensions\n{\n    // ...\n}"),
        packages=[Package("Microsoft.AspNetCore.Authentication.JwtBearer", "8.0.5")],
        unresolved=["Mystery.Lib"],
        conflict_notes=["overrides http-token-handler at L50-L55"],
    )
    out = render_card(inp)
    golden = (Path(__file__).parent / "fixtures" / "card_golden.txt").read_text()
    assert out == golden, f"\n--- got ---\n{out}\n--- want ---\n{golden}"


def test_card_with_no_packages_or_conflicts():
    inp = CardInput(
        detector_id="logging-serilog",
        display="Serilog",
        source_path="src/Logging/SerilogExt.cs",
        region=Region("src/Logging/SerilogExt.cs", 1, 5, "// snippet"),
        packages=[],
        unresolved=[],
        conflict_notes=[],
    )
    out = render_card(inp)
    assert "PACKAGES" in out
    assert "(none)" in out
    assert "CONFLICTS" not in out  # only shown when present
