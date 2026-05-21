import pytest
from pathlib import Path
from convention_scan.loader import Detector
from convention_scan.scanner import scan, ScanWarning


def mkdet(**over):
    base = dict(
        id="jwt-bearer", display="JWT", layer="auth", priority=80,
        files=("src/**/*.cs",), signal={"cs": ("AddJwtBearer",)},
        extract="enclosing-method-or-extension",
    )
    base.update(over)
    return Detector(**base)


def write(p: Path, body: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_finds_signal_in_matching_file(tmp_path):
    write(tmp_path / "src" / "Auth.cs", "public void X() { AddJwtBearer(); }")
    claims = scan([mkdet()], repo_root=tmp_path)
    assert len(claims) == 1
    assert claims[0].detector_id == "jwt-bearer"
    assert claims[0].file_path.endswith("Auth.cs")
    assert claims[0].line_number > 0


def test_no_match_returns_empty_and_logs(tmp_path, capsys):
    write(tmp_path / "src" / "Other.cs", "public void Y() {}")
    claims = scan([mkdet()], repo_root=tmp_path)
    assert claims == []
    assert "NO_MATCH: jwt-bearer" in capsys.readouterr().err


def test_skips_unreadable_file_and_logs(tmp_path, capsys):
    write(tmp_path / "src" / "Auth.cs", "AddJwtBearer();")
    bad = tmp_path / "src" / "Bad.cs"
    bad.write_text("AddJwtBearer();")
    bad.chmod(0o000)
    try:
        claims = scan([mkdet()], repo_root=tmp_path)
    finally:
        bad.chmod(0o644)
    assert len(claims) == 1
    assert "READ_FAILED" in capsys.readouterr().err


def test_signal_dispatched_per_extension(tmp_path):
    det = mkdet(
        files=("src/**/*.cs", "config/*.json"),
        signal={"cs": ("AddJwtBearer",), "json": ('"Authority":',)},
    )
    write(tmp_path / "src" / "A.cs", "AddJwtBearer();")
    write(tmp_path / "config" / "x.json", '{ "Authority": "x" }')
    claims = scan([det], repo_root=tmp_path)
    assert len(claims) == 2


def test_warns_on_too_broad_glob(tmp_path, capsys):
    det = mkdet(files=("**/*",))
    write(tmp_path / "src" / "A.cs", "AddJwtBearer();")
    scan([det], repo_root=tmp_path)
    assert "BROAD_GLOB" in capsys.readouterr().err
