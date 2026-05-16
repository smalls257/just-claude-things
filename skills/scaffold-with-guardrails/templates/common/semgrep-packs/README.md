# Vendored Semgrep Packs

Community packs vendored here so gates never call registry.semgrep.dev.

Shipped:
- `owasp-top-ten.yaml` — `semgrep.dev/p/owasp-top-ten` (543 rules, snapshot 2026-05-16)
- `csharp.yaml` — `semgrep.dev/p/csharp` (27 rules, snapshot 2026-05-16)

Scaffold copies both files to `<target-repo>/.semgrep/packs/`. Custom per-app rules live in `<target-repo>/.semgrep/<app>/` (scaffolded per language template).

To refresh:

```bash
curl -sL -o owasp-top-ten.yaml https://semgrep.dev/c/p/owasp-top-ten
curl -sL -o csharp.yaml        https://semgrep.dev/c/p/csharp
```

Pack provenance + license summarised in `docs/rules-audit.md` (Task 27).
