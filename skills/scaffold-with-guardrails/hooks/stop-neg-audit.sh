#!/usr/bin/env bash
# Stop hook — fires when Claude ends a turn with outstanding uncommitted changes.
# Prints neg-audit reminder. Wired via .claude/settings.json Stop event.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if ! git diff --quiet || ! git diff --cached --quiet; then
  cat <<'NEGAUDIT'

═══ Negentropic Self-Audit (outstanding diff) ═══

Walk the Violation Guide before closing this turn. Any of these introduced?
  Paper Tiger · Distributed Monolith · Leaky Narrative · Infected Core ·
  Black Box · Computational Friction · Forensic Coding · God Class ·
  Fossil Comments · Silent Fallback

Run `git diff` to review.
NEGAUDIT
fi
