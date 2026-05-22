#!/usr/bin/env python3
"""Deterministic Phase-1 file emitter for e2e test gate.

NOT the canonical Phase-1 implementation — that lives in the
scaffold-with-guardrails skill and is LLM-driven for flexibility.
This emitter captures the file-emission subset for unit testing.
If scaffold.md drifts in a way the LLM-driven skill would catch, this
emitter and its tests will catch it too.

CLI:
  python3 phase1_emit.py --target-root /tmp/x --app-name MyApp
"""
from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates" / "csharp"


def _run(cmd: list[str], cwd: Path) -> None:
    """Run a subprocess, surfacing failures verbatim.

    Raises SystemExit on non-zero returncode so the caller's error message
    includes the full stdout+stderr — no Silent Fallback (the retry-helper
    anti-pattern) where a failed dotnet command quietly returns control.
    """
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}", file=sys.stderr)
        sys.exit(result.returncode)


def _extract_canonical_program_cs() -> str:
    """Extract the canonical Program.cs body from scaffold.md.

    The same dual-anchor approach the Task 9 pytest uses: find the first
    ```csharp fenced block in scaffold.md containing
    `var builder = WebApplication.CreateBuilder(args)` AND `app.Run();`.
    """
    body = (TEMPLATES / "scaffold.md").read_text()
    for block in re.findall(r"```csharp\n(.*?)```", body, re.DOTALL):
        if "var builder = WebApplication.CreateBuilder(args)" in block and "app.Run();" in block:
            return block
    raise RuntimeError("Canonical Program.cs block not found in scaffold.md")


def emit(target_root: Path, app_name: str) -> None:
    target_root.mkdir(parents=True, exist_ok=True)

    # 1. Copy global.json, .props, gitignore, coverlet.runsettings.
    # Directory.Packages.props MUST land before any `dotnet add package` to
    # prevent dotnet from writing inline Version="..." attrs that bypass CPM pins.
    for fname in ("global.json", "Directory.Build.props", "Directory.Packages.props", "coverlet.runsettings"):
        shutil.copy(TEMPLATES / fname, target_root / fname)
    shutil.copy(TEMPLATES / "gitignore", target_root / ".gitignore")

    # 2. dotnet new sln + projects.
    _run(["dotnet", "new", "sln", "-n", app_name], cwd=target_root)
    for layer in ("Domain", "Application", "Infrastructure", "Persistence"):
        _run([
            "dotnet", "new", "classlib", "-n", f"{app_name}.{layer}",
            "-o", f"src/{app_name}.{layer}",
        ], cwd=target_root)
    _run([
        "dotnet", "new", "webapi", "-n", f"{app_name}.Api",
        "-o", f"src/{app_name}.Api",
    ], cwd=target_root)
    _run([
        "dotnet", "new", "worker", "-n", f"{app_name}.Service",
        "-o", f"src/{app_name}.Service",
    ], cwd=target_root)
    _run([
        "dotnet", "new", "xunit", "-n", f"{app_name}.Tests.Unit",
        "-o", f"tests/{app_name}.Tests.Unit",
    ], cwd=target_root)

    # 3. Add all projects to the solution file.
    for csproj in target_root.rglob("*.csproj"):
        _run(["dotnet", "sln", "add", str(csproj.relative_to(target_root))], cwd=target_root)

    # 4. Strip Class1.cs + UnitTest1.cs placeholders (Forensic Coding prevention).
    for f in target_root.rglob("Class1.cs"):
        f.unlink()
    for f in target_root.rglob("UnitTest1.cs"):
        f.unlink()

    # 5. Strip inline Version="..." attributes from csprojs so CPM takes over.
    # `dotnet new webapi|worker|xunit` bakes explicit version attrs that
    # NU1008-fail under ManagePackageVersionsCentrally=true.
    for csproj in target_root.rglob("*.csproj"):
        text = csproj.read_text()
        text = re.sub(r' Version="[^"]*"', "", text)
        csproj.write_text(text)

    # 6. Add ProjectReferences per scaffold.md (post-X7: Api has NO Persistence ref).
    def _add_refs(host_csproj: Path, refs: list[str]) -> None:
        for r in refs:
            target_csproj = target_root / "src" / f"{app_name}.{r}" / f"{app_name}.{r}.csproj"
            _run([
                "dotnet", "add", str(host_csproj), "reference", str(target_csproj),
            ], cwd=target_root)

    # Application ← Domain
    _add_refs(
        target_root / "src" / f"{app_name}.Application" / f"{app_name}.Application.csproj",
        ["Domain"],
    )
    # Infrastructure ← Application + Domain
    _add_refs(
        target_root / "src" / f"{app_name}.Infrastructure" / f"{app_name}.Infrastructure.csproj",
        ["Application", "Domain"],
    )
    # Persistence ← Application + Domain
    _add_refs(
        target_root / "src" / f"{app_name}.Persistence" / f"{app_name}.Persistence.csproj",
        ["Application", "Domain"],
    )
    # Api ← Application + Infrastructure + Domain (NO Persistence — X7 fix)
    _add_refs(
        target_root / "src" / f"{app_name}.Api" / f"{app_name}.Api.csproj",
        ["Application", "Infrastructure", "Domain"],
    )
    # Service ← all four (Worker legitimately wires repos for background jobs)
    _add_refs(
        target_root / "src" / f"{app_name}.Service" / f"{app_name}.Service.csproj",
        ["Application", "Infrastructure", "Persistence", "Domain"],
    )
    # Tests.Unit ← all four src layers (NetArchTest needs each assembly ref)
    _add_refs(
        target_root / "tests" / f"{app_name}.Tests.Unit" / f"{app_name}.Tests.Unit.csproj",
        ["Domain", "Application", "Infrastructure", "Persistence"],
    )

    # 7. Add SwaggerUI package via central package management.
    api_csproj = target_root / "src" / f"{app_name}.Api" / f"{app_name}.Api.csproj"
    _run(["dotnet", "add", str(api_csproj), "package", "Swashbuckle.AspNetCore.SwaggerUI"],
         cwd=target_root)

    # 8. Strip ALL inline Version="..." once more — dotnet add package puts one back.
    for csproj in target_root.rglob("*.csproj"):
        text = csproj.read_text()
        text = re.sub(r' Version="[^"]*"', "", text)
        csproj.write_text(text)

    # 9. Suppress CA1707 on the test project (underscores in route-named test methods).
    test_csproj = (
        target_root / "tests" / f"{app_name}.Tests.Unit" / f"{app_name}.Tests.Unit.csproj"
    )
    text = test_csproj.read_text()
    text = text.replace(
        "</PropertyGroup>",
        "    <NoWarn>$(NoWarn);CA1707</NoWarn>\n  </PropertyGroup>",
        1,
    )
    test_csproj.write_text(text)

    # 10. Write Api Program.cs from the canonical scaffold.md body (marker-baked).
    program_body = _extract_canonical_program_cs()
    # Substitute the <App> placeholder with the real app name.
    program_body = program_body.replace("<App>", app_name)
    (target_root / "src" / f"{app_name}.Api" / "Program.cs").write_text(program_body)

    # 11. Delete the *.http file dotnet new webapi ships (trips quality rules).
    for f in (target_root / "src" / f"{app_name}.Api").rglob("*.http"):
        f.unlink()

    # 12. Write Api Configuration/DatabaseOptions.cs + appsettings.Development.json.
    # Program.cs binds DatabaseOptions via ValidateOnStart — both files are
    # required for the first `dotnet run` (and for dotnet build without errors).
    config_dir = target_root / "src" / f"{app_name}.Api" / "Configuration"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "DatabaseOptions.cs").write_text(
        f"using System.ComponentModel.DataAnnotations;\n"
        f"\n"
        f"namespace {app_name}.Api.Configuration;\n"
        f"\n"
        f"public sealed class DatabaseOptions\n"
        f"{{\n"
        f"    public const string SectionName = \"Database\";\n"
        f"\n"
        f"    [Required]\n"
        f"    [MinLength(10)]\n"
        f"    public string ConnectionString {{ get; init; }} = string.Empty;\n"
        f"\n"
        f"    [Range(1, 300)]\n"
        f"    public int CommandTimeoutSeconds {{ get; init; }} = 30;\n"
        f"}}\n"
    )
    app_name_lower = app_name.lower()
    (target_root / "src" / f"{app_name}.Api" / "appsettings.Development.json").write_text(
        f'{{\n'
        f'  "Logging": {{ "LogLevel": {{ "Default": "Information", "Microsoft.AspNetCore": "Warning" }} }},\n'
        f'  "Database": {{\n'
        f'    "ConnectionString": "Host=localhost;Database={app_name_lower};Username=postgres;Password=postgres",\n'
        f'    "CommandTimeoutSeconds": 30\n'
        f'  }}\n'
        f'}}\n'
    )

    # 13. AssemblyMarker.cs per layer (required by NetArchTest for assembly reference).
    # Must be `public` — internal would be inaccessible from Tests.Unit (CS0122).
    for layer in ("Domain", "Application", "Infrastructure", "Persistence", "Api", "Service"):
        (target_root / "src" / f"{app_name}.{layer}" / "AssemblyMarker.cs").write_text(
            f"namespace {app_name}.{layer};\n"
            f"\n"
            f"/// <summary>NetArchTest anchor — gives Architecture tests an Assembly reference. Do not add members.</summary>\n"
            f"public sealed class AssemblyMarker {{ }}\n"
        )

    # 14. Worker.cs — replace the generated default that trips CA1848 + quality.yaml.
    # `dotnet new worker` emits DateTimeOffset.Now (trips *-QUAL-R005) and an
    # unstructured LogInformation call (trips CA1848 under TWAE on src/).
    (target_root / "src" / f"{app_name}.Service" / "Worker.cs").write_text(
        f"namespace {app_name}.Service;\n"
        f"\n"
        f"public sealed class Worker(ILogger<Worker> logger) : BackgroundService\n"
        f"{{\n"
        f"    private static readonly Action<ILogger, DateTimeOffset, Exception?> LogHeartbeat =\n"
        f"        LoggerMessage.Define<DateTimeOffset>(\n"
        f"            LogLevel.Information,\n"
        f"            new EventId(1, nameof(LogHeartbeat)),\n"
        f'            "Worker running at: {{Time}}");\n'
        f"\n"
        f"    protected override async Task ExecuteAsync(CancellationToken stoppingToken)\n"
        f"    {{\n"
        f"        while (!stoppingToken.IsCancellationRequested)\n"
        f"        {{\n"
        f"            if (logger.IsEnabled(LogLevel.Information))\n"
        f"            {{\n"
        f"                LogHeartbeat(logger, DateTimeOffset.UtcNow, null);\n"
        f"            }}\n"
        f"            await Task.Delay(1000, stoppingToken);\n"
        f"        }}\n"
        f"    }}\n"
        f"}}\n"
    )

    # 15. .semgrep/<app-lower>/api.yaml — lib-api-no-persistence-ref rule.
    # This is the semgrep gate that enforces the X7 fix at CI time.
    semgrep_dir = target_root / ".semgrep" / app_name.lower()
    semgrep_dir.mkdir(parents=True, exist_ok=True)
    (semgrep_dir / "api.yaml").write_text(
        f"rules:\n"
        f"  - id: lib-api-no-persistence-ref\n"
        f"    languages: [generic]\n"
        f"    paths:\n"
        f"      include:\n"
        f'        - "src/{app_name}.Api/**/*.csproj"\n'
        f"    pattern: '<ProjectReference Include=\"$X.Persistence/...'\n"
        f'    message: "Api must not reference Persistence directly. Use Application layer."\n'
        f"    severity: ERROR\n"
    )
    # Stub rule files so semgrep scan --config .semgrep/ does not error on missing configs.
    for stub in (
        "application.yaml", "infrastructure.yaml", "persistence.yaml",
        "service.yaml", "security.yaml", "quality.yaml", "async.yaml", "dapper.yaml",
    ):
        (semgrep_dir / stub).write_text("rules: []\n")

    # 16. Directory.Build.targets — semgrep BeforeTargets="Build".
    # SKIP_SEMGREP=1 lets the e2e test suppress semgrep if the tool is absent
    # without changing the production gate.
    (target_root / "Directory.Build.targets").write_text(
        "<Project>\n"
        "  <Target Name=\"SemgrepLint\" BeforeTargets=\"Build\" Condition=\"'$(SKIP_SEMGREP)' != '1'\">\n"
        "    <Exec\n"
        "      Command=\"semgrep scan --config .semgrep/ src/ --error --quiet\"\n"
        "      WorkingDirectory=\"$(MSBuildThisFileDirectory)\"\n"
        "      IgnoreExitCode=\"false\" />\n"
        "  </Target>\n"
        "</Project>\n"
    )

    # Note: lock file generation (dotnet restore --use-lock-file) is intentionally
    # NOT run here — the `dotnet add` calls above already create obj/ cache files,
    # and running a second restore before the final build step causes a
    # project.assets.json collision (NuGet's parallel restore sees the same
    # project twice via /var and /private/var on macOS). The caller (e2e bats gate
    # or the LLM-driven skill) is responsible for running `dotnet restore
    # --use-lock-file` once, after any package additions (e.g., graft's Serilog
    # ref), and before the final `dotnet build`.


def main() -> None:
    p = argparse.ArgumentParser(
        description="Deterministic Phase-1 file emitter for e2e test gate."
    )
    p.add_argument("--target-root", required=True, help="Directory to emit into (created if absent).")
    p.add_argument("--app-name", required=True, help="PascalCase app name (e.g. MyApp).")
    args = p.parse_args()
    emit(Path(args.target_root), args.app_name)


if __name__ == "__main__":
    main()
