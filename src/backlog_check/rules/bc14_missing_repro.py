"""BC-14: a bug whose description has no steps to reproduce."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-14"


def check_bc14(ctx: Context) -> Iterator[Finding]:
    patterns = [
        re.compile(p, re.IGNORECASE)
        for lang in ctx.config.languages()
        for p in ctx.config.repro_patterns[lang]
    ]
    for item in ctx.active:
        if item.kind == "bug" and not any(p.search(item.description) for p in patterns):
            yield ctx.finding(RULE, item, "bc14.missing_repro_steps", field="description")
