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
