"""Summary of a check run: counts per rule and severity, share of ready stories."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .config import Config
from .engine import to_items
from .model import RULE_IDS, SEVERITIES, Finding, Item


def summarize(
    items: Iterable[Item | Mapping[str, Any]],
    findings: Sequence[Finding],
    config: Config | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Count items and findings. A story is "ready" if it has no finding of severity error."""
    cfg = config if isinstance(config, Config) else Config.from_dict(config)
    all_items = to_items(items)
    active = [item for item in all_items if not cfg.is_done(item.status)]
    stories = [item for item in active if item.kind == "story"]
    with_error = {f.item for f in findings if f.severity == "error"}
    ready = sum(1 for story in stories if story.id not in with_error)
    by_rule: dict[str, dict[str, int]] = {}
    for rule in RULE_IDS:
        counts = {
            s: sum(1 for f in findings if f.rule == rule and f.severity == s) for s in SEVERITIES
        }
        counts = {s: n for s, n in counts.items() if n}
        if counts:
            by_rule[rule] = counts
    return {
        "items": len(all_items),
        "checked": len(active),
        "findings": len(findings),
        "by_severity": {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES},
        "by_rule": by_rule,
        "stories": len(stories),
        "ready_stories": ready,
        # ASSUMPTION: the share counts unfinished stories; null when there are none.
        "ready_ratio": round(ready / len(stories), 4) if stories else None,
    }
