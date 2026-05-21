import pytest
from pathlib import Path
from convention_scan.package_resolver import resolve_packages


SNIPPET = """
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Company.Auth.Common;
using System.Text;

public static class X
{
    public static void Y() {}
}
"""

CPM = """
<Project>
  <ItemGroup>
    <PackageVersion Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.5" />
    <PackageVersion Include="Company.Auth.Common" Version="2.1.0" />
  </ItemGroup>
</Project>
"""

CSPROJ = """
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" />
    <PackageReference Include="Company.Auth.Common" />
  </ItemGroup>
</Project>
"""


def write(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_resolves_using_directives_to_packages(tmp_path):
    write(tmp_path / "Directory.Packages.props", CPM)
    write(tmp_path / "src" / "App.csproj", CSPROJ)
    pkgs, unresolved = resolve_packages(SNIPPET, source_file=tmp_path / "src" / "Auth.cs", repo_root=tmp_path)
    names = [p.name for p in pkgs]
    assert "Microsoft.AspNetCore.Authentication.JwtBearer" in names
    assert "Company.Auth.Common" in names
    assert all(p.version for p in pkgs)


def test_system_namespaces_ignored(tmp_path):
    write(tmp_path / "Directory.Packages.props", CPM)
    write(tmp_path / "src" / "App.csproj", CSPROJ)
    pkgs, unresolved = resolve_packages(SNIPPET, source_file=tmp_path / "src" / "Auth.cs", repo_root=tmp_path)
    assert all("System" not in p.name for p in pkgs)


def test_unresolved_namespace_surfaced(tmp_path):
    write(tmp_path / "Directory.Packages.props", CPM)
    write(tmp_path / "src" / "App.csproj", CSPROJ)
    snippet = SNIPPET + "\nusing Mystery.Lib;\n"
    pkgs, unresolved = resolve_packages(snippet, source_file=tmp_path / "src" / "Auth.cs", repo_root=tmp_path)
    assert "Mystery.Lib" in unresolved


def test_multi_version_picks_highest(tmp_path, capsys):
    cpm = CPM
    write(tmp_path / "Directory.Packages.props", cpm)
    cpm2 = """
<Project>
  <ItemGroup>
    <PackageVersion Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="9.0.1" />
  </ItemGroup>
</Project>
"""
    write(tmp_path / "sub" / "Directory.Packages.props", cpm2)
    write(tmp_path / "src" / "App.csproj", CSPROJ)
    pkgs, _ = resolve_packages(
        "using Microsoft.AspNetCore.Authentication.JwtBearer;",
        source_file=tmp_path / "src" / "Auth.cs", repo_root=tmp_path,
    )
    versions = [p.version for p in pkgs if p.name == "Microsoft.AspNetCore.Authentication.JwtBearer"]
    assert versions == ["9.0.1"]
    assert "PACKAGE_VERSION_PICK" in capsys.readouterr().err


def test_resolver_picks_up_csproj_pinned_version(tmp_path):
    """Task 8 / Bug X1: reference repos may pin package versions inline in
    csproj `<PackageReference Version="...">` rather than in
    Directory.Packages.props. The resolver must use those versions
    when no .props pin is available.
    """
    csproj = tmp_path / "Reference.Api.csproj"
    csproj.write_text('''<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Serilog" Version="3.1.1" />
    <PackageReference Include="Serilog.AspNetCore" Version="8.0.1" />
  </ItemGroup>
</Project>
''')
    src = tmp_path / "src" / "Reference.Api" / "Logging" / "SerilogConfig.cs"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("using Serilog;\npublic static class X {}\n")
    snippet = "using Serilog;\nusing Serilog.AspNetCore;\npublic class C {}\n"

    packages, unresolved = resolve_packages(snippet, src, tmp_path)
    names = {p.name for p in packages}
    assert "Serilog" in names
    assert "Serilog.AspNetCore" in names
    assert unresolved == []
    # Versions came from csproj, not .props
    by_name = {p.name: p.version for p in packages}
    assert by_name["Serilog"] == "3.1.1"
    assert by_name["Serilog.AspNetCore"] == "8.0.1"


def test_resolver_prefers_props_version_when_both_sources_pin(tmp_path):
    """Directory.Packages.props is the canonical pin source. If both sources
    pin the same package, .props wins. (csproj is fallback for unpinned setups.)"""
    props = tmp_path / "Directory.Packages.props"
    props.write_text('''<Project>
  <ItemGroup>
    <PackageVersion Include="Serilog" Version="4.0.0" />
  </ItemGroup>
</Project>
''')
    csproj = tmp_path / "X.csproj"
    csproj.write_text('''<Project Sdk="Microsoft.NET.Sdk.Web">
  <ItemGroup>
    <PackageReference Include="Serilog" Version="3.1.1" />
  </ItemGroup>
</Project>
''')
    src = tmp_path / "src" / "X.cs"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("using Serilog;\nclass X {}\n")
    snippet = "using Serilog;\nclass C {}\n"

    packages, unresolved = resolve_packages(snippet, src, tmp_path)
    by_name = {p.name: p.version for p in packages}
    assert by_name["Serilog"] == "4.0.0"
    assert unresolved == []


def test_resolver_handles_csproj_packageref_without_version(tmp_path):
    """A csproj `<PackageReference>` without an inline Version attribute is
    valid under central package management. It should still register the
    package name in `available` (so it's not falsely unresolved if
    Directory.Packages.props pins it), but contribute no version to the
    csproj-side version map. Existing behavior must hold."""
    csproj = tmp_path / "X.csproj"
    csproj.write_text('''<Project Sdk="Microsoft.NET.Sdk.Web">
  <ItemGroup>
    <PackageReference Include="Serilog" />
  </ItemGroup>
</Project>
''')
    src = tmp_path / "X.cs"
    src.write_text("using Serilog;\nclass X {}\n")
    snippet = "using Serilog;\nclass C {}\n"

    packages, unresolved = resolve_packages(snippet, src, tmp_path)
    # Without a .props pin and without a csproj-inline version, this is unresolved.
    assert packages == []
    assert "Serilog" in unresolved


def test_resolver_pulls_serilog_family_siblings(tmp_path):
    """Bug X5: `using Serilog;` resolves Serilog, but real reference repos
    also pin Serilog.AspNetCore + Serilog.Sinks.Console, whose types live
    in the SAME Serilog namespace. Resolver must include those family
    siblings so the grafted csproj has all the references the snippet
    body needs."""
    from convention_scan.package_resolver import resolve_packages
    csproj = tmp_path / "Reference.Api.csproj"
    csproj.write_text('''<Project Sdk="Microsoft.NET.Sdk.Web">
  <ItemGroup>
    <PackageReference Include="Serilog" Version="3.1.1" />
    <PackageReference Include="Serilog.AspNetCore" Version="8.0.1" />
    <PackageReference Include="Serilog.Sinks.Console" Version="5.0.1" />
    <PackageReference Include="Dapper" Version="2.1.66" />
  </ItemGroup>
</Project>
''')
    src = tmp_path / "src" / "X.cs"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("using Serilog;\nclass X {}\n")
    snippet = "using Serilog;\nclass C {}\n"

    packages, unresolved = resolve_packages(snippet, src, tmp_path)
    names = {p.name for p in packages}
    assert "Serilog" in names
    assert "Serilog.AspNetCore" in names, "Family sibling Serilog.AspNetCore not pulled"
    assert "Serilog.Sinks.Console" in names, "Family sibling Serilog.Sinks.Console not pulled"
    # Family sweep must NOT pull unrelated packages.
    assert "Dapper" not in names
    # No spurious unresolved entries.
    assert unresolved == []
    # Versions come from the same csproj source.
    by_name = {p.name: p.version for p in packages}
    assert by_name["Serilog.AspNetCore"] == "8.0.1"
    assert by_name["Serilog.Sinks.Console"] == "5.0.1"


def test_resolver_family_sweep_bounded_for_multi_segment_primary(tmp_path):
    """Bug X5: when the primary is multi-segment (e.g.,
    Microsoft.AspNetCore.OpenApi), the family root is the first TWO
    segments — not just the first. Otherwise a single `using
    Microsoft.AspNetCore.Builder;` would pull every `Microsoft.*` package.
    """
    from convention_scan.package_resolver import resolve_packages
    csproj = tmp_path / "X.csproj"
    csproj.write_text('''<Project Sdk="Microsoft.NET.Sdk.Web">
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="9.0.0" />
    <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="9.0.0" />
    <PackageReference Include="Microsoft.Extensions.Hosting" Version="9.0.0" />
    <PackageReference Include="Microsoft.Data.Sqlite" Version="9.0.0" />
  </ItemGroup>
</Project>
''')
    src = tmp_path / "X.cs"
    src.write_text("using Microsoft.AspNetCore.OpenApi;\nclass X {}\n")
    # Note: namespaces resolver SKIPS Microsoft.AspNetCore.Builder / .Http /
    # Microsoft.Extensions per SYSTEM_PREFIXES, but Microsoft.AspNetCore.OpenApi
    # is NOT in that skip set — it should resolve.
    snippet = "using Microsoft.AspNetCore.OpenApi;\nclass C {}\n"

    packages, unresolved = resolve_packages(snippet, src, tmp_path)
    names = {p.name for p in packages}
    assert "Microsoft.AspNetCore.OpenApi" in names
    # Family bound: same first two segments.
    assert "Microsoft.AspNetCore.Authentication.JwtBearer" in names, \
        "Family sweep should include other Microsoft.AspNetCore.* siblings"
    # Bound boundary: different first-two-segment families NOT included.
    assert "Microsoft.Extensions.Hosting" not in names, \
        "Family sweep must NOT cross from Microsoft.AspNetCore.* to Microsoft.Extensions.*"
    assert "Microsoft.Data.Sqlite" not in names, \
        "Family sweep must NOT cross from Microsoft.AspNetCore.* to Microsoft.Data.*"


def test_resolver_family_sweep_no_op_when_no_siblings(tmp_path):
    """Bug X5: a primary with no family siblings in available is fine —
    just the primary returned, no spurious unresolved entries."""
    from convention_scan.package_resolver import resolve_packages
    csproj = tmp_path / "X.csproj"
    csproj.write_text('''<Project Sdk="Microsoft.NET.Sdk.Web">
  <ItemGroup>
    <PackageReference Include="Dapper" Version="2.1.66" />
  </ItemGroup>
</Project>
''')
    src = tmp_path / "X.cs"
    src.write_text("using Dapper;\nclass X {}\n")
    snippet = "using Dapper;\nclass C {}\n"

    packages, unresolved = resolve_packages(snippet, src, tmp_path)
    names = [p.name for p in packages]
    assert names == ["Dapper"]
    assert unresolved == []


def test_resolver_family_sweep_dedupes_when_namespace_explicit(tmp_path):
    """Bug X5: if the snippet explicitly uses both Foo and Foo.Bar, and
    csproj pins both Foo + Foo.Bar, resolver returns each once (no
    duplicate entries from primary-match + family-sweep)."""
    from convention_scan.package_resolver import resolve_packages
    csproj = tmp_path / "X.csproj"
    csproj.write_text('''<Project Sdk="Microsoft.NET.Sdk.Web">
  <ItemGroup>
    <PackageReference Include="Serilog" Version="3.1.1" />
    <PackageReference Include="Serilog.AspNetCore" Version="8.0.1" />
  </ItemGroup>
</Project>
''')
    src = tmp_path / "X.cs"
    src.write_text("using Serilog;\nusing Serilog.AspNetCore;\nclass X {}\n")
    snippet = "using Serilog;\nusing Serilog.AspNetCore;\nclass C {}\n"

    packages, unresolved = resolve_packages(snippet, src, tmp_path)
    names = [p.name for p in packages]
    # Each package exactly once even though both pathways (primary + family) found them.
    assert names.count("Serilog") == 1
    assert names.count("Serilog.AspNetCore") == 1
