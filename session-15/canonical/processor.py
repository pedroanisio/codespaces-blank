from __future__ import annotations

from pathlib import Path

from lib import extract, io as figure_io, render


def process_image(image_path: str | Path, output_dir: str | Path, image_id: str) -> dict[str, str]:
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    json_dir = output_dir / "json"
    processed_dir = output_dir / "processed"
    json_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    figure = extract.extract_flood_fill(str(image_path))

    json_path = json_dir / f"{image_id}.json"
    png_path = processed_dir / f"{image_id}.png"
    figure_io.save_figure(figure.to_dict(), json_path)
    render.draw(
        figure.to_dict(),
        str(png_path),
        title=f"Regenerated from {image_path.name}",
        straight_fold=True,
    )

    return {
        "json_relpath": str(Path("json") / json_path.name),
        "processed_relpath": str(Path("processed") / png_path.name),
        "processed_image": png_path.name,
    }
