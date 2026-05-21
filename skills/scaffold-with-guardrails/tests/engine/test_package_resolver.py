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
