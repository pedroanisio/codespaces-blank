# Half-Mirror Figure Pipeline — Canonical

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

---

Consolidated pipeline for extracting right-half silhouettes and detail strokes
from frontal line-art images, storing them as JSON, and rendering full symmetric
figures via matplotlib mirroring.

This directory was assembled by copying (not moving) from the two source
directories — `figure_project/` and `halfmirror_pack/` — which remain untouched.

## Structure

```
canonical/
├── scripts/
│   ├── draw_figure.py                  # Matplotlib renderer: JSON -> mirrored PNG
│   ├── convert.py                      # Text (.txt) -> JSON converter (CLI)
│   ├── extract_contours.py             # v1: flood-fill + skeleton extraction (CLI)
│   ├── extract_scanline.py             # v3: scan-line silhouette extraction
│   ├── extract_with_guide_removal.py   # v4: scan-line + guide line removal
│   ├── batch_extract.py               # Batch wrapper for v3 extraction
│   ├── refine.py                       # Post-processing: close gaps, resample, smooth
│   ├── analyze.py                      # Cross-dataset comparison and profiling
│   └── learn_and_generate.py           # Data-driven generation via contour averaging
├── data/
│   ├── extracted/                      # 9 extracted figure JSONs
│   ├── generated/                      # 2 data-driven generated JSONs
│   ├── refined/                        # 1 refined JSON (anatomy_study)
│   └── source/                         # 5 full-data text dumps
├── renders/
│   ├── extracted/                      # 10 rendered PNGs from extracted/refined data
│   ├── generated/                      # 2 rendered PNGs from generated data
│   └── comparisons/                    # 5 comparison/composite PNGs
└── README.md
```

## Provenance

| File | Copied from | Reason |
|------|-------------|--------|
| `scripts/draw_figure.py` | `figure_project/scripts/` | Identical in both sources |
| `scripts/convert.py` | `figure_project/scripts/` | Only location |
| `scripts/extract_contours.py` | `halfmirror_pack/` | v1 extractor, CLI-ready |
| `scripts/extract_scanline.py` | `figure_project/scripts/` | v3 extractor |
| `scripts/extract_with_guide_removal.py` | `figure_project/scripts/` | v4 extractor |
| `scripts/batch_extract.py` | `figure_project/scripts/` | Only location |
| `scripts/refine.py` | `figure_project/scripts/` | Only location |
| `scripts/analyze.py` | `figure_project/scripts/` | Only location |
| `scripts/learn_and_generate.py` | `figure_project/scripts/` | Only location |
| `data/extracted/{anatomy_study,biker_girl,hero_figure,moto_rider}.json` | `halfmirror_pack/` | Richer schema (includes `symmetry` + `measurements`) |
| `data/extracted/tactical_operator.json` | `halfmirror_pack/` | Unique to that source |
| `data/extracted/{heroine,warrior}_{front,back}.json` | `figure_project/data/extracted/` | Unique to that source |
| `data/generated/*.json` | `figure_project/data/generated/` | Only location |
| `data/refined/*.json` | `figure_project/data/refined/` | Only location |
| `data/source/*_full_data.txt` | `halfmirror_pack/` | Only location |
| `renders/extracted/*.png` | Mixed — see JSON source | Matched to JSON provenance |
| `renders/generated/*.png` | `figure_project/renders/generated/` | Only location |
| `renders/comparisons/*.png` | `figure_project/renders/comparisons/` | Only location |

## Data Format (JSON)

```json
{
  "contour": [[dx, dy], ...],
  "strokes": [[[dx, dy], ...], ...],
  "meta": { "contour_points": N, "detail_strokes": M, "source": "..." },
  "symmetry": { ... },
  "measurements": { ... }
}
```

- `dx` = distance from midline (head-units, positive = right)
- `dy` = distance from crown (head-units, 0 = top of head, 8 = sole)
- `symmetry` and `measurements` present in flood-fill-extracted files only
- Renderer mirrors both contour and strokes to create a full symmetric figure

## Datasets

| File | Contour pts | Strokes | Type | Extraction |
|------|-------------|---------|------|------------|
| `anatomy_study.json` | 699 | 81 | Male, nude anatomy | flood-fill |
| `biker_girl.json` | 639 | 179 | Female, leather jacket | flood-fill |
| `hero_figure.json` | 640 | 118 | Male, sentai armor | flood-fill |
| `moto_rider.json` | 734 | 292 | Male, motorcycle gear | flood-fill |
| `tactical_operator.json` | 788 | 148 | Male, tactical gear | flood-fill |
| `heroine_front.json` | 700 | 163 | Female, bodysuit (front) | scan-line v4 |
| `heroine_back.json` | 700 | 120 | Female, bodysuit (back) | scan-line v4 |
| `warrior_front.json` | 700 | 173 | Male, barbarian armor (front) | scan-line v3 |
| `warrior_back.json` | 700 | 160 | Male, barbarian armor (back) | scan-line v3 |
| `generated_learned.json` | 800 | 81 | Anatomy-weighted average | data-driven |
| `generated_heroic.json` | 800 | 81 | Hero-weighted variant | data-driven |
| `anatomy_study_refined.json` | 700 | 81 | Refined anatomy | post-processed |

## Usage

```bash
# Render any JSON to PNG
python scripts/draw_figure.py data/extracted/moto_rider.json output.png

# Convert text dump to JSON
python scripts/convert.py data/source/hero_figure_full_data.txt output.json

# Extract from image (v1, CLI-ready)
python scripts/extract_contours.py input.jpg output.json
```

## Extraction Script Lineage

```
extract_contours.py   (v1)  flood-fill + skeleton, CLI args, richer output schema
        │
extract_scanline.py   (v3)  scan-line silhouette, hardcoded paths
        │
extract_with_guide_removal.py  (v4)  adds horizontal/vertical guide removal
        │
batch_extract.py      wrapper around v3 logic for multiple images
```

## Known Limitations

- Scripts `extract_scanline.py`, `batch_extract.py`, `extract_with_guide_removal.py`,
  `refine.py`, `analyze.py`, and `learn_and_generate.py` contain **hardcoded paths**
  from the original authoring environment. Only `draw_figure.py`, `convert.py`, and
  `extract_contours.py` accept CLI arguments.
- Extraction logic is duplicated across v3/v4/batch scripts.
- No automated tests exist for the numerical pipeline.

---

*Artifact produced with Claude Opus 4.6 — consolidation only, no code was modified.*
