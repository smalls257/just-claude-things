#!/usr/bin/env bash
# Y/N prompter for convention scan. Streams cards, captures decisions, persists
# partial state on SIGINT so user can resume after Ctrl-C.
# Compatible with bash 3.2+ (macOS default).
set -euo pipefail

CARDS=""
OUT=""
PARTIAL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cards) CARDS="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --partial) PARTIAL="$2"; shift 2 ;;
    *) echo "UNKNOWN_ARG: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$CARDS" || -z "$OUT" || -z "$PARTIAL" ]] && { echo "USAGE: $0 --cards F --out F --partial F" >&2; exit 2; }
[[ ! -f "$CARDS" ]] && { echo "CARDS_MISSING: $CARDS" >&2; exit 2; }

# Decisions stored as lines: "key=value" in a temp file
DECISIONS_TMP=$(mktemp)
trap 'rm -f "$DECISIONS_TMP"' EXIT

decisions_set() {
  local key="$1" val="$2"
  # Remove existing entry if any, then append
  local tmp
  tmp=$(mktemp)
  grep -v "^${key}=" "$DECISIONS_TMP" > "$tmp" 2>/dev/null || true
  echo "${key}=${val}" >> "$tmp"
  mv "$tmp" "$DECISIONS_TMP"
}

decisions_get() {
  local key="$1"
  grep "^${key}=" "$DECISIONS_TMP" 2>/dev/null | cut -d= -f2- || true
}

write_json() {
  local target="$1"
  {
    echo "{"
    local first=1
    while IFS='=' read -r k v; do
      [[ -z "$k" ]] && continue
      [[ $first -eq 1 ]] || echo ","
      first=0
      printf '  "%s": "%s"' "$k" "$v"
    done < "$DECISIONS_TMP"
    echo
    echo "}"
  } > "$target"
}

on_int() {
  echo "INTERRUPT: writing $PARTIAL" >&2
  write_json "$PARTIAL"
  exit 130
}
trap on_int INT

# Pre-load partial if present (resume)
if [[ -f "$PARTIAL" ]]; then
  while IFS= read -r line; do
    # Match lines like:  "key": "y"
    if [[ "$line" =~ \"([^\"]+)\":\ *\"([yn])\" ]]; then
      decisions_set "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    fi
  done < "$PARTIAL"
fi

# Read CARDS on fd 3, leaving stdin (fd 0) available for user prompts
exec 3< "$CARDS"
while IFS= read -r line <&3; do
  [[ "$line" =~ ^CARD:\ (.+)$ ]] || continue
  id="${BASH_REMATCH[1]}"
  existing=$(decisions_get "$id")
  if [[ -n "$existing" ]]; then
    echo "RESUME_SKIP: $id (already $existing)" >&2
    continue
  fi
  while true; do
    printf "Adopt %s? (y/n): " "$id" >&2
    read -r ans <&0 || ans=""
    case "$ans" in
      y|Y) decisions_set "$id" "y"; break ;;
      n|N) decisions_set "$id" "n"; break ;;
      *) echo "INVALID: enter y or n" >&2 ;;
    esac
  done
done
exec 3<&-

write_json "$OUT"
rm -f "$PARTIAL" || true
