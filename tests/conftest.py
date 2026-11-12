"""Shared helpers for tests."""

from __future__ import annotations

from typing import Any

from backlog_check import Item


def story(item_id: str, **fields: Any) -> Item:
    """A complete story that triggers no rule on its own (in German and English)."""
    values: dict[str, Any] = {
        "kind": "story",
        "title": f"Titel {item_id}",
        "description": "Damit es klappt / so that it works",
        "acceptance_criteria": ("Kriterium",),
        "estimate": 3,
    }
    values.update(fields)
    return Item(id=item_id, **values)
