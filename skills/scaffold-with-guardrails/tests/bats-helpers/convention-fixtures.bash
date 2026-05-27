# bats helpers for convention-scan tests.

setup_reference_repo() {
  local dir="$1"
  local signal_text="${2:-AddJwtBearer}"
  mkdir -p "$dir/src/Api"
  cat > "$dir/src/Api/Auth.cs" <<EOF
using Microsoft.AspNetCore.Authentication.JwtBearer;
public static class AuthExt
{
    public static IServiceCollection AddAuth(this IServiceCollection s)
    { s.AddAuthentication().${signal_text}(o => { o.Authority = "x"; }); return s; }
}
EOF
  cat > "$dir/src/Api/Api.csproj" <<'EOF'
<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup><TargetFramework>net9.0</TargetFramework></PropertyGroup></Project>
EOF
  cat > "$dir/Directory.Packages.props" <<'EOF'
<Project><ItemGroup><PackageVersion Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.5"/></ItemGroup></Project>
EOF
  ( cd "$dir" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
}

assert_conventions_block_has() {
  local design="$1"
  local needle="$2"
  grep -q "$needle" "$design" || { echo "MISSING: $needle in $design" >&2; return 1; }
}

assert_staged_file_exists() {
  local target_root="$1"
  local name="$2"
  [ -f "$target_root/.scaffold/staged/$name" ] || { echo "MISSING_STAGED: $name" >&2; return 1; }
}
