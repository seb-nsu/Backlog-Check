"""Data types for items and findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

KINDS = ("epic", "story", "bug")
PRIORITIES = ("must", "should", "could", "wont")
SEVERITIES = ("info", "warning", "error")
RULE_IDS = tuple(f"BC-{n:02d}" for n in range(1, 16))


@dataclass(frozen=True)
class Item:
    """One backlog entry in the input format described in docs/KONZEPT.md."""

    id: str
    kind: str
    title: str
    description: str = ""
    acceptance_criteria: tuple[str, ...] = ()
    estimate: int | float | None = None
    priority: str | None = None
    rank: int | None = None
    status: str | None = None
    depends_on: tuple[str, ...] = ()
    parent: str | None = None
    updated: str | None = None  # last change as ISO date YYYY-MM-DD
    line: int | None = field(default=None, compare=False, repr=False)  # position in the source


@dataclass(frozen=True)
class Finding:
    """One finding. Text is built by the caller from ``message_key`` and ``params``."""

    rule: str
    severity: str
    item: str
    message_key: str
    params: dict[str, Any] = field(default_factory=dict)
    related: tuple[str, ...] = ()
    field: str | None = None
    span: tuple[int, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the finding in the output format, with a fixed key order."""
        return {
            "rule": self.rule,
            "severity": self.severity,
            "item": self.item,
            "related": list(self.related),
            "field": self.field,
            "span": list(self.span) if self.span is not None else None,
            "message_key": self.message_key,
            "params": {key: self.params[key] for key in sorted(self.params)},
        }
