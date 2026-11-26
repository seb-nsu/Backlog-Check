"""BC-17: ``depends_on`` or ``parent`` names an id that is not in the backlog."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-17"


def check_bc17(ctx: Context) -> Iterator[Finding]:
    # ASSUMPTION: ids are compared exactly, as everywhere else ("en-2" is not "EN-2"). Done
    # items are not checked, like for every other rule.
    for item in ctx.active:
        for index, dep_id in enumerate(item.depends_on):
            if dep_id not in ctx.by_id:
                yield ctx.finding(
                    RULE,
                    item,
                    "bc17.unknown_dependency",
                    params={"id": dep_id},
                    field=f"depends_on[{index}]",
                )
        if item.parent is not None and item.parent not in ctx.by_id:
            yield ctx.finding(
                RULE, item, "bc17.unknown_parent", params={"id": item.parent}, field="parent"
            )
