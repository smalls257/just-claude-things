"""Walks tests/detectors/<layer>/<id>/{positive,negative}/ and asserts the detector
fires on positive fixtures and is silent on negatives. Each detector PR must ship
a positive AND negative fixture or this runner refuses the PR (Anchor)."""
from pathlib import Path

import pytest

from convention_scan.loader import load_registry
from convention_scan.scanner import scan

ROOT = Path(__file__).resolve().parents[2]
SKILL_DETECTORS = ROOT / "detectors"
FIXTURE_ROOT = Path(__file__).parent


def _all_detectors():
    return load_registry(skill_root=SKILL_DETECTORS, project_root=None)


def _fixture_pairs():
    pairs = []
    for det in _all_detectors():
        layer_dir = FIXTURE_ROOT / det.layer / det.id
        pos = layer_dir / "positive"
        neg = layer_dir / "negative"
        pairs.append(pytest.param(det, pos, neg, id=f"{det.layer}/{det.id}"))
    return pairs


@pytest.mark.parametrize("det,pos,neg", _fixture_pairs())
def test_detector_has_positive_and_negative(det, pos, neg):
    assert pos.exists() and any(pos.iterdir()), f"missing positive fixture for {det.id}"
    assert neg.exists() and any(neg.iterdir()), f"missing negative fixture for {det.id}"


@pytest.mark.parametrize("det,pos,neg", _fixture_pairs())
def test_detector_fires_on_positive(det, pos, neg):
    claims = scan([det], repo_root=pos)
    assert claims, f"{det.id} did not fire on positive fixture"


@pytest.mark.parametrize("det,pos,neg", _fixture_pairs())
def test_detector_silent_on_negative(det, pos, neg):
    claims = scan([det], repo_root=neg)
    assert claims == [], f"{det.id} unexpectedly fired on negative fixture: {claims}"
