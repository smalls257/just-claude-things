import pytest
from pathlib import Path
from convention_scan.writer import (
    write_conventions, WriterError, AdoptedEntry, RejectedEntry,
    DevNamedEntry, DiscoveredEntry, ConflictEntry, ScanMeta,
)


META = ScanMeta(
    reference_repo="../canonical-api",
    reference_repo_commit="a1b2c3d",
    scanned_at="2026-05-20T14:32:00Z",
    engine_version="0.1.0",
)


def _design_with_module_block(design_path: Path):
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text("# Design\n\n<module name=\"core\"/>\n")


def test_writes_block_when_none_exists(tmp_path):
    design = tmp_path / "docs" / "tech-design" / "svc.md"
    _design_with_module_block(design)
    staged_dir = tmp_path / ".scaffold" / "staged"
    write_conventions(
        design_path=design, staged_root=staged_dir, meta=META,
        adopted=[AdoptedEntry("auth-jwt-bearer", "src/Auth.cs:L12-L45", "staged/auth-jwt-bearer.cs",
                              "MS.X:8.0.5", "public class X {}")],
        rejected=[], dev_named=[], discovered=[], conflicts=[],
    )
    body = design.read_text()
    assert "<conventions" in body
    assert "auth-jwt-bearer" in body
    assert (staged_dir / "auth-jwt-bearer.cs").read_text() == "public class X {}"


def test_replaces_existing_block_atomically(tmp_path):
    design = tmp_path / "docs" / "tech-design" / "svc.md"
    _design_with_module_block(design)
    design.write_text(design.read_text() + """
<conventions reference-repo="old" reference-repo-commit="old" scanned-at="old" engine-version="0.0.1">
  <adopted detector="x" source="x" staged="x" packages=""/>
</conventions>
""")
    staged_dir = tmp_path / ".scaffold" / "staged"
    (staged_dir).mkdir(parents=True, exist_ok=True)
    write_conventions(
        design_path=design, staged_root=staged_dir, meta=META,
        adopted=[AdoptedEntry("new", "src/N.cs:L1-L5", "staged/new.cs", "", "// new")],
        rejected=[], dev_named=[], discovered=[], conflicts=[],
    )
    body = design.read_text()
    assert "detector=\"x\"" not in body
    assert "detector=\"new\"" in body


def test_malformed_existing_block_halts(tmp_path):
    design = tmp_path / "docs" / "tech-design" / "svc.md"
    _design_with_module_block(design)
    design.write_text(design.read_text() + "\n<conventions><adopted unclosed\n")
    with pytest.raises(WriterError, match="MALFORMED_EXISTING_BLOCK"):
        write_conventions(
            design_path=design, staged_root=tmp_path / ".scaffold" / "staged", meta=META,
            adopted=[], rejected=[], dev_named=[], discovered=[], conflicts=[],
        )


def test_empty_new_decisions_over_nonempty_old_requires_confirm(tmp_path):
    design = tmp_path / "docs" / "tech-design" / "svc.md"
    _design_with_module_block(design)
    design.write_text(design.read_text() + """
<conventions reference-repo="r" reference-repo-commit="c" scanned-at="t" engine-version="0.1.0">
  <adopted detector="x" source="x" staged="x" packages=""/>
</conventions>
""")
    with pytest.raises(WriterError, match="OVERWRITE_EMPTY"):
        write_conventions(
            design_path=design, staged_root=tmp_path / ".scaffold" / "staged", meta=META,
            adopted=[], rejected=[], dev_named=[], discovered=[], conflicts=[],
            confirm_overwrite_empty=False,
        )


def test_overwrite_empty_confirmed_allows_empty_block(tmp_path):
    design = tmp_path / "docs" / "tech-design" / "svc.md"
    _design_with_module_block(design)
    design.write_text(design.read_text() + """
<conventions reference-repo="r" reference-repo-commit="c" scanned-at="t" engine-version="0.1.0">
  <adopted detector="x" source="x" staged="x" packages=""/>
</conventions>
""")
    write_conventions(
        design_path=design, staged_root=tmp_path / ".scaffold" / "staged", meta=META,
        adopted=[], rejected=[], dev_named=[], discovered=[], conflicts=[],
        confirm_overwrite_empty=True,
    )
    assert "<adopted" not in design.read_text()


def test_rejected_kept_for_re_run_defaults(tmp_path):
    design = tmp_path / "docs" / "tech-design" / "svc.md"
    _design_with_module_block(design)
    write_conventions(
        design_path=design, staged_root=tmp_path / ".scaffold" / "staged", meta=META,
        adopted=[],
        rejected=[RejectedEntry("caching-redis", "src/C.cs:L8-L40", "dev-skipped")],
        dev_named=[], discovered=[], conflicts=[],
    )
    assert "<rejected" in design.read_text()
    assert "caching-redis" in design.read_text()


def test_staged_files_are_written(tmp_path):
    design = tmp_path / "docs" / "tech-design" / "svc.md"
    _design_with_module_block(design)
    staged = tmp_path / ".scaffold" / "staged"
    write_conventions(
        design_path=design, staged_root=staged, meta=META,
        adopted=[AdoptedEntry("a", "src/A.cs:L1-L2", "staged/a.cs", "", "body-a")],
        rejected=[],
        dev_named=[DevNamedEntry("flags", "src/F.cs:L1-L2", "staged/dev-flags.cs", True, "", "body-f")],
        discovered=[DiscoveredEntry("corr", "src/C.cs:L1-L2", "staged/discovered-corr.cs", True, "", "body-c")],
        conflicts=[],
    )
    assert (staged / "a.cs").read_text() == "body-a"
    assert (staged / "dev-flags.cs").read_text() == "body-f"
    assert (staged / "discovered-corr.cs").read_text() == "body-c"
