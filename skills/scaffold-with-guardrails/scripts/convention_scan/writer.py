"""Write <conventions> block + staged snippet files atomically."""
from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from xml.etree import ElementTree as ET


class WriterError(Exception):
    pass


@dataclass(frozen=True)
class ScanMeta:
    reference_repo: str
    reference_repo_commit: str
    scanned_at: str
    engine_version: str


@dataclass(frozen=True)
class AdoptedEntry:
    detector: str
    source: str
    staged: str
    packages: str
    snippet_text: str


@dataclass(frozen=True)
class RejectedEntry:
    detector: str
    source: str
    reason: str


@dataclass(frozen=True)
class DevNamedEntry:
    target: str
    source: str
    staged: str
    adopted: bool
    packages: str
    snippet_text: str


@dataclass(frozen=True)
class DiscoveredEntry:
    name: str
    source: str
    staged: str
    adopted: bool
    packages: str
    snippet_text: str


@dataclass(frozen=True)
class ConflictEntry:
    winner: str
    loser: str
    overlap: str


BLOCK_RE = re.compile(r"<conventions\b.*?</conventions>", re.DOTALL)
START_RE = re.compile(r"<conventions\b")


def _atomic_write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(body)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _render_block(
    meta: ScanMeta,
    adopted: Sequence[AdoptedEntry],
    rejected: Sequence[RejectedEntry],
    dev_named: Sequence[DevNamedEntry],
    discovered: Sequence[DiscoveredEntry],
    conflicts: Sequence[ConflictEntry],
) -> str:
    lines = [
        f'<conventions',
        f'    reference-repo="{meta.reference_repo}"',
        f'    reference-repo-commit="{meta.reference_repo_commit}"',
        f'    scanned-at="{meta.scanned_at}"',
        f'    engine-version="{meta.engine_version}">',
        "",
    ]
    for a in adopted:
        lines.append(
            f'  <adopted detector="{a.detector}" source="{a.source}" '
            f'staged="{a.staged}" packages="{a.packages}"/>'
        )
    for r in rejected:
        lines.append(f'  <rejected detector="{r.detector}" source="{r.source}" reason="{r.reason}"/>')
    for d in dev_named:
        lines.append(
            f'  <dev-named target="{d.target}" source="{d.source}" '
            f'staged="{d.staged}" adopted="{str(d.adopted).lower()}" packages="{d.packages}"/>'
        )
    for d in discovered:
        lines.append(
            f'  <discovered name="{d.name}" source="{d.source}" '
            f'staged="{d.staged}" adopted="{str(d.adopted).lower()}" packages="{d.packages}"/>'
        )
    for c in conflicts:
        lines.append(f'  <conflict winner="{c.winner}" loser="{c.loser}" overlap="{c.overlap}"/>')
    lines.append("</conventions>")
    return "\n".join(lines)


def _validate_existing(body: str) -> str | None:
    m = BLOCK_RE.search(body)
    if not m:
        # Check if there's an unclosed <conventions> block
        if START_RE.search(body):
            raise WriterError(f"MALFORMED_EXISTING_BLOCK: unclosed <conventions> tag")
        return None
    snippet = m.group(0)
    try:
        ET.fromstring(snippet)
    except ET.ParseError as e:
        raise WriterError(f"MALFORMED_EXISTING_BLOCK: {e}") from e
    return snippet


def _existing_is_nonempty(snippet: str) -> bool:
    return bool(re.search(r"<(adopted|dev-named|discovered)\b", snippet))


def write_conventions(
    design_path: Path,
    staged_root: Path,
    meta: ScanMeta,
    adopted: Sequence[AdoptedEntry],
    rejected: Sequence[RejectedEntry],
    dev_named: Sequence[DevNamedEntry],
    discovered: Sequence[DiscoveredEntry],
    conflicts: Sequence[ConflictEntry],
    confirm_overwrite_empty: bool = False,
) -> None:
    if not design_path.exists():
        raise WriterError(f"DESIGN_MISSING: {design_path}")

    body = design_path.read_text()
    existing = _validate_existing(body)

    new_block = _render_block(meta, adopted, rejected, dev_named, discovered, conflicts)
    new_has_adoptions = bool(adopted or any(d.adopted for d in dev_named) or any(d.adopted for d in discovered))

    if existing and _existing_is_nonempty(existing) and not new_has_adoptions and not confirm_overwrite_empty:
        raise WriterError("OVERWRITE_EMPTY: existing block has adoptions but new scan empty; confirm with confirm_overwrite_empty=True")

    if existing:
        new_body = body.replace(existing, new_block)
    else:
        sep = "" if body.endswith("\n") else "\n"
        new_body = body + sep + "\n" + new_block + "\n"

    _atomic_write(design_path, new_body)

    staged_root.mkdir(parents=True, exist_ok=True)
    for entry in adopted:
        target = staged_root.parent / entry.staged if not Path(entry.staged).is_absolute() else Path(entry.staged)
        if entry.staged.startswith("staged/"):
            target = staged_root / Path(entry.staged).name
        _atomic_write(target, entry.snippet_text)
    for d in dev_named:
        if not d.adopted:
            continue
        target = staged_root / Path(d.staged).name
        _atomic_write(target, d.snippet_text)
    for d in discovered:
        if not d.adopted:
            continue
        target = staged_root / Path(d.staged).name
        _atomic_write(target, d.snippet_text)
