"""
rules — Declarative rule engine for file classification.

Provides:
    Rule        A single atomic matcher (type + params + optional negation)
    RuleGroup   A set of Rules combined with AND/OR logic
    RULE_EVALUATORS  Registry mapping rule type names to evaluator functions

Rule types:
    extension        Match file suffix(es)
    name_glob        Match filename via glob pattern(s)
    name_regex       Match filename via regex
    stem_contains    Match if stem contains substring(s)
    stem_startswith  Match if stem starts with prefix(es)
    content_contains Match if file head contains string(s)
    content_regex    Match if file head matches regex
    size_gt          Match if file size > N bytes
    size_lt          Match if file size < N bytes
    path_contains    Match if relative path contains keyword(s)

Extending:
    Register a new evaluator with:
        RULE_EVALUATORS["my_rule"] = lambda info, params: bool
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from typing import Any, Callable

from lib.file_info import FileInfo


# ── Individual rule evaluators ──────────────────────────────────────────────

def _eval_extension(info: FileInfo, params: Any) -> bool:
    if isinstance(params, str):
        params = [params]
    return info.suffix in [p.lower() for p in params]


def _eval_name_glob(info: FileInfo, params: Any) -> bool:
    if isinstance(params, str):
        params = [params]
    return any(fnmatch.fnmatch(info.name, pat) for pat in params)


def _eval_name_regex(info: FileInfo, params: Any) -> bool:
    if isinstance(params, str):
        params = [params]
    return any(re.search(pat, info.name) for pat in params)


def _eval_stem_contains(info: FileInfo, params: Any) -> bool:
    if isinstance(params, str):
        params = [params]
    stem_lower = info.stem.lower()
    return any(kw.lower() in stem_lower for kw in params)


def _eval_stem_startswith(info: FileInfo, params: Any) -> bool:
    if isinstance(params, str):
        params = [params]
    stem_lower = info.stem.lower()
    return any(stem_lower.startswith(kw.lower()) for kw in params)


def _eval_content_contains(info: FileInfo, params: Any) -> bool:
    if not info.head:
        return False
    if isinstance(params, str):
        params = [params]
    return any(kw in info.head for kw in params)


def _eval_content_regex(info: FileInfo, params: Any) -> bool:
    if not info.head:
        return False
    if isinstance(params, str):
        params = [params]
    return any(re.search(pat, info.head, re.MULTILINE) for pat in params)


def _eval_size_gt(info: FileInfo, params: Any) -> bool:
    return info.size > int(params)


def _eval_size_lt(info: FileInfo, params: Any) -> bool:
    return info.size < int(params)


def _eval_path_contains(info: FileInfo, params: Any) -> bool:
    if isinstance(params, str):
        params = [params]
    rel_lower = info.rel.lower()
    return any(kw.lower() in rel_lower for kw in params)


# ── Rule evaluator registry ────────────────────────────────────────────────

RULE_EVALUATORS: dict[str, Callable[[FileInfo, Any], bool]] = {
    "extension":        _eval_extension,
    "name_glob":        _eval_name_glob,
    "name_regex":       _eval_name_regex,
    "stem_contains":    _eval_stem_contains,
    "stem_startswith":  _eval_stem_startswith,
    "content_contains": _eval_content_contains,
    "content_regex":    _eval_content_regex,
    "size_gt":          _eval_size_gt,
    "size_lt":          _eval_size_lt,
    "path_contains":    _eval_path_contains,
}


# ── Composite rule types ───────────────────────────────────────────────────

@dataclass(frozen=True)
class Rule:
    """A single atomic rule parsed from config."""
    type: str
    params: Any
    negate: bool = False

    def evaluate(self, info: FileInfo) -> bool:
        evaluator = RULE_EVALUATORS.get(self.type)
        if evaluator is None:
            raise ValueError(f"Unknown rule type: '{self.type}'. "
                             f"Available: {sorted(RULE_EVALUATORS)}")
        result = evaluator(info, self.params)
        return (not result) if self.negate else result

    def explain(self) -> str:
        neg = "NOT " if self.negate else ""
        return f"{neg}{self.type}({self.params})"


@dataclass(frozen=True)
class RuleGroup:
    """A group of rules combined with a logical operator.

    mode="any"  → OR  (file matches if ANY rule matches)  — default
    mode="all"  → AND (file matches if ALL rules match)
    """
    rules: tuple[Rule, ...]
    mode: str = "any"  # "any" | "all"

    def evaluate(self, info: FileInfo) -> bool:
        if self.mode == "all":
            return all(r.evaluate(info) for r in self.rules)
        return any(r.evaluate(info) for r in self.rules)

    def explain_match(self, info: FileInfo) -> list[str]:
        return [r.explain() for r in self.rules if r.evaluate(info)]


def parse_rule(raw: dict[str, Any]) -> Rule:
    """Parse a single rule dict from config."""
    negate = raw.pop("negate", False) if isinstance(raw, dict) else False
    rule_keys = [k for k in raw if k != "negate"]
    if len(rule_keys) != 1:
        raise ValueError(
            f"Each rule must have exactly one type key, got: {rule_keys}. "
            f"Full rule: {raw}"
        )
    rule_type = rule_keys[0]
    return Rule(type=rule_type, params=raw[rule_type], negate=negate)
