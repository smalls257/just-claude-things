# Phase-2: Domain Populate

> Invoked from `scaffold.md` Phase-1 final step when `<module>` tags are
> present in the tech-design doc and the user accepts the Phase-2 prompt.
> Reads tagged sections, emits typed C# skeletons that compile and fail
> loud at runtime.
>
> See `../../TECH-DESIGN-TAGS.md` for the tag schema.

## Entry conditions

You only enter Phase-2 if all of the following are true:

1. Phase-1 (`scaffold.md`) completed successfully — solution builds, arch
   tests pass on empty scaffold.
2. The tech-design doc at `docs/tech-design/<slug>.md` contains at least
   one `<module name="...">` block.
3. `../../PREREQ-CHECK.md` tag well-formedness validation passed.
4. The user answered **Y** to the Phase-1 → Phase-2 handoff prompt.

The prose list above is the intent. The pre-flight gate below is the
**tripwire** — without it, a subagent can silently scope-narrow Phase-1
(skip `.semgrep/`, `AGENTS.md`, NetArchTest, hooks) and still enter
Phase-2, producing a code-only scaffold with no governance. That is the
Silent Fallback this skill exists to prevent.

## Pre-flight gate (mandatory — do not skip)

Before any pre-check, parsing, or generation work, run **every** check
below from the repo root. **Collect all failures** and emit a single
batched report. Abort on any failure.

### Tripwire 1: Phase-1 artifact inventory

Each path below must exist. For directories, "exist" means present and
non-empty.

| Path                                                                | What it proves                                                          |
|---------------------------------------------------------------------|-------------------------------------------------------------------------|
| `*.sln`                                                             | `dotnet new sln` ran                                                    |
| `global.json`                                                       | SDK pin emitted                                                         |
| `Directory.Build.props`                                             | TWAE / lockfile-mode / InvariantGlobalization wired                     |
| `Directory.Build.targets`                                           | semgrep gate wired into `BeforeTargets="Build"`                         |
| `Directory.Packages.props`                                          | central package management active                                       |
| `coverlet.runsettings`                                              | coverage threshold (70%) configured                                     |
| `.editorconfig`                                                     | shared IDE baseline                                                     |
| `CLAUDE.md`                                                         | Six Principles + Violation Guide embedded                               |
| `.semgrep/`                                                         | semgrep rule directory exists                                           |
| `.semgrep/*/security.yaml`                                          | cross-cutting security rules                                            |
| `.semgrep/*/quality.yaml`                                           | code-quality baseline                                                   |
| `.semgrep/*/async.yaml`                                             | async correctness rules                                                 |
| `.claude/settings.json`                                             | hook wiring                                                             |
| `.claude/hooks/pre-commit.sh`                                       | pre-commit gate                                                         |
| `.claude/hooks/pre-push.sh`                                         | pre-push gate                                                           |
| `.github/PULL_REQUEST_TEMPLATE.md`                                  | PR-template gate checklist                                              |
| `src/*/AGENTS.md` (≥ 1)                                             | at least one per-layer governance doc                                   |
| `src/*/AssemblyMarker.cs` (≥ 1)                                     | at least one NetArchTest assembly anchor                                |
| `tests/*.Tests.Unit/Architecture/*ArchitectureTests.cs` (≥ 1)       | at least one NetArchTest exists                                         |
| `BYPASS-POLICY.md`                                                  | gate-bypass discipline doc copied from `templates/common/`              |
| `BRANCH-PROTECTION.md`                                              | branch-protection requirements doc copied from `templates/common/`      |
| `.githooks/pre-commit`                                              | gate-system local pre-commit hook                                       |
| `.githooks/pre-push`                                                | gate-system local pre-push hook                                         |
| `.githooks/commit-msg`                                              | gate-system commit-msg hook (enforces `Verified:` trailer when needed)  |
| `scripts/bootstrap.sh`                                              | reproducible bootstrap (`./scripts/bootstrap.sh` from scaffold step)    |
| `.tools/manifest.toml`                                              | pinned tool versions for `tools-pin-check.yml`                          |
| `.semgrep/packs/csharp.yaml`                                        | OWASP / C# rules pack copied from `templates/common/`                   |
| `.semgrep/packs/owasp-top-ten.yaml`                                 | OWASP top-ten rules pack copied from `templates/common/`                |
| `.github/workflows/gates-backstop.yml.disabled`                     | server-side backstop workflow (shipped disabled per scaffold step)      |
| `.github/workflows/tools-pin-check.yml`                             | tool-pin drift workflow                                                 |
| `.github/workflows/stryker-nightly.yml`                             | nightly Stryker mutation-test workflow                                  |
| `.gates.toml`                                                       | gate config (thresholds, rule packs in play)                            |
| `.gitconfig.gates`                                                  | per-repo git config that activates `.githooks/`                         |
| `stryker-config.json`                                               | Stryker mutation-test config                                            |
| `NuGet.Config`                                                      | project-scoped feed override (`<clear/>` + nuget.org); prevents inherited Azure DevOps feed from wedging `dotnet tool install` with 401 (Silent Fallback the scaffold step exists to avoid) |
| `docs/rules-audit.md`                                               | rules-audit doc for the OWASP / gate-system layer                       |

### Running the gate

All three tripwires live in a single harness script. Run it from the
target repo root:

```bash
bash "$SCAFFOLD/scripts/phase2-preflight.sh"
```

- Exit `0` → all 3 tripwires passed; proceed to `## Process overview`.
- Exit `1` → batched failure report printed to stderr (missing artifacts list + verbatim `dotnet build` / `dotnet test` output if either failed). Abort Phase-2. Do not pre-check, do not parse, do not generate. Fix the root cause (re-run Phase-1 to completion or hand-author the missing artifacts) and re-run.

The harness collects every failure before exiting — Sensor over fail-fast,
because the dev needs the full picture in one shot. Build/test failures
are reported with verbatim `dotnet` output indented under their heading.

The gate-system rows in the inventory above are not decorative.
`BYPASS-POLICY.md` and the PR template reference the `Verified:` trailer
enforced by `.githooks/commit-msg` and the `gates-backstop.yml` workflow.
If those files are absent, the docs become Forensic Coding (instructions
for plumbing that does not exist) and the Phase-2 scaffold ships with a
broken governance story. This gate is the Sensor that prevents that drift.

## Process overview

```
1. Pre-check — parse all <module> blocks, validate cross-references
2. (If gaps) Gap report → user prompts: fix and re-run, or proceed with stubs
3. Parse tech-design to JSON (phase2-parse.py) — one task per work item
4. TaskCreate per task, dispatch implementer subagent per task,
   reading the matching templates/csharp/phase2-task-templates/*.md
5. Post-build sensor (phase2-postbuild.sh): dotnet build + endpoint-wiring check
6. Summary report
```

## Pre-check

Before generating any files, validate the tag graph end-to-end. Fail loud
on every problem. **No silent fixes.** Tag well-formedness (e.g., balanced
`<module>` tags, parseable attributes) was already enforced by
`../../PREREQ-CHECK.md` per entry condition 3; this section validates the
**semantic cross-references** between modules, entities, enums, contracts,
and endpoints.

### Step P1: Parse all `<module>` blocks

For each `<module name="X">` block in the tech-design doc:

1. Record module name `X`.
2. For each inner tag (`<entities>`, `<enums>`, `<contracts>`, `<endpoints>`):
   - List each `### H3` item.
   - For entities: extract the SQL fence content (the `CREATE TABLE ...`
     statement). If no SQL fence inside an entity H3 → record as a
     **structural failure** (collected and reported by Step P4 alongside
     cross-reference failures, so the user sees all problems at once).

3. For each entity, parse the SQL CREATE TABLE to determine:
   - Column names and types (UUID, BIGINT, TEXT, TIMESTAMPTZ, etc.)
   - PK column
   - Each `CHECK (col IN ('a','b','c'))` → links to an `<enums>` entry
   - Each `*_id UUID NOT NULL` → FK candidate (P3 determines whether it is same-module or cross-module)

4. Record contracts and endpoints by name.

### Step P2: Build the type table

Build a single global table:

| Module | Kind | Name | References |
|---|---|---|---|
| Orders | entity | Order | OrderStatus (enum), CustomerId (Guid, cross-module ID — OK) |
| Orders | enum | OrderStatus | (none) |
| Orders | contract | CreateOrderRequest | (none) |
| Orders | endpoint | POST /orders | CreateOrderRequest, OrderResponse |
| ... | ... | ... | ... |

Print this table to the user before proceeding.

### Step P3: Validate cross-references

Run each rule. Collect all failures before prompting:

1. **Endpoint → DTO refs.** For each `<endpoint>`, the Request and Response
   types must exist in some `<contracts>` block (same module or `Shared`).
   - Failure: `"Endpoint {Module}.{POST /path} references undefined DTO {Name}"`

2. **Entity column enum refs.** If an entity column has `CHECK (col IN
   ('a','b','c'))`, that enum must exist in `<enums>` of the same module
   **or in `<module name="Shared">`'s `<enums>`**.
   - Failure: `"Entity {Module}.{Entity}.{column} CHECK constraint references undefined enum {Name}"`

3. **Cross-module entity refs forbidden.** Two surfaces to scan:
   - **In `<contracts>` field lists:** any field typed as
     `{OtherModule}.{Entity}` or as `{Entity}` where `{Entity}` is defined
     in a different module's `<entities>` block.
   - **In `<entities>` prose (outside the SQL fence):** any sentence
     introducing a field of type `{Entity}` (rather than a Guid ID) where
     `{Entity}` lives in another module.
   - SQL columns themselves use SQL primitive types (`UUID`, `BIGINT`, …) —
     a `*_id UUID NOT NULL` column is the **correct** cross-module FK shape
     and is not a violation. Only fail if the C#-side artifact (contract
     field or entity prose) carries the entity-typed reference.
   - Failure: `"Entity {Module}.{Entity}.{field} references cross-module entity {OtherModule}.{Entity}. Use Guid {field}Id instead."`

4. **Module name PascalCase.** `<module name="orders">` (lowercase) fails.
   - Failure: `"Module name '{name}' must be PascalCase"`

5. **Module name must not equal App name.** For every `<module name="X">`,
   compare `X` to the App name (the same value used elsewhere as
   `{{APP_NAME}}` — resolve from the `<App>.sln` filename in the repo root,
   or from the scaffold-context App value if Phase-1 just ran). If any
   module name equals the App name (case-sensitive PascalCase match), fail:
   - Failure: `"Module name '{name}' collides with App name '{app}'. Rename the module in the tech-design — the App is the bounded context; modules sit inside it and must not share its name."`

   Concrete shell:
   ```bash
   APP=$(ls *.sln 2>/dev/null | head -1 | sed 's/\.sln$//')
   # Extract every module name from the tech-design (one per line).
   grep -oE '<module name="[^"]+"' "docs/tech-design/${SLUG}.md" \
     | sed -E 's/.*name="([^"]+)"/\1/' \
     | while read -r MOD; do
         if [ "$MOD" = "$APP" ]; then
           echo "FAIL: Module name '$MOD' collides with App name '$APP'. Rename the module in the tech-design."
         fi
       done
   ```

   This prevents **namespace shadowing** — without the check, Phase-2
   emits `namespace {{APP_NAME}}.Domain.{{MODULE}};` where `{{MODULE}} ==
   {{APP_NAME}}`, producing tokens like `namespace Library.Domain.Library;`
   and `using Library.Domain.Library;` inside `Library.Api.Library.Contracts`.
   C# enclosing-namespace-first resolution can compile this in small trees
   but breaks confusingly when a sibling type also called `Library` enters
   scope, and every reader pays a **Leaky Narrative** tax mentally
   disambiguating the duplicated `Library` token at every call site. The
   fix lives in the tech-design (rename the module), not in the generator
   (auto-suffixing would be a Silent Fallback that hides the design smell).

### Step P4: Gap report + user prompt

If any **structural** failures (from P1) or **cross-reference** failures (from P3) collected:

```
Phase-2 pre-check found N issues:

  1. Endpoint Orders.POST /orders references undefined DTO LineItem
  2. Entity Orders.Order.customer references cross-module entity Customers.Customer. Use Guid customerId instead.
  ...

Fix the tech-design and re-run, or proceed and stub the missing pieces
with `object` placeholders? [fix/proceed]
```

- If user picks `fix` → abort Phase-2 cleanly, print `"Tech-design at {path} needs updates. Re-run scaffold when ready."`
- If user picks `proceed` → continue to generation with `object` placeholder for undefined DTO refs, `Guid` placeholder for cross-module FK leakage. **Log every substitution in the summary report.**

If no failures, continue to generation without a user prompt.

### Step P5: Create per-module directories

Phase-2 emits files into `src/{{APP_NAME}}.{{LAYER}}/{{MODULE}}/` and
`tests/{{APP_NAME}}.Tests.Unit/{{MODULE}}/`. Phase-1 created the
per-layer directories but NOT the per-module subdirectories. The
`Write` tool creates parent dirs implicitly, but bash file emission
(heredoc, `cat >`, `cp`) does not — and a `Write` failure mid-stream
leaves the tree in a partially-emitted state that's hard to diff.
Create every per-module directory up front, before any file emission:

```bash
# Run from the repo root. {{MODULE}} ranges over every <module name="…">
# block in the tech-design. Loop in the executor — don't paste literal
# placeholders.
for MODULE in <every module name>; do
  mkdir -p src/"$APP".Domain/"$MODULE"
  mkdir -p src/"$APP".Application/"$MODULE"
  mkdir -p src/"$APP".Persistence/"$MODULE"
  mkdir -p src/"$APP".Api/"$MODULE"
  mkdir -p tests/"$APP".Tests.Unit/"$MODULE"
  mkdir -p tests/"$APP".Tests.Integration/"$MODULE"
done
```

Idempotent — `mkdir -p` is a no-op on re-run. Re-running Phase-2
(the documented workflow) does not need to skip this block.

## Generation (task-driven)

Parse the tech-design once and turn each work item into a Claude Code Task. The orchestrator dispatches one subagent per task; each subagent reads its own task description plus the matching template from `templates/csharp/phase2-task-templates/`. The 733-line skim-prose model is replaced by per-task ~50-line scope.

### Step G1: Parse tech-design to JSON

```bash
python "$SCAFFOLD/scripts/phase2-parse.py" "docs/tech-design/{{SLUG}}.md" > /tmp/phase2-tasks.json
```

The JSON schema is documented in `docs/superpowers/specs/2026-05-20-phase2-task-driven-orchestration-design.md`. Inputs the parser cannot infer (App name, migrations directory) come from the grill answers and are merged in the next step.

### Step G2: Create tasks

For each entry in `tasks[]`, invoke `TaskCreate` with:

- **subject**: `"phase2-{TYPE}: {MODULE}.{NAME or METHOD-PATH}"`
- **description**: read the matching `phase2-task-templates/{TYPE}.md`, substitute `{{APP_NAME}}`, `{{MODULE}}`, `{{SLUG}}`, `{{NAME}}`, and embed the task's JSON slice as `{{TASK_JSON}}`. The description is exactly what the subagent will read.
- **metadata**: `{ "task_type": "{TYPE}", "module": "{MODULE}" }` (used by post-build summary)

### Step G3: Execution loop

While any task is `pending` or `in_progress`:

1. Call `TaskList`, pick the lowest-ID pending task.
2. Claim by setting `owner` and `status=in_progress`.
3. Dispatch an implementer subagent with the task description as the prompt.
4. On subagent return:
   - DONE → `status=completed`
   - DONE_WITH_CONCERNS → dispatch reviewer per `subagent-driven-development` skill
   - BLOCKED → leave `in_progress`, attach error to metadata, surface in CLI
5. Loop until no `pending` tasks remain.

### Step G4: Post-build sensor

After all tasks complete:

```bash
APP_NAME="{{APP_NAME}}" MODULES="{{SPACE_SEPARATED_MODULE_LIST}}" \
  bash "$SCAFFOLD/scripts/phase2-postbuild.sh"
```

The script emits structured lines (`BUILD_STATUS=…`, `UNWIRED_MODULES_BEGIN`/`END`) the orchestrator parses into the summary report.

### Step G5: Summary report

Fill `templates/csharp/phase2-summary-report.txt` placeholders from the task list + postbuild output and print to stdout. See the legend at the bottom of that template for substitution rules.

## Post-build validation

After all task subagents return, invoke the post-build sensor (created in Phase-2 setup):

```bash
APP_NAME="{{APP_NAME}}" \
MODULES="{{SPACE_SEPARATED_MODULE_LIST}}" \
  bash "$SCAFFOLD/scripts/phase2-postbuild.sh"
```

The script emits the following structured tokens on stdout (full contract documented in the script header):

- `BUILD_STATUS=SUCCEEDED|FAILED`
- `BUILD_LOG_BEGIN`…`BUILD_LOG_END` (only on FAILED)
- `PROGRAM_CS_MISSING=<path>` (only when `src/{{APP_NAME}}.Api/Program.cs` absent — every module is unwired by definition)
- `UNWIRED_MODULES=none` OR `UNWIRED_MODULES_BEGIN`…`UNWIRED_MODULES_END` (always)

Exit code:
- `0` — build green AND Program.cs present AND all modules wired
- `1` — anything else (build red, missing Program.cs, or any unwired module)
- `2` — APP_NAME or MODULES env vars unset (orchestrator bug)

### Why `UNWIRED_MODULES` is a hard fail, not a warning

Phase-2 emits `Map{{MODULE}}Endpoints` extensions but does NOT modify `Program.cs` (composition is dev-owned). If the dev forgets to wire a module, the build is green, semgrep is green, arch tests pass — and every endpoint in that module returns 404 in production. That is a textbook **Silent Fallback**: the system looks correct from every observable surface and silently produces the wrong behaviour.

The unwired tripwire makes the exit code track the actual postcondition (app is wired and buildable), not just `dotnet`'s return code. Parse the structured tokens above into the summary report under `Modules not wired in Program.cs:` so a dev reading the summary sees the gap without scrolling.

### If build fails

1. **Do not delete or roll back generated files.** They stay on disk.
2. The `BUILD_LOG_BEGIN/END` block carries the verbatim compiler output — splice it into the summary under a `dotnet build FAILED` heading.
3. Exit Phase-2 with non-zero status.

Common build-failure causes:
- A `<contract>` DTO uses a type not yet generated (e.g., `LineItem`) and pre-check skipped it. Add `<entities>LineItem</entities>` to the tech-design and re-run.
- Generated code clashes with hand-written code from a prior session. Inspect the **Files OVERWRITTEN** list in the summary report and `git diff` each entry against the prior commit; merge by hand and commit before re-running.

## Summary report

After successful build (or after failed-build report), emit the summary
using the canonical template at:

```
$SCAFFOLD/templates/csharp/phase2-summary-report.txt
```

The template uses two placeholder shapes:

- `{{NAME}}` — single value, always substituted (e.g., `{{SLUG}}`, `{{N_ENTITIES}}`, `{{BUILD_STATUS}}`).
- `{{NAME | "default string"}}` — list value; emit one indented line per
  entry, or print the default string verbatim when the list is empty.

The legend at the bottom of the template file shows worked examples for
each list section. The summary is the last thing Phase-2 emits before
exiting.

## Template DSL — closed grammar for per-task emit templates

Templates under `$SCAFFOLD/templates/csharp/phase2-task-templates/*.md` use this small grammar. An emit subagent must implement exactly these four constructs and nothing else:

1. **`{{VAR}}`** — direct substitution from the task JSON or orchestrator-provided context (e.g., `{{MODULE}}`, `{{NAME}}`, `{{APP_NAME}}`, `{{SLUG}}`).

2. **`{{for each X in inputs.Y:}} ... {{end for}}`** — iterate over a list field of the task JSON. Inside the body, fields of the loop variable are accessed as `{{X.field}}` (e.g., `{{column.cs_type}}`).

3. **`{{if not last:}}TEXT{{end if}}`** — inside a `for each`, emit `TEXT` for every iteration except the last. Used for trailing-comma suppression in record bodies. The only conditional construct in the grammar.

4. **`{{expr | PascalCase}}`** — pipe filter. The only filter is `PascalCase`. Used in `enum.md` to PascalCase enum value names (e.g., `in_progress` → `InProgress`).

Anything else in a template (loops, conditions, filters not on this list) is a bug in the template. The emit subagent's verification step `file contains no unsubstituted {{...}} tokens` catches grammar misses at write time.

## File header template

Every generated `.cs` file MUST start with this header:

```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><{{TAG}}>{{ITEM}}</{{TAG}}></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
```

The migration file uses a SQL-comment version:

```sql
-- Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
-- Regenerated on every Phase-2 run. Throwaway post-dev-deploy.
```

Header placeholders are filled per-file by the generation prompts.
