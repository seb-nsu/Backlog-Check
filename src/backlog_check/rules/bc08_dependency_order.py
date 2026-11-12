"""BC-08: an item ranks before, or has a higher priority than, an item it depends on."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import PRIORITIES, Finding

RULE = "BC-08"
PRIORITY_ORDER = {priority: index for index, priority in enumerate(PRIORITIES)}


def check_bc08(ctx: Context) -> Iterator[Finding]:
    for item in ctx.active:
        seen: set[str] = set()
        for index, dep_id in enumerate(item.depends_on):
            # Done dependencies are fulfilled; unknown ids and self references are skipped.
            if dep_id in seen or dep_id == item.id or dep_id not in ctx.active_ids:
                continue
            seen.add(dep_id)
            dep = ctx.by_id[dep_id]
            rank_wrong = item.rank is not None and dep.rank is not None and item.rank < dep.rank
            priority_wrong = (
                item.priority is not None
                and dep.priority is not None
                and PRIORITY_ORDER[item.priority] < PRIORITY_ORDER[dep.priority]
            )
            params: dict[str, object] = {"dependency": dep_id}
            if rank_wrong:
                params.update(rank=item.rank, dependency_rank=dep.rank)
            if priority_wrong:
                params.update(priority=item.priority, dependency_priority=dep.priority)
            if rank_wrong and priority_wrong:
                key = "bc08.rank_and_priority_order"
            elif rank_wrong:
                key = "bc08.rank_order"
            elif priority_wrong:
                key = "bc08.priority_order"
            else:
                continue
            yield ctx.finding(
                RULE, item, key, params=params, related=(dep_id,), field=f"depends_on[{index}]"
            )
