from pathlib import Path
import sys

SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import phase2_parse  # noqa: E402

FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "library-demo.md"


def test_parses_single_module():
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    assert result["app_name_hint"] == "Library"
    assert result["slug"] == "library-demo"
    assert result["modules"] == ["Library"]


def test_emits_entity_tasks_with_columns():
    result = phase2_parse.parse(FIXTURE.read_text(encoding="utf-8"))
    entity_tasks = [t for t in result["tasks"] if t["type"] == "entity"]
    assert len(entity_tasks) == 2

    author = next(t for t in entity_tasks if t["name"] == "Author")
    assert author["module"] == "Library"
    assert author["columns"] == [
        {"sql_name": "id",         "sql_type": "UUID",        "cs_type": "Guid",           "cs_name": "Id"},
        {"sql_name": "name",       "sql_type": "TEXT",        "cs_type": "string",         "cs_name": "Name"},
        {"sql_name": "created_at", "sql_type": "TIMESTAMPTZ", "cs_type": "DateTimeOffset", "cs_name": "CreatedAt"},
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
    assert author_row["module"] == "Library"
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
    assert reading_status["module"] == "Library"
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
    assert create_author["module"] == "Library"
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
    assert len(route_tasks) == 2

    post = next(t for t in route_tasks if t["method"] == "POST")
    assert post["module"] == "Library"
    assert post["path"] == "/authors"
    assert post["request"] == "CreateAuthorRequest"
    assert post["response"] == "AuthorResponse"

    get = next(t for t in route_tasks if t["method"] == "GET")
    assert get["path"] == "/authors/{id}"
    assert get["request"] is None
    assert get["response"] == "AuthorResponse"
