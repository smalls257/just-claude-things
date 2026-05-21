#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PB="$HERE/../../scripts/phase2-postbuild.sh"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

cat > "$tmpdir/svc.md" <<'EOF'
# svc
<conventions reference-repo="r" reference-repo-commit="c" scanned-at="t" engine-version="0.1.0">
  <adopted detector="jwt-bearer" source="src/Auth.cs:L1-L5" staged="staged/jwt-bearer.cs" packages=""/>
  <adopted detector="serilog" source="src/Log.cs:L1-L5" staged="staged/serilog.cs" packages=""/>
</conventions>
EOF

cat > "$tmpdir/Program.cs" <<'EOF'
// SOURCE: adopted:jwt-bearer — src/Auth.cs:L1-L5
builder.Services.AddJwtBearer();
EOF

# Missing serilog graft — expect failure
set +e
"$PB" --check-grafts --design "$tmpdir/svc.md" --target-program "$tmpdir/Program.cs"
rc=$?
set -e
[ "$rc" -ne 0 ] || { echo "FAIL: should have failed — serilog graft missing"; exit 1; }

# Add the serilog comment — should now pass
echo "// SOURCE: adopted:serilog — src/Log.cs:L1-L5" >> "$tmpdir/Program.cs"
"$PB" --check-grafts --design "$tmpdir/svc.md" --target-program "$tmpdir/Program.cs"
echo "POSTBUILD OK"
