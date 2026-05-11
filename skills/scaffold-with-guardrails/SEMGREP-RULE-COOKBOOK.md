# Semgrep Rule Cookbook

Reusable rule patterns for `scaffold-with-guardrails`. Each rule ships with a
`metadata.arch-rule` ID matching an `AGENTS.md` row and a matching NetArchTest test.

## No `catch (Exception) { return default; }` — Silent Fallback (C#)

```yaml
rules:
  - id: no-silent-exception-swallow
    pattern: |
      catch (Exception $E)
      {
        return $X;
      }
    message: "Silent fallback — surface the error; do not swallow."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <MODULE>-R001
      violation: Silent Fallback
```

## Domain may not reference Infrastructure or Persistence (C# .csproj)

```yaml
rules:
  - id: domain-no-infra-refs
    pattern-either:
      - pattern: |
          <ProjectReference Include="...$X.Infrastructure..." />
      - pattern: |
          <ProjectReference Include="...$X.Persistence..." />
    paths:
      include:
        - "src/*.Domain/*.csproj"
    message: "Domain may not reference Infrastructure or Persistence."
    severity: ERROR
    languages: [generic]
    metadata:
      arch-rule: <MODULE>-R002
      violation: Infected Core
```

## No `f-string` in structured log message (Python)

```yaml
rules:
  - id: no-fstring-in-log
    pattern-either:
      - pattern: $LOGGER.info(f"...")
      - pattern: $LOGGER.error(f"...")
      - pattern: $LOGGER.warning(f"...")
    message: "Use structured extra={...}, not f-strings, in log calls."
    severity: ERROR
    languages: [python]
    metadata:
      arch-rule: <MODULE>-R003
      violation: Leaky Narrative
```

## No `shell=True` in subprocess calls (Python)

```yaml
rules:
  - id: no-shell-true
    pattern: subprocess.$F(..., shell=True, ...)
    message: "shell=True is a command-injection risk. Pass list[str] instead."
    severity: ERROR
    languages: [python]
    metadata:
      arch-rule: <MODULE>-R004
```

## Application layer may not reference Persistence (C# .csproj)

```yaml
rules:
  - id: application-no-persistence-refs
    pattern: |
      <ProjectReference Include="...$X.Persistence..." />
    paths:
      include:
        - "src/*.Application/*.csproj"
    message: "Application layer may not reference Persistence directly."
    severity: ERROR
    languages: [generic]
    metadata:
      arch-rule: <MODULE>-R005
      violation: Infected Core
```

## Enterprise C# rule bundle

The rules below are **cross-cutting** — they apply across all layers and are
usually written to `.semgrep/<app-lower>/{security,quality,async,dapper}.yaml`
rather than per-layer files. Substitute `<APP>` for the app name (e.g.
`bookworm`) and `<APP-KEY>` for the upper-case key (e.g. `BOOKWORM`).

### security.yaml — production security baseline

```yaml
rules:
  - id: <APP>-no-hardcoded-connection-string
    pattern-regex: '"[^"]*Server\s*=[^;]+;\s*Database\s*=[^;]+;\s*User\s*Id\s*=[^;]+;\s*Password\s*=\s*[^${"][^";]+"'
    paths:
      include: ["src/**/*.cs"]
      exclude: ["src/**/Migrations/**", "tests/**"]
    message: "Hardcoded credentials in connection string. Use IConfiguration / user-secrets / env vars."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-SEC-R001
      violation: Black Box
      cwe: "CWE-798"

  - id: <APP>-no-sql-injection-dapper-interpolation
    pattern-either:
      - pattern: $CONN.Query<$T>($"...{$X}...", ...)
      - pattern: $CONN.QueryAsync<$T>($"...{$X}...", ...)
      - pattern: $CONN.Execute($"...{$X}...", ...)
      - pattern: $CONN.ExecuteAsync($"...{$X}...", ...)
    paths:
      include: ["src/**/*.cs"]
    message: "Interpolated SQL passed to Dapper Query/Execute is a SQL-injection vector. Use parameters (@name) and pass them via an anonymous object."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-SEC-R002
      violation: Black Box
      cwe: "CWE-89"

  - id: <APP>-no-weak-hash
    pattern-either:
      - pattern: MD5.Create()
      - pattern: MD5.HashData(...)
      - pattern: SHA1.Create()
      - pattern: SHA1.HashData(...)
    paths:
      include: ["src/**/*.cs"]
    message: "MD5 / SHA1 are broken. Use SHA256/SHA512 or Argon2id for passwords."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-SEC-R003
      violation: Black Box
      cwe: "CWE-327"

  - id: <APP>-no-weak-cipher
    pattern-either:
      - pattern: DES.Create()
      - pattern: TripleDES.Create()
      - pattern: new RC2CryptoServiceProvider()
    paths:
      include: ["src/**/*.cs"]
    message: "DES / 3DES / RC2 are obsolete. Use AES-256-GCM."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-SEC-R004
      violation: Black Box
      cwe: "CWE-327"

  - id: <APP>-no-insecure-random-for-secrets
    pattern-either:
      - pattern: new Random().Next(...)
      - pattern: new Random().NextBytes(...)
    paths:
      include: ["src/**/*.cs"]
      exclude: ["src/**/*Test*.cs"]
    message: "System.Random is predictable. For tokens/secrets use RandomNumberGenerator.GetBytes."
    severity: WARNING
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-SEC-R005
      violation: Black Box
      cwe: "CWE-338"

  - id: <APP>-no-binary-formatter
    pattern-either:
      - pattern: new BinaryFormatter()
      - pattern: BinaryFormatter.$M(...)
    paths:
      include: ["src/**/*.cs"]
    message: "BinaryFormatter is insecure-by-design (deprecated). Use System.Text.Json."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-SEC-R006
      violation: Black Box
      cwe: "CWE-502"

  - id: <APP>-no-cors-any-origin-with-credentials
    pattern: $X.AllowAnyOrigin().AllowCredentials()
    paths:
      include: ["src/**/*.cs"]
    message: "AllowAnyOrigin + AllowCredentials exposes auth cookies. Pin specific origins."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-SEC-R008
      violation: Black Box
      cwe: "CWE-942"
```

### quality.yaml — code quality baseline

```yaml
rules:
  - id: <APP>-no-empty-catch
    # Bare `catch { }` (no type) does not round-trip through the C# AST parser,
    # so we use a regex pattern. The typed variant (next rule) uses the AST.
    pattern-regex: 'catch\s*\{\s*\}'
    paths:
      include: ["src/**/*.cs"]
    message: "Empty bare catch swallows failures. Surface or log with context."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-QUAL-R001
      violation: Silent Fallback

  - id: <APP>-no-throw-ex
    pattern: |
      catch ($T $E)
      {
        ...
        throw $E;
      }
    paths:
      include: ["src/**/*.cs"]
    message: "`throw $E` rewrites the stack trace. Use bare `throw;`."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-QUAL-R003
      violation: Black Box

  - id: <APP>-no-console-writeline-in-src
    pattern-either:
      - pattern: Console.WriteLine(...)
      - pattern: Console.Write(...)
    paths:
      include: ["src/**/*.cs"]
      exclude: ["src/**/Program.cs"]
    message: "Use ILogger<T>, not Console. Structured logging is observable; Console is a Black Box."
    severity: WARNING
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-QUAL-R004
      violation: Black Box

  - id: <APP>-no-datetime-now
    pattern-either:
      - pattern: DateTime.Now
      - pattern: DateTime.Today
      - pattern: DateTimeOffset.Now
    paths:
      include: ["src/**/*.cs"]
      exclude: ["src/**/Program.cs"]
    message: "DateTime.Now is server-timezone-coupled and untestable. Use IClock or UtcNow at the boundary."
    severity: WARNING
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-QUAL-R005
      violation: Infected Core

  - id: <APP>-no-direct-httpclient-new
    pattern: new HttpClient(...)
    paths:
      include: ["src/**/*.cs"]
      exclude: ["tests/**"]
    message: "Direct `new HttpClient()` leaks sockets and ignores Polly policies. Inject IHttpClientFactory."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-QUAL-R006
      violation: Computational Friction

  - id: <APP>-no-interpolation-in-logger
    pattern-either:
      - pattern: $LOG.LogInformation($"...")
      - pattern: $LOG.LogWarning($"...")
      - pattern: $LOG.LogError($"...")
      - pattern: $LOG.LogDebug($"...")
      - pattern: $LOG.LogCritical($"...")
    paths:
      include: ["src/**/*.cs"]
    message: "Interpolated string in logger destroys structured fields. Use templates."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-QUAL-R007
      violation: Leaky Narrative

  - id: <APP>-no-service-locator
    # Constructor-parameter pattern doesn't parse in semgrep C#; flag the
    # runtime resolution call instead (which is the actual smell).
    pattern-either:
      - pattern: $SP.GetRequiredService<$T>()
      - pattern: $SP.GetService<$T>()
    paths:
      include: ["src/**/*.cs"]
      exclude:
        - "src/<App>.Api/Program.cs"
        - "src/<App>.Service/Program.cs"
    message: "Resolving services from IServiceProvider at runtime is the Service Locator anti-pattern. Inject concrete dependencies via constructor."
    severity: WARNING
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-QUAL-R008
      violation: Leaky Narrative
```

### async.yaml — async correctness

```yaml
rules:
  - id: <APP>-no-async-void
    pattern-either:
      - pattern: |
          public async void $M(...) { ... }
      - pattern: |
          private async void $M(...) { ... }
      - pattern: |
          internal async void $M(...) { ... }
      - pattern: |
          protected async void $M(...) { ... }
    paths:
      include: ["src/**/*.cs"]
    message: "`async void` swallows exceptions. Use `async Task`."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-ASYNC-R001
      violation: Silent Fallback

  - id: <APP>-no-task-result
    pattern: $T.Result
    paths:
      include: ["src/**/*.cs"]
      exclude: ["tests/**"]
    message: "`.Result` blocks and deadlocks. `await` end-to-end."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-ASYNC-R002
      violation: Computational Friction

  - id: <APP>-no-task-wait
    pattern-either:
      - pattern: $T.Wait()
      - pattern: $T.WaitAll(...)
      - pattern: $T.WaitAny(...)
    paths:
      include: ["src/**/*.cs"]
      exclude: ["tests/**"]
    message: "`.Wait()` blocks and deadlocks. `await` end-to-end."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-ASYNC-R003
      violation: Computational Friction

  - id: <APP>-no-getawaiter-getresult
    pattern: $T.GetAwaiter().GetResult()
    paths:
      include: ["src/**/*.cs"]
      exclude: ["tests/**", "src/**/Program.cs"]
    message: "Sync-over-async. `await` end-to-end."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-ASYNC-R004
      violation: Computational Friction
```

### dapper.yaml — Dapper specifics

Scaffolded apps default to Dapper + Npgsql + DTO row types (see
`templates/csharp/scaffold.md` for rationale). If a particular project
deliberately uses EF Core, replace this file with the EF-Core-equivalent
rule set and flag it in the scaffold output.

```yaml
rules:
  - id: <APP>-dapper-no-interpolated-sql-query
    pattern-either:
      - pattern: $CONN.Query<$T>($"...{$X}...", ...)
      - pattern: $CONN.QueryAsync<$T>($"...{$X}...", ...)
      - pattern: $CONN.QueryFirst<$T>($"...{$X}...", ...)
      - pattern: $CONN.QueryFirstAsync<$T>($"...{$X}...", ...)
      - pattern: $CONN.QueryFirstOrDefault<$T>($"...{$X}...", ...)
      - pattern: $CONN.QueryFirstOrDefaultAsync<$T>($"...{$X}...", ...)
      - pattern: $CONN.QuerySingle<$T>($"...{$X}...", ...)
      - pattern: $CONN.QuerySingleAsync<$T>($"...{$X}...", ...)
      - pattern: $CONN.QuerySingleOrDefault<$T>($"...{$X}...", ...)
      - pattern: $CONN.QuerySingleOrDefaultAsync<$T>($"...{$X}...", ...)
      - pattern: $CONN.Execute($"...{$X}...", ...)
      - pattern: $CONN.ExecuteAsync($"...{$X}...", ...)
      - pattern: $CONN.ExecuteScalar<$T>($"...{$X}...", ...)
      - pattern: $CONN.ExecuteScalarAsync<$T>($"...{$X}...", ...)
    paths:
      include: ["src/**/*.cs"]
    message: "Dapper Query/Execute with interpolated SQL is a SQL-injection vector. Use parameters (@name)."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-DAPPER-R001
      violation: Leaky Narrative
      cwe: "CWE-89"

  - id: <APP>-dapper-no-concat-sql-query
    pattern-either:
      - pattern: $CONN.Query<$T>("..." + $X + "...", ...)
      - pattern: $CONN.QueryAsync<$T>("..." + $X + "...", ...)
      - pattern: $CONN.Execute("..." + $X + "...", ...)
      - pattern: $CONN.ExecuteAsync("..." + $X + "...", ...)
    paths:
      include: ["src/**/*.cs"]
    message: "String concatenation in Dapper SQL is a SQL-injection vector. Use parameters (@name)."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-DAPPER-R002
      violation: Leaky Narrative
      cwe: "CWE-89"

  - id: <APP>-dapper-no-sync-on-async-stack
    pattern-either:
      - pattern: $CONN.Query<$T>(...)
      - pattern: $CONN.QueryFirst<$T>(...)
      - pattern: $CONN.QueryFirstOrDefault<$T>(...)
      - pattern: $CONN.QuerySingle<$T>(...)
      - pattern: $CONN.QuerySingleOrDefault<$T>(...)
      - pattern: $CONN.Execute(...)
      - pattern: $CONN.ExecuteScalar<$T>(...)
    paths:
      include:
        - "src/<App>.Persistence/**/*.cs"
    message: "Prefer the async Dapper overloads (QueryAsync / ExecuteAsync). Sync DB calls block thread-pool threads."
    severity: WARNING
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-DAPPER-R003
      violation: Computational Friction

  - id: <APP>-no-iqueryable-leak
    pattern-either:
      - pattern: |
          public IQueryable<$T> $M(...) { ... }
      - pattern: |
          public IQueryable $M(...) { ... }
    paths:
      include:
        - "src/<App>.Persistence/**/*.cs"
        - "src/<App>.Infrastructure/**/*.cs"
    message: "Public IQueryable leaks the query engine. Materialise in the repository."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-DAPPER-R004
      violation: Leaky Narrative

  - id: <APP>-persistence-no-public-connection
    # Auto-property patterns do not parse in semgrep C#; use a regex that
    # matches both `public IDbConnection X { get; ... }` and method returns.
    pattern-regex: 'public\s+(IDbConnection|NpgsqlConnection|DbConnection)\s+\w+\s*(\{\s*get\s*;|\([^)]*\))'
    paths:
      include:
        - "src/<App>.Persistence/**/*.cs"
    message: "Connection types must not leak through the repository public API as property or method return type. Connections stay private."
    severity: ERROR
    languages: [csharp]
    metadata:
      arch-rule: <APP-KEY>-DAPPER-R005
      violation: Leaky Narrative
```

## Usage rules

- Every rule ships with a `metadata.arch-rule` ID matching an `AGENTS.md` table row.
- Every rule has a matching NetArchTest test in the unit tests project where the violation is detectable structurally (some semgrep rules — e.g. interpolation-in-logger — are pattern-only).
- Per-layer files (`domain.yaml`, `application.yaml`, etc.) hold architecture-direction rules; cross-cutting files (`security.yaml`, `quality.yaml`, `async.yaml`, `dapper.yaml`) hold C#-wide rules.
- Severity discipline: ERROR = build failure; WARNING = visible but non-blocking; INFO = informational only. Tighten WARNINGs to ERRORs as the codebase grows.
- Never suppress a rule with `// semgrep: ignore` or `SKIP_SEMGREP=1`.
- If a rule is a false positive, fix the rule — do not suppress it.
