"""Scan reference repo: per-detector glob + regex, return raw claims."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .loader import Detector


class ScanWarning(UserWarning):
    pass


@dataclass(frozen=True)
class Claim:
    detector_id: str
    file_path: str
    line_number: int
    matched_text: str


def _ext_of(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".props"):
        return "props"
    if name == ".editorconfig":
        return "editorconfig"
    return path.suffix.lstrip(".")


def _is_broad(glob: str) -> bool:
    return glob in ("**/*", "*", "**") or glob.endswith("/**")


def scan(detectors: Iterable[Detector], repo_root: Path) -> list[Claim]:
    claims: list[Claim] = []
    for det in detectors:
        det_claims: list[Claim] = []
        for glob in det.files:
            if _is_broad(glob):
                print(f"BROAD_GLOB: {det.id}: {glob}", file=sys.stderr)
            for f in sorted(repo_root.glob(glob)):
                if not f.is_file():
                    continue
                ext = _ext_of(f)
                patterns = det.signal.get(ext, ())
                if not patterns:
                    continue
                try:
                    text = f.read_text(errors="replace")
                except OSError as e:
                    print(f"READ_FAILED: {f}: {e}", file=sys.stderr)
                    continue
                for pat in patterns:
                    for m in re.finditer(pat, text):
                        line_no = text.count("\n", 0, m.start()) + 1
                        det_claims.append(Claim(
                            detector_id=det.id,
                            file_path=str(f),
                            line_number=line_no,
                            matched_text=m.group(0),
                        ))
        if not det_claims:
            print(f"NO_MATCH: {det.id}", file=sys.stderr)
        claims.extend(det_claims)
    return claims
