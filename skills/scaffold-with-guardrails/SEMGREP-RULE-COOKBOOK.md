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

## Usage rules

- Every rule ships with a `metadata.arch-rule` ID matching an `AGENTS.md` table row.
- Every rule has a matching NetArchTest test in the unit tests project.
- Never suppress a rule with `// semgrep: ignore` or `SKIP_SEMGREP=1`.
- If a rule is a false positive, fix the rule — do not suppress it.
