"""Map `using <ns>;` directives to NuGet package + version via repo metadata."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class Package:
    name: str
    version: str


USING_RE = re.compile(r"^\s*using\s+([A-Za-z_][\w.]*)\s*;", re.MULTILINE)
SYSTEM_PREFIXES = ("System", "Microsoft.Extensions", "Microsoft.AspNetCore.Http", "Microsoft.AspNetCore.Builder")


def _parse_semver(v: str) -> tuple:
    parts = []
    for p in v.split("-")[0].split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _load_packageversions(repo_root: Path) -> dict[str, list[str]]:
    table: dict[str, list[str]] = {}
    for props in repo_root.rglob("Directory.Packages.props"):
        try:
            root = ET.parse(props).getroot()
        except ET.ParseError as e:
            print(f"CPM_PARSE_ERROR: {props}: {e}", file=sys.stderr)
            continue
        for pv in root.iter("PackageVersion"):
            name = pv.get("Include")
            ver = pv.get("Version")
            if name and ver:
                table.setdefault(name, []).append(ver)
    return table


def _load_csproj_packagerefs(repo_root: Path) -> set[str]:
    refs: set[str] = set()
    for csproj in repo_root.rglob("*.csproj"):
        try:
            root = ET.parse(csproj).getroot()
        except ET.ParseError as e:
            print(f"CSPROJ_PARSE_ERROR: {csproj}: {e}", file=sys.stderr)
            continue
        for pr in root.iter("PackageReference"):
            name = pr.get("Include")
            if name:
                refs.add(name)
    return refs


def _candidate_for_namespace(ns: str, all_packages: set[str]) -> str | None:
    """Longest-prefix match: prefer the longest package name that is a prefix of namespace."""
    candidates = [p for p in all_packages if ns == p or ns.startswith(p + ".")]
    if not candidates:
        return None
    return max(candidates, key=len)


def resolve_packages(
    snippet_text: str, source_file: Path, repo_root: Path
) -> tuple[list[Package], list[str]]:
    namespaces = [m.group(1) for m in USING_RE.finditer(snippet_text)]
    namespaces = [n for n in namespaces if not any(n == p or n.startswith(p + ".") for p in SYSTEM_PREFIXES)]

    versions = _load_packageversions(repo_root)
    available = set(versions.keys()) | _load_csproj_packagerefs(repo_root)

    resolved: dict[str, str] = {}
    unresolved: list[str] = []
    for ns in namespaces:
        cand = _candidate_for_namespace(ns, available)
        if cand is None:
            unresolved.append(ns)
            continue
        if cand in resolved:
            continue
        vlist = versions.get(cand, [])
        if not vlist:
            unresolved.append(ns)
            continue
        if len(set(vlist)) > 1:
            picked = max(vlist, key=_parse_semver)
            print(f"PACKAGE_VERSION_PICK: {cand} -> {picked} (candidates: {sorted(set(vlist))})", file=sys.stderr)
        else:
            picked = vlist[0]
        resolved[cand] = picked

    return [Package(name=n, version=v) for n, v in sorted(resolved.items())], unresolved
