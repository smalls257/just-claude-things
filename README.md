# just-claude-things

Personal collection of Claude Code skills, prompts, and tools — built for daily
use, available to share.

## Skills

### Pipeline: idea → issues

Four skills that drive a software product from "we want to build this" to a
tracker-agnostic issue list, enforcing the negentropic lens (Six Principles)
at every step.

| # | Skill | Drives out | Output |
|---|-------|-----------|--------|
| 1 | `requirements-grill` | Functional requirements (pure *what*) | `docs/requirements/<slug>.md` |
| 2 | `tech-design-grill` | Complete tech design (pure *how*) | `docs/tech-design/<slug>.md` + ADRs + `CONTEXT.md` |
| 3 | `scaffold-with-guardrails` | Repo scaffold + CLAUDE.md + AGENTS.md + semgrep + NetArchTest + hooks | populated repo |
| 4 | `to-issues` | Tracer-bullet vertical slices | `docs/issues/<slug>.md` |

Each skill checks for its upstream artifact and refuses to run without it.
Each skill writes WIP-aware YAML frontmatter and can resume deferred work.
Each skill ends with a negentropic self-audit before declaring complete.

## Structure

```
skills/     # Claude Code skill files (one directory per skill)
prompts/    # Reusable prompt templates (future)
tools/      # Scripts and utilities (future)
```

## Usage

Drop a skill directory into `~/.claude/skills/` or any project's `.claude/skills/`.

Each skill directory contains `SKILL.md` plus supporting reference files. Skills
reference each other by prereq chain — run them in order (1 → 2 → 3 → 4).
