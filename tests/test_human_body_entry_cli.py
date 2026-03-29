import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from human_body import entry


def test_generate_human_body_supports_both_geometry_formats():
    random.seed(31)
    indexed = entry.generate_human_body(variation=0, bone_geometry_format="indexed_mesh")
    random.seed(31)
    parametric = entry.generate_human_body(variation=1, bone_geometry_format="parametric_csg")

    assert indexed["boneGeometries"][0]["geometryType"] == "indexed_mesh"
    assert parametric["boneGeometries"][0]["geometryType"] == "parametric_csg"
    assert indexed["name"] == "generated_body_000"
    assert parametric["name"] == "generated_body_001"
    assert any("primaryArteryId" in m["bloodSupply"] for m in indexed["muscles"])


def test_main_writes_stdout_and_output_dir(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["slice.py", "--seed", "5", "--pretty", "-n", "1"])
    entry.main()
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["schemaVersion"] == "3.0.0"

    out_dir = tmp_path / "bodies"
    monkeypatch.setattr(sys, "argv", [
        "slice.py",
        "--seed",
        "5",
        "--pretty",
        "-n",
        "2",
        "-o",
        str(out_dir),
        "--bone-geometry-format",
        "parametric_csg",
    ])
    entry.main()
    captured = capsys.readouterr()
    assert "Wrote 2 file(s)" in captured.err
    files = sorted(out_dir.glob("body_*.json"))
    assert len(files) == 2
    first = json.loads(files[0].read_text())
    assert first["boneGeometries"][0]["geometryType"] == "parametric_csg"


# ---------------------------------------------------------------------------
# Selective generation tests
# ---------------------------------------------------------------------------

def test_include_skeleton_only():
    random.seed(50)
    body = entry.generate_human_body(variation=0, include={"skeleton"})

    # Envelope keys always present
    assert body["schemaVersion"] == "3.0.0"
    assert "proportions" in body
    assert "id" in body
    assert "name" in body

    # Skeleton data present
    assert len(body["skeleton"]) == 206

    # Excluded components must not appear
    for key in ("joints", "muscles", "tendons", "organs", "boneGeometries",
                "nerves", "vascularSystem", "segments", "ligaments", "cartilage"):
        assert key not in body


def test_include_muscles_pulls_deps():
    """Muscles depend on joints + nerves for registry. Output should include
    muscles and tendons but not joints/nerves (they weren't requested)."""
    random.seed(51)
    body = entry.generate_human_body(variation=0, include={"muscles"})
    assert "muscles" in body
    assert "tendons" in body
    assert len(body["muscles"]) > 0
    assert len(body["tendons"]) > 0
    # Deps generated internally but not in output
    assert "joints" not in body
    assert "nerves" not in body


def test_include_multiple_components():
    random.seed(52)
    body = entry.generate_human_body(variation=0, include={"skeleton", "joints", "metadata"})
    assert len(body["skeleton"]) == 206
    assert len(body["joints"]) > 0
    assert "derivationGraph" in body
    assert "constitutiveLaws" in body
    assert "muscles" not in body


def test_exclude_geometry_and_appearance():
    random.seed(53)
    body = entry.generate_human_body(variation=0, exclude={"geometry", "appearance"})
    assert "boneGeometries" not in body
    assert "rendering" not in body
    assert "clothing" not in body
    assert "hair" not in body
    # Everything else present
    assert len(body["skeleton"]) == 206
    assert len(body["joints"]) > 0
    assert len(body["muscles"]) > 0


def test_no_include_no_exclude_returns_all():
    random.seed(54)
    body = entry.generate_human_body(variation=0)
    # Spot-check all component keys present
    all_keys = set()
    for comp in entry.COMPONENTS.values():
        all_keys.update(comp["keys"])
    for key in all_keys:
        assert key in body, f"Missing key {key} in full output"


def test_unknown_component_raises():
    import pytest
    with pytest.raises(ValueError, match="Unknown components"):
        entry.generate_human_body(variation=0, include={"nonexistent"})
    with pytest.raises(ValueError, match="Unknown components"):
        entry.generate_human_body(variation=0, exclude={"bogus"})


def test_cli_include_flag(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "slice.py", "--seed", "60", "--include", "skeleton", "metadata",
    ])
    entry.main()
    body = json.loads(capsys.readouterr().out)
    assert len(body["skeleton"]) == 206
    assert "derivationGraph" in body
    assert "muscles" not in body


def test_cli_exclude_flag(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "slice.py", "--seed", "61", "--exclude", "geometry",
    ])
    entry.main()
    body = json.loads(capsys.readouterr().out)
    assert "boneGeometries" not in body
    assert len(body["skeleton"]) == 206


def test_cli_include_exclude_mutual_exclusion(monkeypatch):
    import pytest
    monkeypatch.setattr(sys, "argv", [
        "slice.py", "--include", "skeleton", "--exclude", "geometry",
    ])
    with pytest.raises(SystemExit):
        entry.main()
