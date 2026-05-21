import pytest
from pathlib import Path
from convention_scan.extractor import extract, ExtractError


CS_METHOD_IN_EXT = """
namespace App.Auth;

public static class JwtExtensions
{
    public static IServiceCollection AddJwtAuth(this IServiceCollection s)
    {
        s.AddAuthentication().AddJwtBearer(o => { o.Authority = "x"; });
        return s;
    }

    public static void Other() {}
}
"""

CS_TRUNCATED = """
public static class Bad
{
    public static void Hit()
    {
        AddJwtBearer();
"""

JSON_APPSETTINGS = """
{
  "Logging": { "LogLevel": { "Default": "Information" } },
  "Jwt": { "Authority": "https://example.com", "Audience": "api" }
}
"""

PROPS = """
<Project>
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
"""


def write(tmp_path, name, body):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def test_enclosing_method_or_extension_returns_class_when_static_ext(tmp_path):
    p = write(tmp_path, "J.cs", CS_METHOD_IN_EXT)
    # line 8 = body of AddJwtAuth (the AddJwtBearer call)
    region = extract(p, 8, "enclosing-method-or-extension")
    assert "public static class JwtExtensions" in region.text
    assert "Other()" in region.text
    assert region.start_line <= 8 <= region.end_line


def test_enclosing_method_returns_just_method(tmp_path):
    p = write(tmp_path, "J.cs", CS_METHOD_IN_EXT)
    region = extract(p, 8, "enclosing-method")
    assert "AddJwtAuth" in region.text
    assert "Other()" not in region.text


def test_enclosing_class_returns_whole_class(tmp_path):
    p = write(tmp_path, "J.cs", CS_METHOD_IN_EXT)
    region = extract(p, 8, "enclosing-class")
    assert "class JwtExtensions" in region.text
    assert "Other()" in region.text


def test_truncated_file_raises(tmp_path):
    p = write(tmp_path, "B.cs", CS_TRUNCATED)
    with pytest.raises(ExtractError, match="EXTRACT_FAILED"):
        extract(p, 5, "enclosing-method")


def test_appsettings_section_returns_json_object(tmp_path):
    p = write(tmp_path, "appsettings.json", JSON_APPSETTINGS)
    # line 4 = the "Jwt" key line
    region = extract(p, 4, "appsettings-section")
    assert "Authority" in region.text
    assert "Logging" not in region.text


def test_props_property_returns_property_item(tmp_path):
    p = write(tmp_path, "Directory.Build.props", PROPS)
    # line 4 = <TargetFramework>net9.0</TargetFramework>
    region = extract(p, 4, "props-property")
    assert "<TargetFramework>net9.0</TargetFramework>" in region.text


def test_line_range_fallback(tmp_path):
    body = "\n".join(f"line{i}" for i in range(20))
    p = write(tmp_path, "f.txt", body)
    region = extract(p, 10, "line-range:3")
    # 3 above + 1 hit + 3 below = 7 lines → end-start == 6
    assert region.end_line - region.start_line == 6


CS_WITH_FILE_USINGS = """using Serilog;
using Foo.Bar;  // inline comment also tolerated

namespace App.Logging;

public static class SerilogConfig
{
    public static void Configure(WebApplicationBuilder builder)
    {
        Log.Logger = new LoggerConfiguration().CreateLogger();
    }
}
"""


def test_extract_preserves_file_level_usings_in_snippet(tmp_path):
    """Bug A root cause: extractor must include file-level using directives
    in the extracted snippet so the grafter can preserve them in the host
    file. Without this, the grafter's preservation logic never sees usings
    in the real convention-scan flow."""
    p = write(tmp_path, "Log.cs", CS_WITH_FILE_USINGS)
    # hit line 6 = body of Configure (the Log.Logger assignment is on line 9)
    region = extract(p, 6, "enclosing-method-or-extension")
    # File-level usings preserved at top of snippet text
    assert "using Serilog;" in region.text
    assert "using Foo.Bar;" in region.text
    # Class block still present
    assert "public static class SerilogConfig" in region.text
    # Source line numbers anchor at the class block, not the using line
    assert region.start_line >= 6


def test_extract_handles_file_with_no_usings(tmp_path):
    """Files without file-level usings still extract correctly — the
    collect helper returns empty and the snippet shape is unchanged."""
    body = "namespace App.X;\n\npublic class Y\n{\n    public void Do() {}\n}\n"
    p = write(tmp_path, "Y.cs", body)
    region = extract(p, 5, "enclosing-method")
    assert "public void Do()" in region.text
    # No spurious blank lines or `using` lines at top
    assert not region.text.lstrip().startswith("using ")


def test_extract_stops_using_collection_at_first_non_using(tmp_path):
    """Once the file leaves the using preamble (namespace, blank, class),
    further `using` directives inside the body are NOT prepended to the
    snippet (they would land inside the body where they were captured
    naturally by the body extraction)."""
    body = """using A;

namespace App;

public class X
{
    public void Do()
    {
        // using B; is a comment, not a directive
    }
}
"""
    p = write(tmp_path, "X.cs", body)
    region = extract(p, 7, "enclosing-method")
    assert "using A;" in region.text  # file-level preamble preserved
    # The body itself does not contain a spurious second "using A;"
    assert region.text.count("using A;") == 1


def test_extract_collect_file_usings_helper_direct():
    """Direct test of the collect helper."""
    from convention_scan.extractor import _collect_file_usings
    body = "using A;\nusing B;  // comment\n\nnamespace X;\n\nclass Y {}\n"
    assert _collect_file_usings(body) == ["using A;", "using B;  // comment"]

    # File with no usings
    assert _collect_file_usings("namespace X;\nclass Y {}\n") == []

    # File where the first line is a comment then usings — the helper
    # tolerates leading blank-or-comment lines? No: stops on first non-blank-non-using.
    assert _collect_file_usings("// header comment\nusing A;\n") == []
