# C# Scaffold — Step-by-Step

Canonical scaffold the skill applies when the tech-design's stack is C# / .NET 9.
Skill grills briefly first, then runs these commands in the target repo.

## Grill questions (skill asks before scaffolding)

1. **App name** (PascalCase, e.g., `ExpensePortal`)
2. **Needs shared client SDK?** → adds `<App>.Client` (classlib)
   - If yes: **Client contracts from Domain types or pure DTOs?** (record decision)

> `<App>.Api` (WebAPI) **and** `<App>.Service` (Worker) are scaffolded by default.
> Delete whichever the project does not need after scaffolding (the alternative —
> asking up front — bakes in a guess that's painful to reverse). Both hosts
> share the same Application layer; deleting one is one project removal +
> one csproj edit, not a refactor.

## Default stack choices

| Concern | Choice | Why |
|---|---|---|
| Data access | **Dapper + Npgsql + DTO row types** | EF Core's `IQueryable`/`DbSet` surface is a Leaky Narrative through the persistence boundary. Dapper makes SQL explicit; DTOs explicitly typed prevent Domain pollution. |
| In-process bus | **MediatR `12.4.1`** (pin) | Last MIT release before the Aug-2024 commercial pivot. Pin until license review approves an upgrade. |
| Out-of-process bus (if used) | **MassTransit `8.3.4`** (pin) | Last MIT v8 release. Pin until license review approves an upgrade. |

If the design explicitly needs EF Core (e.g., heavy aggregate graph mapping),
flag it as a deliberate deviation in the scaffold output and adjust the
layer rules accordingly — but do not switch silently.

## Scaffold commands

> **Rule:** Use CLI scaffolders (`dotnet new`, `dotnet add`) — never hand-roll `.csproj` or project files. Hand-rolling is Computational Friction.

```bash
APP=ExpensePortal
APP_LOWER=expense-portal
SCAFFOLD="$HOME/.claude/plugins/cache/.../skills/scaffold-with-guardrails"

# Pin SDK first so all subsequent dotnet new commands respect it.
# Directory.Packages.props MUST land before any `dotnet add package` runs —
# otherwise `dotnet add` resolves the LATEST version and writes an explicit
# Version="…" attribute into each csproj, silently bypassing the pinned
# MediatR 12.4.1 / MassTransit 8.3.4 (both have post-MIT releases now).
cp "$SCAFFOLD/templates/csharp/global.json" .
cp "$SCAFFOLD/templates/csharp/Directory.Build.props" .
cp "$SCAFFOLD/templates/csharp/Directory.Packages.props" .

dotnet new sln -n "$APP"

# Core layers (always)
dotnet new classlib -n "$APP.Domain"         -o src/"$APP".Domain
dotnet new classlib -n "$APP.Application"    -o src/"$APP".Application
dotnet new classlib -n "$APP.Infrastructure" -o src/"$APP".Infrastructure
dotnet new classlib -n "$APP.Persistence"    -o src/"$APP".Persistence

# Hosts (always scaffold both — user deletes whichever they don't need)
dotnet new webapi   -n "$APP.Api"            -o src/"$APP".Api
dotnet new worker   -n "$APP.Service"        -o src/"$APP".Service

# Conditional (per grill answers)
dotnet new classlib -n "$APP.Client"         -o src/"$APP".Client        # if client SDK

# Test projects (always)
dotnet new xunit    -n "$APP.Tests.Unit"        -o tests/"$APP".Tests.Unit
dotnet new xunit    -n "$APP.Tests.Integration" -o tests/"$APP".Tests.Integration

find . -name "*.csproj" | sort | xargs dotnet sln add

# Strip Version="…" from generated csprojs. `dotnet new webapi|worker|xunit`
# emits explicit versions for Microsoft.AspNetCore.OpenApi /
# Microsoft.NET.Test.Sdk / xunit / xunit.runner.visualstudio / coverlet.collector,
# which NU1008-fails immediately under ManagePackageVersionsCentrally=true.
# Those IDs are pinned in Directory.Packages.props; removing the inline
# versions lets central management take over. Note the macOS-portable
# `sed -i.bak …` form — GNU sed accepts `-i` without an argument, BSD sed
# does not. Deleting the `.bak` files after keeps the working tree clean.
find src tests -name '*.csproj' -exec sed -i.bak 's/ Version="[^"]*"//g' {} +
find src tests -name '*.csproj.bak' -delete

# Dependency direction: Domain ← Application ← Infrastructure/Persistence
dotnet add src/"$APP".Application/"$APP".Application.csproj \
  reference src/"$APP".Domain/"$APP".Domain.csproj

dotnet add src/"$APP".Infrastructure/"$APP".Infrastructure.csproj \
  reference src/"$APP".Application/"$APP".Application.csproj \
             src/"$APP".Domain/"$APP".Domain.csproj

dotnet add src/"$APP".Persistence/"$APP".Persistence.csproj \
  reference src/"$APP".Application/"$APP".Application.csproj \
             src/"$APP".Domain/"$APP".Domain.csproj

# Test project refs
dotnet add tests/"$APP".Tests.Unit/"$APP".Tests.Unit.csproj \
  reference src/"$APP".Domain/"$APP".Domain.csproj \
             src/"$APP".Application/"$APP".Application.csproj

# Both hosts reference all four layers (composition root)
for HOST in Api Service; do
  dotnet add src/"$APP".$HOST/"$APP".$HOST.csproj \
    reference src/"$APP".Application/"$APP".Application.csproj \
               src/"$APP".Infrastructure/"$APP".Infrastructure.csproj \
               src/"$APP".Persistence/"$APP".Persistence.csproj \
               src/"$APP".Domain/"$APP".Domain.csproj
done

# NuGet packages — pin MediatR + MassTransit to last MIT releases.
# Directory.Packages.props (copied above) sets ManagePackageVersionsCentrally=true,
# so the `dotnet add package` calls below register versionless PackageReferences
# and pick up the pinned versions from Directory.Packages.props automatically.
dotnet add src/"$APP".Domain/"$APP".Domain.csproj package CSharpFunctionalExtensions
dotnet add src/"$APP".Application/"$APP".Application.csproj package CSharpFunctionalExtensions
dotnet add src/"$APP".Application/"$APP".Application.csproj package MediatR
dotnet add src/"$APP".Persistence/"$APP".Persistence.csproj package Dapper
dotnet add src/"$APP".Persistence/"$APP".Persistence.csproj package Npgsql
dotnet add src/"$APP".Persistence/"$APP".Persistence.csproj package CSharpFunctionalExtensions
dotnet add src/"$APP".Service/"$APP".Service.csproj package MediatR
dotnet add src/"$APP".Service/"$APP".Service.csproj package MassTransit
dotnet add src/"$APP".Service/"$APP".Service.csproj package MassTransit.RabbitMQ
dotnet add tests/"$APP".Tests.Unit/"$APP".Tests.Unit.csproj package NetArchTest.Rules
```

### Directory.Packages.props version pins

Lives at `templates/csharp/Directory.Packages.props` — copied verbatim by the
scaffold (see the `cp` at the top of the bash block above). MediatR and
MassTransit are pinned to their last MIT releases; bumping them requires
license review.

## Files the skill hand-writes after dotnet new

After `dotnet new`, the skill creates these files (generators don't produce them):

- `.gitignore` (root) — copied from `templates/csharp/gitignore`
- `.editorconfig` (root) — shared IDE formatting baseline + C# diagnostic severities; copied from `templates/common/.editorconfig`
- `global.json` (root) — pins SDK; copied verbatim from `templates/csharp/global.json`
- `Directory.Build.props` (root) — TWAE on src, lockfile-mode (CI), InvariantGlobalization on hosts; copied from `templates/csharp/Directory.Build.props`
- `coverlet.runsettings` (root) — coverage collection config + 70% threshold; copied from `templates/csharp/coverlet.runsettings`
- `Directory.Build.targets` (root) — semgrep gate before every build
- `Directory.Packages.props` (root) — central package management with pinned MediatR/MassTransit MIT versions; copied from `templates/csharp/Directory.Packages.props`
- `.semgrep/<app-lower>/<layer>.yaml` — one per layer for architecture-direction rules (Domain/Application/Infrastructure/Persistence/Api/Service)
- `.semgrep/<app-lower>/security.yaml` — cross-cutting security baseline (hardcoded creds, SQL injection, weak crypto, BinaryFormatter, CORS misconfig — see `SEMGREP-RULE-COOKBOOK.md`)
- `.semgrep/<app-lower>/quality.yaml` — code-quality baseline (empty catch, throw ex, Console.WriteLine, DateTime.Now, new HttpClient, logger interpolation, IServiceProvider injection)
- `.semgrep/<app-lower>/async.yaml` — async correctness (async void, .Result, .Wait(), .GetAwaiter().GetResult())
- `.semgrep/<app-lower>/dapper.yaml` — Dapper specifics (no interpolated SQL in Query/Execute, no string-concat SQL, prefer async overloads, no public IQueryable leak)
- `tests/<App>.Tests.Unit/Architecture/<Layer>ArchitectureTests.cs` — one per layer
- `CLAUDE.md` (root) — from `CLAUDE-MD-TEMPLATE.md`, embeds Six Principles + Violation Guide inline (scaffolded repos are self-contained — do not rely on the global CLAUDE.md being present)
- `src/<App>.<Layer>/AGENTS.md` — from `AGENTS-MD-TEMPLATE.md`, one per layer
- `.github/PULL_REQUEST_TEMPLATE.md` — Six Principles + gates checklist; copied from `templates/common/.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/openapi-diff.yml.disabled` — OpenAPI contract diff stub via oasdiff; copied from `templates/csharp/github-workflows/openapi-diff.yml.disabled` (rename to `.yml` after wiring spec gen)
- `.claude/settings.json` — hook wiring
- `.claude/hooks/{pre-commit,pre-push,stop-neg-audit}.sh` — copied from this skill (`chmod +x`)
- `src/<App>.<Layer>/AssemblyMarker.cs` — one per layer (required by NetArchTest to get assembly reference)
- `src/<App>.{Api,Service}/Configuration/*Options.cs` — typed config + `ValidateOnStart` triad (one file per options group)

After `dotnet new webapi`, also **strip the weather-forecast boilerplate** from `src/<App>.Api/Program.cs` (and delete `src/<App>.Api/*.http`). The generated example would trip `quality.yaml` (DateTime.Now, Random) and is not part of the app.

After `dotnet new worker`, the default `Program.cs` is a minimal `Host.CreateApplicationBuilder` shell — leave it; the user wires MediatR/MassTransit at composition time. Add the same `AssemblyMarker.cs` and `AGENTS.md` pattern under `src/<App>.Service/`.

**Also fix the generated `Worker.cs`.** `dotnet new worker` emits
`_logger.LogInformation("Worker running at: {time}", DateTimeOffset.Now)` which
trips CA1848 (use compile-time logging delegates) and CA1727 (PascalCase
placeholders) — both promoted to errors by `TreatWarningsAsErrors=true` on
`src/`. Replace the `LogInformation` call with a `LoggerMessage` delegate so the
first build is green:

```csharp
public sealed class Worker(ILogger<Worker> logger) : BackgroundService
{
    private static readonly Action<ILogger, DateTimeOffset, Exception?> LogHeartbeat =
        LoggerMessage.Define<DateTimeOffset>(
            LogLevel.Information,
            new EventId(1, nameof(LogHeartbeat)),
            "Worker running at: {Time}");

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            if (logger.IsEnabled(LogLevel.Information))
            {
                LogHeartbeat(logger, DateTimeOffset.Now, null);
            }
            await Task.Delay(1000, stoppingToken);
        }
    }
}
```

Or strip the heartbeat body entirely if the worker has real work to do — the
goal is just to keep the first build clean under TWAE.

## Lockfile generation (one-time after scaffold)

`Directory.Build.props` enables `RestorePackagesWithLockFile`. After the
initial `dotnet restore`, each project has a `packages.lock.json`.
**Commit these files.** Without them, `RestoreLockedMode=true` under CI
will fail.

```bash
dotnet restore --use-lock-file
git add -- '**/packages.lock.json'
git commit -m "chore: lock NuGet transitives"
```

To bump a dependency:

```bash
dotnet add <project> package <name> --version <v>
dotnet restore --force-evaluate
```

### CI environment variable

`RestoreLockedMode` is conditioned on `$(CI) == 'true'`. GitHub Actions,
GitLab CI, CircleCI, and Travis set `CI=true` automatically. **Azure
DevOps does not** — it sets `TF_BUILD=True` instead. On Azure DevOps,
either set `CI` explicitly in the pipeline:

```yaml
variables:
  CI: 'true'
```

or invoke restore with the property directly:

```bash
dotnet restore -p:RestoreLockedMode=true
```

## Options validation pattern (hand-written by skill per host)

Every typed configuration class in `<App>.Api/Configuration/` or
`<App>.Service/Configuration/` must follow this triad:

1. POCO with `DataAnnotations` constraints (`[Required]`, `[Range]`, etc.)
2. `services.AddOptions<T>().Bind(section).ValidateDataAnnotations().ValidateOnStart()`
3. Consumers inject `IOptions<T>` / `IOptionsSnapshot<T>` — never `IConfiguration`

Why: surfaces config errors at process start, not the first request.
Tied to the Sensor principle (failures visible at the boundary, not buried).

Example:

`src/<App>.Api/Configuration/DatabaseOptions.cs`:

```csharp
using System.ComponentModel.DataAnnotations;

namespace <App>.Api.Configuration;

public sealed class DatabaseOptions
{
    public const string SectionName = "Database";

    [Required]
    [MinLength(10)]
    public string ConnectionString { get; init; } = string.Empty;

    [Range(1, 300)]
    public int CommandTimeoutSeconds { get; init; } = 30;
}
```

`src/<App>.Api/Program.cs` (wiring):

```csharp
builder.Services
    .AddOptions<DatabaseOptions>()
    .Bind(builder.Configuration.GetSection(DatabaseOptions.SectionName))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

## Coverage threshold (gate-aware)

`coverlet.runsettings` is generated at repo root with a 70% line/branch/method
threshold. Wire it into the test gate by editing the pre-commit `50-tests-unit`
script (after scaffolding) to invoke:

```bash
dotnet test --collect:"XPlat Code Coverage" --settings coverlet.runsettings
```

Or add a CI-only check (preferred — keeps pre-commit fast):

```yaml
- name: Coverage gate
  run: dotnet test --collect:"XPlat Code Coverage" --settings coverlet.runsettings
```

Tune the `<Threshold>` value as the suite matures. Mutation testing (Stryker)
covers the "tests run but don't assert" gap that line coverage misses.

## Gate system installation (always)

After `dotnet new` steps complete, the skill installs the language-agnostic
gate system from `templates/common/` and the .NET-conditional pieces from
`templates/csharp/`:

```bash
# Language-agnostic
# Use `cp -R <src>/. <dst>/` (trailing `/.`) for directory copies — bare
# `cp -R <src> <dst>` on macOS nests src *inside* dst on re-run, which makes
# the scaffold non-idempotent and silently produces .githooks/githooks/...
cp "$SCAFFOLD/templates/common/.editorconfig" .
mkdir -p .githooks       && cp -R "$SCAFFOLD/templates/common/githooks/."     .githooks/
mkdir -p scripts         && cp -R "$SCAFFOLD/templates/common/scripts/."      scripts/
cp    "$SCAFFOLD/templates/common/gitconfig-gates"     .gitconfig.gates
cp    "$SCAFFOLD/templates/common/gates.toml.example"  .gates.toml
mkdir -p .tools
cp "$SCAFFOLD/templates/common/tools/manifest.toml.template" .tools/manifest.toml
cp "$SCAFFOLD/templates/common/tools/gitignore-template"     .tools/.gitignore
mkdir -p .semgrep/packs
# csharp.yaml is already C#-only — copy verbatim.
cp "$SCAFFOLD/templates/common/semgrep-packs/csharp.yaml" .semgrep/packs/
# owasp-top-ten.yaml vendors 544 rules across 25 languages. Filter at copy
# time to the C#-applicable subset (csharp / C# / generic / yaml /
# dockerfile / regex / json / bash). Drops the pack from ~1.3 MB to ~190 KB
# and stops semgrep from loading 467 inert python/java/go/php/ruby/scala/
# kotlin/swift/clojure/solidity/hcl/terraform/html rules on every gate run.
# When the python / typescript scaffolds land, copy this block with a
# different KEEP set; do NOT mutate the vendored common/ file.
SRC="$SCAFFOLD/templates/common/semgrep-packs/owasp-top-ten.yaml" \
DST=".semgrep/packs/owasp-top-ten.yaml" \
python3 - <<'PY'
import os, yaml
KEEP = {'csharp', 'C#', 'generic', 'yaml', 'dockerfile', 'regex', 'json', 'bash'}
with open(os.environ['SRC']) as f:
    pack = yaml.safe_load(f)
pack['rules'] = [r for r in pack['rules'] if set(r.get('languages', []) or []) & KEEP]
with open(os.environ['DST'], 'w') as f:
    yaml.safe_dump(pack, f, sort_keys=False, default_flow_style=False, width=4096)
print(f"Filtered OWASP pack -> {len(pack['rules'])} C#-applicable rules")
PY
cp    "$SCAFFOLD/templates/common/docs/BYPASS-POLICY.md"      BYPASS-POLICY.md
cp    "$SCAFFOLD/templates/common/docs/BRANCH-PROTECTION.md"  BRANCH-PROTECTION.md
mkdir -p docs
cp "$SCAFFOLD/templates/common/docs/rules-audit.md.template" docs/rules-audit.md
mkdir -p .github
cp "$SCAFFOLD/templates/common/.github/PULL_REQUEST_TEMPLATE.md" .github/
mkdir -p .github/workflows
cp "$SCAFFOLD/templates/common/github-workflows/gates-backstop.yml.disabled" .github/workflows/
cp "$SCAFFOLD/templates/common/github-workflows/tools-pin-check.yml"          .github/workflows/

# .NET-conditional
cp "$SCAFFOLD/templates/csharp/github-workflows/stryker-nightly.yml" .github/workflows/
cp "$SCAFFOLD/templates/csharp/github-workflows/openapi-diff.yml.disabled" .github/workflows/
cp "$SCAFFOLD/templates/csharp/stryker-config.json" .
cp "$SCAFFOLD/templates/csharp/coverlet.runsettings" .

# Make executables
chmod +x .githooks/pre-commit .githooks/pre-push .githooks/commit-msg
chmod +x .githooks/pre-commit.d/* .githooks/pre-push.d/* .githooks/commit-msg.d/*
chmod +x scripts/*.sh

# Stryker.NET tool install
dotnet new tool-manifest 2>/dev/null || true
dotnet tool install dotnet-stryker

# Run bootstrap to wire hooks + fetch tools
./scripts/bootstrap.sh
```

After the scaffold completes, the user must commit the populated
`.tools/manifest.toml` (with real SHA256 checksums) to make the pinning
contract binding.

## Directory.Build.targets (hand-written by skill)

Cross-platform (forward slashes; works on macOS, Linux, Windows):

```xml
<Project>
  <Target Name="SemgrepLint" BeforeTargets="Build" Condition="'$(SKIP_SEMGREP)' != '1'">
    <Exec
      Command="semgrep scan --config .semgrep/ src/ --error --quiet"
      WorkingDirectory="$(MSBuildThisFileDirectory)"
      IgnoreExitCode="false" />
  </Target>
</Project>
```

## .claude/settings.json (hand-written by skill)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "hooks": [
          {
            "type": "command",
            "command": ".githooks/pre-commit"
          }
        ]
      },
      {
        "matcher": "Bash(git push:*)",
        "hooks": [
          {
            "type": "command",
            "command": ".githooks/pre-push"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/stop-neg-audit.sh"
          }
        ]
      }
    ]
  }
}
```

Note the matcher tightening (`Bash(git commit:*)` instead of `Bash`) — fixes the broad-matcher issue from the audit. Claude Code's hook matcher accepts glob-like patterns; this only fires on `git commit`/`git push` invocations. Verify the exact `.claude/settings.json` hook schema against current Claude Code docs at scaffold time — the schema may evolve between skill versions.

## NetArchTest starter — one per module (hand-written by skill)

```csharp
using System.Reflection;
using NetArchTest.Rules;
using Xunit;

namespace {{APP_NAME}}.Tests.Unit.Architecture;

public class DomainArchitectureTests
{
    private static readonly Assembly DomainAssembly =
        typeof({{APP_NAME}}.Domain.AssemblyMarker).Assembly;

    /// <summary>Enforces {{APP_KEY}}-DOMAIN-R001</summary>
    [Fact]
    public void Domain_HasNoInfrastructureReferences()
    {
        var result = Types.InAssembly(DomainAssembly)
            .ShouldNot()
            .HaveDependencyOnAny(
                "{{APP_NAME}}.Application",
                "{{APP_NAME}}.Infrastructure",
                "{{APP_NAME}}.Persistence",
                "{{APP_NAME}}.Api",
                "{{APP_NAME}}.Service",
                "Dapper",
                "Npgsql",
                "System.Data",
                "System.Data.Common",
                "Microsoft.EntityFrameworkCore",
                "MediatR",
                "MassTransit",
                "Microsoft.AspNetCore",
                "Microsoft.Extensions.Hosting")
            .GetResult();

        Assert.True(result.IsSuccessful,
            $"Domain has forbidden refs: {string.Join(", ", result.FailingTypeNames ?? [])}");
    }
}
```
