#!/usr/bin/env bats

@test "CONVENTION-SCAN.md exists and covers required sections" {
  f=skills/scaffold-with-guardrails/CONVENTION-SCAN.md
  [ -f "$f" ]
  grep -q "When the scan runs" "$f"
  grep -q "What the dev sees" "$f"
  grep -q "Decision lifecycle" "$f"
  grep -q "Re-run path" "$f"
  grep -q "Troubleshooting" "$f"
}
