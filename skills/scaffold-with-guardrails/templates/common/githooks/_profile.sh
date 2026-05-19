# shellcheck shell=bash
# Profile + tier resolver. Sourced by gates that need tier-aware behavior.
# Usage:
#   . "$(...)/_profile.sh"
#   tier=$(resolve_tier "complexity" "optional")
#   case "$tier" in error) ... ;; warn) ... ;; off) ... ;; esac
#
# Sourceable: do NOT enable set -e/-u here; callers may run under set -u.

GATES_TOML="${GATES_TOML:-$(git rev-parse --show-toplevel 2>/dev/null)/.gates.toml}"

# Reads top-level `profile = "..."` from .gates.toml.
# Empty/missing file or empty value falls back to "standard" (friendly default).
read_profile() {
  local p=""
  if [ -f "$GATES_TOML" ]; then
    p=$(grep -E '^profile *=' "$GATES_TOML" 2>/dev/null | head -1 | sed 's/.*"\(.*\)".*/\1/')
  fi
  echo "${p:-standard}"
}

# resolve_tier <gate-name> <default-tier>
# Tier defaults:
#   critical → error in all profiles
#   standard → error in standard/regulated, warn in prototype
#   optional → warn in standard, error in regulated, off in prototype
#   always   → run in all profiles
# Override via [gates.<name>] enforce = "warn"|"error"|"off"
# Output: one of error|warn|off.
resolve_tier() {
  local name="$1"
  local default="$2"
  local profile
  profile=$(read_profile)

  # Per-gate override. awk leaves any section on `[`, then re-enters only on
  # `[gates.<name>]`. Stripping `"` and spaces assumes single-token values
  # (warn/error/off) — fine for this domain.
  local override=""
  if [ -f "$GATES_TOML" ]; then
    override=$(awk -v g="$name" '
      /^\[/             { in_section = 0 }
      /^\[gates\./      { in_section = ($0 ~ "^\\[gates\\." g "\\]") }
      in_section && /^enforce/ {
        gsub(/[" ]/, "")
        split($0, a, "=")
        print a[2]
        exit
      }
    ' "$GATES_TOML" 2>/dev/null)
  fi
  if [ -n "$override" ]; then
    echo "$override"
    return
  fi

  case "$default:$profile" in
    critical:*)            echo "error" ;;
    standard:prototype)    echo "warn"  ;;
    standard:*)            echo "error" ;;
    optional:prototype)    echo "off"   ;;
    optional:standard)     echo "warn"  ;;
    optional:regulated)    echo "error" ;;
    always:*)              echo "error" ;;
    *)                     echo "error" ;;
  esac
}

# resolve_setting <gate_name> <key> <default>
# Reads "<key> = <value>" scoped to [gates.<gate_name>] in .gates.toml.
# Strips surrounding quotes and whitespace. Returns default if absent.
resolve_setting() {
  local g="$1" key="$2" default="${3:-}"
  local toml="${GATES_TOML:-${REPO_ROOT}/.gates.toml}"
  [ -f "$toml" ] || { echo "$default"; return; }
  local v
  v=$(awk -v g="$g" -v k="$key" '
    /^\[/ { in_section = 0 }
    /^\[gates\./ { in_section = ($0 ~ "^\\[gates\\." g "\\]") }
    in_section {
      # Match "<key> = " at line start (after optional whitespace)
      if (match($0, "^[ \t]*" k "[ \t]*=[ \t]*")) {
        val = substr($0, RSTART + RLENGTH)
        gsub(/^["[:space:]]+|["[:space:]]+$/, "", val)
        print val; exit
      }
    }
  ' "$toml")
  echo "${v:-$default}"
}
