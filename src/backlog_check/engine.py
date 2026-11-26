"""Runs the rules and applies configuration: enabled rules, severities, ignore list, order."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .config import Config
from .context import Context
from .model import Finding, Item
from .reader import build_items
from .rules import RULES
from .rules.custom import check_custom


def check(
    items: Iterable[Item | Mapping[str, Any]], config: Config | Mapping[str, Any] | None = None
) -> list[Finding]:
    """Check a backlog and return the findings.

    ``items`` may be :class:`Item` objects or mappings in the input format; mappings are
    validated and raise :class:`InputError` with their 1-based position as line.
    Findings are ordered by the position of their item in the input, then by rule ID.
    """
    cfg = config if isinstance(config, Config) else Config.from_dict(config)
    ctx = Context(to_items(items), cfg)
    found = [
        finding
        for rule_id, rule in RULES.items()
        if cfg.rules[rule_id].enabled
        for finding in rule(ctx)
    ]
    found += [
        finding
        for custom in cfg.custom_rules
        if custom.enabled
        for finding in check_custom(ctx, custom)
    ]
    findings = [f for f in found if not any(entry.matches(f) for entry in cfg.ignore)]
    findings.sort(key=lambda f: (ctx.position[f.item], f.rule))
    return findings


def to_items(items: Iterable[Item | Mapping[str, Any]]) -> list[Item]:
    """Validate a mixed sequence of items and mappings; positions count from 1."""
    return build_items((index, item) for index, item in enumerate(items, start=1))
