"""
Refine a figure JSON: close contour gap, resample, smooth, dedup strokes.

Usage:
    python scripts/refine.py <input.json> [output.json]
"""

import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import geometry, io as fio


def refine(input_path: str, output_path: str) -> dict:
    orig = fio.load_figure(input_path)
    c = np.array(orig["contour"])
    strokes_raw = [np.array(s) for s in orig["strokes"]]

    # ─── CONTOUR ───
    gap = np.linalg.norm(c[0] - c[-1])
    print(f"[contour] closure gap before: {gap:.5f}")

    c = geometry.close_gap(c)
    print(f"[contour] after gap closure: {len(c)} pts")

    c = geometry.resample(c, n=700)
    print(f"[contour] resampled: {len(c)} pts")

    c_smooth = geometry.smooth(c, kernel=3, mode="wrap")
    disp = np.sqrt(np.sum((c_smooth - c) ** 2, axis=1))
    print(f"[contour] smoothing displacement: mean={disp.mean():.5f}, max={disp.max():.5f}")

    neg_before = np.sum(c_smooth[:, 0] < 0)
    c_smooth = geometry.clamp_dx(c_smooth)
    print(f"[contour] clamped {neg_before} negative-dx pts to 0")

    new_diffs = np.diff(c_smooth, axis=0)
    new_steps = np.sqrt(new_diffs[:, 0] ** 2 + new_diffs[:, 1] ** 2)
    print(f"[contour] final step sizes: mean={new_steps.mean():.5f}, "
          f"std={new_steps.std():.5f}, cv={new_steps.std()/new_steps.mean()*100:.1f}%")

    # ─── STROKES ───
    refined_strokes = []
    stats = {"palindromes_fixed": 0, "dups_removed": 0, "clipped": 0, "dropped": 0}

    for s in strokes_raw:
        # Remove consecutive duplicates
        s_clean = geometry.remove_consecutive_dups(s)
        stats["dups_removed"] += len(s) - len(s_clean)
        s = s_clean

        if len(s) < 3:
            stats["dropped"] += 1
            continue

        # Deduplicate palindromes
        s_dedup = geometry.dedup_palindrome(s)
        if len(s_dedup) < len(s):
            stats["palindromes_fixed"] += 1
        s = s_dedup

        # Clip out-of-bounds (above head)
        before = len(s)
        s = s[s[:, 1] >= -0.01]
        stats["clipped"] += before - len(s)

        if len(s) < 3:
            stats["dropped"] += 1
            continue

        # Light smoothing
        if len(s) >= 7:
            s = np.column_stack([
                uniform_filter1d(s[:, 0], 3, mode="nearest"),
                uniform_filter1d(s[:, 1], 3, mode="nearest"),
            ])

        refined_strokes.append(s)

    print(f"\n[strokes] palindromes deduped: {stats['palindromes_fixed']}")
    print(f"[strokes] duplicate pts removed: {stats['dups_removed']}")
    print(f"[strokes] out-of-bounds pts clipped: {stats['clipped']}")
    print(f"[strokes] strokes dropped (too short): {stats['dropped']}")
    print(f"[strokes] final count: {len(refined_strokes)} (was {len(strokes_raw)})")
    print(f"[strokes] total pts: {sum(len(s) for s in strokes_raw)} → "
          f"{sum(len(s) for s in refined_strokes)}")

    # ─── OUTPUT ───
    refined = {
        "contour": c_smooth.tolist(),
        "strokes": [s.tolist() for s in refined_strokes],
        "meta": fio.build_meta(
            contour_points=len(c_smooth),
            detail_strokes=len(refined_strokes),
            source=orig["meta"]["source"],
            refined=True,
            refinements=[
                "contour: closed gap (bridge interpolation)",
                "contour: resampled to uniform arc-length (700 pts)",
                "contour: light smoothing (uniform filter k=3, wrap mode)",
                "contour: clamped negative dx to 0",
                f"strokes: {stats['palindromes_fixed']} palindromes deduped",
                f"strokes: {stats['dups_removed']} consecutive duplicate pts removed",
                "strokes: light smoothing (uniform filter k=3, nearest mode)",
                f"strokes: {stats['clipped']} out-of-bounds pts clipped",
            ],
        ),
        "symmetry": orig.get("symmetry", {}),
    }

    fio.save_figure(refined, output_path)
    return refined


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python refine.py <input.json> [output.json]")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else in_path.rsplit(".", 1)[0] + "_refined.json"
    refine(in_path, out_path)
