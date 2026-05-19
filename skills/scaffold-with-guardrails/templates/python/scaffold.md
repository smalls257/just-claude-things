# Python Scaffold — Step-by-Step

Canonical scaffold the skill applies when the tech-design's stack is Python 3.10+.

## Grill questions

1. **App name** (snake_case, e.g., `expense_portal`)
2. **Web framework needed?** → FastAPI default; user can opt to Flask
3. **CLI entrypoint needed?** → adds `__main__.py`

## Default stack choices

| Concern | Choice | Why |
|---|---|---|
| Package manager | **uv** | Fast, reproducible; respects `pyproject.toml` |
| Linter / format | **ruff** | One tool, no flake8/black/isort sprawl |
| Test runner | **pytest** | Standard |
| Type checker | **mypy --strict** | Buffer principle: types are docs that compile |

## Scaffold commands

```bash
APP=expense_portal
uv init --package "$APP"
uv add fastapi uvicorn[standard]
uv add --dev pytest pytest-asyncio mypy ruff
```

## Files hand-written after uv init

- `pyproject.toml` extended with `[tool.ruff]`, `[tool.mypy]` strict config
- `.semgrep/<app>/quality.yaml`, `security.yaml` (Python equivalents)
- `tests/conftest.py`
- `CLAUDE.md`, `AGENTS.md` per layer

## Gate system installation

Same as csharp scaffold — see `templates/csharp/scaffold.md` "Gate system installation" section. Skip the `.NET-conditional` block.
