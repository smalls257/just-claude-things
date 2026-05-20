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
set -uo pipefail

if [ -z "${APP_NAME:-}" ] || [ -z "${MODULES:-}" ]; then
  echo "ERROR: APP_NAME and MODULES env vars must be set" >&2
  exit 2
fi

FAIL=0

# Tripwire 1: build green
BUILD_LOG=$(mktemp)
if ! dotnet build > "$BUILD_LOG" 2>&1; then
  echo "BUILD_STATUS=FAILED"
  echo "BUILD_LOG_BEGIN"
  cat "$BUILD_LOG"
  echo "BUILD_LOG_END"
  FAIL=1
else
  echo "BUILD_STATUS=SUCCEEDED"
fi
rm -f "$BUILD_LOG"

# Tripwire 2: wiring check
PROGRAM_CS="src/${APP_NAME}.Api/Program.cs"
UNWIRED=()
if [ -f "$PROGRAM_CS" ]; then
  for MODULE in $MODULES; do
    grep -q "app\.Map${MODULE}Endpoints(" "$PROGRAM_CS" || UNWIRED+=("$MODULE")
  done
else
  echo "WARNING: $PROGRAM_CS not found; cannot check endpoint wiring" >&2
fi

if [ "${#UNWIRED[@]}" -ne 0 ]; then
  echo "UNWIRED_MODULES_BEGIN"
  for M in "${UNWIRED[@]}"; do
    echo "  ${M}   <-- add app.Map${M}Endpoints(); to Program.cs (else routes 404)"
  done
  echo "UNWIRED_MODULES_END"
else
  echo "UNWIRED_MODULES=none"
fi

exit "$FAIL"
