# Vendored Semgrep Packs

Community packs are vendored here so gates never call registry.semgrep.dev.

To refresh a pack:

```bash
# Download pack rules
curl -sL "https://semgrep.dev/c/p/owasp-top-ten" -o owasp-top-ten.yaml
curl -sL "https://semgrep.dev/c/p/csharp" -o csharp.yaml
```

Scaffold copies these files to `<target-repo>/.semgrep/packs/`. Custom rules live in `<target-repo>/.semgrep/<app>/` (already scaffolded by the .NET template).

Pack provenance + license summarised in `docs/rules-audit.md` (Task 27).
