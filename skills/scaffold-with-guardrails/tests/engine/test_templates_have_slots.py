from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRAM_CS = ROOT / "templates" / "csharp" / "Program.cs"
SNIPPETS = ROOT / "templates" / "csharp" / "snippets"

REQUIRED_SLOTS = [
    "// {{CONVENTION:auth}}",
    "// {{CONVENTION:logging}}",
    "// {{CONVENTION:middleware}}",
    "// {{CONVENTION:observability}}",
    "// {{CONVENTION:http-outbound}}",
    "// {{CONVENTION:data}}",
]


def test_program_cs_has_all_required_slots():
    body = PROGRAM_CS.read_text()
    missing = [s for s in REQUIRED_SLOTS if s not in body]
    assert not missing, f"missing slot markers: {missing}"


def test_each_layer_has_stub_template():
    for layer in ("auth", "logging", "data", "middleware", "observability", "http-outbound"):
        f = SNIPPETS / f"{layer}.stub.cs"
        assert f.exists(), f"missing stub template: {f}"
