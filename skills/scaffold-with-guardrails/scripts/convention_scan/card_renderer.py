"""Render reviewable TTY card for one detector claim."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .extractor import Region
from .package_resolver import Package


@dataclass(frozen=True)
class CardInput:
    detector_id: str
    display: str
    source_path: str
    region: Region
    packages: Sequence[Package]
    unresolved: Sequence[str] = ()
    conflict_notes: Sequence[str] = ()


BAR = "=" * 70
SEP = "-" * 70


def render_card(inp: CardInput) -> str:
    pkgs = ",".join(f"{p.name}:{p.version}" for p in inp.packages) or "(none)"
    lines = [
        BAR,
        f"DETECTOR: {inp.detector_id} — {inp.display}",
        f"SOURCE:   {inp.source_path}:L{inp.region.start_line}-L{inp.region.end_line}",
        f"PACKAGES: {pkgs}",
    ]
    if inp.unresolved:
        lines.append("UNRESOLVED: " + ", ".join(inp.unresolved))
    if inp.conflict_notes:
        lines.append("CONFLICTS: " + "; ".join(inp.conflict_notes))
    lines.append(SEP)
    lines.append(inp.region.text)
    lines.append(SEP)
    return "\n".join(lines) + "\n"
