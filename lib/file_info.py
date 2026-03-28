"""
file_info — File metadata extraction for rule-based classification.

Provides a FileInfo dataclass and a loader that pre-computes name, stem,
suffix, size, head (first N bytes), and relative path — everything a
declarative rule engine needs to classify a file without re-reading it.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Extensions whose content can be read as UTF-8 text for content-based rules.
TEXT_SUFFIXES: set[str] = {
    ".json", ".md", ".txt", ".html", ".htm", ".py", ".ts", ".tsx",
    ".js", ".jsx", ".css", ".yaml", ".yml", ".toml", ".csv", ".tsv",
    ".xml", ".svg", ".sh", ".bash", ".zsh", ".rs", ".go", ".rb",
    ".java", ".c", ".h", ".cpp", ".hpp", ".sql", ".graphql", ".proto",
    ".env", ".ini", ".cfg", ".conf", ".tex", ".rst", ".adoc",
}


@dataclass
class FileInfo:
    """Pre-computed metadata about a file, used by rule evaluation."""
    path: Path
    name: str
    stem: str
    suffix: str          # lowercase, includes dot
    size: int
    head: str            # first N bytes as text (empty if binary/unreadable)
    rel: str             # path relative to scan root


def load_file_info(path: Path, root: Path, *, head_bytes: int = 1024) -> FileInfo:
    """Build FileInfo for a single file.

    Parameters
    ----------
    path        : Absolute path to the file.
    root        : Root directory used to compute the relative path.
    head_bytes  : Maximum bytes to read from the file head for content rules.
    """
    suffix = path.suffix.lower()
    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    head = ""
    if suffix in TEXT_SUFFIXES or path.name.startswith("."):
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:head_bytes]
        except OSError:
            pass

    try:
        rel = str(path.relative_to(root))
    except ValueError:
        rel = path.name

    return FileInfo(
        path=path,
        name=path.name,
        stem=path.stem,
        suffix=suffix,
        size=size,
        head=head,
        rel=rel,
    )
