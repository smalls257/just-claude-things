#!/usr/bin/env bats

@test "SKILL.md references Phase-1.5 between Phase-1 validate and Phase-2 neg-audit" {
  run grep -n "Phase-1.5" skills/scaffold-with-guardrails/SKILL.md
  [ "$status" -eq 0 ]
  run grep -n "convention-scan.sh" skills/scaffold-with-guardrails/SKILL.md
  [ "$status" -eq 0 ]
}
