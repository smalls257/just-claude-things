#!/usr/bin/env bats

@test "scaffold.md documents slot markers and per-template ownership" {
  f=skills/scaffold-with-guardrails/templates/csharp/scaffold.md
  [ -f "$f" ]
  grep -q "{{CONVENTION:" "$f"
  grep -q "Program.cs" "$f"
  for layer in auth logging data middleware observability http-outbound; do
    grep -q "$layer" "$f"
  done
}
