#!/usr/bin/env bash
# Verify .tools/manifest.toml: all checksums present, no REPLACE_ME.
# Exit 0 if all valid, 1 if any placeholder remains, 2 if manifest missing.

set -uo pipefail
MANIFEST="${1:-.tools/manifest.toml}"

if [ ! -f "$MANIFEST" ]; then
  echo "Manifest not found: $MANIFEST" >&2
  exit 2
fi

if grep -q "REPLACE_ME" "$MANIFEST"; then
  echo "[STALE] manifest.toml contains REPLACE_ME placeholders." >&2
  echo "Run ./scripts/bootstrap.sh to populate checksums, then commit." >&2
  exit 1
fi
echo "Manifest OK: all checksums populated."
