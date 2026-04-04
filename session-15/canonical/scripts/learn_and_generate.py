"""
Data-driven figure generator.

Strategy:
  1. Normalize source contours to a common parameterization (800 pts)
  2. Compute weighted-average contour
  3. Transplant strokes from source to target via proportional dx mapping
  4. Generate new figures with different weight profiles

Usage:
    python scripts/learn_and_generate.py <source1.json> <source2.json> ... --output-dir <dir>

If no arguments given, uses the 3 default sources (moto, anatomy, hero)
and writes to data/generated/.
"""

import sys
from pathlib import Path

import numpy as np
from scipy.signal import argrelextrema
from scipy.ndimage import uniform_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import geometry, io as fio, profile as prof


# ═══════════════════════════════════════════════════════════
#  Contour parameterization & averaging
# ═══════════════════════════════════════════════════════════

def resample_normalized(data: dict, n: int = 800) -> np.ndarray:
    """Resample a figure's contour to n points at normalized arc-length."""
    c = np.array(data["contour"])
    cum, total = geometry.arc_lengths(c)
    t_norm = cum / total
    t_uniform = np.linspace(0, 1, n)
    return np.column_stack([
        np.interp(t_uniform, t_norm, c[:, 0]),
        np.interp(t_uniform, t_norm, c[:, 1]),
    ])


def weighted_average_contour(
    contours: dict[str, np.ndarray],
    weights: dict[str, float],
) -> np.ndarray:
    """Compute a weighted average of resampled contours, then smooth + clamp."""
    result = sum(weights[name] * contours[name] for name in weights)
    return geometry.smooth(result)


# ═══════════════════════════════════════════════════════════
#  Landmark detection (for diagnostics)
# ═══════════════════════════════════════════════════════════

def find_landmarks(c: np.ndarray) -> dict[str, int]:
    """Find structural landmarks (head peak, neck valley, etc.) via dx extrema."""
    dx_smooth = uniform_filter1d(c[:, 0], 25, mode="nearest")

    peaks = argrelextrema(dx_smooth, np.greater, order=20)[0]
    valleys = argrelextrema(dx_smooth, np.less, order=20)[0]

    all_extrema = sorted(
        [(p, "peak", c[p, 0], c[p, 1]) for p in peaks]
        + [(v, "valley", c[v, 0], c[v, 1]) for v in valleys],
        key=lambda x: x[0],
    )

    landmarks = {}

    for idx, typ, dx, dy in all_extrema:
        if typ == "peak" and dy < 1.5 and dx > 0.2:
            landmarks["head_peak"] = idx
            break

    for idx, typ, dx, dy in all_extrema:
        if typ == "valley" and idx > landmarks.get("head_peak", 0) and dy < 2.0 and dx < 0.5:
            landmarks["neck_valley"] = idx
            break

    first_half = [(i, t, d, y) for i, t, d, y in all_extrema if i < 400 and t == "peak"]
    if first_half:
        landmarks["body_peak"] = max(first_half, key=lambda x: x[2])[0]

    mid_valleys = [(i, t, d, y) for i, t, d, y in all_extrema if t == "valley" and 2.5 < y < 5.0]
    if mid_valleys:
        landmarks["inner_valley"] = min(mid_valleys, key=lambda x: x[2])[0]

    return landmarks


# ═══════════════════════════════════════════════════════════
#  Stroke transplanting
# ═══════════════════════════════════════════════════════════

def transplant_strokes(
    source_contour: np.ndarray | list,
    source_strokes: list,
    target_contour: np.ndarray,
) -> list[np.ndarray]:
    """Transplant strokes by mapping relative dx position within the silhouette."""
    src_c = np.array(source_contour)
    src_w = prof.width_interpolator(src_c)
    tgt_w = prof.width_interpolator(target_contour)

    transplanted = []
    for stroke in source_strokes:
        s = np.array(stroke)
        new_s = np.zeros_like(s)
        for j in range(len(s)):
            dy, dx = s[j, 1], s[j, 0]
            sw = max(float(src_w(dy)), 0.01)
            tw = max(float(tgt_w(dy)), 0.01)
            new_s[j, 0] = (dx / sw) * tw
            new_s[j, 1] = dy
        transplanted.append(new_s)

    return transplanted


# ═══════════════════════════════════════════════════════════
#  Stroke analysis (diagnostics)
# ═══════════════════════════════════════════════════════════

def print_stroke_summary(all_stats: dict[str, dict]) -> None:
    """Print stroke-count-by-region table."""
    names = list(all_stats.keys())
    region_names = list(next(iter(all_stats.values())).keys())

    print("\nStroke patterns by region:")
    print(f"{'Region':<16} " + " ".join(f"{n:>8}" for n in names) + f" {'avg':>8}")
    for region in region_names:
        counts = [len(all_stats[n].get(region, [])) for n in names]
        avg = np.mean(counts)
        print(f"{region:<16} " + " ".join(f"{c:>8}" for c in counts) + f" {avg:>8.1f}")


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

def generate(
    sources: dict[str, dict],
    output_dir: Path,
) -> None:
    """Full generation pipeline: resample, average, transplant, save."""

    # Step 1: Resample all contours to 800 pts
    contours = {name: resample_normalized(data) for name, data in sources.items()}

    for name, c in contours.items():
        lm = find_landmarks(c)
        print(f"{name}: landmarks at indices {lm}")

    # Step 2: Weighted-average contour (anatomy-heavy = "learned")
    learned_weights = {"moto": 0.2, "anat": 0.6, "hero": 0.2}
    learned_contour = weighted_average_contour(contours, learned_weights)

    print(f"\nLearned contour: {len(learned_contour)} pts")
    print(f"  dx range: [{learned_contour[:,0].min():.4f}, {learned_contour[:,0].max():.4f}]")
    print(f"  dy range: [{learned_contour[:,1].min():.4f}, {learned_contour[:,1].max():.4f}]")

    # Step 3: Stroke analysis
    all_region_stats = {
        name: prof.classify_by_region([np.array(s) for s in data["strokes"]])
        for name, data in sources.items()
    }
    print_stroke_summary(all_region_stats)

    # Step 4: Transplant anatomy strokes onto learned contour
    anat = sources["anat"]
    learned_strokes = transplant_strokes(anat["contour"], anat["strokes"], learned_contour)

    print(f"\nGenerated contour: {len(learned_contour)} pts")
    print(f"Transplanted anatomy strokes: {len(learned_strokes)}")

    generated = {
        "contour": learned_contour.tolist(),
        "strokes": [s.tolist() for s in learned_strokes],
        "meta": fio.build_meta(
            contour_points=len(learned_contour),
            detail_strokes=len(learned_strokes),
            source="data_driven_generation",
            method="weighted_average_contour + stroke_transplant",
            weights=learned_weights,
        ),
    }
    fio.save_figure(generated, output_dir / "generated_learned.json")

    # Step 5: Heroic variant (hero-heavy)
    heroic_weights = {"moto": 0.1, "anat": 0.3, "hero": 0.6}
    heroic_contour = weighted_average_contour(contours, heroic_weights)
    heroic_strokes = transplant_strokes(anat["contour"], anat["strokes"], heroic_contour)

    heroic = {
        "contour": heroic_contour.tolist(),
        "strokes": [s.tolist() for s in heroic_strokes],
        "meta": fio.build_meta(
            contour_points=len(heroic_contour),
            detail_strokes=len(heroic_strokes),
            source="data_driven_heroic_variant",
            method="hero_weighted_contour + stroke_transplant",
            weights=heroic_weights,
        ),
    }
    fio.save_figure(heroic, output_dir / "generated_heroic.json")


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    data_dir = base / "data" / "extracted"
    out_dir = base / "data" / "generated"

    if len(sys.argv) > 1 and sys.argv[1] != "--output-dir":
        # Custom sources
        paths = []
        output = out_dir
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == "--output-dir":
                output = Path(sys.argv[i + 1])
                i += 2
            else:
                paths.append(sys.argv[i])
                i += 1
        sources = {Path(p).stem: fio.load_figure(p) for p in paths}
        generate(sources, output)
    else:
        # Default: moto, anatomy, hero
        sources = {
            "moto": fio.load_figure(data_dir / "moto_rider.json"),
            "anat": fio.load_figure(data_dir / "anatomy_study.json"),
            "hero": fio.load_figure(data_dir / "hero_figure.json"),
        }
        generate(sources, out_dir)
