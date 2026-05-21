"""Resolve overlapping region claims by priority."""
from __future__ import annotations

from dataclasses import dataclass

from .scanner import Claim
from .extractor import Region
from .loader import Detector


class ConflictError(Exception):
    pass


@dataclass(frozen=True)
class Conflict:
    winner: str
    loser: str
    file_path: str
    overlap_start: int
    overlap_end: int


def _overlaps(a: Region, b: Region) -> bool:
    """Check if two regions overlap in the same file."""
    return a.file_path == b.file_path and a.start_line <= b.end_line and b.start_line <= a.end_line


def resolve(
    claims: list[Claim],
    regions: dict[tuple[str, str, int], Region],
    detectors: list[Detector],
) -> tuple[list[Claim], list[Conflict]]:
    """Resolve overlapping claims by priority.

    Args:
        claims: List of claims to resolve.
        regions: Mapping of (detector_id, file_path, line_number) to Region.
        detectors: List of detectors with priority information.

    Returns:
        Tuple of (winning claims, conflicts).

    Raises:
        ConflictError: If equal-priority detectors overlap or detector ID is unknown.
    """
    # Build priority lookup and validate all claim detector IDs
    priority = {d.id: d.priority for d in detectors}
    registered_ids = set(d.id for d in detectors)
    unknown_ids = {c.detector_id for c in claims} - registered_ids
    if unknown_ids:
        raise ConflictError(
            f"UNKNOWN_DETECTOR_IDS: {sorted(unknown_ids)}"
        )

    # Sort claims by priority (descending), then by detector_id, then by line_number
    sorted_claims = sorted(
        claims,
        key=lambda c: (-priority[c.detector_id], c.detector_id, c.line_number),
    )

    winner_pairs: list[tuple[Claim, Region]] = []
    conflicts: list[Conflict] = []

    for claim in sorted_claims:
        key = (claim.detector_id, claim.file_path, claim.line_number)
        region = regions.get(key)

        # If no region, claim passes through automatically
        if region is None:
            winner_pairs.append((claim, None))
            continue

        # Check for overlap with any existing winner region
        overlap_with = None
        overlapping_pair_index = None
        for idx, (_, wr) in enumerate(winner_pairs):
            if wr is not None and _overlaps(region, wr):
                overlap_with = wr
                overlapping_pair_index = idx
                break

        if overlap_with is None:
            # No overlap; this claim wins
            winner_pairs.append((claim, region))
        else:
            # Overlap detected; resolve by priority
            winner_claim, _ = winner_pairs[overlapping_pair_index]

            wp = priority[winner_claim.detector_id]
            lp = priority[claim.detector_id]

            if wp == lp:
                raise ConflictError(
                    f"EQUAL_PRIORITY_OVERLAP: detectors '{winner_claim.detector_id}' and "
                    f"'{claim.detector_id}' both priority {wp} overlap in {claim.file_path}"
                )

            # Calculate overlap range
            overlap_start = max(region.start_line, overlap_with.start_line)
            overlap_end = min(region.end_line, overlap_with.end_line)

            # Record conflict (higher priority wins)
            conflicts.append(Conflict(
                winner=winner_claim.detector_id,
                loser=claim.detector_id,
                file_path=claim.file_path,
                overlap_start=overlap_start,
                overlap_end=overlap_end,
            ))

    # Extract just the claims from the pairs
    winners = [claim for claim, _ in winner_pairs]
    return winners, conflicts
