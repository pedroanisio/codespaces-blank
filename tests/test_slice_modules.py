import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def test_sliced_generator_import_and_output_shape():
    from human_body.entry import generate_human_body

    random.seed(123)
    body = generate_human_body(variation=0, bone_geometry_format="indexed_mesh")

    assert body["schemaVersion"] == "3.0.0"
    assert len(body["skeleton"]) == 206
    assert len(body["boneGeometries"]) == 206
    assert len(body["joints"]) >= 72
