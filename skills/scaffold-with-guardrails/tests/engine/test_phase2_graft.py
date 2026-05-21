import pytest
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase2_graft.py"


def write(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _seed(tmp_path):
    """Seed a target tree shaped like a real scaffold: program at
    src/<App>.Api/Program.cs, staged snippets as `public static class` blocks
    (which is what convention-scan stages today; bug #6 was the inline-blob
    fallback being invalid in top-level Program.cs).
    """
    design = tmp_path / "svc.md"
    design.write_text("""# svc
<module name="core"/>

<conventions reference-repo="r" reference-repo-commit="abc1234" scanned-at="t" engine-version="0.1.0">
  <adopted detector="jwt-bearer" source="src/Auth.cs:L1-L5" staged="staged/jwt-bearer.cs" packages="MS.X:8.0.5"/>
  <dev-named target="flags" source="src/F.cs:L1-L5" staged="staged/dev-flags.cs" adopted="true" packages="LD.SDK:8.0.0"/>
</conventions>
""")
    api_dir = tmp_path / "src" / "Svc.Api"
    api_dir.mkdir(parents=True)
    program = api_dir / "Program.cs"
    program.write_text(
        "var builder = WebApplication.CreateBuilder(args);\n"
        "// {{CONVENTION:auth}}\n"
        "// {{CONVENTION:dev-flags}}\n"
        "// {{CONVENTION:observability}}\n"
        "var app = builder.Build();\n"
        "app.Run();\n"
    )
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "jwt-bearer.cs").write_text(
        "public static class JwtBearerExt\n"
        "{\n"
        "    public static IServiceCollection AddJwtBearer(this IServiceCollection s)\n"
        "    {\n"
        "        return s;\n"
        "    }\n"
        "}\n"
    )
    (staged / "dev-flags.cs").write_text(
        "public static class FlagsExt\n"
        "{\n"
        "    public static IServiceCollection AddFlags(this IServiceCollection s)\n"
        "    {\n"
        "        return s;\n"
        "    }\n"
        "}\n"
    )
    cpm = tmp_path / "Directory.Packages.props"
    cpm.write_text("<Project>\n  <ItemGroup>\n  </ItemGroup>\n</Project>\n")
    return design, program, staged, cpm


def _run(design, program, staged, cpm=None):
    args = ["python3", str(SCRIPT),
            "--design", str(design),
            "--target-program", str(program),
            "--staged-root", str(staged)]
    if cpm:
        args += ["--cpm", str(cpm)]
    return subprocess.run(args, capture_output=True, text=True)


def test_inserts_snippet_with_source_comment(tmp_path):
    design, program, staged, cpm = _seed(tmp_path)
    res = _run(design, program, staged, cpm)
    assert res.returncode == 0, res.stderr
    body = program.read_text()
    # Slot was replaced with a SOURCE attribution + the call line.
    assert "// SOURCE: adopted:jwt-bearer — src/Auth.cs:L1-L5" in body
    assert "{{CONVENTION:auth}}" not in body
    # Extension on IServiceCollection -> builder.Services.AddJwtBearer()
    assert "builder.Services.AddJwtBearer();" in body
    # The class declaration must NOT be inlined into Program.cs (bug #6).
    assert "public static class JwtBearerExt" not in body
    # Host file landed at src/Svc.Api/Auth/JwtBearerExt.cs.
    host = program.parent / "Auth" / "JwtBearerExt.cs"
    assert host.exists()
    assert "public static class JwtBearerExt" in host.read_text()


def test_dev_named_grafted_when_adopted(tmp_path):
    design, program, staged, cpm = _seed(tmp_path)
    res = _run(design, program, staged, cpm)
    body = program.read_text()
    # Dev-named convention is grafted at // {{CONVENTION:dev-flags}}.
    assert "builder.Services.AddFlags();" in body


def test_missing_staged_file_halts(tmp_path):
    design, program, staged, cpm = _seed(tmp_path)
    (staged / "jwt-bearer.cs").unlink()
    res = _run(design, program, staged, cpm)
    assert res.returncode != 0
    assert "MISSING_STAGED" in res.stderr


def test_missing_slot_halts(tmp_path):
    design, program, staged, cpm = _seed(tmp_path)
    program.write_text("var app = WebApplication.CreateBuilder(args).Build();\napp.Run();\n")
    res = _run(design, program, staged, cpm)
    assert res.returncode != 0
    assert "NO_SLOT" in res.stderr


def test_packages_appended_to_cpm(tmp_path):
    design, program, staged, cpm = _seed(tmp_path)
    _run(design, program, staged, cpm)
    body = cpm.read_text()
    assert 'Include="MS.X"' in body and 'Version="8.0.5"' in body
    assert 'Include="LD.SDK"' in body


def test_existing_package_not_duplicated(tmp_path):
    design, program, staged, cpm = _seed(tmp_path)
    cpm.write_text("""<Project>
  <ItemGroup>
    <PackageVersion Include="MS.X" Version="8.0.5"/>
  </ItemGroup>
</Project>
""")
    _run(design, program, staged, cpm)
    body = cpm.read_text()
    assert body.count('Include="MS.X"') == 1


SNIPPET_WITH_USINGS = '''using Serilog;
using Foo.Bar;

public static class SerilogConfig
{
    public static void Configure(WebApplicationBuilder builder)
    {
        Log.Logger = new LoggerConfiguration().CreateLogger();
        builder.Host.UseSerilog();
    }
}
'''


def test_extract_snippet_usings_pulls_top_using_block():
    """Bug A: snippet usings at top of file must be captured for the host file."""
    from phase2_graft import _extract_snippet_usings
    result = _extract_snippet_usings(SNIPPET_WITH_USINGS)
    assert result == ["using Serilog;", "using Foo.Bar;"]


def test_extract_snippet_usings_stops_at_first_non_using():
    """Once a non-using non-blank line appears, the using block is done."""
    from phase2_graft import _extract_snippet_usings
    snippet = '''using A;

namespace Foo;

using B;  // not a top-level using

public class X { }
'''
    result = _extract_snippet_usings(snippet)
    assert result == ["using A;"]


def test_wrap_in_file_merges_snippet_usings_with_defaults():
    """Bug A: host file's `using` block must include snippet usings + defaults,
    deduped, snippet usings first (they are more specific)."""
    from phase2_graft import _wrap_in_file
    out = _wrap_in_file(SNIPPET_WITH_USINGS, "Lib.Api.Logging")
    # Snippet usings present
    assert "using Serilog;" in out
    assert "using Foo.Bar;" in out
    # Defaults still present
    assert "using System;" in out
    assert "using Microsoft.AspNetCore.Builder;" in out
    # No duplicate `using Serilog;` block
    assert out.count("using Serilog;") == 1


def test_wrap_in_file_emits_nuget_todo_for_known_third_party_root():
    """Bug A: when a snippet using names a known third-party root (Serilog,
    MassTransit, MediatR, etc.) emit a `// TODO NUGET: <root>` breadcrumb
    above its using so the dev sees the package gap."""
    from phase2_graft import _wrap_in_file
    out = _wrap_in_file(SNIPPET_WITH_USINGS, "Lib.Api.Logging")
    # The TODO comment lives immediately above `using Serilog;`.
    assert "// TODO NUGET: Serilog" in out
    serilog_idx = out.index("using Serilog;")
    todo_idx = out.index("// TODO NUGET: Serilog")
    assert todo_idx < serilog_idx


def test_ensure_program_using_inserts_after_last_using():
    """Bug A: Program.cs gets the reverse-using for the host namespace.
    Insertion goes after the last `^using ` line at column 0."""
    from phase2_graft import _ensure_program_using
    program = '''using System;
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);
// {{CONVENTION:logging}}
var app = builder.Build();
app.Run();
'''
    out = _ensure_program_using(program, "Lib.Api.Logging")
    lines = out.splitlines()
    # Find the position of the new using
    new_using_idx = next(i for i, l in enumerate(lines) if l == "using Lib.Api.Logging;")
    # Must be after `using Microsoft.AspNetCore.Builder;`
    last_existing_idx = next(i for i, l in enumerate(lines) if l == "using Microsoft.AspNetCore.Builder;")
    assert new_using_idx == last_existing_idx + 1


def test_ensure_program_using_is_idempotent():
    """Bug A: re-running graft must not duplicate the using."""
    from phase2_graft import _ensure_program_using
    program = '''using System;
using Lib.Api.Logging;

var builder = WebApplication.CreateBuilder(args);
'''
    out = _ensure_program_using(program, "Lib.Api.Logging")
    assert out.count("using Lib.Api.Logging;") == 1


def test_ensure_program_using_preserves_crlf_line_endings():
    """Bug A: Windows-checkout Program.cs may use CRLF. The inserted
    using must match the existing usings' line-ending style, not mix LF
    and CRLF."""
    from phase2_graft import _ensure_program_using
    program = "using System;\r\nusing Microsoft.AspNetCore.Builder;\r\n\r\nvar builder = WebApplication.CreateBuilder(args);\r\n"
    out = _ensure_program_using(program, "Lib.Api.Logging")
    # The inserted line should end with CRLF, not LF.
    assert "using Lib.Api.Logging;\r\n" in out
    # No mixed-ending line for the new using.
    assert "using Lib.Api.Logging;\n" not in out.replace("\r\n", "")


def test_extract_snippet_usings_tolerates_inline_comments():
    """Bug A: snippet usings may have trailing `// comment` documentation.
    They must still be captured."""
    from phase2_graft import _extract_snippet_usings
    snippet = '''using Serilog;  // for structured logging
using Foo.Bar;  // utility

public class X { }
'''
    result = _extract_snippet_usings(snippet)
    assert result == [
        "using Serilog;  // for structured logging",
        "using Foo.Bar;  // utility",
    ]


def test_ensure_package_emits_well_formed_indented_xml(tmp_path):
    """Bug X4a: _ensure_package must produce well-indented XML so the
    appended <PackageVersion> sits on its own line before </ItemGroup>,
    not run-on. dotnet build tolerates ugly XML, but linters and humans
    don't.
    """
    from phase2_graft import _ensure_package
    cpm = tmp_path / "Directory.Packages.props"
    cpm.write_text(
        '<Project>\n'
        '  <ItemGroup>\n'
        '    <PackageVersion Include="Existing" Version="1.0.0" />\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    _ensure_package(cpm, "Serilog", "3.1.1")
    body = cpm.read_text()
    # The new <PackageVersion> must sit on its own line, not run-on with </ItemGroup>.
    assert "Serilog" in body
    assert 'Version="3.1.1"' in body
    # No run-on: should not contain `</ItemGroup>` on the same line as the new entry.
    for line in body.splitlines():
        if "Serilog" in line:
            assert "</ItemGroup>" not in line, (
                f"Run-on detected — new PackageVersion sits on same line as </ItemGroup>: {line!r}"
            )


def test_ensure_csproj_reference_adds_packageref_without_version(tmp_path):
    """Bug X4b: graft must add <PackageReference Include="Name" /> to the csproj
    so central package management can resolve the package. The PackageReference
    has no Version attribute — that lives in Directory.Packages.props.
    """
    from phase2_graft import _ensure_csproj_reference
    csproj = tmp_path / "MyApp.Api.csproj"
    csproj.write_text(
        '<Project Sdk="Microsoft.NET.Sdk.Web">\n'
        '  <PropertyGroup>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n'
        '  </PropertyGroup>\n'
        '  <ItemGroup>\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    _ensure_csproj_reference(csproj, "Serilog")
    body = csproj.read_text()
    assert '<PackageReference Include="Serilog"' in body
    # Critical: NO Version attribute on the PackageReference (CPM provides it).
    import re
    m = re.search(r'<PackageReference Include="Serilog"[^/]*/>', body)
    assert m is not None
    assert 'Version=' not in m.group(0), (
        "PackageReference must NOT have Version under central package management"
    )


def test_ensure_csproj_reference_is_idempotent(tmp_path):
    """Bug X4b: re-running graft must not add duplicate <PackageReference> lines."""
    from phase2_graft import _ensure_csproj_reference
    csproj = tmp_path / "MyApp.Api.csproj"
    csproj.write_text(
        '<Project Sdk="Microsoft.NET.Sdk.Web">\n'
        '  <ItemGroup>\n'
        '    <PackageReference Include="Serilog" />\n'
        '  </ItemGroup>\n'
        '</Project>\n'
    )
    _ensure_csproj_reference(csproj, "Serilog")
    body = csproj.read_text()
    assert body.count('Include="Serilog"') == 1


def test_ensure_csproj_reference_creates_itemgroup_if_missing(tmp_path):
    """Bug X4b: csproj without an existing ItemGroup must get one created
    when graft adds the first package reference."""
    from phase2_graft import _ensure_csproj_reference
    csproj = tmp_path / "MyApp.Api.csproj"
    csproj.write_text(
        '<Project Sdk="Microsoft.NET.Sdk.Web">\n'
        '  <PropertyGroup>\n'
        '    <TargetFramework>net9.0</TargetFramework>\n'
        '  </PropertyGroup>\n'
        '</Project>\n'
    )
    _ensure_csproj_reference(csproj, "Serilog")
    body = csproj.read_text()
    assert "<ItemGroup>" in body
    assert '<PackageReference Include="Serilog"' in body
