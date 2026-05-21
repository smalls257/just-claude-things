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
