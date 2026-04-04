"""
Batch extract from multiple images using the v3 scan-line pipeline.

Usage:
    python scripts/batch_extract.py <image1> <output1> [<image2> <output2> ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.extract_scanline import run


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2 != 0:
        print("Usage: python batch_extract.py <img1> <out1.json> [<img2> <out2.json> ...]")
        sys.exit(1)

    pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    for img_path, out_path in pairs:
        print(f"\n{'='*60}")
        run(img_path, out_path)
