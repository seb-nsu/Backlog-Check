"""BC-13: an item that has not been changed for longer than ``stale_days``."""

from __future__ import annotations

import datetime
from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-13"


def check_bc13(ctx: Context) -> Iterator[Finding]:
    # ASSUMPTION: without a reference date in the configuration the rule does not run, because
    # the package never reads the clock (same input, same output).
    if ctx.config.reference_date is None:
        return
    today = datetime.date.fromisoformat(ctx.config.reference_date)
    max_days = ctx.config.stale_days
    for item in ctx.active:
        if item.updated is None:
            continue
        days = (today - datetime.date.fromisoformat(item.updated)).days
        if days > max_days:
            yield ctx.finding(
                RULE,
                item,
                "bc13.stale",
                params={"updated": item.updated, "days": days, "max_days": max_days},
                field="updated",
            )
