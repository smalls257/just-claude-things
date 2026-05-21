"""Load + validate detector registry. Skill defaults merged with project overrides."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

VALID_LAYERS = {
    "auth", "logging", "data", "caching", "http-inbound", "http-outbound",
    "middleware", "observability", "messaging", "testing",
    "api-conventions", "build", "security",
}

VALID_EXTRACT = {
    "enclosing-method-or-extension",
    "enclosing-method",
    "enclosing-class",
    "appsettings-section",
    "props-property",
}

KNOWN_KEYS = {
    "id", "display", "layer", "priority", "files", "signal", "extract",
    "replaces", "notes",
}


class RegistryError(Exception):
    pass


@dataclass(frozen=True)
class Detector:
    id: str
    display: str
    layer: str
    priority: int
    files: tuple
    signal: dict
    extract: str
    replaces: Optional[str] = None
    notes: Optional[str] = None
    source_path: Optional[str] = None


def _parse_one(path: Path) -> Detector:
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise RegistryError(f"REGISTRY_PARSE_ERROR: {path}: {e}") from e
    if not isinstance(raw, dict):
        raise RegistryError(f"REGISTRY_PARSE_ERROR: {path}: top-level must be mapping")

    for key in raw:
        if key not in KNOWN_KEYS and not key.startswith("line-range"):
            print(f"UNKNOWN_KEY: {path}: {key}", file=sys.stderr)

    required = ("id", "display", "layer", "priority", "files", "signal", "extract")
    for k in required:
        if k not in raw:
            raise RegistryError(f"MISSING_FIELD: {path}: {k}")

    layer = raw["layer"]
    if layer not in VALID_LAYERS:
        raise RegistryError(f"INVALID_LAYER: {path}: {layer}")

    extract = raw["extract"]
    if not (extract in VALID_EXTRACT or extract.startswith("line-range:")):
        raise RegistryError(f"INVALID_EXTRACT: {path}: {extract}")

    priority = raw["priority"]
    if not isinstance(priority, int) or not (0 <= priority <= 100):
        raise RegistryError(f"INVALID_PRIORITY: {path}: {priority}")

    files = tuple(raw["files"])
    signal_raw = raw["signal"] or {}
    needed_exts = {ext for ext in ("cs", "json", "props", "editorconfig") if any(ext in g for g in files)}
    for ext in needed_exts:
        if ext not in signal_raw or not signal_raw[ext]:
            raise RegistryError(f"MISSING_SIGNAL: {path}: signal.{ext} required for files={files}")
    signal = {k: tuple(v) for k, v in signal_raw.items()}

    return Detector(
        id=raw["id"],
        display=raw["display"],
        layer=layer,
        priority=priority,
        files=files,
        signal=signal,
        extract=extract,
        replaces=raw.get("replaces"),
        notes=raw.get("notes"),
        source_path=str(path),
    )


def load_registry(skill_root: Path, project_root: Optional[Path]) -> list:
    """Return validated, deduped, priority-sorted detector list."""
    detectors: dict = {}

    for yml in sorted(skill_root.rglob("*.yaml")):
        d = _parse_one(yml)
        if d.id in detectors:
            raise RegistryError(
                f"DUPLICATE_ID: {d.id} in {yml} and {detectors[d.id].source_path} "
                f"— skill defaults must have unique ids"
            )
        detectors[d.id] = d

    if project_root and project_root.exists():
        for yml in sorted(project_root.rglob("*.yaml")):
            d = _parse_one(yml)
            target_id = d.replaces or d.id
            if target_id in detectors:
                detectors.pop(target_id)
            detectors[d.id] = d

    return sorted(detectors.values(), key=lambda x: (-x.priority, x.id))
