# Windows bootstrap smoke test

Automated tests cover the bash bootstrap on Linux/macOS. The PowerShell variant is smoke-tested manually because we don't run a Windows CI runner.

## Procedure

1. Clone the scaffolded repo to a Windows machine.
2. Open PowerShell in the repo root.
3. Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
   ```
4. Verify:
   - `git config --get include.path` returns `../.gitconfig.gates`
   - A trivial commit triggers the pre-commit hook
   - Re-running with `-Offline` is idempotent (no duplicate include.path entries)
   - `git config --get-all include.path | Measure-Object -Line` returns `1`

## What's NOT tested

- The `Fetch-Tool` stub is a deliberate v1 placeholder (same as bash).
- Worktree junction creation requires admin privileges on older Windows.
- The `bash` shim for self-test requires Git for Windows to be on PATH.

## Failure escalation

If bootstrap.ps1 fails on a clean Windows checkout, capture the full output and file an issue. Don't bypass — fix the script.
