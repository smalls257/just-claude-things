# Convention Scan — Phase-1.5 reference

Phase-1.5 runs after Phase-1 (tech-design validation) and before Phase-2 (code
generation). It harvests reusable patterns from a canonical reference repo and
persists adoption decisions for Phase-2 to graft.

## When the scan runs

- Triggered automatically by the scaffold orchestrator after Phase-1 validate
- Triggered manually by re-running `scripts/convention-scan.sh`
- Skipped when no `--reference-repo` is supplied (Phase-2 falls back to stub
  templates with informational comments for each unadopted layer)

## What the dev sees

For each detected pattern, a TTY card:

```
======================================================================
DETECTOR: auth-jwt-bearer — JWT bearer auth
SOURCE:   src/Auth/JwtExtensions.cs:L12-L45
PACKAGES: Microsoft.AspNetCore.Authentication.JwtBearer:8.0.5
----------------------------------------------------------------------
public static class JwtExtensions
{
    public static IServiceCollection AddJwtAuth(this IServiceCollection s)
    { ... }
}
----------------------------------------------------------------------
Adopt auth-jwt-bearer? (y/n):
```

The prompt loops until `y` or `n` — invalid input re-prompts. Ctrl-C writes
`.scaffold/staged/.partial-decisions.json` and exits; the next invocation
resumes from where you stopped.

## Decision lifecycle

1. **Adopted** → `<adopted>` entry in `<conventions>` block + verbatim staged
   snippet under `.scaffold/staged/<id>.cs`
2. **Rejected** → `<rejected>` entry with `reason="dev-skipped"` (preserved
   on re-run so previous defaults are kept)
3. **Dev-named adopted** → `<dev-named>` entry; Phase-2 grafts at
   `// {{CONVENTION:dev-<target>}}` marker
4. **Discovered adopted** → `<discovered>` entry; Phase-2 grafts at
   `// {{CONVENTION:discovered-<name>}}` marker

## Re-run path

The orchestrator detects an existing `<conventions>` block on boot and
re-scans, replacing the block atomically (tempfile + rename). Previous
adopt/reject decisions become defaults for the new card prompts.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `REGISTRY_PARSE_ERROR` | YAML syntax in a detector file | Fix the offending detector YAML named in the error |
| `DUPLICATE_ID` | Two skill detectors with same `id` | Rename one or set `replaces:` on the project override |
| `SELF_SCAN` | Reference repo == target repo | Point `--reference-repo` to a different repo |
| `REF_DIRTY` | Reference repo has uncommitted changes | Commit/stash, or confirm continue at the prompt |
| `EXTRACT_FAILED` | Truncated/malformed file at hit | Fix the source file or exclude via signal regex tuning |
| `EQUAL_PRIORITY_OVERLAP` | Two detectors at same priority claim same region | Adjust `priority` in one of them |
| `OVERWRITE_EMPTY` | Re-scan produced empty decisions over non-empty existing block | Re-run with `--confirm-overwrite-empty` |
| `MISSING_STAGED` (Phase-2) | Adopted entry has no staged file | Re-run Phase-1.5 |
| `NO_SLOT` (Phase-2) | Adopted layer missing `// {{CONVENTION:<layer>}}` marker | Add the marker to the Phase-2 template |
| `REFERENCE_DRIFT` (Phase-2) | Reference repo HEAD moved since scan | Re-run Phase-1.5 to refresh |
