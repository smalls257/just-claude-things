#!/usr/bin/env bats
# Bug #2: convention-scan.sh's autocommit failed when the target repo's
# .githooks/pre-commit referenced missing tools (gitleaks, scc, drifted
# semgrep). The conventions block + staged snippets had already been written;
# the commit step failed and surfaced confusing tool-not-found errors. The
# fix runs the bot commit with core.hooksPath=/dev/null so target hooks (for
# *human* commits) do not gate the scaffold-bot step.

load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/docs/tech-design"
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A \
    && git -c user.email=t@t -c user.name=t commit -q -m init )

  # Install a target-side hooks dir that ALWAYS rejects every commit by
  # referencing a tool that does not exist. This mimics the gate-system
  # pre-commit hook failing for missing gitleaks/scc/etc.
  mkdir -p "$TARGET/.githooks"
  cat > "$TARGET/.githooks/pre-commit" <<'EOF'
#!/usr/bin/env bash
echo "FAKE_HOOK_FAILURE: missing tool" >&2
exit 1
EOF
  chmod +x "$TARGET/.githooks/pre-commit"
  git -C "$TARGET" config core.hooksPath .githooks
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "convention-scan autocommit bypasses target .githooks/pre-commit" {
  run bash -c "printf 'y\ny\ny\ny\ny\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo '$REF' --target-repo '$TARGET' \
    --design '$TARGET/docs/tech-design/svc.md' --keywords ''"
  [ "$status" -eq 0 ]
  # Commit must have landed despite the always-failing hook.
  run git -C "$TARGET" log --oneline
  echo "$output" | grep -q "convention scan adopted decisions"
}
