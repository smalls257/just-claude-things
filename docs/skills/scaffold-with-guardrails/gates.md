# Gates

## What is a gate

A gate is the check itself: the semgrep rule firing, the NetArchTest assertion
failing, the coverlet threshold not being met. A hook is the git event handler
that *invokes* a gate — `pre-commit`, `pre-push`, or a CI workflow step. The
distinction matters because a single gate (e.g., semgrep) may be invoked by
multiple hooks (pre-commit runner `30-static-analysis` and the build target
`SemgrepLint`), and a single hook script may run several gates in sequence. The
gate owns the verdict; the hook owns the trigger and determines when that verdict
is sought. See `hooks.md` for hook lifecycle details.

## Gate inventory

| Gate | Tool | Runs at | Catches | Bypass key |
|---|---|---|---|---|
| Architecture rules | semgrep + NetArchTest | pre-commit + build | Cross-layer references that violate dependency direction | `--no-verify` (commit/push) |
| Security baseline | semgrep | pre-commit + build | Hardcoded creds, SQL injection, weak crypto, BinaryFormatter, CORS misconfig | `--no-verify` (commit/push) |
| Code quality | semgrep | pre-commit + build | Empty catch, throw ex, Console.WriteLine, DateTime.Now, new HttpClient, logger interpolation, IServiceProvider injection | `--no-verify` (commit/push) |
| Async correctness | semgrep | pre-commit + build | async void, .Result, .Wait, .GetAwaiter().GetResult | `--no-verify` (commit/push) |
| Dapper specifics | semgrep | pre-commit + build | Interpolated/concat SQL, public IQueryable leak | `--no-verify` (commit/push) |
| OWASP Top 10 | semgrep (vendored pack) | pre-commit + build | OWASP top-ten patterns, filtered to C#-applicable rules | `--no-verify` (commit/push) |
| Coverage threshold | coverlet + runsettings | pre-push + CI | Line/branch/method coverage below 70% | `--no-verify` (audited) |
| Lockfile mode | dotnet restore | CI only | Drifted lockfile vs `packages.lock.json` | n/a (CI is final word) |
| Mutation testing | Stryker.NET | nightly CI | Tests that pass without asserting | n/a (nightly, advisory) |
| OpenAPI contract | oasdiff (stub) | pre-push (when wired) | Breaking changes to public API surface | `--no-verify` (audited) |

> `SKIP_SEMGREP=1` skips only the **build-time** semgrep target in
> `Directory.Build.targets`; it does NOT bypass the pre-commit hook
> (`pre-commit.d/30-static-analysis`). To bypass the pre-commit semgrep gate,
> use `git commit --no-verify`. Both bypasses must be logged in
> `docs/rules-audit.md`.

## semgrep

### Where rules live

Semgrep is driven exclusively from vendored rules — no registry pulls, no telemetry.
After scaffolding, the repo contains:

```
.semgrep/
  <app-lower>/
    architecture.yaml   # cross-layer dependency-direction rules
    security.yaml       # security baseline (hardcoded creds, weak crypto, etc.)
    quality.yaml        # code-quality baseline (empty catch, Console.Write, etc.)
    async.yaml          # async-correctness rules (async void, .Result, .Wait)
    dapper.yaml         # Dapper-specific SQL and IQueryable rules
  packs/
    csharp.yaml         # vendored community C# security pack
    owasp-top-ten.yaml  # OWASP Top 10 pack filtered to C#-applicable rules
```

The per-app files under `.semgrep/<app-lower>/` are generated with placeholder
rule IDs (`<APP-KEY>-SEC-R001`, etc.) that the developer customises. The packs
under `.semgrep/packs/` are copied from `templates/common/semgrep-packs/`.

### Exact invocation

The pre-commit dispatcher runs `pre-commit.d/30-static-analysis`:

```bash
semgrep scan \
    --config "${REPO_ROOT}/.semgrep" \
    --metrics=off \
    --error \
    --quiet=false \
    <staged-source-files>
```

`SEMGREP_SEND_METRICS=off` is exported before the call. The gate self-skips
(exits 77) when no staged source files match `\.(cs|py|ts|tsx|js|jsx|go|java)$`.

The skill hand-writes `Directory.Build.targets` at the scaffolded repo root
(canonical block: `skills/scaffold-with-guardrails/templates/csharp/scaffold.md`
around line 544). The `SemgrepLint` target wires semgrep into every
`dotnet build` on the full `src/` tree when `SKIP_SEMGREP != '1'`:

```xml
<Target Name="SemgrepLint" BeforeTargets="Build" Condition="'$(SKIP_SEMGREP)' != '1'">
  <Exec Command="semgrep scan --config .semgrep/ src/ --error --quiet"
        WorkingDirectory="$(MSBuildThisFileDirectory)"
        IgnoreExitCode="false" />
</Target>
```

### Example failure

```
src/Bookworm.Application/Orders/PlaceOrderHandler.cs
  72│  var result = await _conn.QueryAsync<OrderRow>($"SELECT * FROM orders WHERE id = {orderId}");
     ╰─[bookworm-SEC-R002] Interpolated SQL passed to Dapper QueryAsync is a SQL-injection
       vector. Use parameters (@id) and pass them via an anonymous object.
       Severity: ERROR  Rule: bookworm-SEC-R002 (CWE-89)

Ran 47 rules on 12 files: 1 finding.
```

Semgrep exit 1 = findings (blocking). Exit 2 = config error. Exit 3+ = tool
error (triggers `gate_tool_error`, exits 3).

### How to extend

Add a rule to `.semgrep/<app-lower>/` following
`../../../skills/scaffold-with-guardrails/SEMGREP-RULE-COOKBOOK.md`. Every
rule needs a `metadata.arch-rule` ID matching an `AGENTS.md` row,
`severity: ERROR` for blocking gates, and a `violation:` field. Verify YAML
with `semgrep scan --config .semgrep/ --dry-run src/`, then smoke-test by
introducing the violation and confirming the hook blocks.

## NetArchTest

### Where rules live

NetArchTest assertions live in the unit-test project as a dedicated class:

```
tests/<App>.Tests.Unit/
  Architecture/
    DomainArchitectureTests.cs
    ApplicationArchitectureTests.cs
    (additional layers as needed)
```

Each class uses `NetArchTest.Rules` and anchors to the layer's `AssemblyMarker`
placed in each `src/<App>.<Layer>/` project at scaffold time.

### Exact invocation

NetArchTest tests run as part of the standard `dotnet test` pass. The
pre-commit gate `50-tests-unit` calls:

```bash
dotnet test --filter "FullyQualifiedName~Tests.Unit" \
            --nologo --no-restore --verbosity minimal
```

The `--no-restore` flag assumes restore has already happened (as it has by the
time the hook fires). For ad-hoc verification, drop `--no-restore`:
`dotnet test --filter "FullyQualifiedName~Tests.Unit" --nologo --verbosity minimal`.

This covers both functional unit tests and all architecture tests. Integration
tests run separately via the pre-push gate `10-tests-integration`.

### Example failure

```
  Failed Domain_HasNoInfrastructureReferences [2 ms]
  Message:
    Assert.True() Failure
    Expected: True
    Actual:   False
    Domain has forbidden refs:
      Bookworm.Domain.Orders.OrderRepository,
      Bookworm.Domain.Pricing.PriceCalculator

1 failed, 14 passed (8.3s)
```

The assertion names the failing types — exactly which Domain classes have
leaked a reference to Infrastructure or Persistence.

### How to extend

Add a fluent assertion to the matching `*ArchitectureTests.cs` class. The
standard pattern is:

```csharp
[Fact]
public void Application_HasNoPersistenceReferences()
{
    var result = Types.InAssembly(ApplicationAssembly)
        .ShouldNot()
        .HaveDependencyOnAny("{{APP_NAME}}.Persistence")
        .GetResult();

    Assert.True(result.IsSuccessful,
        $"Application has forbidden refs: {string.Join(", ", result.FailingTypeNames ?? [])}");
}
```

Each test should map to a rule ID in `AGENTS.md` (e.g., `<APP-KEY>-DOMAIN-R002`).
Add a matching semgrep rule to `.semgrep/<app-lower>/` where the violation is
also detectable at the file/import level — semgrep fires at commit time,
NetArchTest fires at compile/test time (belt-and-braces).

## coverlet + threshold

### Where rules live

Coverage configuration is at the repo root:

```
coverlet.runsettings
```

The threshold is encoded in the `<Configuration>` block of the
`XPlat code coverage` data collector:

```xml
<Threshold>70</Threshold>
<ThresholdType>line,branch,method</ThresholdType>
<ThresholdStat>total</ThresholdStat>
```

Test projects and generated code are excluded:

```xml
<Exclude>[*.Tests.*]*,[*]*.AssemblyMarker,[*]*.Migrations.*</Exclude>
<ExcludeByAttribute>GeneratedCodeAttribute,CompilerGeneratedAttribute</ExcludeByAttribute>
```

### Exact invocation

```bash
dotnet test --collect:"XPlat Code Coverage" --settings coverlet.runsettings
```

Run as a CI step (recommended — keeps push fast) or extend
`pre-push.d/10-tests-integration` to pass `--settings`. Coverlet exits
non-zero when any of line, branch, or method coverage falls below 70%.

### Example failure

```
Calculating coverage result...
  Generating report 'TestResults/*/coverage.cobertura.xml'
+--------+-----------+-------------+------------+
| Module | Line      | Branch      | Method     |
+--------+-----------+-------------+------------+
| Bookworm.Application | 61.3% | 54.2% | 68.0% |
+--------+-----------+-------------+------------+

[ERROR]: Branch coverage below threshold: 54.2% < 70%
[ERROR]: Method coverage below threshold: 68.0% < 70%

Build FAILED.
```

### How to extend

Raise `<Threshold>` in `coverlet.runsettings` as the suite matures — 70% is
the floor. Add exclusions to `<Exclude>` using `[AssemblyGlob]TypeGlob` syntax.
Lowering the threshold requires a recorded decision in `docs/rules-audit.md`.

## lockfile mode

### Where rules live

Lockfile mode is controlled in `Directory.Build.props` at the repo root:

```xml
<RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
<RestoreLockedMode Condition="'$(CI)' == 'true'">true</RestoreLockedMode>
```

`RestoreLockedMode` activates when `CI=true` (set automatically by GitHub
Actions). Local restores are unrestricted to avoid blocking dependency updates.
Each project accumulates a `packages.lock.json` on first restore; these files
must be committed and kept in sync with `.csproj` changes.

### Exact invocation

```bash
dotnet restore
```

No flags needed in CI — `RestoreLockedMode=true` is set by the MSBuild property.
NuGet fails the restore if the resolved graph does not match the committed
`packages.lock.json`.

### Example failure

```
error NU1004: The packages lock file is inconsistent with the project
dependencies so restore can't be run in locked mode. Please disable
the RestoreLockedMode MSBuild property or delete the lock file and
run restore again.
  Mismatched packages:
    Npgsql: lock file has 9.0.3, project resolves 9.0.4
```

Fires when a `.csproj` is updated and the developer forgets to commit the
refreshed `packages.lock.json`.

### How to extend

No extension needed — the gate is configuration-only. To update a dependency:
run `dotnet restore` locally (unlocked mode, regenerates `packages.lock.json`),
then commit the `.csproj` change and updated lockfile together. To opt a project
out, set `<RestorePackagesWithLockFile>false</RestorePackagesWithLockFile>` in
that project's `.csproj` and record the exception in `docs/rules-audit.md`.

## stryker (nightly)

### Where rules live

Configuration lives at `stryker-config.json` (repo root).

```json
{
  "stryker-config": {
    "test-projects": ["tests/**/*.Tests.Unit.csproj"],
    "mutate": ["src/**/*.cs", "!src/**/Program.cs", "!src/**/AssemblyMarker.cs"],
    "reporters": ["html", "json", "progress"],
    "thresholds": { "high": 80, "low": 60, "break": 50 },
    "concurrency": 4
  }
}
```

Workflow: `.github/workflows/stryker-nightly.yml`, `cron: '0 6 * * *'` (06:00 UTC).

### Exact invocation

```bash
dotnet stryker --config-file stryker-config.json --reporter html --reporter json
```

The workflow uploads the HTML report as an artifact, then checks the mutation
score against `break` (50) via `jq` and exits non-zero if below threshold.

### Example failure

```
[Progress] Mutating Bookworm.Application (48 mutants)
[Progress] Mutating Bookworm.Domain (31 mutants)
...
Mutation score: 44.2 (79 killed / 179 total)
Threshold (break): 50

Killed:   79 (44.2%)
Survived: 94 (52.5%)
Timeout:   6  (3.3%)

Score is below the break threshold of 50. Exiting with non-zero exit code.
```

Survived mutants are the actionable output: code paths that existing tests
never actually assert. The HTML report (uploaded as a CI artifact) shows
which mutation on which line survived.

### How to extend

Lower `break` threshold only with a recorded decision in `docs/rules-audit.md`;
increasing it over time is the expected trajectory. Add exclusions to `mutate`
(e.g., `!src/**/Migrations/**`) for generated code. To run locally:
`dotnet stryker --config-file stryker-config.json`; add `--mutation-level Basic`
for a faster pass during investigation (full runs take 30–90 min).

## openapi-diff

### Where rules live

The workflow ships as a disabled stub at
`.github/workflows/openapi-diff.yml.disabled`. **Wired in but not yet
enforced** — until the stub is renamed to `.yml`, breaking API changes are not
caught here; semgrep, NetArchTest, and coverlet still run on every commit and
push. Rename to `.yml` once the API host exposes an OpenAPI document (via
`Microsoft.Extensions.ApiDescription.Server` and `dotnet getdocument`). A
committed baseline spec must exist at `docs/openapi/openapi.json`.

### Exact invocation (when activated)

The workflow triggers on PRs touching `src/**/*.cs`, `src/**/*.csproj`, or
`docs/openapi/**`. Steps: build the API with `SKIP_SEMGREP=1`, generate the
current spec via `dotnet getdocument`, fetch the base-branch spec from
`docs/openapi/openapi.json`, run `tufin/oasdiff-action/diff@main`
(informational), then run `tufin/oasdiff-action/breaking@main` with
`fail-on: ERR` — the blocking step:

```yaml
- name: Breaking-change check
  uses: tufin/oasdiff-action/breaking@main
  with:
    base: artifacts/openapi.base.json
    revision: artifacts/openapi.head.json
    fail-on: ERR
```

### Example failure (when wired)

*Illustrative format. Real `oasdiff` output is tabular (markdown table of
breaking changes); see `tufin/oasdiff` README for canonical examples.*

```
[oasdiff] Checking for breaking changes...
2 breaking changes found:

  error   [response-property-removed] GET /orders/{id} response 200
          removed property 'totalTax' from schema

  error   [request-property-required-value-added] POST /orders request body
          added required property 'taxCode'

Breaking changes are not allowed.
```

### How to extend

To activate: rename the workflow to `.yml`, configure `dotnet getdocument` in
the API `.csproj`, generate an initial `docs/openapi/openapi.json` from `main`,
and commit it. Every subsequent PR that introduces a breaking change will be
blocked. To allow an intentional break, bump the API version and update the
baseline in the same PR.

## Adding a new gate

Skipping any step leaves the gate either silent (not enforced) or a Black Box
(enforced but undocumented):

1. **Write the rule.** For semgrep, follow
   `../../../skills/scaffold-with-guardrails/SEMGREP-RULE-COOKBOOK.md` — include
   a `metadata.arch-rule` ID, a `violation:` field, and `severity: ERROR` for
   blocking gates. For NetArchTest, add a fluent `[Fact]` assertion to the
   matching `*ArchitectureTests.cs` under `tests/<App>.Tests.Unit/Architecture/`.

2. **Add a `.d/` runner script.** Create an executable script under
   `templates/common/githooks/pre-commit.d/` or `pre-push.d/`. Pattern:
   source `_output.sh`, applicability-check and `exit 77` when not applicable,
   tool-existence check, invoke, on failure call `gate_fail_block` and `exit 1`.
   Number the script to control execution order (e.g., `70-my-gate`).

3. **Document the gate here.** Add a row to the inventory table (tool, trigger,
   what it catches, bypass key) and a per-gate section (rules location, exact
   invocation, example failure, how to extend).

4. **Smoke-test.** Deliberately introduce the violation, confirm the hook
   blocks with the expected rule ID, then remove it and confirm clean pass.
   A gate that has never fired is a Black Box: you do not know it works.
