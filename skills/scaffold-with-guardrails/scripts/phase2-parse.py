"""Phase-2 tech-design parser. Reads tech-design markdown, emits JSON task list."""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
from xml.etree import ElementTree as ET


class ParseError(Exception):
    """Raised when parsing encounters a malformed structure."""
    pass


@dataclass(frozen=True)
class Module:
    """Represents a <module> declaration."""
    name: str


@dataclass(frozen=True)
class AdoptedDecision:
    """Represents an adopted convention decision."""
    detector: str
    source: str
    staged: str
    packages: str


@dataclass(frozen=True)
class DevNamedDecision:
    """Represents a dev-named convention decision."""
    target: str
    source: str
    staged: str
    adopted: bool
    packages: str


@dataclass(frozen=True)
class DiscoveredDecision:
    """Represents a discovered convention decision."""
    name: str
    source: str
    staged: str
    adopted: bool
    packages: str


@dataclass(frozen=True)
class Conventions:
    """Represents a <conventions> block with all decision types."""
    reference_repo: str
    reference_repo_commit: str
    scanned_at: str
    engine_version: str
    adopted: List[AdoptedDecision] = field(default_factory=list)
    dev_named: List[DevNamedDecision] = field(default_factory=list)
    discovered: List[DiscoveredDecision] = field(default_factory=list)


@dataclass
class ParseResult:
    """Result of parsing a design document."""
    modules: List[Module]
    conventions: Optional[Conventions] = None
    # Legacy fields for backward compatibility with dict interface
    app_name_hint: str = ""
    slug: str = ""
    tasks: List[dict] = field(default_factory=list)


def parse(markdown: str) -> dict:
    # Bug B guard: `<routes>` is non-canonical. Per TECH-DESIGN-TAGS.md, the
    # endpoint block is named `<endpoints>`. Fail loud here so a doc using
    # the wrong tag does not silently produce zero route tasks.
    if re.search(r"<routes>", markdown):
        raise ParseError(
            "UNKNOWN_TAG: <routes> is not canonical — use <endpoints> "
            "per TECH-DESIGN-TAGS.md."
        )
    slug = _extract_frontmatter_slug(markdown)
    modules = _extract_module_names(markdown)
    app_name_hint = modules[0] if len(modules) == 1 else ""
    entity_tasks = _extract_entity_tasks(markdown)
    row_tasks = [_entity_to_row_task(e) for e in entity_tasks]
    enum_tasks = _extract_enum_tasks(markdown)
    contract_tasks = _extract_contract_tasks(markdown)
    route_tasks = _extract_route_tasks(markdown)
    test_tasks = _derive_test_tasks(entity_tasks, route_tasks)
    migration_tasks = _extract_migration_tasks(markdown)
    return {
        "app_name_hint": app_name_hint,
        "slug": slug,
        "modules": modules,
        "tasks": entity_tasks + row_tasks + enum_tasks + contract_tasks + route_tasks + test_tasks + migration_tasks,
    }


def parse_design(path: Path) -> ParseResult:
    """Parse a tech-design markdown file into modules and conventions.

    Args:
        path: Path to the design markdown file.

    Returns:
        ParseResult with modules and conventions (if present).

    Raises:
        ParseError: If the conventions block is malformed XML.
    """
    markdown = path.read_text(encoding="utf-8")
    module_names = _extract_module_names(markdown)
    modules = [Module(name=name) for name in module_names]
    conventions = _parse_conventions(markdown)
    return ParseResult(modules=modules, conventions=conventions)


def _entity_to_row_task(entity_task: dict) -> dict:
    return {
        "type": "row",
        "module": entity_task["module"],
        "name": entity_task["name"],
        "columns": list(entity_task["columns"]),
    }


def _derive_test_tasks(entity_tasks: list[dict], route_tasks: list[dict]) -> list[dict]:
    unit_tests = [
        {"type": "unit_test", "module": e["module"], "entity": e["name"]}
        for e in entity_tasks
    ]
    integ_tests = [
        {"type": "integration_test", "module": r["module"], "method": r["method"], "path": r["path"]}
        for r in route_tasks
    ]
    return unit_tests + integ_tests


CONV_BLOCK_RE = re.compile(r"<conventions\b.*?</conventions>", re.DOTALL)


def _build_adopted(el) -> AdoptedDecision:
    """Build an AdoptedDecision, validating required attributes.

    Raises ParseError if any required attribute is missing.
    """
    detector = el.get("detector")
    source = el.get("source")
    staged = el.get("staged")
    for attr, val in [("detector", detector), ("source", source), ("staged", staged)]:
        if val is None:
            raise ParseError(f"MALFORMED_CONVENTIONS: <adopted> missing required attr '{attr}'")
    return AdoptedDecision(detector=detector, source=source, staged=staged, packages=el.get("packages", ""))


def _build_dev_named(el) -> DevNamedDecision:
    """Build a DevNamedDecision, validating required attributes.

    Raises ParseError if any required attribute is missing.
    """
    target = el.get("target")
    source = el.get("source")
    staged = el.get("staged")
    for attr, val in [("target", target), ("source", source), ("staged", staged)]:
        if val is None:
            raise ParseError(f"MALFORMED_CONVENTIONS: <dev-named> missing required attr '{attr}'")
    return DevNamedDecision(target=target, source=source, staged=staged,
                            adopted=el.get("adopted", "false") == "true",
                            packages=el.get("packages", ""))


def _build_discovered(el) -> DiscoveredDecision:
    """Build a DiscoveredDecision, validating required attributes.

    Raises ParseError if any required attribute is missing.
    """
    name = el.get("name")
    source = el.get("source")
    staged = el.get("staged")
    for attr, val in [("name", name), ("source", source), ("staged", staged)]:
        if val is None:
            raise ParseError(f"MALFORMED_CONVENTIONS: <discovered> missing required attr '{attr}'")
    return DiscoveredDecision(name=name, source=source, staged=staged,
                              adopted=el.get("adopted", "false") == "true",
                              packages=el.get("packages", ""))


def _parse_conventions(body: str) -> Optional[Conventions]:
    """Parse a <conventions> block from design markdown.

    Returns None if no conventions block is found.
    Raises ParseError if the block is malformed XML or missing required attributes.
    """
    m = CONV_BLOCK_RE.search(body)
    if not m:
        return None
    try:
        root = ET.fromstring(m.group(0))
    except ET.ParseError as e:
        raise ParseError(f"MALFORMED_CONVENTIONS: {e}") from e

    adopted = [_build_adopted(el) for el in root.findall("adopted")]
    dev_named = [_build_dev_named(el) for el in root.findall("dev-named")]
    discovered = [_build_discovered(el) for el in root.findall("discovered")]

    return Conventions(
        reference_repo=root.get("reference-repo", ""),
        reference_repo_commit=root.get("reference-repo-commit", ""),
        scanned_at=root.get("scanned-at", ""),
        engine_version=root.get("engine-version", ""),
        adopted=adopted,
        dev_named=dev_named,
        discovered=discovered,
    )


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

# C# reference types whose properties need `= default!;` to silence CS8618
# under TreatWarningsAsErrors. Value types (Guid, int, bool, DateTime, etc.)
# do not — `default` is a valid value and the compiler does not warn.
# `object` is the parser's fallback for unknown SQL types; treat it as
# reference for safety so the generated code still compiles.
_REFERENCE_CS_TYPES = frozenset({"string", "object"})


def _cs_init_for(cs_type: str) -> str:
    """Return the property initializer suffix (e.g. '= default!;') for a CS
    type, or '' if no initializer is needed.

    A trailing `?` (nullable reference type) means no initializer — `null`
    is a valid value and CS8618 does not fire.
    """
    if cs_type.endswith("?"):
        return ""
    if cs_type in _REFERENCE_CS_TYPES:
        return "= default!;"
    return ""


def _pascal_case(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def _pascal_case_camel(name: str) -> str:
    # Handles lowerCamelCase ("authorId" → "AuthorId") AND snake_case ("page_count" → "PageCount").
    if "_" in name:
        return _pascal_case(name)
    return name[:1].upper() + name[1:] if name else name


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
    # First pass: collect column names that appear in a standalone
    # PRIMARY KEY (col, col, ...) clause. These also count as PK columns
    # for create-params purposes.
    pk_from_clause = set()
    for clause in re.finditer(r"PRIMARY KEY\s*\(([^)]+)\)", body, re.IGNORECASE):
        for n in clause.group(1).split(","):
            pk_from_clause.add(n.strip())
    columns = []
    for raw in _split_top_level_commas(body):
        line = raw.strip()
        if not line or line.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "CHECK", "UNIQUE")):
            continue
        parts = line.split()
        sql_name = parts[0]
        sql_type = parts[1].upper().split("(")[0]
        cs_type = SQL_TO_CS.get(sql_type, "object")
        # Bug E: track PK + DEFAULT for create-params skip rule.
        rest_upper = line.upper()
        is_pk = bool(
            re.search(r"\bPRIMARY\s+KEY\b", rest_upper)
        ) or sql_name in pk_from_clause
        # Ignore DEFAULT inside a -- comment. Strip line-comments first.
        no_comment = re.sub(r"--.*$", "", line).upper()
        has_default = bool(re.search(r"\bDEFAULT\b", no_comment))
        columns.append({
            "sql_name": sql_name,
            "sql_type": sql_type,
            "cs_type": cs_type,
            "cs_name": _pascal_case(sql_name),
            "cs_init": _cs_init_for(cs_type),
            "is_pk": is_pk,
            "has_default": has_default,
        })
    return columns


def _lower_camel(snake_or_pascal: str) -> str:
    """Lower-camel form. snake_case → snakeCase. PascalCase → pascalCase."""
    if "_" in snake_or_pascal:
        parts = snake_or_pascal.split("_")
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
    if not snake_or_pascal:
        return snake_or_pascal
    return snake_or_pascal[0].lower() + snake_or_pascal[1:]


def _build_create_params(columns: list[dict]) -> str:
    """Bug E: assemble the Create() factory's parameter list.

    Per entity.md doc line 42: "all non-PK, non-default columns as
    (Type name, Type name), lowerCamelCase". Empty list → empty string.
    """
    parts = [
        f"{c['cs_type']} {_lower_camel(c['sql_name'])}"
        for c in columns
        if not c.get("is_pk") and not c.get("has_default")
    ]
    return ", ".join(parts)


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
            invariants = invariants_match.group(1).strip() if invariants_match else "(invariants not specified in tech design)"
            cols = _parse_create_table_columns(sql)
            tasks.append({
                "type": "entity",
                "module": module,
                "name": name,
                "columns": cols,
                "invariants": invariants,
                "create_params": _build_create_params(cols),
            })
    return tasks


def _extract_enum_tasks(markdown: str) -> list[dict]:
    explicit: list[dict] = []
    implicit: list[dict] = []
    for mod_match in re.finditer(
        r'<module\s+name="([^"]+)">(.*?)</module>', markdown, re.DOTALL
    ):
        module = mod_match.group(1)
        body = mod_match.group(2)
        # Explicit <enums> block (preferred form). Values may be a fenced code
        # block (```\n...```) OR a markdown bullet list (- value).
        for enums_match in re.finditer(r"<enums>(.*?)</enums>", body, re.DOTALL):
            for h3 in re.finditer(
                r"^###\s+(\S+).*?(?=^###\s|\Z)",
                enums_match.group(1),
                re.MULTILINE | re.DOTALL,
            ):
                name = h3.group(1)
                chunk = h3.group(0)
                values: list[str] = []
                fenced = re.search(r"```\n([\s\S]+?)```", chunk)
                if fenced:
                    values = [v.strip() for v in fenced.group(1).split() if v.strip()]
                else:
                    bullets = re.findall(r"^\s*[-*]\s+(\S+)\s*$", chunk, re.MULTILINE)
                    values = [b.strip() for b in bullets if b.strip()]
                if not values:
                    continue  # heading with neither fence nor bullets — surface as gap
                explicit.append({"type": "enum", "module": module, "name": name, "values": values})

        # Implicit enum: TEXT CHECK (col IN ('a','b',...)) -> enum named {Entity}{ColumnPascal}.
        entities_match = re.search(r"<entities>(.*?)</entities>", body, re.DOTALL)
        if entities_match:
            for h3 in re.finditer(
                r"^###\s+(\S+).*?(?=^###\s|\Z)",
                entities_match.group(1),
                re.MULTILINE | re.DOTALL,
            ):
                entity_name = h3.group(1)
                chunk = h3.group(0)
                for check_in in re.finditer(
                    r"(\w+)\s+TEXT\s+NOT\s+NULL\s+CHECK\s*\(\s*\1\s+IN\s*\((.*?)\)",
                    chunk,
                    re.IGNORECASE | re.DOTALL,
                ):
                    column = check_in.group(1)
                    values_raw = check_in.group(2)
                    values = [v.strip().strip("'\"") for v in values_raw.split(",")]
                    enum_name = f"{entity_name}{_pascal_case(column)}"
                    implicit.append({
                        "type": "enum",
                        "module": module,
                        "name": enum_name,
                        "values": values,
                    })

    # Dedup: implicit enum whose value-set matches an explicit one is dropped.
    # Explicit declarations are canonical; CHECK IN is enforcement, not a new type.
    explicit_value_sets = {(e["module"], frozenset(e["values"])) for e in explicit}
    deduped_implicit = [
        i for i in implicit
        if (i["module"], frozenset(i["values"])) not in explicit_value_sets
    ]
    return explicit + deduped_implicit


def _extract_contract_tasks(markdown: str) -> list[dict]:
    tasks = []
    for mod_match in re.finditer(
        r'<module\s+name="([^"]+)">(.*?)</module>', markdown, re.DOTALL
    ):
        module = mod_match.group(1)
        contracts_match = re.search(r"<contracts>(.*?)</contracts>", mod_match.group(2), re.DOTALL)
        if not contracts_match:
            continue
        for h3 in re.finditer(
            r"^###\s+(\S+).*?(?=^###\s|\Z)",
            contracts_match.group(1),
            re.MULTILINE | re.DOTALL,
        ):
            name = h3.group(1)
            chunk = h3.group(0)
            fields: list[dict] = []
            # Bullet form: "- fieldName: CsType [— comment]" (also matches "* " marker).
            for bullet in re.finditer(
                r"^\s*[-*]\s+(\w+)\s*:\s*([A-Za-z0-9_<>]+)",
                chunk,
                re.MULTILINE,
            ):
                lower_name = bullet.group(1)
                cs_type = bullet.group(2)
                fields.append({
                    "cs_type": cs_type,
                    "cs_name": _pascal_case_camel(lower_name),
                })
            if not fields:
                continue
            tasks.append({"type": "contract", "module": module, "name": name, "fields": fields})
    return tasks


def _extract_route_tasks(markdown: str) -> list[dict]:
    tasks = []
    for mod_match in re.finditer(
        r'<module\s+name="([^"]+)">(.*?)</module>', markdown, re.DOTALL
    ):
        module = mod_match.group(1)
        endpoints_match = re.search(r"<endpoints>(.*?)</endpoints>", mod_match.group(2), re.DOTALL)
        if not endpoints_match:
            continue
        for h3 in re.finditer(
            r"^###\s+(\S+)\s+(\S+).*?(?=^###\s|\Z)",
            endpoints_match.group(1),
            re.MULTILINE | re.DOTALL,
        ):
            method = h3.group(1)
            path = h3.group(2)
            chunk = h3.group(0)
            # Accept both backtick-quoted (`Type`) and unquoted forms. The
            # captured group requires the type name to start with a letter
            # or underscore — C# identifier rule — so a malformed
            # `Response: 404` (status only, no type) does NOT silently
            # capture `4` as the type. The status code prefix is consumed
            # by the leading `\d*\s*` and the capture starts after it.
            request_match = re.search(r"Request:\s*`?([A-Za-z_]\w*)`?", chunk)
            response_match = re.search(r"Response:\s*\d*\s*`?([A-Za-z_]\w*)`?", chunk)
            tasks.append({
                "type": "route",
                "module": module,
                "method": method,
                "path": path,
                "request": request_match.group(1) if request_match else None,
                "response": response_match.group(1) if response_match else None,
            })
    return tasks


def _extract_migration_tasks(markdown: str) -> list[dict]:
    tasks = []
    for mod_match in re.finditer(
        r'<module\s+name="([^"]+)">(.*?)</module>', markdown, re.DOTALL
    ):
        module = mod_match.group(1)
        body = mod_match.group(2)
        entities_match = re.search(r"<entities>(.*?)</entities>", body, re.DOTALL)
        if not entities_match:
            continue
        tables = []
        for h3 in re.finditer(
            r"^###\s+(\S+).*?(?=^###\s|\Z)",
            entities_match.group(1),
            re.MULTILINE | re.DOTALL,
        ):
            entity = h3.group(1)
            sql_fence = re.search(r"```sql\n(.*?)```", h3.group(0), re.DOTALL)
            if not sql_fence:
                continue
            sql = sql_fence.group(1).rstrip()
            if "CREATE TABLE" not in sql.upper():
                continue
            tables.append({"entity": entity, "sql": sql})
        if tables:
            tasks.append({"type": "migration", "module": module, "tables": tables})
    return tasks


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: phase2-parse.py <tech-design.md>", file=sys.stderr)
        sys.exit(2)
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    json.dump(parse(text), sys.stdout, indent=2)
