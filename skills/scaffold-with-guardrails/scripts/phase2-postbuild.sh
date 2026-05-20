#!/usr/bin/env bash
# Phase-2 post-build sensor harness.
# Runs after Phase-2 file generation completes:
#  1. `dotnet build` (exit 0 required)
#  2. Greps Program.cs for every emitted module's Map{Module}Endpoints call
#  3. Prints diagnostics that the orchestrator feeds into the summary report
#
# Required env vars:
#   APP_NAME — the application name (Library, OrdersDemo, …)
#   MODULES  — space-separated list of module names emitted this run
#
# Stdout contract (consumed by the orchestrator; keep stable):
#   BUILD_STATUS=SUCCEEDED|FAILED                 (always; first line of output)
#   BUILD_LOG_BEGIN ... BUILD_LOG_END             (only on FAILED; raw dotnet build output between markers)
#   PROGRAM_CS_MISSING=<path>                     (only when src/${APP_NAME}.Api/Program.cs absent)
#   UNWIRED_MODULES=none                          (always one of these two forms)
#   UNWIRED_MODULES_BEGIN ... UNWIRED_MODULES_END (BEGIN/END form: one "  <Module>   <-- ..." line per unwired module)
#
# Exit code:
#   0 — build passed AND Program.cs present AND all modules wired
#   1 — any of: build failed, Program.cs missing, ≥1 module unwired
#   2 — APP_NAME or MODULES unset (contract violation by caller)
set -uo pipefail

if [ -z "${APP_NAME:-}" ] || [ -z "${MODULES:-}" ]; then
  echo "ERROR: APP_NAME and MODULES env vars must be set (orchestrator Step G4 should pass them; see scaffold-phase-2.md)" >&2
  exit 2
fi

FAIL=0

# Tripwire 1: build green
BUILD_LOG=$(mktemp)
trap 'rm -f "$BUILD_LOG"' EXIT
if ! dotnet build > "$BUILD_LOG" 2>&1; then
  echo "BUILD_STATUS=FAILED"
  echo "BUILD_LOG_BEGIN"
  cat "$BUILD_LOG"
  echo "BUILD_LOG_END"
  FAIL=1
else
  echo "BUILD_STATUS=SUCCEEDED"
fi

# Tripwire 2: wiring check
PROGRAM_CS="src/${APP_NAME}.Api/Program.cs"
UNWIRED=()
if [ -f "$PROGRAM_CS" ]; then
  # Intentional unquoted expansion: MODULES is a space-separated list by contract.
  for MODULE in $MODULES; do
    grep -q "app\.Map${MODULE}Endpoints(" "$PROGRAM_CS" || UNWIRED+=("$MODULE")
  done
else
  # Program.cs missing = every module unwired. Don't let absence look like success (Silent Fallback).
  echo "WARNING: $PROGRAM_CS not found; cannot check endpoint wiring" >&2
  echo "PROGRAM_CS_MISSING=${PROGRAM_CS}"
  FAIL=1
  # Intentional unquoted expansion: MODULES is a space-separated list by contract.
  for MODULE in $MODULES; do
    UNWIRED+=("$MODULE")
  done
fi

if [ "${#UNWIRED[@]}" -ne 0 ]; then
  echo "UNWIRED_MODULES_BEGIN"
  for M in "${UNWIRED[@]}"; do
    echo "  ${M}   <-- add app.Map${M}Endpoints(); to Program.cs (else routes 404)"
  done
  echo "UNWIRED_MODULES_END"
  FAIL=1
else
  echo "UNWIRED_MODULES=none"
fi

exit "$FAIL"
