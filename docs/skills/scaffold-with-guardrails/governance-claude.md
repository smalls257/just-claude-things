# Governance: Claude

This document describes how `scaffold-with-guardrails` steers Claude's
reasoning and output quality across the full lifecycle of a scaffolded repo —
from first question to final commit.

The core problem governance addresses is this: Claude is capable of generating
code that looks correct, passes review, and satisfies stated requirements while
quietly violating architectural principles. Automated gates (linters, semgrep,
arch tests) catch a specific class of mistake — one that can be expressed as a
pattern. They cannot catch the mistake that is an omission: the observable
signal that was not added, the comment that was not updated to reflect a
changed invariant, the error path that returns a plausible-looking default
instead of raising. Governance is the system that closes that gap by operating
at three different levels simultaneously: before scaffolding, inside every
module Claude touches, and at the moment Claude is about to stop.

---

## Three steering mechanisms

Governance is applied at three distinct moments, each catching a different
class of slippage:

- **Doctrine (CLAUDE.md, inlined at scaffold time).** The canonical Six
  Principles and Violation Guide land inside the repo as a root `CLAUDE.md`.
  Claude reads it on every turn, so the reasoning framework is always in
  context — it does not depend on the user's global environment. Doctrine
  establishes the vocabulary Claude uses to name failures before writing code,
  and the self-audit it runs after.
- **Per-module rules (AGENTS.md, one per layer).** Each module carries its
  own `AGENTS.md` with IDed architectural rules, matched semgrep entries, and
  NetArchTest assertions. Rules live in three places simultaneously so they can
  be enforced at three speeds: human reading, static analysis, and build-time
  assertion. Claude reads the `AGENTS.md` before touching any subdirectory, so
  module-level constraints are always in context when module-level changes are
  being made.
- **Runtime nudge (NEG-AUDIT stop hook).** A shell hook fires whenever Claude
  ends a turn with an outstanding diff. It prints the full Violation Guide as a
  checklist and asks Claude to walk it before declaring done. This surfaces
  quiet entropy — cases where all gates passed but a Principle was quietly bent.

Together, the three mechanisms cover doctrine (what the principles are),
structure (where specific rules apply and how they are enforced), and runtime
(did this specific turn respect them). No single mechanism is sufficient on its
own. Doctrine without per-module rules is philosophy without engineering.
Per-module rules without a runtime nudge leaves the self-audit optional.
A runtime nudge without doctrine gives Claude nothing to audit against.

---

## Doctrine: root CLAUDE.md

**Source:** `../../../skills/scaffold-with-guardrails/CLAUDE-MD-TEMPLATE.md`

The template generates the repo-root `CLAUDE.md` at scaffold time by
substituting placeholders with values drawn from the GRILL-LOOP session:
`{{APP_NAME}}` (the application name, e.g., `ExpensePortal`), `{{APP_LOWER}}`
(the kebab-case derivative used in semgrep paths, e.g., `expense-portal`),
`{{ARCHITECTURE_PARAGRAPH}}` (the architecture overview pulled directly from
the `§Architecture overview` section of the completed tech design doc),
`{{STACK_SUMMARY}}` (the one-liner tech stack from `§Tech stack`), and
`{{CODEBASE_RULES}}` (a bullet list of app-specific rules the skill generates
from the component decomposition and design principles). The result is a
`CLAUDE.md` that reads as purpose-built for the repo, not machine-stamped from
a template, because the substantive content comes from the design decisions
rather than from filler.

The template embeds the Six Principles and Violation Guide as inline prose —
not links to external files. This is a deliberate application of the **Buffer**
Principle: the scaffolded repo's core reasoning context must not depend on the
presence of the scaffolding user's global `~/.claude/CLAUDE.md`. A repo that
can only be reviewed, extended, or diagnosed by someone who has the original
author's global config installed at exactly the right path is a **Distributed
Monolith** between person and machine. The repo's understanding of its own
architecture should be self-contained — visible to a new team member who
clones it with no prior context, legible in an offline code review, and
survivable across forks, handoffs, and archival events.

Beyond portability, inlining doctrine creates a historical record. The version
of the Principles that governed a decision is visible in `git log` at the time
of the commit, not inferred from the current state of someone's global config.
That traceability is an **Anchor** property: the repo preserves the reasoning
context of its own history.

---

## Per-module rules: AGENTS.md

**Source:** `../../../skills/scaffold-with-guardrails/AGENTS-MD-TEMPLATE.md`

The skill generates one `AGENTS.md` for each module produced during scaffolding.
Standard modules are Domain, Application, Infrastructure, Persistence, Api,
and Service; a Client module is added when the tech design calls for one.
Each `AGENTS.md` is generated from the same template but with all placeholders
filled for that specific module: its name, its short key (e.g., `DOMAIN`,
`INFRA`), its purpose statement from the tech design, per-Principle notes
tailored to what that specific layer is responsible for, what belongs in it,
what does not belong in it, and its module-specific naming conventions.

The per-Principle notes are not boilerplate — they are generated from the
tech design's component decomposition. The Domain module's `AGENTS.md` will
note that Anchor requires business concepts to carry their domain meaning in
their names and that Fossil Comments are particularly dangerous here because
domain rules are often verbal before they are code. The Infrastructure module's
`AGENTS.md` will note that Buffer requires all interface contracts to be
defined in the Application layer and implemented here, never the reverse. The
notes read as reminders of reasoning already done during the grill session,
not as generic doctrine restated at the module level.

The architectural rules section is the structural core of each `AGENTS.md`.
Every rule carries an ID in `MODULE_KEY-RXXX` format. That same ID appears in
three places: the prose description in `AGENTS.md` (readable by any engineer
without tooling), the matching semgrep rule in
`.semgrep/<app-lower>/<module-lower>.yaml` (caught at static analysis time,
before the build), and the NetArchTest assertion in
`tests/<AppName>.Tests.Unit/Architecture/<ModuleName>ArchitectureTests.cs`
(enforced at build time, against the compiled assembly). Triple-encoding is not
redundancy — each placement catches violations at a different speed and at a
different cost of false negative. Prose is free but not enforced; it relies on
the engineer reading it. Static analysis is fast and automatic but only covers
patterns it was taught; a new violation shape that was not anticipated by the
rule author passes through silently. NetArchTest operates on compiled assemblies
and can express constraints that semgrep cannot (e.g., transitive references
through third-party packages). All three must agree. A violation that slips past
prose can be caught by semgrep in CI. A violation that semgrep cannot express
can be caught by NetArchTest. There is no gap between the three layers.

> *Note: the skill currently emits rule IDs in two forms — `<APP_KEY>-<MODULE_KEY>-R001` per `SKILL.md` and `scaffold.md`, vs `<MODULE_KEY>-R001` per `AGENTS-MD-TEMPLATE.md`. The `AGENTS-MD-TEMPLATE.md` form is canonical for IDed rules; the APP_KEY-prefixed form should be reconciled in a future pass.*

```markdown
### DOMAIN-R001 — Domain references no outward types

Domain projects must not reference Application, Infrastructure, Persistence,
Api, Service, or runtime infrastructure packages (Dapper, EF Core, MediatR,
MassTransit, ASP.NET Core, Microsoft.Extensions.Hosting, etc.). Domain is a
leaf with no outward references. Violations indicate Infected Core.

- semgrep: `.semgrep/expense-portal/domain.yaml:DOMAIN-R001`
- arch test: `tests/ExpensePortal.Tests.Unit/Architecture/DomainArchitectureTests.cs`
```

The ID `DOMAIN-R001` is the load-bearing token. It appears in semgrep YAML
as the rule `id`, in the NetArchTest `[Fact]` display name, and in the
`AGENTS.md` header. An accepted violation is tracked as
`[Fact(Skip = "DOMAIN-V001: <explanation>")]` — the skip reason includes the
violation ID and a rationale, making every architectural exception visible and
reviewable rather than silently absent.

---

## Runtime nudge: NEG-AUDIT

**Source:** `../../../skills/scaffold-with-guardrails/NEG-AUDIT.md`

**Hook file:** `../../../skills/scaffold-with-guardrails/hooks/stop-neg-audit.sh`

The stop hook fires whenever Claude ends a turn while an outstanding diff
exists in the working tree — that is, when Claude has made changes and is
about to declare itself done. The check is a simple `git diff --quiet &&
git diff --cached --quiet`; if either returns non-empty, the hook prints the
full ten-item Violation Guide as an inline checklist and asks Claude to walk
each entry before the turn closes. The hook is wired as a Claude Code Stop
event via `.claude/settings.json` in the scaffolded repo.

The purpose of NEG-AUDIT is to surface slippage that formal gates cannot catch.
Consider the class of violation that is a missing thing: a **Black Box** where
no per-stage timing was added to a new async path; a **Fossil Comment** where
an old explanation was not updated to reflect a changed invariant; a **Silent
Fallback** where an error path returns a plausible-looking default because
raising felt heavy-handed in the moment. None of these are pattern-matchable by
semgrep. None of them will fail a NetArchTest assertion. They pass all gates and
silently degrade the system's decipherability and reliability. The stop hook
exists because these violations require Claude to ask itself a question, not to
satisfy a rule. Asking the question does not guarantee a correct answer, but not
asking guarantees the slippage accumulates unexamined.

The NEG-AUDIT checklist in `NEG-AUDIT.md` also defines the completion protocol:
if every box is YES (no violation present), Claude sets `status: complete` in
the document frontmatter and stops. If any box is NO, Claude must either fix
the violation and re-run the audit, open an `OQ-XXX`/`D-XXX` entry explaining
why it cannot be fixed without user acknowledgment, or stop and ask the user to
confirm the violation is intentional. Completion without a clean audit — or
a documented exception — is not permitted.

---

## GRILL-LOOP

**Source:** `../../../skills/scaffold-with-guardrails/GRILL-LOOP.md`

GRILL-LOOP is the pre-scaffold interrogation that runs before any file is
generated. The skill asks one question at a time — with a recommended answer
and a one-line rationale for the recommendation — and refuses to move forward
until each question is answered with a statement of fact or a documented open
question (`OQ-XXX`) with rationale. Vague deferrals ("we'll figure it out
later") are rejected on contact. Fuzzy language is sharpened to canonical
terms from the project's `CONTEXT.md` glossary; if a term the user supplies
conflicts with the glossary, the conflict is surfaced immediately before
moving on. Abstract relationship statements ("these modules communicate") are
stress-tested with concrete scenarios that force precision about ownership,
direction of dependency, and what happens at the seam when one side changes.

Each open question is tracked as an `OQ-XXX` entry with a rationale and a
description of what would unblock it. Each decided question becomes a `D-XXX`
entry with the decision recorded. The grill session closes only when every
branch of the decision tree has been resolved — no open branches, no empty
sections in the tech design output template, and a passing NEG-AUDIT on the
document itself.

Scaffolding is blocked until `docs/tech-design/<slug>.md` has
`status: complete` in its frontmatter. That document is produced by the grill
session — the skill writes it from the resolved answers, not from user-supplied
content. The gate exists because the cost structure is asymmetric: asking a
clarifying question during the grill costs one conversational turn. Discovering
a wrong boundary assumption after scaffolding — after modules have been laid
out, after arch tests have been written to enforce the wrong contract, after
semgrep rules encode the wrong dependency direction — costs a full refactor of
the scaffolded structure. GRILL-LOOP moves that discovery cost to the cheapest
possible moment in the project's timeline.

---

## The Six Principles (summary)

**Anchor** — Preservation of Intent. Code carries the business reason behind
every decision, visibly, in the code itself. When the intent behind a rule,
constraint, or algorithm lives only in someone's head or in a ticket from three
years ago, every future maintainer becomes an archaeologist. The names of
functions, types, and constants should be legible as domain prose — not as
abbreviations of implementation steps. Anchor makes a codebase self-explanatory
to anyone who reads it without background context. It pushes back against
**Forensic Coding** (the "why" is missing and must be excavated from commit
history or tribal knowledge) and **Fossil Comments** (the "why" was recorded
but now contradicts or misrepresents what the code actually does).

**Shield** — Structural Integrity. Every unit of the system — module, class,
function — is independently replaceable without requiring coordinated changes
elsewhere. A module that can only move if five others move with it is not a
module; it is a distributed monolith wearing a modular interface as a costume.
Shield is the Principle that makes the system's stated architecture correspond
to its actual architecture. It pushes back against **Distributed Monolith**
(false seams where a "small" change cascades unexpectedly through the system)
and **God Class / God Method** (units that have absorbed so many responsibilities
that they cannot be replaced, tested, or reasoned about in isolation).

**Filter** — Narrative Abstraction. Interfaces should hide the mechanics of
implementation behind language that describes the business domain. A caller
should be able to read a call site as a sentence about what the system is doing
— not as a tour of how it is done. When callers must supply flags, modes, SQL
fragments, or "options dicts" they had to read source code to understand,
the abstraction is leaking: it is advertising its internals rather than
protecting them. Filter pushes back against **Leaky Narrative** (implementation
detail bleeding through a business interface, making callers dependent on what
should be hidden).

**Buffer** — Subsidiarity. Core business logic must not depend on specific
infrastructure. The rules, calculations, and decisions that define what the
system is — the domain — must be testable without a database, a network
connection, or a live clock. Infrastructure lives at the periphery; it
implements contracts defined by the core, not the other way around. When
business rules reach directly for infrastructure, the core cannot be exercised
in isolation and cannot be moved to a different infrastructure provider without
touching the logic itself. Buffer pushes back against **Infected Core** (domain
logic entangled with its environment, unable to pass the Airplane Test).

**Sensor** — Decipherability. Decay you cannot see cannot be stopped. Every
meaningful state transition, side effect, and failure path must be observable
from outside the unit — without attaching a debugger, without redeploying
instrumented code, and without reading source. A system that appears healthy
while silently broken is strictly worse than a system that fails visibly, because
the visible failure tells you where to look. When a failure is invisible, the
first instinct is to guess at the cause; guessing at causes produces fixes that
may obscure the actual problem further. Sensor pushes back against **Black Box**
(failure invisible from the outside, requiring archaeology to diagnose) and
**Silent Fallback** (failures swallowed and returned as fake successes, making
the system appear healthy while broken).

**Engine** — Mechanical Sympathy. Computational waste is physical entropy.
The machine has a specific shape — memory hierarchies, I/O latencies, garbage
collection pressure — and code that ignores that shape pays a tax that compounds
over time and load. Reaching for a bigger instance when the algorithm is the
problem is not a solution; it is an escalating cost with a ceiling. Engine
demands that performance problems be solved by thinking, not by adding hardware.
It also demands that work satisfy the actual need, not merely the stated
specification. Engine pushes back against **Computational Friction** (scale
achieved by hardware rather than by algorithm) and **Paper Tiger** (output that
passes tests but fails to solve the user's actual problem).

Canonical wording lives in `~/.claude/CLAUDE.md`; this is a working summary.

---

## The Violation Guide (summary)

- **Paper Tiger** — Passes tests and meets the spec; users still cannot accomplish
  their goal. Green CI on a feature nobody can use.
- **Distributed Monolith** — A "small" change requires coordinated edits across
  multiple modules or services; correctness depends on shared mutable state
  across instances.
- **Leaky Narrative** — Callers pass flags, modes, SQL fragments, or options
  dicts they had to read source code to fill; the abstraction does not hold.
- **Infected Core** — Unit tests need a real database, a live clock, or a network
  connection to pass; business logic cannot be exercised in isolation.
- **Black Box** — "It just stopped working" with no signal; p99 latency spikes
  with no per-stage timing; a flake with no timestamps. First move is to restore
  sensors, not form hypotheses.
- **Computational Friction** — Every latency problem is answered with a bigger
  instance; N+1 queries lurk behind a cache and the cache is treated as the fix.
- **Forensic Coding** — `git blame` is the only documentation; a constant called
  `MAGIC = 47` with no commit context explaining why.
- **God Class / God Method** — A function with two or more boolean parameters and
  a multi-branch switch; a class named `Manager` or `Handler` with thirty methods.
- **Fossil Comments** — The comment contradicts the code below it; a
  `TODO: remove after v2` dated three years ago and still present.
- **Silent Fallback** — `try/except: pass`; a retry that returns `None` on
  exhaustion; a rate limiter that fails open when the backing store is
  unreachable.

Canonical Tell-list lives in `~/.claude/CLAUDE.md`.

---

## Why doctrine inline, not linked

Scaffolded repos are intended to be self-contained artifacts. They get forked,
handed to new teams, archived, reviewed offline, and audited by people who were
not present at the original scaffold session. The `CLAUDE.md` that governs how
Claude reasons about the repo must travel with the repo. If it consisted of a
link to `~/.claude/CLAUDE.md` on the original author's machine, the repo's
reasoning context would be invisible to anyone who did not have that file at
exactly that path with exactly that content. An engineer reviewing the code on a
new machine, a contractor without access to internal tooling, or a team inheriting
a repository after the original author has left would all be working without the
governing doctrine in context.

That is a **Buffer** violation at the repository level. The scaffolded repo's
core logic — including the framework Claude uses to reason about it — would
depend on a specific external environment that the repo itself cannot carry or
guarantee. The repo's understanding of its own architecture would be an
**Infected Core** failure applied to documentation: business reasoning entangled
with an external dependency (a specific global config file) instead of expressed
inside the artifact itself.

Linking doctrine also makes version history opaque. When a decision was made —
whether to use a result type here, whether this module should own that contract
— it was made under a specific version of the Principles. If doctrine lives in a
linked external file that evolves independently, there is no way to know, from
the repo's commit history, what reasoning framework was active at the time of
any given decision. Inlining doctrine gives the repo an **Anchor**: the
principles in effect at the time of a decision are preserved in `git log`
alongside the decision itself.

The acknowledged cost of inlining is doctrine duplication. Multiple repos carry
copies of the Principles and Violation Guide, and those copies can drift from the
global source of truth over time. This cost is mitigated by the template
mechanism rather than eliminated. The global `~/.claude/CLAUDE.md` remains the
single source of truth for the canonical wording. When doctrine evolves, the
scaffold template (`CLAUDE-MD-TEMPLATE.md`) is updated, and all repos scaffolded
after that point pick up the updated version at scaffold time. Repos scaffolded
before the change carry their snapshot intentionally: they were governed by
the version of the principles that was active when they were built, and that
governance record is preserved in their commit history. Drift is not a bug; it
is a feature that keeps the record honest.
