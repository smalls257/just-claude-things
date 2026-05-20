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
