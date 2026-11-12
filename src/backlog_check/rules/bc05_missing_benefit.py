"""BC-05: a story without a benefit clause in title or description."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-05"


def check_bc05(ctx: Context) -> Iterator[Finding]:
    for item in ctx.active:
        if item.kind != "story":
            continue
        if not any(
            p.search(item.title) or p.search(item.description) for p in ctx.benefit_patterns
        ):
            yield ctx.finding(RULE, item, "bc05.missing_benefit", field="description")
