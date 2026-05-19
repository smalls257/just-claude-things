#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

@test "stryker-nightly workflow is valid YAML with required jobs" {
  local wf="${BATS_TEST_DIRNAME}/../../templates/csharp/github-workflows/stryker-nightly.yml"
  [ -f "$wf" ]
  command -v python3 >/dev/null 2>&1 || skip "python3 not available"
  python3 -c "import yaml" 2>/dev/null || skip "PyYAML not installed"
  python3 - "$wf" <<'PY'
import sys, yaml
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f)
assert 'jobs' in data, "missing jobs key"
assert 'mutate' in data['jobs'], "missing mutate job"
PY
}

@test "stryker-config.json parses and has required keys" {
  local cfg="${BATS_TEST_DIRNAME}/../../templates/csharp/stryker-config.json"
  [ -f "$cfg" ]
  command -v python3 >/dev/null 2>&1 || skip "python3 not available"
  python3 - "$cfg" <<'PY'
import sys, json
with open(sys.argv[1]) as f:
    data = json.load(f)
assert 'stryker-config' in data, "missing stryker-config root key"
sc = data['stryker-config']
for k in ['test-projects', 'mutate', 'thresholds']:
    assert k in sc, f"missing {k}"
for t in ['high', 'low', 'break']:
    assert t in sc['thresholds'], f"missing thresholds.{t}"
PY
}
