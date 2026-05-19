# Vendored Semgrep Packs

Community packs vendored here so gates never call registry.semgrep.dev.

Shipped:
- `owasp-top-ten.yaml` — `semgrep.dev/p/owasp-top-ten` (544 rules across 25 languages, snapshot 2026-05-16). **Vendored full** — do not pre-trim.
- `csharp.yaml` — `semgrep.dev/p/csharp` (27 rules, snapshot 2026-05-16). C#-only by design.

### How scaffolds install these

`csharp.yaml` is copied verbatim into `<target-repo>/.semgrep/packs/`.

`owasp-top-ten.yaml` is **filtered at scaffold time** to only the rules whose `languages:` intersects the target language. The per-language `scaffold.md` (e.g. `templates/csharp/scaffold.md`) carries the filter step and `KEEP` set. For a C# scaffold this drops the pack from ~1.3 MB / 544 rules to ~190 KB / 77 rules and stops semgrep from loading hundreds of python/java/go/php/etc. rules on every gate run. Custom per-app rules live separately in `<target-repo>/.semgrep/<app>/`.

Vendoring the full pack here (rather than pre-trimming) keeps `common/` a single source of truth that mirrors upstream — each language scaffold derives its own subset.

### To refresh

```bash
curl -sL -o owasp-top-ten.yaml https://semgrep.dev/c/p/owasp-top-ten
curl -sL -o csharp.yaml        https://semgrep.dev/c/p/csharp
```

Pack provenance + license summarised in `docs/rules-audit.md` (Task 27).
