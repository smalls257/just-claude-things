#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

@test "gates-backstop workflow is valid YAML with required jobs" {
  local wf="${BATS_TEST_DIRNAME}/../../templates/common/github-workflows/gates-backstop.yml.disabled"
  [ -f "$wf" ]
  python3 - "$wf" <<'PY'
import sys, yaml
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f)
assert 'jobs' in data, "missing jobs key"
assert 'verify' in data['jobs'], "missing verify job"
PY
}

@test "run-gates-ci.sh --help exits 0" {
  local script="${BATS_TEST_DIRNAME}/../../templates/common/scripts/run-gates-ci.sh"
  [ -f "$script" ]
  run "$script" --help
  assert_success
}
