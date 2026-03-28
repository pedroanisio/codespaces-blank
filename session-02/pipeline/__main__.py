#!/usr/bin/env python3
"""
Unified CLI for the SAFE AI Production video pipeline.

Usage:
    python -m pipeline <command> [options]

Commands:
    create      Generate or refine video project JSON documents
    run         Execute the full pipeline (skills → generate → assemble)
    validate    Validate a JSON document against the v3 schema
    check       Verify environment readiness (Python, FFmpeg, API keys)

Examples:
    python -m pipeline create --quick --title "My Film" -o project.json
    python -m pipeline create --idea "A robot discovers music"
    python -m pipeline create --refine project.json --skills s04,s07
    python -m pipeline run --idea "A lone astronaut finds a signal"
    python -m pipeline run render project.json --stub-only
    python -m pipeline validate project.json
    python -m pipeline check
"""
from __future__ import annotations

import sys
import textwrap


def _print_help() -> None:
    print(textwrap.dedent("""\
        usage: python -m pipeline <command> [options]

        SAFE AI Production — Video Pipeline CLI

        commands:
          create      Generate or refine video project JSON documents
          run         Execute the full pipeline (skills → generate → assemble)
          validate    Validate a JSON document against the v3 schema
          check       Verify environment readiness (Python, FFmpeg, API keys)

        Run 'python -m pipeline <command> --help' for command-specific options.

        quick start:
          python -m pipeline check                                  # verify setup
          python -m pipeline create --quick -t "My Film" -o p.json  # scaffold
          python -m pipeline create --idea "A robot learns to paint" # AI-powered
          python -m pipeline run render p.json --stub-only           # render
          python -m pipeline validate p.json                         # validate
    """))


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        _print_help()
        return 0

    command = sys.argv[1]
    # Strip the command from argv so submodule parsers see the right args
    sub_argv = sys.argv[2:]

    if command == "create":
        sys.argv = ["pipeline create", *sub_argv]
        from pipeline.create import main as create_main
        return create_main()

    elif command == "run":
        sys.argv = ["pipeline run", *sub_argv]
        from pipeline.run import main as run_main
        return run_main(sub_argv)

    elif command == "validate":
        if not sub_argv or sub_argv[0] in ("-h", "--help"):
            print("usage: python -m pipeline validate <file.json> [--schema FILE] [-v]")
            return 0 if sub_argv else 1
        # Delegate to create --validate (already fully implemented)
        sys.argv = ["pipeline validate", "--validate", *sub_argv]
        from pipeline.create import main as create_main
        return create_main()

    elif command == "check":
        sys.argv = ["pipeline check", *sub_argv]
        from pipeline.check_env import run_checks
        return run_checks()

    else:
        print(f"Unknown command: {command}")
        print("Run 'python -m pipeline --help' for available commands.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
