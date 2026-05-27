import pytest
from pathlib import Path
from convention_scan.loader import load_registry, RegistryError


def write(p: Path, body: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


VALID = """
id: jwt-bearer
display: JWT bearer auth
layer: auth
priority: 80
files: ["src/**/*.cs"]
signal:
  cs: ["AddJwtBearer"]
extract: enclosing-method-or-extension
"""


def test_loads_single_detector(tmp_path):
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", VALID)
    reg = load_registry(skill_root=tmp_path / "skill", project_root=None)
    assert len(reg) == 1
    assert reg[0].id == "jwt-bearer"
    assert reg[0].layer == "auth"


def test_dedupes_and_sorts_by_priority(tmp_path):
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", VALID)
    write(tmp_path / "skill" / "logging" / "serilog.yaml", VALID.replace("jwt-bearer", "serilog").replace("auth", "logging").replace("80", "30"))
    reg = load_registry(skill_root=tmp_path / "skill", project_root=None)
    assert [d.id for d in reg] == ["jwt-bearer", "serilog"]


def test_project_override_replaces_by_id(tmp_path):
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", VALID)
    override = VALID.replace("priority: 80", "priority: 90\nnotes: project-override")
    write(tmp_path / "proj" / "jwt-bearer.yaml", override)
    reg = load_registry(skill_root=tmp_path / "skill", project_root=tmp_path / "proj")
    assert len(reg) == 1
    assert reg[0].notes == "project-override"


def test_override_without_explicit_replaces_for_different_id_adds_both(tmp_path):
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", VALID)
    bad = VALID.replace("id: jwt-bearer", "id: jwt-bearer-v2")
    write(tmp_path / "proj" / "jwt-bearer-v2.yaml", bad)
    reg = load_registry(skill_root=tmp_path / "skill", project_root=tmp_path / "proj")
    assert len(reg) == 2


def test_explicit_replaces_collapses_pair(tmp_path):
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", VALID)
    override = VALID.replace("id: jwt-bearer", "id: jwt-bearer-v2") + "replaces: jwt-bearer\n"
    write(tmp_path / "proj" / "jwt-bearer-v2.yaml", override)
    reg = load_registry(skill_root=tmp_path / "skill", project_root=tmp_path / "proj")
    assert [d.id for d in reg] == ["jwt-bearer-v2"]


def test_duplicate_id_without_replaces_halts(tmp_path):
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", VALID)
    write(tmp_path / "skill" / "auth" / "jwt-bearer-dup.yaml", VALID)
    with pytest.raises(RegistryError, match="DUPLICATE_ID"):
        load_registry(skill_root=tmp_path / "skill", project_root=None)


def test_malformed_yaml_halts(tmp_path):
    write(tmp_path / "skill" / "auth" / "bad.yaml", "id: [unclosed\n")
    with pytest.raises(RegistryError, match="REGISTRY_PARSE_ERROR"):
        load_registry(skill_root=tmp_path / "skill", project_root=None)


def test_invalid_layer_halts(tmp_path):
    bad = VALID.replace("layer: auth", "layer: not-a-layer")
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", bad)
    with pytest.raises(RegistryError, match="INVALID_LAYER"):
        load_registry(skill_root=tmp_path / "skill", project_root=None)


def test_missing_signal_for_extension_halts(tmp_path):
    bad = VALID.replace("signal:\n  cs: [\"AddJwtBearer\"]", "signal: {}")
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", bad)
    with pytest.raises(RegistryError, match="MISSING_SIGNAL"):
        load_registry(skill_root=tmp_path / "skill", project_root=None)


def test_unknown_top_level_key_warns(tmp_path, capsys):
    extra = VALID + "fictional_key: 1\n"
    write(tmp_path / "skill" / "auth" / "jwt-bearer.yaml", extra)
    load_registry(skill_root=tmp_path / "skill", project_root=None)
    captured = capsys.readouterr()
    assert "UNKNOWN_KEY" in captured.err
