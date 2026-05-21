#!/usr/bin/env bats

@test "GRILL-LOOP.md prompts for reference repo path" {
  f=skills/scaffold-with-guardrails/GRILL-LOOP.md
  [ -f "$f" ]
  grep -qi "reference repo" "$f"
  grep -q "canonical" "$f"
}
