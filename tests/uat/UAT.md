# UAT — Bulletproof Gates

Manual reviewer checklist. IDs match scenario function names in `tests/uat/run-uat.sh`.

To run a single scenario:

```bash
bash tests/uat/run-uat.sh --only sNN_name
```

To run the whole suite (hermetic, < 60s):

```bash
bash tests/uat/run-uat.sh
```

Flags: `--verbose` streams gate output, `--live` uses real tool binaries instead of stubs, `--only ID` runs a single scenario.

On failure, the harness leaves `$UAT_ROOT` intact and prints the diagnostic dir + per-scenario logs.

## Bootstrap (5)

- [ ] **s01_bootstrap_fresh** — `bootstrap.sh` in a scaffolded repo wires `.githooks/`, `.tools/`, `.gates.toml`, sets `core.hooksPath=.githooks`
- [ ] **s02_bootstrap_idempotent** — second `bootstrap.sh` run exits 0 and does not duplicate `include.path`
- [ ] **s03_bootstrap_offline** — `--offline` skips tool downloads (`.tools/` contains only `.gitkeep`)
- [ ] **s04_worktree** — pre-commit invoked from a `git worktree add` resolves paths correctly
- [ ] **s05_verify_tool_pins** — REPLACE_ME manifest → `verify-tool-pins.sh` exits 1

## Gates fire (11)

- [ ] **s06_format** — ruff stub exit 1 → 10-format fails, pre-commit exits 1
- [ ] **s07_secrets** — gitleaks stub exit 1 → 20-secrets fails
- [ ] **s08_static_analysis** — semgrep stub exit 1 → 30-static-analysis fails
- [ ] **s09_deps** — trivy stub exit 1 → 40-deps fails
- [ ] **s10_tests_unit** — pytest stub exit 1 → 50-tests-unit fails
- [ ] **s11_complexity_standard_warn** — lizard stub exit 1, standard profile → warns, pre-commit exits 0
- [ ] **s12_complexity_regulated_fail** — lizard stub exit 1, regulated profile → fails, exits 1
- [ ] **s13_file_size** — scc stub emits oversized file in JSON → 61-file-size warns
- [ ] **s14_tests_integration** — pytest stub exit 1 on pre-push → 10-tests-integration fails
- [ ] **s15_deps_deep** — trivy stub exit 1 on pre-push → 20-deps-deep fails
- [ ] **s16_conventional_commit** — non-conventional subject → 10-conventional emits WARN (gate is warn-only, exit 0)

## Verified trailer (3)

- [ ] **s17_trailer_yes** — all 7 pre-commit gates run and pass → `Verified: yes`
- [ ] **s18_trailer_no** — `git commit --no-verify` skips commit-msg → no `Verified:` trailer
- [ ] **s19_trailer_partial** — `GATES_SKIP=secrets git commit` → `Verified: partial`

## Bypass + safety (4)

- [ ] **s20_dry_run** — `GATES_DRY_RUN=1` + failing gate → pre-commit exits 0, `gates-last-run` has `DRY_RUN=1`
- [ ] **s21_lock_concurrent** — fresh `.git/gates.lock` exists → pre-commit exits 1, `[BLOCK]` in output
- [ ] **s22_lock_stale_takeover** — lock + `GATES_LOCK_STALE_S=0` → takeover, `[WARN] stale` in output, pre-commit exits 0
- [ ] **s23_subdir_hook** — pre-commit invoked from subdirectory → no path-resolution errors

## Profiles (3)

- [ ] **s24_profile_prototype** — `profile = "prototype"` → `complexity` and `file-size` in SKIPPED
- [ ] **s25_profile_standard** — default profile → complexity in WARN, not in FAILED
- [ ] **s26_profile_regulated** — `profile = "regulated"` → complexity in FAILED, pre-commit exits 1

## Tool errors (3)

- [ ] **s27_tool_missing_exit2** — semgrep absent → 30-static-analysis exits 2, FAILED contains `static-analysis:2`
- [ ] **s28_tool_error_exit3** — semgrep stub exit 2 (tool error) → gate exits 3, FAILED contains `static-analysis:3`
- [ ] **s29_self_skip_exit77** — no source files staged → 30-static-analysis exits 77, dispatcher records SKIPPED

## CI templates (4)

- [ ] **s30_gates_backstop_yaml** — `gates-backstop.yml.disabled` parses as valid YAML
- [ ] **s31_tools_pin_check_cron** — `tools-pin-check.yml` cron expression is a valid 5-field schedule
- [ ] **s32_stryker_nightly_jq** — `stryker-nightly.yml` jq path quotes `"stryker-config"` correctly
- [ ] **s33_run_gates_ci_help** — `run-gates-ci.sh --help` exits 0 and prints `Usage:`
