#!/usr/bin/env python3
"""
validate.py — JSON Schema validator for video-project-schema-v2.json

Usage:
    python validate.py [instance.json] [--schema schema.json] [--verbose]

Defaults:
    instance : example-project.json
    schema   : video-project-schema-v2.json

Requirements:
    pip install jsonschema
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    print("ERROR: jsonschema is not installed. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


SCRIPT_DIR = Path(__file__).parent
DEFAULT_SCHEMA = SCRIPT_DIR / "schemas" / "video-project-schema-v2.json"
DEFAULT_INSTANCE = SCRIPT_DIR / "examples" / "example-project.json"


def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def validate(instance_path: Path, schema_path: Path, verbose: bool) -> bool:
    print(f"Schema  : {schema_path}")
    print(f"Instance: {instance_path}")
    print()

    schema = load_json(schema_path)
    instance = load_json(instance_path)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))

    if not errors:
        print("PASS  — instance is valid against the schema.")
        if verbose:
            _print_summary(instance)
        return True

    print(f"FAIL  — {len(errors)} validation error(s) found:\n")
    for i, error in enumerate(errors, 1):
        path = " > ".join(str(p) for p in error.absolute_path) or "(root)"
        print(f"  [{i}] Path   : {path}")
        print(f"       Message: {error.message}")
        if verbose and error.schema_path:
            schema_path_str = " > ".join(str(p) for p in error.absolute_schema_path)
            print(f"       Schema : {schema_path_str}")
        print()

    return False


def _print_summary(instance: dict) -> None:
    print()
    print("--- Instance summary ---")
    print(f"  title          : {instance.get('title', 'N/A')}")
    print(f"  project_id     : {instance.get('project_id', 'N/A')}")
    print(f"  schema_version : {instance.get('schema_version', 'N/A')}")
    print(f"  version        : {instance.get('version', 'N/A')}")
    print(f"  status         : {instance.get('status', 'N/A')}")

    scenes = instance.get("scenes", [])
    total_shots = sum(len(s.get("shots", [])) for s in scenes)
    print(f"  scenes         : {len(scenes)}")
    print(f"  total shots    : {total_shots}")

    registry = instance.get("asset_registry", {})
    print(f"  characters     : {len(registry.get('characters', []))}")
    print(f"  environments   : {len(registry.get('environments', []))}")
    print(f"  props          : {len(registry.get('props', []))}")
    print(f"  style_guides   : {len(registry.get('style_guides', []))}")

    audio = instance.get("audio_assets", {})
    visual = instance.get("visual_assets", {})
    print(f"  audio_assets   : {len(audio)}")
    print(f"  visual_assets  : {len(visual)}")

    outputs = instance.get("outputs", [])
    print(f"  outputs        : {len(outputs)}")

    pipeline = instance.get("render_pipeline", {})
    steps = pipeline.get("steps", [])
    print(f"  pipeline steps : {len(steps)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a VideoProject JSON instance against video-project-schema-v2.json"
    )
    parser.add_argument(
        "instance",
        nargs="?",
        type=Path,
        default=DEFAULT_INSTANCE,
        help=f"Path to the instance JSON file (default: {DEFAULT_INSTANCE.name})",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help=f"Path to the JSON Schema file (default: {DEFAULT_SCHEMA.name})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show extra detail: schema path for each error and instance summary on success",
    )
    args = parser.parse_args()

    ok = validate(args.instance, args.schema, args.verbose)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
