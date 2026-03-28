"""
logging_config.py — Centralized structlog configuration for the pipeline.

Configures structlog with:
  - Console output: colored, human-readable (dev-friendly)
  - JSON file output: one JSON object per line, saved to disk

Usage
-----
  from pipeline.logging_config import configure_logging
  configure_logging(log_dir=Path("./output"), verbose=False)

  # Then in any module:
  import structlog
  log = structlog.get_logger(__name__)
  log.info("shot generated", shot_id="s01", duration=4.2)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog


_configured = False


def configure_logging(
    log_dir: Path | None = None,
    verbose: bool = False,
) -> None:
    """Initialise structlog + stdlib logging with console + JSON file output.

    Parameters
    ----------
    log_dir
        Directory for ``pipeline.log`` (JSON Lines).  When *None* only
        console output is produced.
    verbose
        If *True*, set root log level to DEBUG; otherwise INFO.
    """
    global _configured
    if _configured:
        return
    _configured = True

    log_level = logging.DEBUG if verbose else logging.INFO

    # ── shared processors (run inside structlog before final rendering) ────
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # ── console formatter (colored, human-readable) ───────────────────────
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
        foreign_pre_chain=shared_processors,
    )

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)

    # ── JSON file formatter (one JSON object per line) ────────────────────
    file_handler: logging.Handler | None = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "pipeline.log"

        json_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            foreign_pre_chain=shared_processors,
        )

        file_handler = logging.FileHandler(str(log_path), mode="a", encoding="utf-8")
        file_handler.setFormatter(json_formatter)

    # ── wire up stdlib root logger ────────────────────────────────────────
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)
    root.addHandler(console_handler)
    if file_handler is not None:
        file_handler.setLevel(logging.DEBUG)   # always capture everything on disk
        root.addHandler(file_handler)

    # ── configure structlog itself ────────────────────────────────────────
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
