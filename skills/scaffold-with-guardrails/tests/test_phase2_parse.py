import json
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import phase2_parse  # noqa: E402

FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "library-demo.md"


def test_parses_single_module():
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    assert result["app_name_hint"] == "Catalog"
    assert result["slug"] == "library-demo"
    assert result["modules"] == ["Catalog"]


def test_emits_entity_tasks_with_columns():
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    entity_tasks = [t for t in result["tasks"] if t["type"] == "entity"]
    assert len(entity_tasks) == 2

    author = next(t for t in entity_tasks if t["name"] == "Author")
    assert author["module"] == "Catalog"
    assert author["columns"] == [
        {"sql_name": "id",         "sql_type": "UUID",        "cs_type": "Guid",           "cs_name": "Id",        "cs_init": ""},
        {"sql_name": "name",       "sql_type": "TEXT",        "cs_type": "string",         "cs_name": "Name",      "cs_init": "= default!;"},
        {"sql_name": "created_at", "sql_type": "TIMESTAMPTZ", "cs_type": "DateTimeOffset", "cs_name": "CreatedAt", "cs_init": ""},
    ]
    assert author["invariants"] == "name is non-empty."


def test_entity_columns_preserve_check_in_constraints():
    # Locks the _split_top_level_commas contract: Book.status's CHECK IN
    # constraint has commas inside parens that must NOT split the column list.
    # If this regresses, the column becomes orphan fragments and the parser
    # either crashes or silently produces malformed columns.
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    book = next(t for t in result["tasks"] if t["type"] == "entity" and t["name"] == "Book")
    status_col = next(c for c in book["columns"] if c["sql_name"] == "status")
    assert status_col["sql_type"] == "TEXT"
    assert status_col["cs_type"] == "string"


def test_emits_row_tasks_one_per_entity():
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    row_tasks = [t for t in result["tasks"] if t["type"] == "row"]
    assert len(row_tasks) == 2

    author_row = next(t for t in row_tasks if t["name"] == "Author")
    assert author_row["module"] == "Catalog"
    assert author_row["columns"][0]["cs_name"] == "Id"
    assert author_row["columns"][0]["cs_type"] == "Guid"


def test_emits_enum_task_explicit_wins_over_implicit():
    # The fixture has BOTH an explicit <enums>ReadingStatus (bullet list) AND
    # an implicit CHECK IN on Book.status with the same values. Explicit wins
    # via value-set dedup; the implicit derived name is suppressed.
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    enum_tasks = [t for t in result["tasks"] if t["type"] == "enum"]
    assert len(enum_tasks) == 1

    reading_status = enum_tasks[0]
    assert reading_status["name"] == "ReadingStatus"
    assert reading_status["module"] == "Catalog"
    assert reading_status["values"] == ["unread", "reading", "completed", "abandoned"]


def test_implicit_enum_emitted_when_no_explicit_block_matches_values():
    # If a CHECK IN has values that don't match any explicit enum, the
    # implicit {Entity}{Column} enum IS emitted — the dedup only fires
    # on value-set equality.
    fake_design = '''---
slug: x
---
# X
<module name="X">
<entities>

### Order

```sql
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  state TEXT NOT NULL CHECK (state IN ('open','paid','shipped'))
);
```

**Invariants:** state transitions monotonic.
</entities>
</module>'''
    result = phase2_parse.parse(fake_design)
    enum_tasks = [t for t in result["tasks"] if t["type"] == "enum"]
    assert len(enum_tasks) == 1
    assert enum_tasks[0]["name"] == "OrderState"
    assert enum_tasks[0]["values"] == ["open", "paid", "shipped"]


def test_emits_contract_tasks_from_bullet_lists():
    # Fixture has 5 contracts in bullet form: "- fieldName: CsType — comment".
    # Field cs_name is PascalCase (CreateAuthorRequest.name → Name; CreateBookRequest.authorId → AuthorId).
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    contracts = [t for t in result["tasks"] if t["type"] == "contract"]
    assert len(contracts) == 5

    create_author = next(t for t in contracts if t["name"] == "CreateAuthorRequest")
    assert create_author["module"] == "Catalog"
    assert create_author["fields"] == [{"cs_type": "string", "cs_name": "Name"}]

    author_response = next(t for t in contracts if t["name"] == "AuthorResponse")
    assert author_response["fields"] == [
        {"cs_type": "Guid",   "cs_name": "Id"},
        {"cs_type": "string", "cs_name": "Name"},
    ]

    # lowerCamelCase field name gets PascalCased correctly.
    create_book = next(t for t in contracts if t["name"] == "CreateBookRequest")
    assert {"cs_type": "Guid", "cs_name": "AuthorId"} in create_book["fields"]
    assert {"cs_type": "int",  "cs_name": "PageCount"} in create_book["fields"]


def test_contract_field_snake_case_pascalized():
    # Locks the _pascal_case_camel snake_case branch: contract author may write
    # snake_case bullet field names. They must be PascalCased correctly
    # (page_count → PageCount, not Page_count).
    fake_design = '''---
slug: x
---
# X
<module name="X">
<contracts>

### XThing

- page_count: int
- author_id: Guid

</contracts>
</module>'''
    result = phase2_parse.parse(fake_design)
    contracts = [t for t in result["tasks"] if t["type"] == "contract"]
    assert len(contracts) == 1
    assert contracts[0]["fields"] == [
        {"cs_type": "int",  "cs_name": "PageCount"},
        {"cs_type": "Guid", "cs_name": "AuthorId"},
    ]


def test_emits_route_tasks_from_routes_block():
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    route_tasks = [t for t in result["tasks"] if t["type"] == "route"]
    assert len(route_tasks) == 5

    post = next(
        t for t in route_tasks if t["method"] == "POST" and t["path"] == "/authors"
    )
    assert post["module"] == "Catalog"
    assert post["request"] == "CreateAuthorRequest"
    assert post["response"] == "AuthorResponse"

    get = next(
        t for t in route_tasks if t["method"] == "GET" and t["path"] == "/authors/{id}"
    )
    assert get["request"] is None
    assert get["response"] == "AuthorResponse"

    post_books = next(
        t for t in route_tasks if t["method"] == "POST" and t["path"] == "/books"
    )
    assert post_books["module"] == "Catalog"
    assert post_books["request"] == "CreateBookRequest"
    assert post_books["response"] == "BookResponse"

    get_book = next(
        t for t in route_tasks if t["method"] == "GET" and t["path"] == "/books/{id}"
    )
    assert get_book["request"] is None
    assert get_book["response"] == "BookResponse"

    put_status = next(
        t
        for t in route_tasks
        if t["method"] == "PUT" and t["path"] == "/books/{id}/status"
    )
    assert put_status["request"] == "UpdateStatusRequest"
    assert put_status["response"] == "BookResponse"


def test_emits_unit_test_task_per_entity_and_integration_test_per_route():
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    unit_tests = [t for t in result["tasks"] if t["type"] == "unit_test"]
    integ_tests = [t for t in result["tasks"] if t["type"] == "integration_test"]

    assert len(unit_tests) == 2  # Author, Book
    assert {(t["module"], t["entity"]) for t in unit_tests} == {
        ("Catalog", "Author"),
        ("Catalog", "Book"),
    }

    assert len(integ_tests) == 5
    assert {(t["module"], t["method"], t["path"]) for t in integ_tests} == {
        ("Catalog", "POST", "/authors"),
        ("Catalog", "GET", "/authors/{id}"),
        ("Catalog", "POST", "/books"),
        ("Catalog", "GET", "/books/{id}"),
        ("Catalog", "PUT", "/books/{id}/status"),
    }


def test_emits_one_migration_task_per_module_with_table_sql():
    result = phase2_parse.parse(FIXTURE.read_text())
    migrations = [t for t in result["tasks"] if t["type"] == "migration"]
    assert len(migrations) == 1

    lib = migrations[0]
    assert lib["module"] == "Catalog"
    assert len(lib["tables"]) == 2
    # Order should match emission order in the fixture (Author before Book).
    assert lib["tables"][0]["entity"] == "Author"
    assert lib["tables"][1]["entity"] == "Book"
    # Each table carries its raw CREATE TABLE SQL — emit template will indent/include verbatim.
    assert "CREATE TABLE authors" in lib["tables"][0]["sql"]
    assert "CREATE TABLE books" in lib["tables"][1]["sql"]


def test_entity_columns_carry_cs_init_for_non_nullable_reference_types():
    # Bug #4: under TreatWarningsAsErrors=true, a non-nullable reference-type
    # property without an initializer raises CS8618. The entity template
    # consumes `column.cs_init` and appends it after the property declaration
    # (e.g. `public string Name { get; private set; } = default!;`).
    #
    # Lock: string and object (parser fallback) get `= default!;`. Value types
    # (Guid, int, bool, DateTime, DateTimeOffset, long) get nothing — `default`
    # is a valid value and the compiler does not warn.
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    author = next(t for t in result["tasks"] if t["type"] == "entity" and t["name"] == "Author")
    by_name = {c["cs_name"]: c for c in author["columns"]}
    assert by_name["Id"]["cs_init"] == ""           # Guid (value type)
    assert by_name["Name"]["cs_init"] == "= default!;"  # string (reference type)
    assert by_name["CreatedAt"]["cs_init"] == ""    # DateTimeOffset (value type)


def test_entity_template_references_column_cs_init():
    # Bug #4: the entity template must consume `{{column.cs_init}}` so the
    # parser-emitted initializer suffix actually lands in the generated file.
    # Without this expression in the template, the parser change is dead code.
    template = (SKILL_ROOT / "templates" / "csharp" / "phase2-task-templates" / "entity.md").read_text()
    assert "{{column.cs_init}}" in template, \
        "entity template must reference column.cs_init to emit = default!; for non-nullable reference props (CS8618 fix)"


def test_contract_template_imports_domain_module_namespace():
    # Bug #5: contract DTOs frequently reference Domain enums (e.g. HoldStatus).
    # Without `using {{APP_NAME}}.Domain.{{MODULE}};`, those refs fail to
    # resolve and the build red-lights. Threading "does this field reference
    # an enum?" through the parser was rejected as more invasive than the
    # cost of an unconditional using (IDE0005 only, not a warning).
    template = (SKILL_ROOT / "templates" / "csharp" / "phase2-task-templates" / "contract.md").read_text()
    assert "using {{APP_NAME}}.Domain.{{MODULE}};" in template, \
        "contract template must import Domain.<Module> so DTOs can reference Domain enums without a build break"


def test_cli_emits_valid_json_to_stdout(tmp_path):
    fixture_copy = tmp_path / "library-demo.md"
    fixture_copy.write_text(FIXTURE.read_text(encoding="utf-8"))
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "phase2-parse.py"), str(fixture_copy)],
        capture_output=True,
        text=True,
        check=True,
    )
    parsed = json.loads(result.stdout)
    assert parsed["slug"] == "library-demo"
    assert parsed["modules"] == ["Catalog"]
    # Sanity: all task types are present.
    types = {t["type"] for t in parsed["tasks"]}
    assert types == {"entity", "row", "enum", "contract", "route", "unit_test", "integration_test", "migration"}


def test_cli_exits_2_with_usage_on_missing_argument():
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "phase2-parse.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "usage:" in result.stderr
    # Usage message must name the script so the user knows what they invoked wrong.
    assert "phase2-parse" in result.stderr


def test_cli_exits_nonzero_when_file_missing(tmp_path):
    missing = tmp_path / "no-such-file.md"
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "phase2-parse.py"), str(missing)],
        capture_output=True,
        text=True,
    )
    # Current behavior: FileNotFoundError traceback → exit 1. Lock non-zero,
    # not the specific code, so a future graceful-error refactor stays free.
    assert result.returncode != 0
    # User must see which file we couldn't find.
    assert str(missing) in result.stderr


import pytest


_ENDPOINTS_DESIGN = '''---
slug: x
---
# X
<module name="X">

<contracts>

### CreateOrderRequest

- customerId: Guid
- items: long

### OrderResponse

- id: Guid
- status: string

</contracts>

<endpoints>

### POST /orders

- Request: CreateOrderRequest
- Response: 201 OrderResponse
- Auth: required

### GET /orders/{id}

- Response: 200 OrderResponse | 404

</endpoints>

</module>
'''


def test_endpoints_tag_emits_route_tasks():
    """Bug B: parser must search <endpoints> per TECH-DESIGN-TAGS.md."""
    result = phase2_parse.parse(_ENDPOINTS_DESIGN)
    routes = [t for t in result["tasks"] if t["type"] == "route"]
    assert len(routes) == 2

    post = next(r for r in routes if r["method"] == "POST")
    assert post["path"] == "/orders"
    assert post["request"] == "CreateOrderRequest"
    assert post["response"] == "OrderResponse"

    get = next(r for r in routes if r["method"] == "GET")
    assert get["path"] == "/orders/{id}"
    assert get["request"] is None
    assert get["response"] == "OrderResponse"


def test_endpoints_bullet_unquoted_request_response():
    """Bug B: Request:/Response: bullets without backticks must parse.
    TECH-DESIGN-TAGS.md example at line 97-99 uses unquoted refs.
    """
    result = phase2_parse.parse(_ENDPOINTS_DESIGN)
    routes = [t for t in result["tasks"] if t["type"] == "route"]
    post = next(r for r in routes if r["method"] == "POST")
    assert post["request"] == "CreateOrderRequest", (
        "Bullet `- Request: CreateOrderRequest` without backticks must "
        "still be picked up — the doc example uses this form."
    )


def test_routes_tag_raises_unknown_tag_error():
    """Bug B: explicit `<routes>` (non-canonical) must fail loud, not produce
    zero tasks silently. Drift in either direction surfaces immediately.
    """
    bad_design = _ENDPOINTS_DESIGN.replace("<endpoints>", "<routes>").replace(
        "</endpoints>", "</routes>"
    )
    with pytest.raises(phase2_parse.ParseError) as excinfo:
        phase2_parse.parse(bad_design)
    assert "<routes>" in str(excinfo.value)
    assert "<endpoints>" in str(excinfo.value)


def test_endpoints_response_status_only_does_not_capture_digit():
    """Bug B refinement: `Response: 404` (status code only, no type name)
    must NOT silently capture `4` as the response type. The captured group
    enforces C# identifier rule (starts with letter or underscore)."""
    design = '''---
slug: x
---
<module name="X">

<endpoints>

### DELETE /orders/{id}

- Response: 404

</endpoints>

</module>
'''
    result = phase2_parse.parse(design)
    routes = [t for t in result["tasks"] if t["type"] == "route"]
    assert len(routes) == 1
    assert routes[0]["response"] is None, (
        "Status-only response `Response: 404` should yield response=None, "
        f"not the digit `{routes[0]['response']}` captured from the status code."
    )
