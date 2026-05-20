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
