"""Data-driven figure generator.

Usage:
    python scripts/learn_and_generate.py [<src1.json> <src2.json> ...] [--output-dir <dir>]

If no arguments given, uses moto_rider, anatomy_study, hero_figure
and writes to data/generated/.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import geometry, io as fio, profile as prof


def print_stroke_summary(all_stats: dict[str, dict]) -> None:
    names = list(all_stats.keys())
    region_names = list(next(iter(all_stats.values())).keys())

    print("\nStroke patterns by region:")
    print(f"{'Region':<16} " + " ".join(f"{n:>8}" for n in names) + f" {'avg':>8}")
    for region in region_names:
        counts = [len(all_stats[n].get(region, [])) for n in names]
        avg = np.mean(counts)
        print(f"{region:<16} " + " ".join(f"{c:>8}" for c in counts) + f" {avg:>8.1f}")


def generate(sources: dict[str, dict], output_dir: Path) -> None:
    # Step 1: Resample all contours to 800 pts
    contours = {
        name: geometry.resample_normalized(np.array(data["contour"]))
        for name, data in sources.items()
    }

    for name, c in contours.items():
        lm = prof.find_landmarks(c)
        print(f"{name}: landmarks at indices {lm}")

    # Step 2: Weighted-average contour (anatomy-heavy)
    learned_weights = {"moto": 0.2, "anat": 0.6, "hero": 0.2}
    learned_contour = geometry.weighted_average(contours, learned_weights)

    print(f"\nLearned contour: {len(learned_contour)} pts")
    print(f"  dx range: [{learned_contour[:,0].min():.4f}, {learned_contour[:,0].max():.4f}]")
    print(f"  dy range: [{learned_contour[:,1].min():.4f}, {learned_contour[:,1].max():.4f}]")

    # Step 3: Stroke analysis
    all_region_stats = {
        name: prof.classify_by_region([np.array(s) for s in data["strokes"]])
        for name, data in sources.items()
    }
    print_stroke_summary(all_region_stats)

    # Step 4: Transplant anatomy strokes
    anat = sources["anat"]
    learned_strokes = prof.transplant_strokes(anat["contour"], anat["strokes"], learned_contour)

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

    # Step 5: Heroic variant
    heroic_weights = {"moto": 0.1, "anat": 0.3, "hero": 0.6}
    heroic_contour = geometry.weighted_average(contours, heroic_weights)
    heroic_strokes = prof.transplant_strokes(anat["contour"], anat["strokes"], heroic_contour)

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
        paths, output = [], out_dir
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
        sources = {
            "moto": fio.load_figure(data_dir / "moto_rider.json"),
            "anat": fio.load_figure(data_dir / "anatomy_study.json"),
            "hero": fio.load_figure(data_dir / "hero_figure.json"),
        }
        generate(sources, out_dir)
