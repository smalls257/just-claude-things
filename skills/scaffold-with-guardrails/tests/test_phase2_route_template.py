"""Template-content tests for route.md.

The route template is a markdown file the Phase-2 subagent reads and
substitutes per-task. These tests assert the template body itself —
they do not exercise a renderer (there is no Python renderer; the
subagent renders).
"""
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent
TEMPLATE = SKILL_ROOT / "templates" / "csharp" / "phase2-task-templates" / "route.md"


def test_route_template_emits_app_map_method_not_mapmap():
    """Bug C: template previously rendered `app.Map{{METHOD_PASCAL}}` plus
    `{{METHOD_PASCAL}} = "Map" + capitalize` → `app.MapMapPost("/...")`.
    The literal `Map` belongs in the variable, not the template body.
    """
    body = TEMPLATE.read_text()
    # The fixed template has `app.{{METHOD_PASCAL}}(` exactly once.
    assert "app.{{METHOD_PASCAL}}(" in body, (
        "route.md must call `app.{{METHOD_PASCAL}}(...)` — METHOD_PASCAL "
        "already contains the `Map` prefix per the variable docs."
    )
    # The bug form must not appear anywhere.
    assert "app.Map{{METHOD_PASCAL}}" not in body, (
        "route.md still has the double-Map bug — METHOD_PASCAL already "
        "starts with `Map`, so `app.Map{{METHOD_PASCAL}}` renders MapMap."
    )
