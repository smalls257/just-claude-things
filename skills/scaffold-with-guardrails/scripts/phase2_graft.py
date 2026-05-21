#!/usr/bin/env python3
"""Phase-2 graft: insert staged convention snippets at template slot markers."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent))
from phase2_parse import parse_design


SLOT_RE_TMPL = r"^\s*//\s*\{\{CONVENTION:%s\}\}\s*$"

# Layers whose snippets belong in infrastructure files (e.g. .props, .json),
# not in Program.cs. Graft skips these instead of raising NO_SLOT.
_INFRA_LAYERS = frozenset({"build"})


def _read_yaml_layer(yaml_path: Path) -> str | None:
    """Return the 'layer' field from a detector YAML, or None on failure."""
    if not _YAML_AVAILABLE:
        return None
    try:
        import yaml
        data = yaml.safe_load(yaml_path.read_text())
        return data.get("layer") if isinstance(data, dict) else None
    except Exception:
        return None


def _layer_for_detector(detector_id: str) -> tuple[str, bool]:
    """Return (layer_name, is_code_layer) for a detector.

    is_code_layer is False for infrastructure layers (e.g. build) whose
    snippets live in project files rather than Program.cs.
    """
    detectors_root = Path(__file__).parent.parent / "detectors"
    for f in detectors_root.rglob("*.yaml"):
        if f.stem == detector_id:
            # Prefer the explicit 'layer' field from YAML; fall back to dir name.
            yaml_layer = _read_yaml_layer(f)
            layer = yaml_layer if yaml_layer else f.parent.name
            return layer, layer not in _INFRA_LAYERS
    print(f"UNKNOWN_DETECTOR: {detector_id} not in detector registry", file=sys.stderr)
    sys.exit(1)


def _graft_one(program_body: str, layer: str, snippet: str, source_comment: str) -> str:
    pattern = re.compile(SLOT_RE_TMPL % re.escape(layer), re.MULTILINE)
    if not pattern.search(program_body):
        print(f"NO_SLOT: template has no '// {{{{CONVENTION:{layer}}}}}' marker", file=sys.stderr)
        sys.exit(1)
    replacement = f"{source_comment}\n{snippet.rstrip()}\n"
    return pattern.sub(replacement, program_body, count=1)


def _ensure_package(cpm_path: Path, name: str, version: str) -> None:
    body = cpm_path.read_text()
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"CPM_PARSE_ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    for pv in root.iter("PackageVersion"):
        if pv.get("Include") == name:
            return  # already present
    group = root.find("ItemGroup")
    if group is None:
        group = ET.SubElement(root, "ItemGroup")
    ET.SubElement(group, "PackageVersion", attrib={"Include": name, "Version": version})
    cpm_path.write_text(ET.tostring(root, encoding="unicode"))


def _staged_text(staged_root: Path, staged_attr: str) -> str:
    target = staged_root / Path(staged_attr).name
    if not target.exists():
        print(f"MISSING_STAGED: {target}", file=sys.stderr)
        sys.exit(1)
    return target.read_text()


def _graft_packages(cpm_path: Path | None, packages_str: str) -> None:
    if not cpm_path or not packages_str:
        return
    for pkg in packages_str.split(","):
        pkg = pkg.strip()
        if not pkg or ":" not in pkg:
            continue
        name, version = pkg.split(":", 1)
        _ensure_package(cpm_path, name, version)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--design", required=True)
    p.add_argument("--target-program", required=True)
    p.add_argument("--staged-root", required=True)
    p.add_argument("--cpm")
    args = p.parse_args()

    result = parse_design(Path(args.design))
    if result.conventions is None:
        print("NO_CONVENTIONS: nothing to graft", file=sys.stderr)
        return

    program = Path(args.target_program)
    body = program.read_text()
    staged_root = Path(args.staged_root)
    cpm_path = Path(args.cpm) if args.cpm else None

    for a in result.conventions.adopted:
        layer, is_code_layer = _layer_for_detector(a.detector)
        if is_code_layer:
            body = _graft_one(body, layer, _staged_text(staged_root, a.staged),
                              f"// SOURCE: adopted:{a.detector} — {a.source}")
        _graft_packages(cpm_path, a.packages)

    for d in result.conventions.dev_named:
        if not d.adopted:
            continue
        layer = f"dev-{d.target}"
        body = _graft_one(body, layer, _staged_text(staged_root, d.staged),
                          f"// SOURCE: dev-named:{d.target} — {d.source}")
        _graft_packages(cpm_path, d.packages)

    for d in result.conventions.discovered:
        if not d.adopted:
            continue
        layer = f"discovered-{d.name}"
        body = _graft_one(body, layer, _staged_text(staged_root, d.staged),
                          f"// SOURCE: discovered:{d.name} — {d.source}")

    program.write_text(body)
    print("GRAFT_OK", file=sys.stderr)


if __name__ == "__main__":
    main()
