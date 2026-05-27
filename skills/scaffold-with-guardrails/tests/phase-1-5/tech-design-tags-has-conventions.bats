#!/usr/bin/env bats

@test "TECH-DESIGN-TAGS.md documents <conventions> schema" {
  f=skills/scaffold-with-guardrails/TECH-DESIGN-TAGS.md
  [ -f "$f" ]
  grep -q "<conventions" "$f"
  grep -q "reference-repo-commit" "$f"
  grep -q "<adopted" "$f"
  grep -q "<dev-named" "$f"
  grep -q "<discovered" "$f"
  grep -q "<rejected" "$f"
  grep -q "<conflict" "$f"
}
