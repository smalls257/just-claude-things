#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  mkdir -p "$REF/src/Empty"
  echo '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>' > "$REF/src/Empty/Empty.csproj"
  echo 'public class Plain { public void X() {} }' > "$REF/src/Empty/Plain.cs"
  echo '<Project></Project>' > "$REF/Directory.Packages.props"
  ( cd "$REF" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
  mkdir -p "$TARGET/docs/tech-design"
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "empty reference repo produces empty conventions block, no halt" {
  run bash -c "printf 'y\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo '$REF' --target-repo '$TARGET' \
    --design '$TARGET/docs/tech-design/svc.md' --keywords ''"
  [ "$status" -eq 0 ]
  grep -q '<conventions' "$TARGET/docs/tech-design/svc.md"
  ! grep -q '<adopted' "$TARGET/docs/tech-design/svc.md"
}
