#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PROMPTER="$HERE/../../scripts/convention_scan_prompter.sh"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# Three cards, all accepted/rejected
cat > "$tmpdir/cards.txt" <<'EOF'
CARD: auth-jwt-bearer
CARD: logging-serilog
CARD: data-multi-tenancy
EOF

out_file="$tmpdir/decisions.json"
printf 'y\ny\nn\n' | "$PROMPTER" --cards "$tmpdir/cards.txt" --out "$out_file" --partial "$tmpdir/.partial.json"

grep -q '"auth-jwt-bearer": "y"' "$out_file" || { echo "missing auth decision"; exit 1; }
grep -q '"data-multi-tenancy": "n"' "$out_file" || { echo "missing rejection"; exit 1; }
echo "PROMPTER OK"
