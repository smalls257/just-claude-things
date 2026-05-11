# C# Scaffold — Step-by-Step

Canonical scaffold the skill applies when the tech-design's stack is C# / .NET 9.
Skill grills briefly first, then runs these commands in the target repo.

## Grill questions (skill asks before scaffolding)

1. **App name** (PascalCase, e.g., `ExpensePortal`)
2. **Needs HTTP API?** → adds `<App>.Api` (WebAPI project)
3. **Needs background service / worker?** → adds `<App>.Service` (Worker project)
4. **Needs shared client SDK?** → adds `<App>.Client` (classlib)
   - If yes: **Client contracts from Domain types or pure DTOs?** (record decision)

## Scaffold commands

> **Rule:** Use CLI scaffolders (`dotnet new`, `dotnet add`) — never hand-roll `.csproj` or project files. Hand-rolling is Computational Friction.

```bash
APP=ExpensePortal
APP_LOWER=expense-portal

dotnet new sln -n "$APP"

# Core layers (always)
dotnet new classlib -n "$APP.Domain"         -o src/"$APP".Domain
dotnet new classlib -n "$APP.Application"    -o src/"$APP".Application
dotnet new classlib -n "$APP.Infrastructure" -o src/"$APP".Infrastructure
dotnet new classlib -n "$APP.Persistence"    -o src/"$APP".Persistence

# Conditional (per grill answers)
dotnet new webapi   -n "$APP.Api"            -o src/"$APP".Api           # if HTTP API
dotnet new worker   -n "$APP.Service"        -o src/"$APP".Service       # if worker
dotnet new classlib -n "$APP.Client"         -o src/"$APP".Client        # if client SDK

# Test projects (always)
dotnet new xunit    -n "$APP.Tests.Unit"        -o tests/"$APP".Tests.Unit
dotnet new xunit    -n "$APP.Tests.Integration" -o tests/"$APP".Tests.Integration

find . -name "*.csproj" | sort | xargs dotnet sln add

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

# NuGet packages (add --source if corporate NuGet feeds cause 401 before nuget.org)
dotnet add src/"$APP".Domain/"$APP".Domain.csproj package CSharpFunctionalExtensions
dotnet add src/"$APP".Application/"$APP".Application.csproj package CSharpFunctionalExtensions
dotnet add tests/"$APP".Tests.Unit/"$APP".Tests.Unit.csproj package NetArchTest.Rules
```

## Files the skill hand-writes after dotnet new

After `dotnet new`, the skill creates these files (generators don't produce them):

- `Directory.Build.targets` (root) — semgrep gate before every build
- `Directory.Packages.props` (root) — central package management
- `.semgrep/<app-lower>/<module-lower>.yaml` — one per module, per arch rule
- `tests/<App>.Tests.Unit/Architecture/<Module>ArchitectureTests.cs` — one per module
- `CLAUDE.md` (root) — from `CLAUDE-MD-TEMPLATE.md`
- `src/<App>.<Module>/AGENTS.md` — from `AGENTS-MD-TEMPLATE.md`, one per module
- `.claude/settings.json` — hook wiring
- `.claude/hooks/{pre-commit,pre-push,stop-neg-audit}.sh` — copied from this skill
- `src/<App>.<Module>/AssemblyMarker.cs` — one per module (required by NetArchTest to get assembly reference)

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
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/pre-commit.sh"
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

Note: Verify the exact `.claude/settings.json` hook schema against current Claude Code docs at scaffold time — the schema may evolve between skill versions.

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
                "{{APP_NAME}}.Infrastructure",
                "{{APP_NAME}}.Persistence",
                "Microsoft.EntityFrameworkCore",
                "Npgsql")
            .GetResult();

        Assert.True(result.IsSuccessful,
            $"Domain has forbidden refs: {string.Join(", ", result.FailingTypeNames ?? [])}");
    }
}
```
