"""Phase-2 tech-design parser. Reads tech-design markdown, emits JSON task list."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse(markdown: str) -> dict:
    slug = _extract_frontmatter_slug(markdown)
    modules = _extract_module_names(markdown)
    app_name_hint = modules[0] if len(modules) == 1 else ""
    return {
        "app_name_hint": app_name_hint,
        "slug": slug,
        "modules": modules,
        "tasks": [],
    }


def _extract_frontmatter_slug(markdown: str) -> str:
    m = re.search(r"^---\n(.*?)\n---", markdown, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    s = re.search(r"^slug:\s*(\S+)", fm, re.MULTILINE)
    return s.group(1) if s else ""


def _extract_module_names(markdown: str) -> list[str]:
    return re.findall(r'<module\s+name="([^"]+)">', markdown)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: phase2-parse.py <tech-design.md>", file=sys.stderr)
        sys.exit(2)
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    json.dump(parse(text), sys.stdout, indent=2)
