"""
config — YAML/JSON config loader with auto-discovery.

Provides:
    load_config(path)   Load and parse a YAML or JSON config file
    find_config(dir, names)  Search for config files by name in a directory
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON config file and return the parsed dict.

    File format is detected by extension (.yaml/.yml → YAML, .json → JSON).
    Unknown extensions try YAML first (if available), then JSON.
    """
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        if yaml is None:
            print("ERROR: PyYAML is required for YAML configs. "
                  "Install with: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
        return yaml.safe_load(text) or {}
    elif suffix == ".json":
        return json.loads(text)
    else:
        try:
            if yaml:
                return yaml.safe_load(text) or {}
            return json.loads(text)
        except Exception:
            return json.loads(text)


def find_config(
    scan_dir: Path,
    names: list[str] | None = None,
) -> Path | None:
    """Search for a config file in a directory by conventional names.

    Parameters
    ----------
    scan_dir : Directory to search in.
    names    : List of filenames to try, in order.
               Defaults to ["organize.yaml", "organize.yml", "organize.json"].
    """
    if names is None:
        names = ["organize.yaml", "organize.yml", "organize.json"]
    for name in names:
        candidate = scan_dir / name
        if candidate.is_file():
            return candidate
    return None
