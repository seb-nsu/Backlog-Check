"""Apply the mechanical suggestions to a backlog and return it in the input format.

Only fixes that follow from the finding without judgement are applied:

- BC-04: a title that joins two activities is split; the item keeps the first part and a new
  item of the same kind, epic and priority gets the second part.
- BC-07: the named id is added to ``depends_on``.
- BC-12: a story without an epic gets the epic the suggestion names, if there is one.
- BC-18: the repeated criterion is removed.

Every other finding needs a decision by the author and is left alone. Like findings, the
changes carry ``message_key`` and ``params`` instead of sentences.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from .config import Config
from .context import Context
from .engine import to_items
from .model import Finding, Item
from .reader import FIELDS
from .suggest import SPLIT_STRIP, _closest_epic, _share_object


@dataclass(frozen=True)
class Change:
    """One applied fix. Text is built by the caller from ``message_key`` and ``params``."""

    rule: str
    item: str
    message_key: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "item": self.item,
            "message_key": self.message_key,
            "params": {key: self.params[key] for key in sorted(self.params)},
        }


def apply_fixes(
    items: Iterable[Item | Mapping[str, Any]],
    findings: Sequence[Finding],
    config: Config | Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[Change]]:
    """Return the fixed backlog (a list of items in the input format) and the changes."""
    cfg = config if isinstance(config, Config) else Config.from_dict(config)
    ctx = Context(to_items(items), cfg)
    current = dict(ctx.by_id)
    removed: dict[str, set[int]] = {}
    added: dict[str, list[Item]] = {}
    taken = set(ctx.by_id)
    changes: list[Change] = []
    for finding in findings:
        item = current[finding.item]
        key = finding.message_key
        if key == "bc07.hidden_dependency":
            dep_id = finding.params["id"]
            current[item.id] = replace(item, depends_on=(*item.depends_on, dep_id))
            changes.append(Change(finding.rule, item.id, "fix.add_dependency", {"id": dep_id}))
        elif key == "bc18.duplicate_criterion":
            index = int(finding.field.removeprefix("acceptance_criteria[").rstrip("]"))
            removed.setdefault(item.id, set()).add(index)
            params = {"field": finding.field, "first": finding.params["first"]}
            changes.append(Change(finding.rule, item.id, "fix.remove_criterion", params))
        elif key == "bc12.story_without_epic" and item.parent is None:
            # ASSUMPTION: only a story without any parent gets one; an unknown parent may be
            # a typo and is left for the author (BC-17).
            epic = _closest_epic(ctx, ctx.by_id[item.id])
            if epic is not None:
                current[item.id] = replace(item, parent=epic)
                changes.append(Change(finding.rule, item.id, "fix.set_parent", {"epic": epic}))
        elif key == "bc04.multiple_concerns" and finding.field == "title":
            split = _split_title(ctx, ctx.by_id[item.id], finding)
            if split is not None:
                first, second = split
                new_id = _free_id(item.id, taken)
                taken.add(new_id)
                current[item.id] = replace(item, title=first)
                # ASSUMPTION: the new item takes kind, epic, priority and status; description,
                # criteria, estimate and dependencies stay with the original, so the author
                # decides what belongs to the new item.
                new = Item(
                    id=new_id,
                    kind=item.kind,
                    title=second,
                    priority=item.priority,
                    status=item.status,
                    parent=item.parent,
                )
                added.setdefault(item.id, []).append(new)
                params = {"first": first, "second": second, "new_id": new_id}
                changes.append(Change(finding.rule, item.id, "fix.split_item", params))
    result = []
    for original in ctx.items:
        item = current[original.id]
        if original.id in removed:
            criteria = tuple(
                text
                for index, text in enumerate(item.acceptance_criteria)
                if index not in removed[original.id]
            )
            item = replace(item, acceptance_criteria=criteria)
        result.append(item_to_dict(item))
        result.extend(item_to_dict(new) for new in added.get(original.id, ()))
    return result, changes


def _split_title(ctx: Context, item: Item, finding: Finding) -> tuple[str, str] | None:
    start, end = finding.span
    first = item.title[:start].strip(SPLIT_STRIP)
    second = item.title[end:].strip(SPLIT_STRIP)
    if not (first and second):
        return None
    return _share_object(first.split(), second.split(), ctx.config.language)


def _free_id(item_id: str, taken: set[str]) -> str:
    """The first of ``<id>-2``, ``<id>-3``, ... that is not used yet."""
    number = 2
    while f"{item_id}-{number}" in taken:
        number += 1
    return f"{item_id}-{number}"


def item_to_dict(item: Item) -> dict[str, Any]:
    """An item in the input format, with only the fields that are set, in a fixed order."""
    data: dict[str, Any] = {}
    for name in FIELDS:
        value = getattr(item, name)
        if value is None or value == "" or value == ():
            continue
        data[name] = list(value) if isinstance(value, tuple) else value
    return data
