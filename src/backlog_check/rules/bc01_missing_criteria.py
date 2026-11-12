"""BC-01: a story or bug without acceptance criteria."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-01"


def check_bc01(ctx: Context) -> Iterator[Finding]:
    for item in ctx.active:
        if item.kind in ("story", "bug") and not item.acceptance_criteria:
            yield ctx.finding(RULE, item, "bc01.missing", field="acceptance_criteria")
