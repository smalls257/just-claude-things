#!/usr/bin/env bats

@test "scaffold-phase-2.md documents convention graft step" {
  f=skills/scaffold-with-guardrails/templates/csharp/scaffold-phase-2.md
  [ -f "$f" ]
  grep -q "phase2_graft.py" "$f"
  grep -q "CONVENTION" "$f"
  grep -q "check-grafts" "$f"
}
