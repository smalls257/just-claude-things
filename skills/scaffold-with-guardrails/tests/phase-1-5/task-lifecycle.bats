#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures
load ../bats-helpers/assertions

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  TASKLOG=$(mktemp)
  export TASKLOG
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/docs/tech-design"
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
}

teardown() { rm -rf "$TARGET" "$REF" "$TASKLOG"; }

@test "every pipeline step emits in_progress + completed lines" {
  run bash -c "printf 'y\ny\ny\ny\ny\n' | TASKLOG='$TASKLOG' bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo '$REF' --target-repo '$TARGET' \
    --design '$TARGET/docs/tech-design/svc.md' --keywords ''"
  [ "$status" -eq 0 ]
  for n in load-registry grill-reference run-detectors resolve-conflicts \
           resolve-packages grill-keywords dev-review discovery-sweep \
           write-block commit; do
    assert_task_in_progress "$TASKLOG" "$n"
    assert_task_completed "$TASKLOG" "$n"
  done
}
