import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from phase2_parse import parse_design, ParseError


DESIGN = """
# svc
<module name="core">
</module>

<conventions reference-repo="r" reference-repo-commit="abc1234" scanned-at="2026-05-20T10:00:00Z" engine-version="0.1.0">
  <adopted detector="jwt-bearer" source="src/Auth.cs:L1-L5" staged="staged/jwt-bearer.cs" packages="MS.X:8.0.5"/>
  <dev-named target="flags" source="src/F.cs:L1-L5" staged="staged/dev-flags.cs" adopted="true" packages=""/>
  <discovered name="corr" source="src/C.cs:L1-L5" staged="staged/discovered-corr.cs" adopted="false" packages=""/>
  <rejected detector="redis" source="src/R.cs:L1-L5" reason="dev-skipped"/>
</conventions>
"""


def test_parses_modules_and_conventions(tmp_path):
    p = tmp_path / "svc.md"
    p.write_text(DESIGN)
    result = parse_design(p)
    assert any(m.name == "core" for m in result.modules)
    assert any(a.detector == "jwt-bearer" for a in result.conventions.adopted)
    assert any(d.target == "flags" and d.adopted for d in result.conventions.dev_named)
    assert any(d.name == "corr" and not d.adopted for d in result.conventions.discovered)
    assert result.conventions.reference_repo_commit == "abc1234"


def test_missing_conventions_block_is_okay(tmp_path):
    p = tmp_path / "svc.md"
    p.write_text("# svc\n<module name=\"core\">\n</module>\n")
    result = parse_design(p)
    assert result.conventions is None or result.conventions.adopted == []


def test_malformed_conventions_block_halts(tmp_path):
    p = tmp_path / "svc.md"
    p.write_text("# svc\n<module name=\"core\">\n</module>\n<conventions><adopted unclosed\n</conventions>")
    with pytest.raises(ParseError, match="MALFORMED_CONVENTIONS"):
        parse_design(p)
