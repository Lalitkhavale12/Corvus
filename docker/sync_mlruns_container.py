"""Sync host mlruns/ into a container-readable copy (Phase 3, Task 3).

Windows-host -> Linux-container impedance (Rule 3 blocking fix): the file
store records ABSOLUTE Windows artifact URIs (``c:\\...\\mlruns/...``), which
a Linux container cannot resolve even with the directory mounted — every
``models:/`` / ``runs:/`` artifact read fails with ``No such artifact``.
Copying + rebasing only the location prefix to ``/mlruns`` keeps run IDs,
versions, stages, and artifact BYTES identical, so the served v9 is the same
v9 the D-01 promotion wrote. Host ``mlruns/`` is never modified.

Usage (re-run after any new training/promotion before ``compose up``):
    .\\venv\\python.exe docker/sync_mlruns_container.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "mlruns"
DEST = PROJECT_ROOT / "docker" / ".mlruns.container"

# Text files that may carry the absolute store prefix (run / experiment /
# registry / logged-model metas plus the MLmodel flavor files).
REWRITTEN_NAMES = {"meta.yaml", "MLmodel"}


def _prefix_variants() -> list[str]:
    """Host prefix spellings: drive-letter case x separator style."""
    raw = str(SRC)
    drive, rest = raw[0], raw[1:]
    variants = set()
    for d in {drive.upper(), drive.lower()}:
        for sep in {"\\", "/"}:
            variants.add(d + rest.replace("\\", sep).replace("/", sep))
    return sorted(variants)


def main() -> int:
    if not SRC.is_dir():
        print(f"SYNC ERROR: host store missing: {SRC}")
        return 1
    variants = _prefix_variants()
    if DEST.exists():
        shutil.rmtree(DEST)
    rewritten = 0
    for src_path in SRC.rglob("*"):
        rel = src_path.relative_to(SRC)
        if ".trash" in rel.parts:
            continue
        dest_path = DEST / rel
        if src_path.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
        elif src_path.name in REWRITTEN_NAMES:
            text = src_path.read_text(encoding="utf-8")
            for variant in variants:
                text = text.replace(variant, "/mlruns")
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(text, encoding="utf-8")
            rewritten += 1
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_path, dest_path)
    # Fail closed: no host prefix may survive in the copy.
    leftovers = []
    for dest_path in DEST.rglob("*"):
        if dest_path.is_file():
            data = dest_path.read_bytes()
            if any(v.encode() in data for v in variants):
                leftovers.append(str(dest_path.relative_to(DEST)))
    if leftovers:
        print(f"SYNC ERROR: host prefix survives in {len(leftovers)} files:")
        for path in leftovers[:10]:
            print(f"  {path}")
        return 1
    print(f"SYNCED {SRC} -> {DEST} ({rewritten} location files rebased to /mlruns)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
