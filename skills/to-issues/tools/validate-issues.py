#!/usr/bin/env python3
"""Validate a docs/issues/<slug>.md file produced by the `to-issues` skill.

Checks:
  - YAML frontmatter integrity (required fields, source files exist)
  - Issue IDs unique
  - Dependency graph acyclic (DFS cycle detection)
  - No orphan refs (every "Depends on: ISSUE-XXX" points to a real issue)
  - Coverage: every FR-XXX from source_requirements appears in >= 1 issue Source
  - Coverage: every OQ-XXX from source_requirements has a spike
  - Coverage: every D-XXX from source_tech_design has a spike
  - Topological order: deps appear before dependents in the file

Usage: python validate-issues.py docs/issues/<slug>.md

Exit codes: 0 clean, 1 violations found, 2 usage error.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Issue:
    id: str
    title: str
    depends_on: list[str] = field(default_factory=list)
    source_frs: list[str] = field(default_factory=list)
    source_oqs: list[str] = field(default_factory=list)
    source_ds: list[str] = field(default_factory=list)
    is_spike: bool = False
    line_no: int = 0


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        _die("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        _die("frontmatter not closed")
    raw = text[4:end]
    body = text[end + 5:]
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


def parse_issues(body: str) -> list[Issue]:
    issues: list[Issue] = []
    current: Issue | None = None
    section = ""
    for n, line in enumerate(body.splitlines(), 1):
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if line.startswith("### ISSUE-"):
            if current:
                issues.append(current)
            m = re.match(r"### (ISSUE-\d+):\s*(.+)", line)
            if not m:
                _die(f"malformed issue header at line {n}: {line!r}")
            current = Issue(
                id=m.group(1),
                title=m.group(2),
                line_no=n,
                is_spike="spike" in section,
            )
            continue
        if current is None:
            continue
        if line.startswith("**Depends on:**"):
            payload = line.split(":", 1)[1].strip()
            current.depends_on = [x.strip() for x in re.findall(r"ISSUE-\d+", payload)]
        elif line.startswith("- FR-"):
            current.source_frs += re.findall(r"FR-\d+", line)
        elif line.startswith("- OQ-"):
            current.source_oqs += re.findall(r"OQ-\d+", line)
        elif line.startswith("- D-"):
            current.source_ds += re.findall(r"D-\d+", line)
    if current:
        issues.append(current)
    return issues


def extract_ids(path: Path, pattern: str) -> set[str]:
    if not path.exists():
        return set()
    return set(re.findall(pattern, path.read_text()))


def detect_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        color[node] = GRAY
        stack.append(node)
        for nxt in graph.get(node, []):
            if color.get(nxt, WHITE) == GRAY:
                return stack[stack.index(nxt):] + [nxt]
            if color.get(nxt, WHITE) == WHITE:
                cyc = dfs(nxt)
                if cyc:
                    return cyc
        stack.pop()
        color[node] = BLACK
        return None

    for node in graph:
        if color[node] == WHITE:
            cyc = dfs(node)
            if cyc:
                return cyc
    return None


def _die(msg: str) -> None:
    print(f"validate-issues: {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate-issues.py <issues-md>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        _die(f"file not found: {path}")
    text = path.read_text()
    meta, body = parse_frontmatter(text)

    violations: list[str] = []

    for field_name in ("slug", "status", "source_requirements", "source_tech_design"):
        if field_name not in meta:
            violations.append(f"frontmatter missing field: {field_name}")

    repo_root = path.parent.parent.parent
    req_path = repo_root / meta.get("source_requirements", "")
    td_path = repo_root / meta.get("source_tech_design", "")
    if not req_path.exists():
        violations.append(f"source_requirements not found: {req_path}")
    if not td_path.exists():
        violations.append(f"source_tech_design not found: {td_path}")

    issues = parse_issues(body)
    seen: set[str] = set()
    for issue in issues:
        if issue.id in seen:
            violations.append(f"duplicate issue id: {issue.id}")
        seen.add(issue.id)

    all_ids = {issue.id for issue in issues}
    for issue in issues:
        for dep in issue.depends_on:
            if dep not in all_ids:
                violations.append(f"{issue.id} depends on unknown {dep}")

    graph = {issue.id: issue.depends_on for issue in issues}
    cyc = detect_cycle(graph)
    if cyc:
        violations.append("cycle detected: " + " -> ".join(cyc))

    pos = {issue.id: idx for idx, issue in enumerate(issues)}
    for issue in issues:
        for dep in issue.depends_on:
            if pos.get(dep, -1) > pos[issue.id]:
                violations.append(
                    f"{issue.id} (line {issue.line_no}) listed before dependency {dep}"
                )

    fr_ids = extract_ids(req_path, r"FR-\d+")
    oq_ids = extract_ids(req_path, r"OQ-\d+")
    d_ids = extract_ids(td_path, r"D-\d+")

    covered_frs: set[str] = set()
    spike_oqs: set[str] = set()
    spike_ds: set[str] = set()
    for issue in issues:
        covered_frs.update(issue.source_frs)
        if issue.is_spike:
            spike_oqs.update(issue.source_oqs)
            spike_ds.update(issue.source_ds)

    for fr in sorted(fr_ids - covered_frs):
        violations.append(f"{fr} not covered by any issue")
    for oq in sorted(oq_ids - spike_oqs):
        violations.append(f"{oq} has no spike issue")
    for d in sorted(d_ids - spike_ds):
        violations.append(f"{d} has no spike issue")

    if violations:
        for v in violations:
            print(f"  x {v}")
        print(f"\n{len(violations)} violation(s) found")
        return 1

    print(f"  ok {len(issues)} issues, all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
