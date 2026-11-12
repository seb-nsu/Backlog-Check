"""BC-06: an item ranked within the top N without an estimate."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-06"


def check_bc06(ctx: Context) -> Iterator[Finding]:
    top = ctx.config.estimate_required_top
    # ASSUMPTION: "die obersten 20" means rank 1 to 20 as given in the input, not the
    # position among unfinished items.
    for item in ctx.active:
        if item.rank is not None and item.rank <= top and item.estimate is None:
            yield ctx.finding(
                RULE,
                item,
                "bc06.missing_estimate",
                params={"rank": item.rank, "top": top},
                field="estimate",
            )
