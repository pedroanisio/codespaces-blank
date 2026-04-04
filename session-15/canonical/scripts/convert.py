"""Convert a full-data text dump to figure JSON.

Usage:
    python scripts/convert.py <input.txt> [output.json]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import io as fio

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert.py <input.txt> [output.json]")
        sys.exit(1)

    txt_path = sys.argv[1]
    json_path = sys.argv[2] if len(sys.argv) > 2 else None
    fio.convert_text(txt_path, json_path)
