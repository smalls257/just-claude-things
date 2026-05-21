#!/usr/bin/env bash
# Orchestrator: drives the 10-step convention-scan pipeline.
set -euo pipefail

REF=""
TARGET=""
DESIGN=""
KEYWORDS=""
DISCOVER_ALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reference-repo) REF="$2"; shift 2 ;;
    --target-repo)    TARGET="$2"; shift 2 ;;
    --design)         DESIGN="$2"; shift 2 ;;
    --keywords)       KEYWORDS="$2"; shift 2 ;;
    --discover-all)   DISCOVER_ALL=1; shift ;;
    *) echo "UNKNOWN_ARG: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$REF" || -z "$TARGET" || -z "$DESIGN" ]] && {
  echo "USAGE: $0 --reference-repo R --target-repo T --design D [--keywords K] [--discover-all]" >&2
  exit 2
}

HERE=$(cd "$(dirname "$0")" && pwd)
SKILL_ROOT=$(cd "$HERE/.." && pwd)
SKILL_DETECTORS="$SKILL_ROOT/detectors"
PROJECT_DETECTORS="$TARGET/.scaffold/detectors"

# Step 2 guardrails
[[ "$(cd "$REF" && pwd)" == "$(cd "$TARGET" && pwd)" ]] && {
  echo "SELF_SCAN: reference repo == target repo" >&2; exit 1; }
[[ -d "$REF/src" ]] || { echo "REF_NO_SRC: $REF has no src/ directory" >&2; exit 1; }
# csproj check: warn only — test repos may use Directory.Packages.props without .csproj
if ! find "$REF" -name "*.csproj" -maxdepth 5 2>/dev/null | grep -q .; then
  echo "REF_WARN_NO_CSPROJ: $REF has no *.csproj (continuing)" >&2
fi
if ! git -C "$REF" diff --quiet 2>/dev/null || ! git -C "$REF" diff --cached --quiet 2>/dev/null; then
  echo "REF_DIRTY: reference repo has uncommitted changes" >&2
  printf "Continue anyway? (y/n): " >&2
  read -r ans <&0
  [[ "$ans" =~ ^[yY]$ ]] || exit 1
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

CARDS="$WORK/cards.txt"
STATE="$WORK/state.json"
DECISIONS="$WORK/decisions.json"
DEV_NAMED_STATE="$WORK/dev-named.json"
DISCO_STATE="$WORK/discovered.json"
DISCO_DECISIONS="$WORK/discovered-decisions.json"
PARTIAL="$TARGET/.scaffold/staged/.partial-decisions.json"

mkdir -p "$TARGET/.scaffold/staged"

echo "[1/10] load registry" >&2
PYTHONPATH="$SKILL_ROOT/scripts" python3 -m convention_scan load \
  --skill-detectors "$SKILL_DETECTORS" \
  ${PROJECT_DETECTORS:+--project-detectors "$PROJECT_DETECTORS"} >/dev/null

echo "[3-5/10] scan + extract + resolve packages, render cards" >&2
PYTHONPATH="$SKILL_ROOT/scripts" python3 -m convention_scan scan-and-render \
  --skill-detectors "$SKILL_DETECTORS" \
  ${PROJECT_DETECTORS:+--project-detectors "$PROJECT_DETECTORS"} \
  --reference-repo "$REF" --cards-out "$CARDS" --state-out "$STATE"

# Step 6: dev-named keywords
echo "[]" > "$DEV_NAMED_STATE"
if [[ -n "$KEYWORDS" ]]; then
  echo "[6/10] dev-named keyword scan: $KEYWORDS" >&2
fi

echo "[7/10] dev review of fixed/dev-named cards" >&2
bash "$HERE/convention_scan_prompter.sh" --cards "$CARDS" --out "$DECISIONS" --partial "$PARTIAL"

echo "[8/10] discovery sweep" >&2
CLAIMED="$WORK/claimed.txt"
python3 -c "
import json, sys
data = json.loads(open('$STATE').read())
for w in data['winners']:
    print(w['source'].split(':')[0])
" > "$CLAIMED"
if [[ "$DISCOVER_ALL" == "1" ]]; then
  PYTHONPATH="$SKILL_ROOT/scripts" python3 -m convention_scan discover \
    --reference-repo "$REF" --claimed-files "$CLAIMED" --out "$DISCO_STATE" --discover-all
else
  PYTHONPATH="$SKILL_ROOT/scripts" python3 -m convention_scan discover \
    --reference-repo "$REF" --claimed-files "$CLAIMED" --out "$DISCO_STATE"
fi

# Build cards for discovered + prompt
> "$WORK/disco-cards.txt"
python3 -c "
import json
data = json.loads(open('$DISCO_STATE').read())
for d in data:
    print('CARD: discovered-' + d['name'])
" >> "$WORK/disco-cards.txt"
bash "$HERE/convention_scan_prompter.sh" --cards "$WORK/disco-cards.txt" \
  --out "$DISCO_DECISIONS" --partial "${PARTIAL}.disco"

echo "[9/10] write conventions block + stage snippets" >&2
PYTHONPATH="$SKILL_ROOT/scripts" python3 -m convention_scan write \
  --state "$STATE" --decisions "$DECISIONS" --design "$DESIGN" \
  --staged-root "$TARGET/.scaffold/staged" --reference-repo "$REF" \
  --dev-named "$DEV_NAMED_STATE" \
  --discovered-state "$DISCO_STATE" \
  --discovered-decisions "$DISCO_DECISIONS"

echo "[10/10] git add + commit" >&2
git -C "$TARGET" add "$DESIGN" .scaffold/staged
git -C "$TARGET" -c user.email=convention-scan@scaffold -c user.name="Convention Scan" \
  commit -m "feat(scaffold): convention scan adopted decisions" \
  || echo "GIT_COMMIT: nothing to commit" >&2

echo "DONE" >&2
