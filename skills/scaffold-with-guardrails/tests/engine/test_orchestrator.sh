#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ORCH="$HERE/../../scripts/convention-scan.sh"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# build a tiny reference repo
mkdir -p "$tmpdir/refrepo/src/Auth"
cat > "$tmpdir/refrepo/src/Auth/JwtAuth.cs" <<'EOF'
using Microsoft.AspNetCore.Authentication.JwtBearer;
public static class JwtAuthExtensions
{
    public static IServiceCollection AddJwtAuth(this IServiceCollection s)
    { s.AddAuthentication().AddJwtBearer(o => { o.Authority = "x"; }); return s; }
}
EOF
cat > "$tmpdir/refrepo/Directory.Packages.props" <<'EOF'
<Project><ItemGroup><PackageVersion Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.5"/></ItemGroup></Project>
EOF
( cd "$tmpdir/refrepo" && git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -q -m init )

mkdir -p "$tmpdir/target/docs/tech-design"
cat > "$tmpdir/target/docs/tech-design/svc.md" <<'EOF'
# svc

<module name="core"/>
EOF
( cd "$tmpdir/target" && git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -q -m init )

# accept everything
printf 'y\ny\ny\ny\ny\ny\ny\ny\ny\ny\n' | "$ORCH" \
  --reference-repo "$tmpdir/refrepo" \
  --target-repo "$tmpdir/target" \
  --design "$tmpdir/target/docs/tech-design/svc.md" \
  --keywords ""

grep -q '<conventions' "$tmpdir/target/docs/tech-design/svc.md" || { echo "block missing"; exit 1; }
grep -q 'jwt-bearer' "$tmpdir/target/docs/tech-design/svc.md" || { echo "adoption missing"; exit 1; }
test -f "$tmpdir/target/.scaffold/staged/jwt-bearer.cs" || { echo "staged missing"; exit 1; }
echo "ORCH OK"
