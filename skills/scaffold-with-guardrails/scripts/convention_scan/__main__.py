"""CLI entry — orchestrator-callable subcommands for each pipeline step."""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .card_renderer import CardInput, render_card
from .conflict_resolver import resolve as resolve_conflicts
from .discovery import sweep
from .extractor import ExtractError, extract
from .loader import load_registry
from .package_resolver import resolve_packages
from .scanner import scan
from .writer import (
    AdoptedEntry, ConflictEntry, DevNamedEntry, DiscoveredEntry,
    RejectedEntry, ScanMeta, write_conventions,
)


def cmd_load(args):
    skill = Path(args.skill_detectors)
    proj = Path(args.project_detectors) if args.project_detectors else None
    reg = load_registry(skill_root=skill, project_root=proj)
    print(json.dumps([d.id for d in reg]))


def cmd_scan_and_render(args):
    skill = Path(args.skill_detectors)
    proj = Path(args.project_detectors) if args.project_detectors else None
    repo = Path(args.reference_repo)
    out_cards = Path(args.cards_out)
    out_state = Path(args.state_out)

    detectors = load_registry(skill_root=skill, project_root=proj)
    raw_claims = scan(detectors, repo_root=repo)

    regions = {}
    surviving = []
    by_id = {d.id: d for d in detectors}
    for c in raw_claims:
        det = by_id[c.detector_id]
        try:
            r = extract(Path(c.file_path), c.line_number, det.extract)
        except ExtractError as e:
            print(f"EXTRACT_FAILED: {c.detector_id}: {e}", file=sys.stderr)
            continue
        regions[(c.detector_id, c.file_path, c.line_number)] = r
        surviving.append(c)

    winners, conflicts = resolve_conflicts(surviving, regions, detectors)

    cards_lines = []
    state = {"winners": [], "conflicts": []}
    for w in winners:
        r = regions[(w.detector_id, w.file_path, w.line_number)]
        pkgs, unresolved = resolve_packages(r.text, source_file=Path(w.file_path), repo_root=repo)
        det = by_id[w.detector_id]
        cn = [f"overrides {c.loser} at L{c.overlap_start}-L{c.overlap_end}"
              for c in conflicts if c.winner == w.detector_id]
        card = render_card(CardInput(
            detector_id=w.detector_id, display=det.display,
            source_path=str(Path(w.file_path).relative_to(repo)),
            region=r, packages=pkgs, unresolved=unresolved, conflict_notes=cn,
        ))
        print(card)
        cards_lines.append(f"CARD: {w.detector_id}")
        state["winners"].append({
            "id": w.detector_id,
            "source": f"{Path(w.file_path).relative_to(repo)}:L{r.start_line}-L{r.end_line}",
            "snippet": r.text,
            "packages": ",".join(f"{p.name}:{p.version}" for p in pkgs),
        })
    for c in conflicts:
        state["conflicts"].append({
            "winner": c.winner, "loser": c.loser,
            "overlap": f"{c.file_path}:L{c.overlap_start}-L{c.overlap_end}",
        })
    out_cards.parent.mkdir(parents=True, exist_ok=True)
    out_cards.write_text("\n".join(cards_lines) + "\n")
    out_state.parent.mkdir(parents=True, exist_ok=True)
    out_state.write_text(json.dumps(state))


def cmd_discover(args):
    repo = Path(args.reference_repo)
    claimed = set()
    if args.claimed_files:
        claimed = set(Path(args.claimed_files).read_text().splitlines())
    top_n = None if args.discover_all else 5
    cands = sweep(repo, claimed_files=claimed, top_n=top_n)
    out = []
    for c in cands:
        out.append({"name": c.name, "source_path": c.source_path,
                    "start_line": c.start_line, "end_line": c.end_line,
                    "text": c.text, "score": c.score})
    Path(args.out).write_text(json.dumps(out))


def cmd_write(args):
    state = json.loads(Path(args.state).read_text())
    decisions = json.loads(Path(args.decisions).read_text())
    dev_named = json.loads(Path(args.dev_named).read_text()) if args.dev_named else []
    discovered_state = json.loads(Path(args.discovered_state).read_text()) if args.discovered_state else []
    discovered_decisions = json.loads(Path(args.discovered_decisions).read_text()) if args.discovered_decisions else {}

    ref_commit = subprocess.check_output(
        ["git", "-C", args.reference_repo, "rev-parse", "--short", "HEAD"]
    ).decode().strip()

    meta = ScanMeta(
        reference_repo=args.reference_repo,
        reference_repo_commit=ref_commit,
        scanned_at=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        engine_version=__version__,
    )

    adopted, rejected = [], []
    for w in state["winners"]:
        ans = decisions.get(w["id"], "n")
        if ans == "y":
            adopted.append(AdoptedEntry(
                detector=w["id"], source=w["source"],
                staged=f"staged/{w['id']}.cs", packages=w["packages"],
                snippet_text=w["snippet"],
            ))
        else:
            rejected.append(RejectedEntry(detector=w["id"], source=w["source"], reason="dev-skipped"))

    dev_named_entries = []
    for d in dev_named:
        dev_named_entries.append(DevNamedEntry(
            target=d["target"], source=d["source"],
            staged=f"staged/dev-{d['target']}.cs",
            adopted=decisions.get(f"dev-{d['target']}", "n") == "y",
            packages=d.get("packages", ""), snippet_text=d["snippet"],
        ))

    discovered_entries = []
    for d in discovered_state:
        discovered_entries.append(DiscoveredEntry(
            name=d["name"], source=f"{d['source_path']}:L{d['start_line']}-L{d['end_line']}",
            staged=f"staged/discovered-{d['name']}.cs",
            adopted=discovered_decisions.get(f"discovered-{d['name']}", "n") == "y",
            packages="", snippet_text=d["text"],
        ))

    conflict_entries = [
        ConflictEntry(winner=c["winner"], loser=c["loser"], overlap=c["overlap"])
        for c in state["conflicts"]
    ]

    write_conventions(
        design_path=Path(args.design), staged_root=Path(args.staged_root), meta=meta,
        adopted=adopted, rejected=rejected, dev_named=dev_named_entries,
        discovered=discovered_entries, conflicts=conflict_entries,
        confirm_overwrite_empty=args.confirm_overwrite_empty,
    )


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_load = sub.add_parser("load")
    p_load.add_argument("--skill-detectors", required=True)
    p_load.add_argument("--project-detectors")
    p_load.set_defaults(func=cmd_load)

    p_sc = sub.add_parser("scan-and-render")
    p_sc.add_argument("--skill-detectors", required=True)
    p_sc.add_argument("--project-detectors")
    p_sc.add_argument("--reference-repo", required=True)
    p_sc.add_argument("--cards-out", required=True)
    p_sc.add_argument("--state-out", required=True)
    p_sc.set_defaults(func=cmd_scan_and_render)

    p_d = sub.add_parser("discover")
    p_d.add_argument("--reference-repo", required=True)
    p_d.add_argument("--claimed-files")
    p_d.add_argument("--out", required=True)
    p_d.add_argument("--discover-all", action="store_true")
    p_d.set_defaults(func=cmd_discover)

    p_w = sub.add_parser("write")
    p_w.add_argument("--state", required=True)
    p_w.add_argument("--decisions", required=True)
    p_w.add_argument("--design", required=True)
    p_w.add_argument("--staged-root", required=True)
    p_w.add_argument("--reference-repo", required=True)
    p_w.add_argument("--dev-named")
    p_w.add_argument("--discovered-state")
    p_w.add_argument("--discovered-decisions")
    p_w.add_argument("--confirm-overwrite-empty", action="store_true")
    p_w.set_defaults(func=cmd_write)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
