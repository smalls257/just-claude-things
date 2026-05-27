#!/usr/bin/env python3
"""Phase-2 graft: insert staged convention snippets at template slot markers."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
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

# Layer → subdirectory under src/<App>.<HostLayer>/ where the snippet file
# is moved. Maps to the directory layout the previous run used by hand.
# Unknown layers fall back to the layer name itself (PascalCased).
_LAYER_DIR = {
    "logging": "Logging",
    "observability": "Observability",
    "auth": "Auth",
    "data": "Data",
    "middleware": "Middleware",
    "http-outbound": "Http",
    "caching": "Caching",
    "messaging": "Messaging",
    "security": "Security",
    "api-conventions": "ApiConventions",
}

# Which middleware-ish layers' call site lives AFTER `var app = builder.Build();`
# rather than before. Matches the Program.cs template — the `middleware` slot
# is the only one beneath the build line.
_POST_BUILD_LAYERS = frozenset({"middleware"})

# Match a `public static class <Name>` declaration. We rely on the snippet
# being self-contained (one outer class). If there are multiple, we take the
# first — convention-scan only stages one block per detector.
_CLASS_RE = re.compile(r"public\s+(?:static\s+)?(?:sealed\s+)?(?:partial\s+)?class\s+(\w+)")

# Match a `public static <RetType> <MethodName>(...)` declaration. We collect
# every candidate and rank them; the ranking decides the call site shape.
_METHOD_RE = re.compile(
    r"public\s+static\s+(?:async\s+)?[\w<>,\s\?\[\]]+?\s+(\w+)\s*\(\s*([^)]*)\)",
    re.DOTALL,
)


def _strip_attrs(s: str) -> str:
    return re.sub(r"\[[^\]]*\]\s*", "", s).strip()


def _ranked_entry_points(snippet: str) -> list[tuple[int, str, str, str]]:
    """Return candidate entry points ranked by call-site preference.

    Each tuple is (rank, method_name, first_param_type, first_param_name).
    Lower rank = preferred. Empty list when nothing matches.

    Heuristic precedence (matches the bug-#6 spec):
      1. extension method `this WebApplicationBuilder`
      2. extension method `this IServiceCollection`
      3. extension method `this WebApplication`
      4. plain static method whose first param is WebApplicationBuilder
      5. plain static method whose first param is IServiceCollection
      6. plain static method whose first param is WebApplication
      7. any other public static method (alphabetical fallback)
    """
    candidates: list[tuple[int, str, str, str]] = []
    for m in _METHOD_RE.finditer(snippet):
        name = m.group(1)
        params = m.group(2).strip()
        if not params:
            continue
        first_param = _strip_attrs(params.split(",", 1)[0])
        is_extension = first_param.startswith("this ")
        body = first_param[5:].strip() if is_extension else first_param
        # body now looks like "WebApplicationBuilder builder" — pull the type.
        parts = body.split()
        if len(parts) < 2:
            continue
        first_type, first_name = parts[0], parts[1]
        if first_type == "WebApplicationBuilder":
            rank = 1 if is_extension else 4
        elif first_type == "IServiceCollection":
            rank = 2 if is_extension else 5
        elif first_type == "WebApplication":
            rank = 3 if is_extension else 6
        else:
            rank = 7
        candidates.append((rank, name, first_type, first_name))
    # Stable sort: rank first, then alphabetical method name.
    candidates.sort(key=lambda c: (c[0], c[1]))
    return candidates


_MIDDLEWARE_RE = re.compile(
    r"public\s+(?:async\s+)?Task\s+InvokeAsync\s*\(\s*HttpContext\b"
)


def _emit_call_line(snippet: str, class_name: str | None) -> str | None:
    """Render the single line that replaces the slot marker.

    Returns None when no entry point can be inferred — the caller leaves a
    TODO comment in that case (do not crash the graft over a heuristic miss).
    """
    # Middleware classes have no static entry point — they are registered by
    # type via app.UseMiddleware<T>(). Detect by the InvokeAsync(HttpContext)
    # signature and short-circuit before the entry-point ranking.
    if class_name is not None and _MIDDLEWARE_RE.search(snippet):
        return f"app.UseMiddleware<{class_name}>();"

    eps = _ranked_entry_points(snippet)
    if not eps:
        return None
    rank, method, first_type, _ = eps[0]
    if rank == 1:  # extension this WebApplicationBuilder
        return f"builder.{method}();"
    if rank == 2:  # extension this IServiceCollection
        return f"builder.Services.{method}();"
    if rank == 3:  # extension this WebApplication
        return f"app.{method}();"
    if class_name is None:
        return None
    if rank == 4:  # static (WebApplicationBuilder builder)
        return f"{class_name}.{method}(builder);"
    if rank == 5:  # static (IServiceCollection services)
        return f"{class_name}.{method}(builder.Services);"
    if rank == 6:  # static (WebApplication app)
        return f"{class_name}.{method}(app);"
    return f"{class_name}.{method}();"


def _outer_class_name(snippet: str) -> str | None:
    m = _CLASS_RE.search(snippet)
    return m.group(1) if m else None


def _host_namespace(app_name: str, layer: str) -> str:
    subdir = _LAYER_DIR.get(layer, layer.replace("-", " ").title().replace(" ", ""))
    return f"{app_name}.Api.{subdir}"


def _host_file_path(target_root: Path, app_name: str, layer: str, class_name: str) -> Path:
    subdir = _LAYER_DIR.get(layer, layer.replace("-", " ").title().replace(" ", ""))
    return target_root / "src" / f"{app_name}.Api" / subdir / f"{class_name}.cs"


# Default usings written into every grafted host file. The detector layer
# can suggest narrower ones, but these cover the common surface and the
# rest is up to the developer's editor's "remove unused" pass.
_DEFAULT_USINGS = (
    "using System;",
    "using Microsoft.AspNetCore.Builder;",
    "using Microsoft.AspNetCore.Http;",
    "using Microsoft.Extensions.DependencyInjection;",
)

# Bug A: third-party namespace roots we know about. When a snippet using
# names one of these as its first segment, emit a `// TODO NUGET: <root>`
# comment so the dev sees the package gap. Not exhaustive — additions are
# safe but missing entries only cost a comment, not correctness.
#
# Entries here are not required to have matching pins in
# Directory.Packages.props. The TODO is a *breadcrumb* that the dev must
# act on (add the package, picking the right one for their needs);
# auto-installing a guessed package would be a Silent Fallback.
_KNOWN_THIRD_PARTY_ROOTS = frozenset({
    "Serilog",
    "MassTransit",
    "MediatR",
    "FluentValidation",
    "Polly",
    "Dapper",
    "Npgsql",
    "Microsoft.AspNetCore.Authentication.JwtBearer",
})


_USING_RE = re.compile(r"^\s*using\s+[A-Za-z0-9_.]+\s*;(?:\s*//.*)?\s*$")


def _extract_snippet_usings(snippet: str) -> list[str]:
    """Bug A: pull `using X;` lines from the top of a staged snippet.

    Scans line-by-line from the top. Each line that matches a using
    directive is captured. The first non-blank, non-using line ends the
    block — even if more using directives appear later, they are NOT
    captured (only the top preamble is the convention's contract).
    """
    out = []
    for line in snippet.splitlines():
        stripped = line.strip()
        if not stripped:
            if not out:
                continue  # leading blank line, keep scanning
            continue  # blank between usings, keep scanning
        if _USING_RE.match(line):
            out.append(stripped)
            continue
        break  # first non-using non-blank → preamble done
    return out


def _wrap_in_file(class_block: str, namespace: str) -> str:
    """Wrap a bare class block in a file-scoped namespace + merged usings.

    Bug A: previously this used `_DEFAULT_USINGS` only and dropped any
    `using X;` lines that lived at the top of the staged snippet. The
    grafted host file then failed CS0103 because the snippet's body
    referenced types from the dropped usings (e.g. `Log.Logger` requires
    `using Serilog;`). The fix:
      1. Capture snippet usings via `_extract_snippet_usings`.
      2. Strip them from the body so the wrapped file does not double-emit.
      3. Merge with `_DEFAULT_USINGS`, preserving order (snippet first,
         defaults second), deduped.
      4. For each snippet using whose first segment is a known third-party
         root, emit a `// TODO NUGET: <root>` comment above it.
    """
    snippet_usings = _extract_snippet_usings(class_block)
    # Strip the captured usings (and any leading blank lines) from the body.
    body = class_block
    for u in snippet_usings:
        # Remove the first matching using line (account for whitespace).
        body = re.sub(
            r"^\s*" + re.escape(u) + r"\s*\n",
            "",
            body,
            count=1,
        )
    body = body.lstrip()

    merged_usings: list[str] = []
    seen: set[str] = set()
    for u in list(snippet_usings) + list(_DEFAULT_USINGS):
        if u not in seen:
            merged_usings.append(u)
            seen.add(u)

    # Insert NuGet TODOs above snippet usings whose root is third-party.
    annotated: list[str] = []
    for u in merged_usings:
        if u in snippet_usings:
            m = re.match(r"using\s+([A-Za-z0-9_.]+)\s*;", u)
            if m:
                # Match against either the full namespace OR its first segment.
                ns = m.group(1)
                root = ns.split(".")[0]
                if ns in _KNOWN_THIRD_PARTY_ROOTS or root in _KNOWN_THIRD_PARTY_ROOTS:
                    annotated.append(f"// TODO NUGET: {root}")
        annotated.append(u)

    return (
        "\n".join(annotated)
        + f"\n\nnamespace {namespace};\n\n"
        + body
        + ("\n" if not body.endswith("\n") else "")
    )


def _ensure_program_using(program_body: str, host_namespace: str) -> str:
    """Bug A: insert `using <host_namespace>;` in Program.cs if absent.

    Insertion point: immediately after the last `^using ` line at column 0.
    If no using lines exist, prepend at the top. Idempotent — already-present
    using is a no-op.

    Preserves the line-ending style of the existing usings (LF vs CRLF)
    so we don't introduce mixed endings on Windows-checked-out repos.
    """
    target_line = f"using {host_namespace};"
    if target_line in program_body:
        return program_body
    lines = program_body.splitlines(keepends=True)
    last_using_idx = -1
    detected_eol = "\n"
    for i, line in enumerate(lines):
        if line.startswith("using ") and line.rstrip().endswith(";"):
            last_using_idx = i
            if line.endswith("\r\n"):
                detected_eol = "\r\n"
            elif line.endswith("\n"):
                detected_eol = "\n"
    if last_using_idx == -1:
        return target_line + detected_eol + program_body
    lines.insert(last_using_idx + 1, target_line + detected_eol)
    return "".join(lines)


def _infer_app_name(target_program: Path) -> str:
    """Derive the App name from the .Api project path that contains Program.cs.

    `src/<App>.Api/Program.cs` → `<App>`. Falls back to the parent dir name
    minus a `.Api` suffix if the file is rooted elsewhere.
    """
    parent = target_program.parent.name
    if parent.endswith(".Api"):
        return parent[: -len(".Api")]
    return parent


def _read_yaml_layer(yaml_path: Path) -> str | None:
    """Return the 'layer' field from a detector YAML, or None on failure."""
    if not _YAML_AVAILABLE:
        return None
    try:
        import yaml
        data = yaml.safe_load(yaml_path.read_text())
        return data.get("layer") if isinstance(data, dict) else None
    except Exception as e:
        print(f"WARN: could not read layer from {yaml_path}: {e}", file=sys.stderr)
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


def _slot_exists(program_body: str, layer: str) -> bool:
    """Check if a slot marker exists for the given layer."""
    pattern = re.compile(SLOT_RE_TMPL % re.escape(layer), re.MULTILINE)
    return bool(pattern.search(program_body))


def _graft_one(
    program_body: str,
    layer: str,
    snippet: str,
    source_comment: str,
    target_root: Path,
    app_name: str,
) -> str:
    """Insert a call line at the slot and write the snippet to a separate host file.

    Bug #6: previously this inlined the full `public static class X { ... }`
    block at the slot marker, which is invalid C# in a Program.cs that uses
    top-level statements (nested class declarations cannot appear between
    statements). The fix:
      1. Lift the class block into `src/<App>.Api/<LayerDir>/<Class>.cs`
         wrapped in a file-scoped namespace.
      2. Replace the marker with a single call line derived from the entry
         point (extension method on IServiceCollection / WebApplicationBuilder /
         WebApplication, or static method invocation otherwise).
      3. When no entry point can be inferred, leave a TODO comment and do
         not crash — convention-scan stage runs uninstrumented; we surface
         the gap rather than block the build.
    """
    pattern = re.compile(SLOT_RE_TMPL % re.escape(layer), re.MULTILINE)
    if not pattern.search(program_body):
        print(f"NO_SLOT: template has no '// {{{{CONVENTION:{layer}}}}}' marker", file=sys.stderr)
        sys.exit(1)

    class_name = _outer_class_name(snippet)
    call_line = _emit_call_line(snippet, class_name)

    if class_name is None or call_line is None:
        # Could not infer a host file or call shape. Leave breadcrumbs at the
        # slot so the dev can wire it manually; do not crash the graft.
        replacement = (
            f"{source_comment}\n"
            f"// TODO: wire {class_name or '<unknown class>'} — convention-scan "
            f"could not infer entry shape from staged snippet for layer '{layer}'.\n"
        )
        return pattern.sub(replacement, program_body, count=1)

    host_path = _host_file_path(target_root, app_name, layer, class_name)
    host_path.parent.mkdir(parents=True, exist_ok=True)
    namespace = _host_namespace(app_name, layer)
    host_path.write_text(_wrap_in_file(snippet, namespace))

    # Bug A: ensure Program.cs has `using <host_namespace>;` so the call
    # line below resolves without a fully-qualified path.
    program_body = _ensure_program_using(program_body, namespace)

    replacement = (
        f"{source_comment}\n"
        f"// HOSTED: src/{app_name}.Api/{_LAYER_DIR.get(layer, layer)}/{class_name}.cs\n"
        f"{call_line}\n"
    )
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
    # Bug X4a: re-indent so the new <PackageVersion> doesn't run on with
    # </ItemGroup>. ET.tostring preserves source whitespace but appends new
    # SubElements without a tail. Pretty-printing the whole tree fixes it.
    ET.indent(root, space="  ")
    cpm_path.write_text(ET.tostring(root, encoding="unicode") + "\n")


def _ensure_csproj_reference(csproj_path: Path, name: str) -> None:
    """Bug X4b: add <PackageReference Include="Name" /> to a csproj if absent.

    Under central package management (`ManagePackageVersionsCentrally=true`),
    csprojs declare PackageReference WITHOUT Version — the version lives in
    Directory.Packages.props. Without this reference, the project does not
    consume the package and `dotnet build` fails CS0246 even though the
    version is pinned in .props.
    """
    body = csproj_path.read_text()
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"CSPROJ_PARSE_ERROR: {csproj_path}: {e}", file=sys.stderr)
        sys.exit(1)
    for pr in root.iter("PackageReference"):
        if pr.get("Include") == name:
            return  # already present
    group = root.find("ItemGroup")
    if group is None:
        group = ET.SubElement(root, "ItemGroup")
    ET.SubElement(group, "PackageReference", attrib={"Include": name})
    ET.indent(root, space="  ")
    csproj_path.write_text(ET.tostring(root, encoding="unicode") + "\n")


def _staged_text(staged_root: Path, staged_attr: str) -> str:
    target = staged_root / Path(staged_attr).name
    if not target.exists():
        print(f"MISSING_STAGED: {target}", file=sys.stderr)
        sys.exit(1)
    return target.read_text()


def _graft_packages(cpm_path: Path | None, packages_str: str, csproj_paths: list[Path] | None = None) -> None:
    if not packages_str:
        return
    for pkg in packages_str.split(","):
        pkg = pkg.strip()
        if not pkg or ":" not in pkg:
            continue
        name, version = pkg.split(":", 1)
        if cpm_path:
            _ensure_package(cpm_path, name, version)
        if csproj_paths:
            for csproj in csproj_paths:
                _ensure_csproj_reference(csproj, name)


def _target_root_of(program: Path) -> Path:
    """Walk up from src/<App>.Api/Program.cs to the repo root.

    The graft writes snippet host files under `<repo-root>/src/<App>.Api/<Layer>/...`,
    so we need the path two levels above Program.cs in the standard layout.
    Falls back to two-parent-up if the path differs.
    """
    # standard: <root>/src/<App>.Api/Program.cs
    if program.parent.parent.name == "src":
        return program.parent.parent.parent
    return program.parent.parent


def _format_target_project(target_root: Path, app_name: str) -> None:
    """Bug X6: run `dotnet format` on the target Api project after graft.

    Convention snippets come from a reference repo that may use different
    formatting (braceless `if`, single-line lambdas, etc.) than the target.
    Under `TreatWarningsAsErrors=true`, the target's `.editorconfig` may
    promote IDE0011/IDE0058 to errors; the grafted snippet then fails to
    build. Running `dotnet format` once after all grafts reconciles style
    against the target's rules.

    Bounded to the Api csproj to keep runtime tolerable. Silently skips
    if `dotnet` is not on PATH (CI without .NET, unit tests).
    """
    if shutil.which("dotnet") is None:
        print("WARN: dotnet not on PATH — skipping post-graft format", file=sys.stderr)
        return
    csproj = target_root / "src" / f"{app_name}.Api" / f"{app_name}.Api.csproj"
    if not csproj.exists():
        print(f"WARN: csproj not found at {csproj} — skipping post-graft format", file=sys.stderr)
        return
    result = subprocess.run(
        ["dotnet", "format", str(csproj), "--no-restore"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"WARN: dotnet format exited {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--design", required=True)
    p.add_argument("--target-program", required=True)
    p.add_argument("--staged-root", required=True)
    p.add_argument("--cpm")
    p.add_argument("--target-root", help="repo root where src/<App>.Api/... lives; inferred from --target-program when omitted")
    p.add_argument("--app-name", help="App name (defaults to dirname of Program.cs minus .Api suffix)")
    p.add_argument("--no-format", action="store_true", help="Skip post-graft `dotnet format` (use for tests without .NET on PATH)")
    args = p.parse_args()

    result = parse_design(Path(args.design))
    if result.conventions is None:
        print("NO_CONVENTIONS: nothing to graft", file=sys.stderr)
        return

    program = Path(args.target_program)
    body = program.read_text()
    staged_root = Path(args.staged_root)
    cpm_path = Path(args.cpm) if args.cpm else None
    target_root = Path(args.target_root) if args.target_root else _target_root_of(program)
    app_name = args.app_name or _infer_app_name(program)
    api_csprojs = list(target_root.glob("src/*.Api/*.csproj"))

    for a in result.conventions.adopted:
        layer, is_code_layer = _layer_for_detector(a.detector)
        if is_code_layer:
            body = _graft_one(body, layer, _staged_text(staged_root, a.staged),
                              f"// SOURCE: adopted:{a.detector} — {a.source}",
                              target_root, app_name)
        _graft_packages(cpm_path, a.packages, api_csprojs)

    for d in result.conventions.dev_named:
        if not d.adopted:
            continue
        layer = f"dev-{d.target}"
        if not _slot_exists(body, layer):
            print(f"WARN_NO_SLOT: no '// {{{{CONVENTION:{layer}}}}}' in template — add marker to graft dev-named:{d.target}", file=sys.stderr)
            continue
        body = _graft_one(body, layer, _staged_text(staged_root, d.staged),
                          f"// SOURCE: dev-named:{d.target} — {d.source}",
                          target_root, app_name)
        _graft_packages(cpm_path, d.packages, api_csprojs)

    for d in result.conventions.discovered:
        if not d.adopted:
            continue
        layer = f"discovered-{d.name}"
        if not _slot_exists(body, layer):
            print(f"WARN_NO_SLOT: no '// {{{{CONVENTION:{layer}}}}}' in template — add marker to graft discovered:{d.name}", file=sys.stderr)
            continue
        body = _graft_one(body, layer, _staged_text(staged_root, d.staged),
                          f"// SOURCE: discovered:{d.name} — {d.source}",
                          target_root, app_name)

    program.write_text(body)

    if not args.no_format:
        _format_target_project(target_root, app_name)

    print("GRAFT_OK", file=sys.stderr)


if __name__ == "__main__":
    main()
