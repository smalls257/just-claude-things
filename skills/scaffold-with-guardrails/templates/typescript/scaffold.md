# TypeScript Scaffold — Step-by-Step

Canonical scaffold the skill applies when the tech-design's stack is TypeScript (Node 20+).

## Grill questions

1. **App name** (kebab-case, e.g., `expense-portal`)
2. **Runtime target?** → Node service / browser SPA / library
3. **Framework?** → Hono (service), Vite+React (SPA), tsup (library)

## Default stack choices

| Concern | Choice | Why |
|---|---|---|
| Package manager | **pnpm** | Reproducible installs, strict workspace boundaries |
| Linter | **eslint** | Industry default; configure for strict rules |
| Format | **prettier** | One opinion, no debate |
| Test runner | **vitest** | Fast, ESM-native |
| Type checker | **tsc --strict --noUncheckedIndexedAccess** | Buffer principle: types as boundaries |

## Scaffold commands

```bash
APP=expense-portal
pnpm init
pnpm add -D typescript vitest @types/node eslint prettier
```

## Gate system installation

Same as csharp scaffold — see `templates/csharp/scaffold.md` "Gate system installation" section. Skip the `.NET-conditional` block.
