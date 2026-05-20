"""Phase-2 tech-design parser. Reads tech-design markdown, emits JSON task list."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse(markdown: str) -> dict:
    slug = _extract_frontmatter_slug(markdown)
    modules = _extract_module_names(markdown)
    app_name_hint = modules[0] if len(modules) == 1 else ""
    entity_tasks = _extract_entity_tasks(markdown)
    return {
        "app_name_hint": app_name_hint,
        "slug": slug,
        "modules": modules,
        "tasks": entity_tasks,
    }


def _extract_frontmatter_slug(markdown: str) -> str:
    m = re.search(r"^---\n(.*?)\n---", markdown, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    s = re.search(r"^slug:\s*(\S+)", fm, re.MULTILINE)
    return s.group(1) if s else ""


def _extract_module_names(markdown: str) -> list[str]:
    return re.findall(r'<module\s+name="([^"]+)">', markdown)


SQL_TO_CS = {
    "UUID": "Guid",
    "BIGINT": "long",
    "INTEGER": "int",
    "INT": "int",
    "TEXT": "string",
    "TIMESTAMPTZ": "DateTimeOffset",
    "TIMESTAMP": "DateTime",
    "BOOLEAN": "bool",
}


def _pascal_case(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def _split_top_level_commas(body: str) -> list[str]:
    """Split on commas that sit at paren-depth 0 — preserves CHECK (... IN (...)) clauses."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _parse_create_table_columns(sql: str) -> list[dict]:
    body_match = re.search(r"CREATE TABLE \w+\s*\((.*?)\);", sql, re.DOTALL | re.IGNORECASE)
    if not body_match:
        return []
    body = body_match.group(1)
    columns = []
    for raw in _split_top_level_commas(body):
        line = raw.strip()
        if not line or line.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "CHECK", "UNIQUE")):
            continue
        parts = line.split()
        sql_name = parts[0]
        sql_type = parts[1].upper().split("(")[0]
        cs_type = SQL_TO_CS.get(sql_type, "object")
        columns.append({
            "sql_name": sql_name,
            "sql_type": sql_type,
            "cs_type": cs_type,
            "cs_name": _pascal_case(sql_name),
        })
    return columns


def _extract_entity_tasks(markdown: str) -> list[dict]:
    tasks = []
    for mod_match in re.finditer(
        r'<module\s+name="([^"]+)">(.*?)</module>', markdown, re.DOTALL
    ):
        module = mod_match.group(1)
        body = mod_match.group(2)
        entities_match = re.search(r"<entities>(.*?)</entities>", body, re.DOTALL)
        if not entities_match:
            continue
        entities_body = entities_match.group(1)
        for h3 in re.finditer(
            r"^###\s+(\S+).*?(?=^###\s|\Z)", entities_body, re.MULTILINE | re.DOTALL
        ):
            name = h3.group(1)
            chunk = h3.group(0)
            sql_fence = re.search(r"```sql\n(.*?)```", chunk, re.DOTALL)
            if not sql_fence:
                continue
            sql = sql_fence.group(1)
            if "CREATE TABLE" not in sql.upper():
                continue  # documentation-only entity
            invariants_match = re.search(r"\*\*Invariants:\*\*\s*(.+?)(?=\n\n|\Z)", chunk, re.DOTALL)
            invariants = invariants_match.group(1).strip() if invariants_match else "TODO: define invariants"
            tasks.append({
                "type": "entity",
                "module": module,
                "name": name,
                "columns": _parse_create_table_columns(sql),
                "invariants": invariants,
            })
    return tasks


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: phase2-parse.py <tech-design.md>", file=sys.stderr)
        sys.exit(2)
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    json.dump(parse(text), sys.stdout, indent=2)
