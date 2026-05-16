# Vendored Semgrep Packs

Community packs vendored here so gates never call registry.semgrep.dev.

Shipped:
- `owasp-top-ten.yaml` — `semgrep.dev/p/owasp-top-ten`, **filtered to C#-applicable subset** (77 rules: csharp + C# + generic + yaml + dockerfile + regex + json + bash). Original pack was 544 rules across 25 languages; the 467 python/java/go/php/ruby/scala/kt/swift/clojure/solidity/hcl/terraform/html rules were dropped because they never fire against a .NET tree and added 1.1 MB of inert YAML to every gate run.
- `csharp.yaml` — `semgrep.dev/p/csharp` (27 rules, snapshot 2026-05-16)

Scaffold copies both files to `<target-repo>/.semgrep/packs/`. Custom per-app rules live in `<target-repo>/.semgrep/<app>/` (scaffolded per language template).

To refresh the upstream packs:

```bash
curl -sL -o owasp-top-ten.yaml https://semgrep.dev/c/p/owasp-top-ten
curl -sL -o csharp.yaml        https://semgrep.dev/c/p/csharp
```

After refreshing `owasp-top-ten.yaml`, **re-run the language filter** so the descoped subset stays in sync:

```bash
python3 -c "
import yaml
KEEP = {'csharp', 'C#', 'generic', 'yaml', 'dockerfile', 'regex', 'json', 'bash'}
with open('owasp-top-ten.yaml') as f: pack = yaml.safe_load(f)
pack['rules'] = [r for r in pack['rules'] if set(r.get('languages', []) or []) & KEEP]
with open('owasp-top-ten.yaml', 'w') as f:
    yaml.safe_dump(pack, f, sort_keys=False, default_flow_style=False, width=4096)
"
```

When the python or typescript scaffolds land, broaden `KEEP` (or split per-language pack files under `templates/<lang>/semgrep-packs/`) rather than re-vendoring the full 544-rule blob.

Pack provenance + license summarised in `docs/rules-audit.md` (Task 27).
