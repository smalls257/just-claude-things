import json
import subprocess
import re
from pathlib import Path

import pytest

HERE = Path(__file__).parent
REFS = HERE / "reference-repos"
SNAPS = HERE / "snapshots"
SKILL_ROOT = HERE.parent.parent
ORCH = SKILL_ROOT / "scripts" / "convention-scan.sh"
SKILL_DETECTORS = SKILL_ROOT / "detectors"

FIXTURES = ["minimal-api", "controllers-classic", "kitchen-sink", "multi-project", "dirty"]


def _init_git(repo: Path):
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "init"], cwd=repo, check=True)


def _normalize(text: str, ref_root: Path | None = None) -> str:
    """Strip volatile absolute paths and timestamps so snapshots are portable."""
    out = re.sub(r'(reference-repo|scanned-at|reference-repo-commit)="[^"]*"',
                 lambda m: f'{m.group(1)}="<X>"', text)
    if ref_root is not None:
        # source= attributes embed the tmp_path ref dir — replace with stable token
        out = out.replace(str(ref_root) + "/", "<REF>/")
    return out


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_matches_snapshot(name, tmp_path):
    ref_src = REFS / name
    assert ref_src.exists(), f"fixture missing: {ref_src}"

    ref = tmp_path / "ref"
    subprocess.run(["cp", "-R", str(ref_src), str(ref)], check=True)
    _init_git(ref)

    target = tmp_path / "target"
    (target / "docs" / "tech-design").mkdir(parents=True)
    (target / "docs" / "tech-design" / "svc.md").write_text("# svc\n\n<module name=\"core\"/>\n")
    _init_git(target)

    answer_count = 60
    answers = ("y\n" * answer_count).encode()
    res = subprocess.run(
        ["bash", str(ORCH),
         "--reference-repo", str(ref),
         "--target-repo", str(target),
         "--design", str(target / "docs" / "tech-design" / "svc.md"),
         "--keywords", ""],
        input=answers, capture_output=True,
    )
    if name == "dirty":
        # dirty fixture has malformed files — expect surfaced errors but completion
        assert b"EXTRACT_FAILED" in res.stderr or b"READ_FAILED" in res.stderr or res.returncode == 0, res.stderr
        return
    assert res.returncode == 0, res.stderr.decode()

    design_body = (target / "docs" / "tech-design" / "svc.md").read_text()
    snap_path = SNAPS / f"{name}.expected.md"

    if not snap_path.exists():
        # First run: capture snapshot
        norm = _normalize(design_body, ref)
        snap_path.parent.mkdir(parents=True, exist_ok=True)
        snap_path.write_text(norm)
        pytest.skip(f"Snapshot created: {snap_path.name} — re-run to verify")

    snap = snap_path.read_text()
    norm = _normalize(design_body, ref)
    assert norm == snap, f"\n--- got ---\n{norm}\n--- want ---\n{snap}"
