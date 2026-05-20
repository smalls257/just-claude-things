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
# Skill substitutes the real plugin-cache path at invocation time. When
# reading this playbook by hand, replace <path-to-skill> with the
# absolute path to your local checkout of skills/scaffold-with-guardrails.
SCAFFOLD="<path-to-skill>"

# Initialise git if not already a repo. `bootstrap.sh` (run at the end of
# the gate install) calls `git rev-parse` to locate the worktree root and
# will fail with "not a git repository" on a fresh dir. `git init -q` is a
# safe no-op on an existing repo (reinitialises the same .git dir).
git init -q

# Pin SDK first so all subsequent dotnet new commands respect it.
# Directory.Packages.props MUST land before any `dotnet add package` runs —
# otherwise `dotnet add` resolves the LATEST version and writes an explicit
# Version="…" attribute into each csproj, silently bypassing the pinned
# MediatR 12.4.1 / MassTransit 8.3.4 (both have post-MIT releases now).
cp "$SCAFFOLD/templates/csharp/global.json" .
cp "$SCAFFOLD/templates/csharp/Directory.Build.props" .
cp "$SCAFFOLD/templates/csharp/Directory.Packages.props" .

# .gitignore must land before any `dotnet new` that creates bin/ or obj/
# (i.e., `classlib`, `webapi`, `worker`, `xunit` — not `sln` or
# `tool-manifest`, which only emit text files into the working directory).
# Every classlib/webapi/worker/xunit project, plus every subsequent
# build/test, creates bin/, obj/, TestResults/ under each project. Without
# this copy, `git status` shows ~550 untracked artifacts the moment the
# first build finishes. Source file is named `gitignore` (no leading dot)
# in templates/ so it ships through filesystems / git operations that
# strip dotfiles; rename on copy.
cp "$SCAFFOLD/templates/csharp/gitignore" .gitignore

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

# Suppress CA1707 (identifier contains underscore) on test projects only.
# Phase-2 emits integration test classes named `{METHOD}_{PATH_SAFE}_Tests`
# (e.g., `GET_orders_byId_Tests`) — the underscores encode the HTTP route and
# are the xUnit/.NET community convention for route-named tests; renaming
# them to `MethodPathTests` destroys readability for no real benefit. We
# suppress the warning at the test-project level, NOT globally — `src/`
# stays strict (Directory.Build.props sets EnforceCodeStyleInBuild=true and
# TreatWarningsAsErrors on `src/`, and that policy stands). The injection
# adds <NoWarn>$(NoWarn);CA1707</NoWarn> into the existing <PropertyGroup>
# of each Tests.* csproj. Same macOS-portable sed form as above.
for TEST_CSPROJ in \
  tests/"$APP".Tests.Unit/"$APP".Tests.Unit.csproj \
  tests/"$APP".Tests.Integration/"$APP".Tests.Integration.csproj; do
  # Inject `<NoWarn>` before the first `</PropertyGroup>` only. Using `sed`
  # for cross-version newline handling (GNU `\n` vs. BSD literal-newline)
  # is fragile; awk gives one portable form. `&& mv` keeps the write atomic.
  awk '
    !done && /<\/PropertyGroup>/ {
      print "    <NoWarn>$(NoWarn);CA1707</NoWarn>"
      done = 1
    }
    { print }
  ' "$TEST_CSPROJ" > "$TEST_CSPROJ.tmp" && mv "$TEST_CSPROJ.tmp" "$TEST_CSPROJ"
done

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
- `.semgrep/<app-lower>/security.yaml` — cross-cutting security baseline (hardcoded creds, SQL injection, weak crypto, BinaryFormatter, CORS misconfig — see `$SCAFFOLD/SEMGREP-RULE-COOKBOOK.md` at skill root for rule patterns and example YAML)
- `.semgrep/<app-lower>/quality.yaml` — code-quality baseline (empty catch, throw ex, Console.WriteLine, DateTime.Now, new HttpClient, logger interpolation, IServiceProvider injection)
- `.semgrep/<app-lower>/async.yaml` — async correctness (async void, .Result, .Wait(), .GetAwaiter().GetResult())
- `.semgrep/<app-lower>/dapper.yaml` — Dapper specifics (no interpolated SQL in Query/Execute, no string-concat SQL, prefer async overloads, no public IQueryable leak)
- `tests/<App>.Tests.Unit/Architecture/<Layer>ArchitectureTests.cs` — one per layer
- `CLAUDE.md` (root) — from `CLAUDE-MD-TEMPLATE.md`, embeds Six Principles + Violation Guide inline (scaffolded repos are self-contained — do not rely on the global CLAUDE.md being present)
- `src/<App>.<Layer>/AGENTS.md` — from `AGENTS-MD-TEMPLATE.md`, one per layer. **Layer count includes `<App>.Client` when scaffolded** — the client SDK is a public-surface boundary and gets its own AGENTS.md describing its contract-stability rules
- `.github/PULL_REQUEST_TEMPLATE.md` — Six Principles + gates checklist; copied from `templates/common/.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/openapi-diff.yml.disabled` — OpenAPI contract diff stub via oasdiff; copied from `templates/csharp/github-workflows/openapi-diff.yml.disabled` (rename to `.yml` after wiring spec gen)
- `.claude/settings.json` — hook wiring
- `.claude/hooks/{pre-commit,pre-push,stop-neg-audit}.sh` — copied from this skill (`chmod +x`)
- `src/<App>.<Layer>/AssemblyMarker.cs` — one per layer (required by NetArchTest to get assembly reference). **Includes `<App>.Client` when scaffolded** so the architecture tests can assert nothing in the client SDK references Infrastructure / Persistence
- `src/<App>.{Api,Service}/Configuration/*Options.cs` — typed config + `ValidateOnStart` triad (one file per options group)
- `src/<App>.{Api,Service}/appsettings.Development.json` — populated with the matching section for every options class so `ValidateOnStart` does not fail on first `dotnet run` (see "Companion settings" under the Options validation pattern)

After `dotnet new webapi`, also **strip the weather-forecast boilerplate** from `src/<App>.Api/Program.cs` (and delete `src/<App>.Api/*.http`). The generated example would trip `quality.yaml` (DateTime.Now, Random) and is not part of the app.

**Also delete the `dotnet new classlib` and `dotnet new xunit` placeholder files** — every classlib leaves a `Class1.cs` containing an empty `Class1`, and every xunit project leaves a `UnitTest1.cs` with a single `Test1` method. These are **Forensic Coding** waiting to happen: dead boilerplate forces every future reader (human or Phase-2 subagent) to figure out it is dead, and a subagent could mistake `Class1.cs` for intentional starting scaffolding and extend it. Delete them before the first commit so the tree only contains code that is alive on purpose. Concretely, after all `dotnet new classlib` / `dotnet new xunit` calls finish, run:

```bash
# Run from the repo root (the directory containing src/ and tests/).
# Strip dotnet new placeholder files (Forensic Coding prevention).
# -maxdepth/-name/-delete is portable across BSD find (macOS) and GNU find (Linux).
find src   -maxdepth 2 -name 'Class1.cs'    -delete
find tests -maxdepth 2 -name 'UnitTest1.cs' -delete
```

This must hit every classlib layer (`Domain`, `Application`, `Infrastructure`, `Persistence`, and `Client` when scaffolded) and both test projects (`<App>.Tests.Unit`, `<App>.Tests.Integration`). After this step, `git status` should show no `Class1.cs` or `UnitTest1.cs` anywhere under `src/` or `tests/`.

Replace `Program.cs` with the canonical skeleton below. It wires the
OpenAPI spec (`/openapi/v1.json`), the Swagger UI page (`/swagger`, with
a bare-prefix redirect so the URL is browser-friendly), a health probe
(`/health`), and a root landing endpoint (`/`) that returns the machine
name plus links to the other three — enough for a smoke test (`curl /`)
to confirm the host boots, options bind, and the kestrel routing table
is alive. Swagger UI and `MapOpenApi` are gated to the Development
environment so production never serves the doc surface.

Add the Swagger UI package reference to `src/<App>.Api/<App>.Api.csproj`
alongside `Microsoft.AspNetCore.OpenApi`:

```xml
<PackageReference Include="Microsoft.AspNetCore.OpenApi" />
<PackageReference Include="Swashbuckle.AspNetCore.SwaggerUI" />
```

(The version is pinned in `Directory.Packages.props`. The package ships
the static UI assets only — the OpenAPI document itself is still
produced by `Microsoft.AspNetCore.OpenApi`, so there are no duplicate
generators.)

```csharp
using <App>.Api.Configuration;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();
builder.Services.AddHealthChecks();

builder.Services
    .AddOptions<DatabaseOptions>()
    .Bind(builder.Configuration.GetSection(DatabaseOptions.SectionName))
    .ValidateDataAnnotations()
    .ValidateOnStart();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseSwaggerUI(opts =>
    {
        opts.SwaggerEndpoint("/openapi/v1.json", "v1");
        opts.RoutePrefix = "swagger";
    });
    app.MapMethods("/swagger", ["GET", "HEAD"],
            () => Results.Redirect("/swagger/index.html"))
        .ExcludeFromDescription();
}

app.UseHttpsRedirection();
app.MapHealthChecks("/health");

app.MapGet("/", () => Results.Ok(new
{
    machine = Environment.MachineName,
    openapi = "/openapi/v1.json",
    swagger = "/swagger",
    health = "/health",
}));

app.Run();
```

`UseSwaggerUI` serves at `/swagger/index.html`; the `MapMethods("/swagger",
["GET","HEAD"])` redirect lets developers hit the bare prefix in a
browser without the 404 dance, and accepts `curl -I /swagger` (HEAD)
without 405 — common in container readiness probes and shell smoke
tests. `ExcludeFromDescription()` keeps the redirect out of the OpenAPI
document.

For each additional `*Options` class, repeat the `AddOptions<T>().Bind().
ValidateDataAnnotations().ValidateOnStart()` triad and extend the `/`
payload with any new probe routes — keep `/` as the single source of
truth for "what routes does this service expose".

After `dotnet new worker`, the default `Program.cs` is a minimal `Host.CreateApplicationBuilder` shell — leave it; the user wires MediatR/MassTransit at composition time. Add the same `AssemblyMarker.cs` and `AGENTS.md` pattern under `src/<App>.Service/`.

**Also fix the generated `Worker.cs`.** `dotnet new worker` emits
`_logger.LogInformation("Worker running at: {time}", DateTimeOffset.Now)` which
trips three gates at once: CA1848 (use compile-time logging delegates) and
CA1727 (PascalCase placeholders) — both promoted to errors by
`TreatWarningsAsErrors=true` on `src/` — and `quality.yaml`'s
`<APP-KEY>-QUAL-R005 library-no-datetime-now` rule, which is
`Program.cs`-excluded only. Replace the `LogInformation` call with a
`LoggerMessage` delegate AND use `DateTimeOffset.UtcNow` so the first build
is green and the semgrep gate stays quiet:

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
                LogHeartbeat(logger, DateTimeOffset.UtcNow, null);
            }
            await Task.Delay(1000, stoppingToken);
        }
    }
}
```

**`UtcNow`, not `Now`** — `quality.yaml`'s `*-QUAL-R005` rule fires on
`DateTimeOffset.Now` anywhere outside `Program.cs`, and `Worker.cs` is not
excluded. Time math should be UTC-internal regardless; tests against
heartbeats need a deterministic source.

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

### Companion settings — required for the host to start

`ValidateOnStart()` throws at process start if the bound section is missing
or fails DataAnnotations. That is the point of the doctrine, but it also
means a freshly-scaffolded host will refuse to run until each options
section has a value source. For every `<App>.{Api,Service}/Configuration/
*Options.cs` the skill writes, also wire a corresponding entry in
`appsettings.Development.json` so `dotnet run` works out of the box.

For `DatabaseOptions` (`Database` section):

```json
{
  "Logging": { "LogLevel": { "Default": "Information", "Microsoft.AspNetCore": "Warning" } },
  "Database": {
    "ConnectionString": "Host=localhost;Database=<app_lower>;Username=postgres;Password=postgres",
    "CommandTimeoutSeconds": 30
  }
}
```

`appsettings.json` (loaded in every env) stays free of secrets — only
non-sensitive defaults belong there. Production values flow in via env
vars (`Database__ConnectionString=...`) or a secret store; the local dev
placeholder above exists solely so the first `dotnet run` succeeds and so
that integration tests have a deterministic target.

For per-developer secrets that should not be committed, prefer
`dotnet user-secrets` over editing `appsettings.Development.json`:

```bash
dotnet user-secrets init --project src/<App>.Api/<App>.Api.csproj
dotnet user-secrets set "Database:ConnectionString" "Host=..." \
  --project src/<App>.Api/<App>.Api.csproj
```

`UserSecrets` only loads in the `Development` environment by default,
which is exactly the seam intended here.

**Environment-loading gotcha.** `appsettings.Development.json` only loads
when `ASPNETCORE_ENVIRONMENT=Development`. `dotnet run` (no flags) picks
that up from `Properties/launchSettings.json` (the `http` profile sets
it). But `dotnet run --no-launch-profile` — common in CI scripts and
smoke tests — defaults to `Production` and will trip `ValidateOnStart`
because `appsettings.json` deliberately holds no DB section. For
headless runs, set the env var explicitly:

```bash
ASPNETCORE_ENVIRONMENT=Development \
  dotnet run --project src/<App>.Api/<App>.Api.csproj --no-launch-profile
```

**macOS `/tmp` symlink gotcha.** On macOS `/tmp` is a symlink to
`/private/tmp`. If the repo lives under `/tmp/...` and was built once
via one form (`dotnet build /tmp/...`), then `dotnet run` invoked via
the other form (`dotnet run /private/tmp/...` or vice versa) can hit
`CS0006: Metadata file '…ref/Foo.dll' could not be found` because MSBuild
caches absolute paths in the `.csproj.lscache` and the two spellings
don't match. Either always use the same prefix, or `cd` into the canonical
path before running. Production paths (under `$HOME` or `/opt`) are
unaffected — this only bites local UAT runs from `/tmp`.

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
# PyYAML prereq — `python3 -c 'import yaml'` only ships with PyYAML
# installed (it's not in the stdlib). Guard the import so the scaffold
# fails loudly with an actionable message instead of a generic
# `ModuleNotFoundError: No module named 'yaml'` mid-script.
python3 -c 'import yaml' 2>/dev/null || {
    echo "PyYAML required for OWASP pack filtering. Installing via pip3..."
    pip3 install --quiet --user pyyaml || {
        echo "ERROR: pip3 install pyyaml failed. Install manually and retry."
        exit 1
    }
}

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

# Stryker.NET tool install.
#
# Write a project-scoped NuGet.Config at the repo root BEFORE running
# `dotnet tool install`. `<clear/>` drops every source inherited from
# the user's global NuGet.Config; `<add ... nuget.org />` is then the
# only feed any `dotnet` command run from this directory will consult.
#
# Do NOT rely on `dotnet tool install --source ...` for this. The
# `--source` flag does not actually prevent feed enumeration: NuGet
# still walks every source in the effective config, and if any of them
# (e.g. an Azure DevOps `msft_consumption` upstream feed) returns 401
# before nuget.org is reached, the install fails — even though
# nuget.org has the package. That is a Silent Fallback: the flag looks
# like it constrains the install, but it does not. A project-scoped
# NuGet.Config with `<clear/>` is the canonical, authoritative override.
# dotnet-stryker is published only on nuget.org; there is no reason to
# consult any private feed for it.
#
# Symptoms this prevents (grep-bait for future debuggers):
#   error NU1301: Unable to load the service index for source
#     https://pkgs.dev.azure.com/.../_packaging/msft_consumption/nuget/v3/index.json
#   Response status code does not indicate success: 401 (Unauthorized)
#
# protocolVersion="3" pins the NuGet v3 API (v2 is deprecated; v3 is
# what every current nuget.org client speaks).
cat > NuGet.Config <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>
</configuration>
EOF

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
        typeof(global::{{APP_NAME}}.Domain.AssemblyMarker).Assembly;

    private static readonly string[] ForbiddenDependencies =
    {
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
        "Microsoft.Extensions.Hosting",
    };

    /// <summary>Enforces {{APP_KEY}}-DOMAIN-R001 (CIL-level)</summary>
    [Fact]
    public void Domain_HasNoInfrastructureReferences()
    {
        var result = Types.InAssembly(DomainAssembly)
            .ShouldNot()
            .HaveDependencyOnAny(ForbiddenDependencies)
            .GetResult();

        Assert.True(result.IsSuccessful,
            $"Domain has forbidden refs: {string.Join(", ", result.FailingTypeNames ?? [])}");
    }

    /// <summary>Enforces {{APP_KEY}}-DOMAIN-R001 (reference-level)</summary>
    [Fact]
    public void Domain_HasNoInfrastructureProjectReferences()
    {
        var forbidden = new HashSet<string>(ForbiddenDependencies, StringComparer.Ordinal);
        var offenders = DomainAssembly.GetReferencedAssemblies()
            .Select(r => r.Name ?? string.Empty)
            .Where(forbidden.Contains)
            .ToArray();
        Assert.True(offenders.Length == 0,
            $"Domain has forbidden project references: {string.Join(", ", offenders)}");
    }
}
```

**Two tests, two failure modes.** `Domain_HasNoInfrastructureReferences` is
the CIL-level check: it scans every type in the Domain assembly and fails
if any of them *uses* a forbidden API (calls a method, names a type, etc.).
`Domain_HasNoInfrastructureProjectReferences` is the reference-level check:
it walks `DomainAssembly.GetReferencedAssemblies()` and fails if the csproj
declares a forbidden `<ProjectReference>` even when no code uses the
referenced types yet. Without the second test the first is a **Paper
Tiger** on an empty scaffold — adding `<ProjectReference Include="...App.
Persistence..." />` to `App.Domain.csproj` leaves zero CIL-level usages
until someone writes the first `new SomePersistenceType()`, and the
CIL-only test stays green during that window. Defense in depth:
`.semgrep/.../{layer}.yaml` catches the csproj edit at lint time; this
second test catches it at build time. Both must pass.

**`global::` prefix on `typeof(...)`** — the test class lives in `{{APP_NAME}}.Tests.Unit.Architecture`. Without `global::`, the C# compiler resolves `{{APP_NAME}}.Domain` against the enclosing namespace first, looking for `{{APP_NAME}}.Tests.Unit.Architecture.{{APP_NAME}}.Domain` and failing with CS0234. The `global::` prefix forces root-namespace resolution.

---

## Phase-1 → Phase-2 handoff

After Phase-1 completes successfully (solution builds, arch tests pass on
empty scaffold), check whether Phase-2 (domain populate) should run.

The handoff asks for explicit consent because Phase-2 overwrites
generated files on every run. Auto-running whenever `<module>` tags
appear would silently destroy in-progress edits the moment PREREQ-CHECK
passes — a Silent Fallback. The prompt is the **Sensor** that prevents
that failure mode.

### Step H1: Scan tech-design for `<module>` tags

Run: `grep -cE '<module[ >]' docs/tech-design/{{SLUG}}.md`

(Matches `<module name="X">`, `<module>`, and `<module name=foo>`. This is intentionally broader than a strict well-formedness check — PREREQ-CHECK step 5 has already failed loud on malformed tags before this point. H1 only needs to ask: *are there any module-tag-shaped tokens?*)

- If `0` → Phase-2 is skipped silently. Print a brief note:
  > *"Tech-design has no `<module>` tags. Phase-2 (domain populate)
  > skipped. See `skills/scaffold-with-guardrails/TECH-DESIGN-TAGS.md`
  > if you want to add them later."*
- If `≥ 1` → continue.

### Step H2: Prompt the user

Print exactly:

```
=========================================
Phase-2: Domain Populate
=========================================

Your tech-design has <module> tags. Phase-2 can read them and generate:
  - Domain entity classes (src/<App>.Domain/<Module>/)
  - Dapper row types (src/<App>.Persistence/<Module>/)
  - C# enums (src/<App>.Domain/<Module>/)
  - API DTOs (src/<App>.Api/<Module>/Contracts/)
  - Minimal route stubs (src/<App>.Api/<Module>/)
  - Test stubs (tests/<App>.Tests.Unit/, tests/<App>.Tests.Integration/)
  - Single bootstrap SQL migration (migrations/0001_initial_schema.sql, or db/migrations/ if that folder pre-exists)

All generated code throws NotImplementedException — boilerplate only,
no business logic. Re-running Phase-2 OVERWRITES generated files;
commit your work first.

Run Phase-2 now? [Y/n]
```

### Step H3: Branch on the answer

- **User answers `n` (or `no`):**
  > *"Phase-2 skipped. To run Phase-2 later, invoke the
  > `templates/csharp/scaffold-phase-2.md` playbook directly — re-running
  > this full skill against the existing scaffold will fail at
  > `dotnet new sln`."*

  Exit Phase-1 cleanly.

- **User answers `Y` (or `yes`, or empty/default):**
  Follow `templates/csharp/scaffold-phase-2.md` exactly. That playbook
  takes over from here.

### Re-running this skill

Phase-1 is **not idempotent today**. The `dotnet new sln` and
`dotnet new classlib` commands above have no existence checks, and the
CLI refuses to overwrite an existing solution. To make changes after
the initial scaffold:

- To run Phase-2 against an existing Phase-1 scaffold: invoke
  `templates/csharp/scaffold-phase-2.md` directly. Phase-2 *is* designed
  to re-run — it overwrites generated domain files on every run.
- To re-run Phase-1 itself: delete the existing solution directory and
  start over. (Future work: add `if [ ! -e "$APP.sln" ]` guards so
  Phase-1 short-circuits to the handoff when scaffold already exists.)
- Phase-2 OVERWRITES generated files. Commit your work before
  re-invoking Phase-2.

