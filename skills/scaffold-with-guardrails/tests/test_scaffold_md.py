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


def test_scaffold_md_api_csproj_does_not_reference_persistence():
    """Bug X7: scaffold.md's canonical Api wiring must not add a
    ProjectReference to Persistence. The skill's own generated semgrep
    rule (lib-api-no-persistence-ref) forbids Api→Persistence direct
    references — playbook must not contradict its own gate.
    """
    body = SCAFFOLD_MD.read_text()
    # The playbook should NOT use a shared `for HOST in Api Service` loop
    # that applies Persistence to both. After the fix, Api gets a separate
    # invocation without Persistence.
    # Red test: the buggy form has a for-loop that includes both Api and
    # Service, and that loop adds Persistence. After the fix, either:
    #   (a) The loop is gone and replaced with separate Api/Service blocks, or
    #   (b) The loop conditionally excludes Persistence for Api.
    # We test for the simplest fix: two separate dotnet add invocations.

    # Check: does the file still have a `for HOST in Api Service` loop that
    # references Persistence? If so, the bug is not fixed.
    buggy_pattern = re.search(
        r"for HOST in Api Service.*?done",
        body,
        re.DOTALL,
    )
    if buggy_pattern:
        loop_content = buggy_pattern.group(0)
        # If the shared loop mentions Persistence, the bug is present.
        assert "Persistence" not in loop_content, (
            "Bug X7 not fixed: `for HOST in Api Service` loop still includes "
            "Persistence reference, which contradicts lib-api-no-persistence-ref"
        )

    # Positive check: look for separate Api composition block.
    api_block_match = re.search(
        r"# Api composition root.*?\ndotnet add src/.*?\.Api/.*?reference.*?(?=\n(?:dotnet|#))",
        body,
        re.DOTALL,
    )
    if api_block_match:
        api_section = api_block_match.group(0)
        # Extract only the reference lines (after "reference" keyword).
        # Comments are OK; we just want to ensure the dotnet command doesn't
        # add Persistence to the Api's reference list.
        ref_match = re.search(r"reference(.*?)(?=\n(?:dotnet|#))", api_section, re.DOTALL)
        if ref_match:
            refs = ref_match.group(1)
            assert "Persistence" not in refs, (
                "Api composition root's reference list still includes Persistence"
            )


def test_scaffold_md_persistence_ref_only_for_service_host():
    """Bug X7 positive check: Persistence ProjectRef is added for Service host
    only. The two hosts get separate ref-list invocations OR an explicit
    conditional excludes Persistence from Api.
    """
    body = SCAFFOLD_MD.read_text()
    # Service should have Persistence in its refs.
    service_blocks = re.findall(
        r'dotnet add src/"\$APP"\.Service/.*?(?=\n(?:dotnet|# |$))',
        body,
        re.DOTALL,
    )
    assert any("Persistence" in block for block in service_blocks), (
        "Service composition root must reference Persistence for background-job wiring"
    )
