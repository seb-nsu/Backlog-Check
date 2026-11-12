"""BC-12: an epic without stories, or a story without an epic, if the backlog has epics."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-12"


def check_bc12(ctx: Context) -> Iterator[Finding]:
    epics = {item.id for item in ctx.items if item.kind == "epic"}
    if not epics:
        return
    for item in ctx.active:
        if item.kind == "epic":
            # ASSUMPTION: done stories count as stories of their epic; bugs do not.
            children = ctx.children.get(item.id, ())
            if not any(ctx.by_id[child].kind == "story" for child in children):
                yield ctx.finding(RULE, item, "bc12.epic_without_stories")
        elif item.kind == "story" and item.parent not in epics:
            # ASSUMPTION: bugs need no epic; a parent that is unknown or not an epic counts
            # as no epic.
            yield ctx.finding(RULE, item, "bc12.story_without_epic", field="parent")
