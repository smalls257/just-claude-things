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


def _load_csproj_packagerefs(repo_root: Path) -> dict[str, list[str]]:
    """Return {package_name: [versions]} from <PackageReference> directives.

    Reference repos that pin versions inline (without Directory.Packages.props)
    pass their versions through this map so the resolver can hand them to the
    grafter. Packages without an inline Version (under central package
    management) contribute an empty list — the name is registered but no
    csproj-side version is available; .props remains the canonical source.
    """
    table: dict[str, list[str]] = {}
    for csproj in repo_root.rglob("*.csproj"):
        try:
            root = ET.parse(csproj).getroot()
        except ET.ParseError as e:
            print(f"CSPROJ_PARSE_ERROR: {csproj}: {e}", file=sys.stderr)
            continue
        for pr in root.iter("PackageReference"):
            name = pr.get("Include")
            ver = pr.get("Version")
            if not name:
                continue
            table.setdefault(name, [])
            if ver:
                table[name].append(ver)
    return table


def _candidate_for_namespace(ns: str, all_packages: set[str]) -> str | None:
    """Longest-prefix match: prefer the longest package name that is a prefix of namespace."""
    candidates = [p for p in all_packages if ns == p or ns.startswith(p + ".")]
    if not candidates:
        return None
    return max(candidates, key=len)


def _family_root(primary: str) -> str:
    """Return the package-family root key for namespace-sibling expansion.

    Bug X5: real reference repos pin sibling packages whose types extend
    the same root namespace (e.g., Serilog.AspNetCore + Serilog.Sinks.Console
    both extend the `Serilog` namespace). After resolving the primary package
    via longest-prefix namespace match, also pull siblings whose names share
    the primary's family root.

    Single-segment primary (e.g., `Serilog`): root is the segment itself —
    siblings are `Serilog.*`.
    Multi-segment primary (e.g., `Microsoft.AspNetCore.OpenApi`): root is the
    first two segments — siblings are `Microsoft.AspNetCore.*`. Capping at two
    segments prevents over-greedy sweeps (e.g., a single using directive
    pulling every `Microsoft.*` package).
    """
    segs = primary.split(".")
    if len(segs) <= 1:
        return primary
    return ".".join(segs[:2])


def _family_siblings(primary: str, available: set[str]) -> list[str]:
    """Packages in `available` that share the primary's family root,
    excluding the primary itself."""
    root = _family_root(primary)
    out: list[str] = []
    for p in available:
        if p == primary:
            continue
        if p == root or p.startswith(root + "."):
            out.append(p)
    return out


def resolve_packages(
    snippet_text: str, source_file: Path, repo_root: Path
) -> tuple[list[Package], list[str]]:
    namespaces = [m.group(1) for m in USING_RE.finditer(snippet_text)]
    namespaces = [n for n in namespaces if not any(n == p or n.startswith(p + ".") for p in SYSTEM_PREFIXES)]

    props_versions = _load_packageversions(repo_root)
    csproj_versions = _load_csproj_packagerefs(repo_root)
    # available = union of names from both sources
    available = set(props_versions.keys()) | set(csproj_versions.keys())
    # merged versions: .props wins when both sources pin the same package.
    versions: dict[str, list[str]] = {}
    for name in available:
        if name in props_versions and props_versions[name]:
            versions[name] = props_versions[name]
        elif name in csproj_versions and csproj_versions[name]:
            versions[name] = csproj_versions[name]
        else:
            versions[name] = []

    def _pick_version(pkg: str) -> str | None:
        vlist = versions.get(pkg, [])
        if not vlist:
            return None
        if len(set(vlist)) > 1:
            picked = max(vlist, key=_parse_semver)
            print(f"PACKAGE_VERSION_PICK: {pkg} -> {picked} (candidates: {sorted(set(vlist))})", file=sys.stderr)
            return picked
        return vlist[0]

    resolved: dict[str, str] = {}
    unresolved: list[str] = []
    for ns in namespaces:
        cand = _candidate_for_namespace(ns, available)
        if cand is None:
            unresolved.append(ns)
            continue
        if cand in resolved:
            continue
        ver = _pick_version(cand)
        if ver is None:
            unresolved.append(ns)
            continue
        resolved[cand] = ver
        # Bug X5: also pull family siblings — they're not in the unresolved
        # list because no using directive named them, but their types extend
        # the same namespace and the snippet body relies on them at runtime.
        for sib in _family_siblings(cand, available):
            if sib in resolved:
                continue
            sib_ver = _pick_version(sib)
            if sib_ver is not None:
                resolved[sib] = sib_ver

    return [Package(name=n, version=v) for n, v in sorted(resolved.items())], unresolved
