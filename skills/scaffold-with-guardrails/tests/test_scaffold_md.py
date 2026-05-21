"""Content-pin tests for scaffold.md canonical Program.cs body.

The scaffold agent hand-writes Program.cs by reading this fenced block.
If the markers aren't already in the canonical body, the agent has to
guess where they go, and Bug X2 reproduces (markers placed before
`var builder` — call lines reference an undeclared variable).
"""
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent
SCAFFOLD_MD = SKILL_ROOT / "templates" / "csharp" / "scaffold.md"


def _extract_program_cs_block() -> str:
    """Return the FIRST fenced ```csharp block in scaffold.md that contains
    `var builder = WebApplication.CreateBuilder(args)` AND `app.Run();`.

    That fenced block is the canonical Program.cs body the scaffold agent
    hand-writes. There are other csharp blocks in the same doc (Worker.cs,
    options class examples) — those are filtered out by the dual-anchor
    requirement.
    """
    body = SCAFFOLD_MD.read_text()
    for block in re.findall(r"```csharp\n(.*?)```", body, re.DOTALL):
        if "var builder = WebApplication.CreateBuilder(args)" in block and "app.Run();" in block:
            return block
    raise AssertionError("Canonical Program.cs block not found in scaffold.md")


def test_program_cs_has_builder_time_convention_markers():
    """Task 9 / Bug X2: the canonical body must carry the five builder-time
    markers (logging, observability, auth, data, http-outbound) AFTER the
    builder.Services configuration and BEFORE `var app = builder.Build();`.
    """
    block = _extract_program_cs_block()
    for layer in ("logging", "observability", "auth", "data", "http-outbound"):
        assert f"// {{{{CONVENTION:{layer}}}}}" in block, (
            f"canonical Program.cs body missing builder-time marker for layer '{layer}'"
        )
    # Position check: each marker appears AFTER `.ValidateOnStart();`
    # (last builder.Services call) and BEFORE `var app = builder.Build();`.
    valid_idx = block.index(".ValidateOnStart();")
    build_idx = block.index("var app = builder.Build();")
    for layer in ("logging", "observability", "auth", "data", "http-outbound"):
        marker_idx = block.index(f"// {{{{CONVENTION:{layer}}}}}")
        assert valid_idx < marker_idx < build_idx, (
            f"marker '{layer}' must sit between .ValidateOnStart() and builder.Build()"
        )


def test_program_cs_has_middleware_convention_marker():
    """Task 9 / Bug X2: middleware marker must sit between
    `var app = builder.Build();` and `app.Run();`, ideally near
    `app.UseHttpsRedirection();`.
    """
    block = _extract_program_cs_block()
    assert "// {{CONVENTION:middleware}}" in block, (
        "canonical Program.cs body missing middleware marker"
    )
    build_idx = block.index("var app = builder.Build();")
    run_idx = block.index("app.Run();")
    marker_idx = block.index("// {{CONVENTION:middleware}}")
    assert build_idx < marker_idx < run_idx, (
        "middleware marker must sit between builder.Build() and app.Run()"
    )


def test_program_cs_markers_not_before_var_builder():
    """Bug X2 regression check: no CONVENTION marker may appear BEFORE
    `var builder = ...`. The call lines they get replaced with reference
    `builder` and `app`, which are not yet declared at that point.
    """
    block = _extract_program_cs_block()
    builder_decl_idx = block.index("var builder = WebApplication.CreateBuilder(args)")
    # All markers must come after the builder declaration.
    for layer in ("logging", "observability", "auth", "data", "http-outbound", "middleware"):
        token = f"// {{{{CONVENTION:{layer}}}}}"
        if token in block:
            assert block.index(token) > builder_decl_idx, (
                f"marker '{layer}' appears BEFORE `var builder = ...` — "
                f"graft will emit a call line referencing undeclared `builder`"
            )
