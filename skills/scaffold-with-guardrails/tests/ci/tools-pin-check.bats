#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

@test "tools-pin-check workflow is valid YAML with required jobs" {
  local wf="${BATS_TEST_DIRNAME}/../../templates/common/github-workflows/tools-pin-check.yml"
  [ -f "$wf" ]
  command -v python3 >/dev/null 2>&1 || skip "python3 not available"
  python3 -c "import yaml" 2>/dev/null || skip "PyYAML not installed"
  python3 - "$wf" <<'PY'
import sys, yaml
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f)
assert 'jobs' in data, "missing jobs key"
assert 'check' in data['jobs'], "missing check job"
# 'on' parses as True in PyYAML (YAML 1.1) — handle both keys
on = data.get('on') or data.get(True)
assert on and 'schedule' in on, "missing schedule trigger"
PY
}
