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
