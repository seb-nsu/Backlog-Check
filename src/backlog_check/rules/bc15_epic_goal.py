"""BC-15: an epic without a goal, i.e. with no or a very short description."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-15"
WORD = re.compile(r"\w+")


def check_bc15(ctx: Context) -> Iterator[Finding]:
    min_words = ctx.config.epic_goal_min_words
    # ASSUMPTION: the goal of an epic is its description; fewer words than the threshold
    # count as no goal.
    for item in ctx.active:
        if item.kind != "epic":
            continue
        words = len(WORD.findall(item.description))
        if words < min_words:
            yield ctx.finding(
                RULE,
                item,
                "bc15.missing_goal",
                params={"words": words, "min_words": min_words},
                field="description",
            )
