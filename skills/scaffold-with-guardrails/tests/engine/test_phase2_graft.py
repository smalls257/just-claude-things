import pytest
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase2_graft.py"


def write(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _seed(tmp_path):
    design = tmp_path / "svc.md"
    design.write_text("""# svc
<module name="core"/>

<conventions reference-repo="r" reference-repo-commit="abc1234" scanned-at="t" engine-version="0.1.0">
  <adopted detector="jwt-bearer" source="src/Auth.cs:L1-L5" staged="staged/jwt-bearer.cs" packages="MS.X:8.0.5"/>
  <dev-named target="flags" source="src/F.cs:L1-L5" staged="staged/dev-flags.cs" adopted="true" packages="LD.SDK:8.0.0"/>
</conventions>
""")
    program = tmp_path / "Program.cs"
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
    (staged / "jwt-bearer.cs").write_text("builder.Services.AddJwtBearer();\n")
    (staged / "dev-flags.cs").write_text("builder.Services.AddFlags();\n")
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
    assert "// SOURCE: adopted:jwt-bearer — src/Auth.cs:L1-L5" in body
    assert "AddJwtBearer" in body
    assert "{{CONVENTION:auth}}" not in body


def test_dev_named_grafted_when_adopted(tmp_path):
    design, program, staged, cpm = _seed(tmp_path)
    res = _run(design, program, staged, cpm)
    body = program.read_text()
    assert "AddFlags" in body


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
