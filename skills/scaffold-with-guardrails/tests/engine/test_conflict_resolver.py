import pytest
from convention_scan.loader import Detector
from convention_scan.scanner import Claim
from convention_scan.extractor import Region
from convention_scan.conflict_resolver import ConflictError, Conflict, resolve


def _det(id_, priority):
    return Detector(
        id=id_, display=id_, layer="auth", priority=priority,
        files=["**/*.cs"], signal={"cs": "x"}, extract="enclosing-method",
    )


def _claim(det_id, path, line):
    return Claim(detector_id=det_id, file_path=path, line_number=line, matched_text="x")


def _region(path, start, end):
    return Region(file_path=path, start_line=start, end_line=end, text="x")


def test_no_overlap_keeps_all():
    dets = [_det("a", 80), _det("b", 30)]
    claims = [_claim("a", "f.cs", 10), _claim("b", "f.cs", 50)]
    regions = {("a", "f.cs", 10): _region("f.cs", 5, 20),
               ("b", "f.cs", 50): _region("f.cs", 40, 60)}
    winners, conflicts = resolve(claims, regions, dets)
    assert len(winners) == 2
    assert len(conflicts) == 0


def test_overlap_higher_priority_wins():
    dets = [_det("a", 80), _det("b", 30)]
    claims = [_claim("a", "f.cs", 10), _claim("b", "f.cs", 12)]
    regions = {("a", "f.cs", 10): _region("f.cs", 5, 20),
               ("b", "f.cs", 12): _region("f.cs", 8, 18)}
    winners, conflicts = resolve(claims, regions, dets)
    assert [w.detector_id for w in winners] == ["a"]
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.winner == "a" and c.loser == "b"


def test_equal_priority_overlap_halts():
    dets = [_det("a", 50), _det("b", 50)]
    claims = [_claim("a", "f.cs", 10), _claim("b", "f.cs", 12)]
    regions = {("a", "f.cs", 10): _region("f.cs", 5, 20),
               ("b", "f.cs", 12): _region("f.cs", 8, 18)}
    with pytest.raises(ConflictError, match="EQUAL_PRIORITY_OVERLAP"):
        resolve(claims, regions, dets)


def test_different_files_never_conflict():
    dets = [_det("a", 80), _det("b", 30)]
    claims = [_claim("a", "a.cs", 10), _claim("b", "b.cs", 10)]
    regions = {("a", "a.cs", 10): _region("a.cs", 5, 20),
               ("b", "b.cs", 10): _region("b.cs", 5, 20)}
    winners, conflicts = resolve(claims, regions, dets)
    assert len(winners) == 2
    assert len(conflicts) == 0


def test_unknown_detector_id_halts():
    dets = [_det("a", 80)]
    claims = [_claim("ghost", "f.cs", 10)]
    regions = {("ghost", "f.cs", 10): _region("f.cs", 5, 20)}
    with pytest.raises(ConflictError, match="UNKNOWN_DETECTOR_IDS"):
        resolve(claims, regions, dets)
