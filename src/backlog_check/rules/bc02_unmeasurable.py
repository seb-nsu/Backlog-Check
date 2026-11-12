"""BC-02: an acceptance criterion with a vague word and neither a number nor a unit."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..context import Context, has_unit, word_pattern
from ..model import Finding

RULE = "BC-02"
DIGIT = re.compile(r"\d")


def check_bc02(ctx: Context) -> Iterator[Finding]:
    patterns = [word_pattern(word) for word in ctx.vague_words]
    for item in ctx.active:
        for index, text in enumerate(item.acceptance_criteria):
            if DIGIT.search(text) or has_unit(text, ctx.units):
                continue
            # ASSUMPTION: one finding per occurrence of a vague word, in text order.
            hits = sorted(
                {(m.start(), m.end(), m.group()) for p in patterns for m in p.finditer(text)}
            )
            for start, end, word in hits:
                yield ctx.finding(
                    RULE,
                    item,
                    "bc02.unmeasurable",
                    params={"word": word},
                    field=f"acceptance_criteria[{index}]",
                    span=(start, end),
                )
