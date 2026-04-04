"""Cross-dataset comparison: contour geometry, stroke statistics, width profiles.

Usage:
    python scripts/analyze.py <file1.json> <file2.json> [<file3.json> ...]

If no arguments given, analyzes all extracted datasets in data/extracted/.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import io as fio, profile as prof


def print_comparison(profiles: list[dict]) -> None:
    names = [p["name"] for p in profiles]
    header = f"{'':>16} " + " ".join(f"{n:>12}" for n in names)
    sep = f"{'─' * 16} " + " ".join(f"{'─' * 12}" for _ in names)
    print(header)
    print(sep)

    float_keys = {"gap", "step_cv", "height", "max_dx", "ratio"}
    for key in [
        "n_contour", "n_strokes", "total_stroke_pts", "step_cv",
        "gap", "height", "max_dx", "ratio", "palindromes", "dup_pts",
        "median_stroke_len", "max_stroke_len",
    ]:
        vals = [p[key] for p in profiles]
        if key in float_keys:
            print(f"{key:>16} " + " ".join(f"{v:>12.4f}" for v in vals))
        else:
            print(f"{key:>16} " + " ".join(f"{v:>12}" for v in vals))

    print(f"\nWidth profile (max dx at each head-unit):")
    print(f"{'hu':>4} " + " ".join(f"{n:>12}" for n in names))
    for hu in range(9):
        vals = [p["widths"].get(float(hu), 0) for p in profiles]
        print(f"{hu:>4} " + " ".join(f"{v:>12.4f}" for v in vals))


def print_stroke_density(name: str, data: dict) -> None:
    strokes = [np.array(s) for s in data["strokes"]]
    c = np.array(data["contour"])
    regions = prof.classify_by_region(strokes)

    print(f"\n{'=' * 60}")
    print(f"  {name} — stroke density by region")
    print(f"{'=' * 60}")
    for rname, rstrokes in regions.items():
        pts = sum(len(s) for s in rstrokes)
        print(f"  {rname:<14} {len(rstrokes):>3} strokes, {pts:>5} pts")

    right_only = sum(1 for s in strokes if s[:, 0].min() >= 0.01)
    crossing = sum(1 for s in strokes if s[:, 0].min() < 0.005 and s[:, 0].max() > 0.01)
    print(f"\nLaterality: {right_only} right-only, {crossing} crossing midline")

    neg = np.sum(c[:, 0] < 0)
    print(f"Contour pts with dx < 0: {neg}")


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "data" / "extracted"

    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        paths = sorted(data_dir.glob("*.json"))
        if not paths:
            print(f"No JSON files found in {data_dir}")
            sys.exit(1)

    datasets = [(p.stem, fio.load_figure(p)) for p in paths]
    profiles = [prof.compute_profile(name, data) for name, data in datasets]
    print_comparison(profiles)

    for name, data in datasets:
        print_stroke_density(name, data)
