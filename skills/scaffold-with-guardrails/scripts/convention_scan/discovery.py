"""Sweep unclaimed regions: look for signal-positive code Claude should review."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DiscoveryCandidate:
    name: str
    source_path: str
    start_line: int
    end_line: int
    text: str
    score: int


SIGNAL_FILENAME_KEYWORDS = ("Extensions", "Middleware", "Configuration", "Setup", "Bootstrap", "Module", "Registration")
DI_TYPE_RE = re.compile(r"this\s+(IServiceCollection|IApplicationBuilder|WebApplication|HostBuilder|IHostBuilder)\b")
ADD_USE_RE = re.compile(r"public\s+static\s+\w[\w<>,\s]*\s+(Add|Use)(\w+)\s*\(")


def _is_signal_file(path: Path) -> bool:
    name = path.name
    if not name.endswith(".cs"):
        return False
    return any(kw in name for kw in SIGNAL_FILENAME_KEYWORDS)


def _has_di_extension(text: str) -> bool:
    return bool(DI_TYPE_RE.search(text) and ADD_USE_RE.search(text))


def _name_from(file: Path, text: str) -> str:
    m = ADD_USE_RE.search(text)
    if m:
        return m.group(2).lower()
    return file.stem.replace("Extensions", "").lower()


def sweep(repo_root: Path, claimed_files: set[str], top_n: Optional[int]) -> list[DiscoveryCandidate]:
    resolved_claimed = {str(Path(p).resolve()) for p in claimed_files}
    cands: list[DiscoveryCandidate] = []
    for f in sorted(repo_root.rglob("*.cs")):
        if str(f.resolve()) in resolved_claimed:
            continue
        if not _is_signal_file(f):
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        if not _has_di_extension(text):
            continue
        lines = text.split("\n")
        cands.append(DiscoveryCandidate(
            name=_name_from(f, text),
            source_path=str(f),
            start_line=1,
            end_line=len(lines),
            text=text,
            score=len(lines),
        ))
    cands.sort(key=lambda c: (-c.score, c.source_path))
    if top_n is not None:
        cands = cands[:top_n]
    return cands
