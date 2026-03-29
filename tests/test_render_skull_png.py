import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from render_skull_png import _configure_anatomical_axis, render_skull_png


def test_render_skull_png_writes_valid_png(tmp_path):
    random.seed(71)
    output_path = tmp_path / "skull.png"

    result = render_skull_png(output_path, seed=71)

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output_path.stat().st_size > 10_000


def test_render_skull_png_supports_three_planes_layout(tmp_path):
    random.seed(72)
    output_path = tmp_path / "skull_3_planes.png"

    result = render_skull_png(output_path, seed=72, layout="three_planes")

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output_path.stat().st_size > 20_000


def test_render_skull_png_supports_four_views_layout(tmp_path):
    random.seed(73)
    output_path = tmp_path / "skull_4_views.png"

    result = render_skull_png(output_path, seed=73, layout="four_views")

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output_path.stat().st_size > 25_000


def test_render_skull_png_supports_external_assets(tmp_path):
    assets_dir = ROOT / "session-3" / "human-controller" / "public" / "assets" / "bones"
    output_path = tmp_path / "skull_external.png"

    result = render_skull_png(
        output_path,
        seed=73,
        layout="four_views",
        source="external",
        assets_dir=assets_dir,
    )

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output_path.stat().st_size > 25_000


def test_render_skull_png_supports_external_source_space(tmp_path):
    assets_dir = ROOT / "session-3" / "human-controller" / "public" / "assets" / "bones"
    output_path = tmp_path / "skull_external_source.png"

    result = render_skull_png(
        output_path,
        seed=73,
        layout="four_views",
        source="external_source",
        assets_dir=assets_dir,
    )

    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output_path.stat().st_size > 25_000


def test_configure_anatomical_axis_uses_orthographic_projection():
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    _configure_anatomical_axis(
        ax,
        label="Coronal",
        elev=0,
        azim=-90,
        center=[0.0, 0.0, 0.0],
        span=10.0,
        margin=1.0,
    )

    assert ax._focal_length == float("inf")
    plt.close(fig)
