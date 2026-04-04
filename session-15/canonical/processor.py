from __future__ import annotations

from pathlib import Path

from lib import extract, geometry, io as figure_io, render, strokes


def process_image(image_path: str | Path, output_dir: str | Path, image_id: str) -> dict[str, str]:
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    json_dir = output_dir / "json"
    processed_dir = output_dir / "processed"
    json_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    data = _extract_figure(image_path)

    json_path = json_dir / f"{image_id}.json"
    png_path = processed_dir / f"{image_id}.png"
    figure_io.save_figure(data, json_path)
    render.draw(
        data,
        str(png_path),
        title=f"Regenerated from {image_path.name}",
    )

    return {
        "json_relpath": str(Path("json") / json_path.name),
        "processed_relpath": str(Path("processed") / png_path.name),
        "processed_image": png_path.name,
    }


def _extract_figure(image_path: Path) -> dict:
    gray = extract.load_gray(str(image_path))
    height, width = gray.shape

    binary = extract.threshold_lines(gray, adaptive=False, global_val=215)
    binary = extract.remove_guides(binary)
    binary = extract.remove_text_components(binary)
    bounds = extract.find_bounds(binary, thresh_ratio=0.03, midline_px=width / 2.0)

    right_outer, right_inner = extract.scanline_silhouette(
        binary,
        bounds,
        max_dx_hu=2.0,
    )
    contour = geometry.smooth(geometry.resample(extract.build_contour(right_outer, right_inner), n=700))
    contour_max = float(contour[:, 0].max())
    detail_strokes = strokes.extract_all(
        gray,
        binary,
        bounds,
        contour_max_dx=contour_max * 1.15,
    )

    return {
        "contour": contour.round(4).tolist(),
        "strokes": [stroke.tolist() for stroke in detail_strokes],
        "meta": figure_io.build_meta(
            contour_points=len(contour),
            detail_strokes=len(detail_strokes),
            source=image_path.name,
            image_size=[width, height],
            midline_px=float(bounds.midline_px),
            y_top_px=bounds.y_top,
            y_bot_px=bounds.y_bot,
            fig_height_px=bounds.fig_height_px,
            scale_px_to_hu=bounds.scale,
        ),
    }
