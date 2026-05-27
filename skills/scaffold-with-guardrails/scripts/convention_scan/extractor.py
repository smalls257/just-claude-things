"""Extract enclosing code region around a hit line."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


class ExtractError(Exception):
    pass


@dataclass(frozen=True)
class Region:
    file_path: str
    start_line: int
    end_line: int
    text: str


def _balance(text: str, hit_idx: int) -> tuple[int, int]:
    """Find { ... } block enclosing hit_idx. Returns (open_idx, close_idx) inclusive."""
    depth = 0
    open_idx = -1
    for i in range(hit_idx, -1, -1):
        c = text[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                open_idx = i
                break
            depth -= 1
    if open_idx < 0:
        raise ExtractError("EXTRACT_FAILED: no enclosing open-brace")
    depth = 0
    for j in range(open_idx, len(text)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return open_idx, j
    raise ExtractError("EXTRACT_FAILED: truncated; no matching close-brace")


def _balance_forward(text: str, start_idx: int) -> tuple[int, int]:
    """Find the next { ... } block at or after start_idx. Returns (open_idx, close_idx).

    Used for file-scoped namespaces and other cases where the hit line precedes
    its own body brace and no enclosing brace exists above it.
    """
    open_idx = text.find("{", start_idx)
    if open_idx < 0:
        raise ExtractError("EXTRACT_FAILED: no following open-brace")
    depth = 0
    for j in range(open_idx, len(text)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return open_idx, j
    raise ExtractError("EXTRACT_FAILED: truncated; no matching close-brace")


def _header_start(text: str, brace_idx: int) -> int:
    i = brace_idx - 1
    while i >= 0 and text[i] in " \t\r\n":
        i -= 1
    return text.rfind("\n", 0, i) + 1


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


_CLASS_DECL_RE = re.compile(r"\b(?:class|struct|record|interface)\s+\w+")

# Bug A root cause fix: file-level using directives must travel with the
# extracted class/method snippet so the grafter can preserve them in the
# host file. Without this, `using Serilog;` is stripped here and the
# grafter's preservation logic never sees it in real e2e flow.
_FILE_USING_RE = re.compile(r"^\s*using\s+[A-Za-z0-9_.]+\s*;(?:\s*//.*)?\s*$")


def _collect_file_usings(text: str) -> list[str]:
    """Capture `using X;` lines from the top of the file.

    Scans line-by-line. Each line matching `_FILE_USING_RE` is captured
    (preserving its original whitespace + any trailing `// comment`).
    The first non-blank-non-using line ends the scan — subsequent
    using directives inside the body are NOT captured (those belong
    where they live in the body, if any).
    """
    out: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue  # blank — keep scanning
        if _FILE_USING_RE.match(line):
            out.append(line.rstrip("\r\n"))
            continue
        break  # first non-blank-non-using line ends the preamble
    return out


def _line_bounds(text: str, hit_line: int) -> tuple[int, int]:
    """Return (line_start_idx, line_end_idx_exclusive) for the 1-indexed hit_line."""
    lines = text.split("\n")
    line_start = sum(len(l) + 1 for l in lines[: hit_line - 1])
    line_end = line_start + len(lines[hit_line - 1]) if hit_line <= len(lines) else line_start
    return line_start, line_end


def _hit_line_text(text: str, hit_line: int) -> str:
    lines = text.split("\n")
    return lines[hit_line - 1] if 1 <= hit_line <= len(lines) else ""


def _resolve_inner_block(text: str, hit_line: int) -> tuple[int, int]:
    """Find the block braces relevant to the hit line.

    Walks backward from the hit line to find an enclosing `{`. If that fails
    (e.g. the hit lands on a type-declaration line at file root in a
    file-scoped namespace), walks forward from the hit line to find the
    block this declaration opens. This second case is what makes file-scoped
    namespaces work without rewriting reference repos to block-scoped form.
    """
    line_start, line_end = _line_bounds(text, hit_line)
    try:
        return _balance(text, line_end - 1 if line_end > line_start else line_start)
    except ExtractError:
        # No enclosing brace (file-scoped namespace + hit on type declaration).
        # If the hit line itself opens a block, use that block.
        if _CLASS_DECL_RE.search(_hit_line_text(text, hit_line)):
            return _balance_forward(text, line_start)
        raise


def _extract_cs(text: str, hit_line: int, mode: str) -> tuple[int, int, str]:
    inner_open, inner_close = _resolve_inner_block(text, hit_line)
    file_usings = _collect_file_usings(text)

    def _with_usings(snippet: str) -> str:
        if not file_usings:
            return snippet
        return "\n".join(file_usings) + "\n\n" + snippet

    if mode == "enclosing-method":
        start = _header_start(text, inner_open)
        snippet = text[start: inner_close + 1]
        return _line_of(text, start), _line_of(text, inner_close), _with_usings(snippet)

    if mode == "enclosing-class":
        # Three shapes to handle:
        # (a) Hit on the class declaration line in a file-scoped namespace —
        #     _resolve_inner_block walked forward; inner_open is the class
        #     body. Header on this block IS the class.
        # (b) Hit inside the class body in a file-scoped namespace —
        #     inner_open is a method/property body; we want one level up.
        # (c) Hit inside a block-scoped namespace — inner_open is the class
        #     body (when hit is on a member) or the namespace body (when hit
        #     is on the class line itself).
        # Walk outward as long as the enclosing header is not a class-like
        # declaration; stop once we land on a class/struct/record/interface.
        cur_open, cur_close = inner_open, inner_close
        for _ in range(4):  # bounded — C# nesting deeper than this is pathological
            header_start = _header_start(text, cur_open)
            header = text[header_start:cur_open]
            if _CLASS_DECL_RE.search(header):
                snippet = text[header_start: cur_close + 1]
                return _line_of(text, header_start), _line_of(text, cur_close), _with_usings(snippet)
            try:
                cur_open, cur_close = _balance(text, cur_open - 1)
            except ExtractError:
                break
        # Fell off the top without finding a class header. Return what we have
        # rather than crashing — the caller will see an oversized snippet and
        # the dev review card surfaces the issue.
        header_start = _header_start(text, inner_open)
        snippet = text[header_start: inner_close + 1]
        return _line_of(text, header_start), _line_of(text, inner_close), _with_usings(snippet)

    if mode == "enclosing-method-or-extension":
        try:
            outer_open, outer_close = _balance(text, inner_open - 1)
        except ExtractError:
            start = _header_start(text, inner_open)
            return _line_of(text, start), _line_of(text, inner_close), _with_usings(text[start: inner_close + 1])
        outer_header_start = _header_start(text, outer_open)
        outer_header = text[outer_header_start:outer_open]
        if "static class" in outer_header:
            snippet = text[outer_header_start: outer_close + 1]
            return _line_of(text, outer_header_start), _line_of(text, outer_close), _with_usings(snippet)
        start = _header_start(text, inner_open)
        return _line_of(text, start), _line_of(text, inner_close), _with_usings(text[start: inner_close + 1])

    raise ExtractError(f"UNKNOWN_MODE: {mode}")


def _extract_json_section(text: str, hit_line: int) -> tuple[int, int, str]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ExtractError(f"EXTRACT_FAILED: invalid JSON: {e}") from e
    lines = text.split("\n")
    hit_idx = sum(len(l) + 1 for l in lines[: hit_line - 1])
    for key in obj:
        key_pat = re.compile(r'"' + re.escape(key) + r'"\s*:')
        for m in key_pat.finditer(text):
            value_start = text.find("{", m.end())
            if value_start < 0:
                continue
            try:
                _, value_end = _balance(text, value_start)
            except ExtractError:
                continue
            start = text.rfind("\n", 0, m.start()) + 1
            if start <= hit_idx <= value_end:
                snippet = text[start: value_end + 1]
                return _line_of(text, start), _line_of(text, value_end), snippet
    raise ExtractError("EXTRACT_FAILED: no enclosing JSON section")


def _extract_props_property(text: str, hit_line: int) -> tuple[int, int, str]:
    lines = text.split("\n")
    if hit_line < 1 or hit_line > len(lines):
        raise ExtractError("EXTRACT_FAILED: hit line OOB")
    line = lines[hit_line - 1]
    if not re.search(r"<\w+>.*</\w+>", line):
        raise ExtractError("EXTRACT_FAILED: not a single-line property")
    return hit_line, hit_line, line


def extract(path: Path, hit_line: int, mode: str) -> Region:
    text = path.read_text(errors="replace")
    if mode.startswith("line-range:"):
        n = int(mode.split(":")[1])
        all_lines = text.split("\n")
        start = max(1, hit_line - n)
        end = min(len(all_lines), hit_line + n)
        snippet = "\n".join(all_lines[start - 1: end])
        return Region(str(path), start, end, snippet)
    if mode == "appsettings-section":
        s, e, t = _extract_json_section(text, hit_line)
        return Region(str(path), s, e, t)
    if mode == "props-property":
        s, e, t = _extract_props_property(text, hit_line)
        return Region(str(path), s, e, t)
    if mode in ("enclosing-method", "enclosing-class", "enclosing-method-or-extension"):
        s, e, t = _extract_cs(text, hit_line, mode)
        return Region(str(path), s, e, t)
    raise ExtractError(f"UNKNOWN_MODE: {mode}")
