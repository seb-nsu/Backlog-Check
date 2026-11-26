"""BC-16: a placeholder such as "<Rolle>", "TODO" or "TBD" was left in the text."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..context import Context, text_fields
from ..model import Finding

RULE = "BC-16"


def check_bc16(ctx: Context) -> Iterator[Finding]:
    # Patterns are case-sensitive so that words like "Todo-Liste" do not count.
    patterns = [
        re.compile(p)
        for lang in ctx.config.languages()
        for p in ctx.config.placeholder_patterns[lang]
    ]
    for item in ctx.active:
        for text_field in text_fields(item):
            matches = [m for p in patterns for m in p.finditer(text_field.text)]
            if not matches:
                continue
            # ASSUMPTION: one finding per field, at the first placeholder in text order; a
            # template full of placeholders would otherwise flood the report.
            first = min(matches, key=lambda m: (m.start(), -m.end()))
            yield ctx.finding(
                RULE,
                item,
                "bc16.unfilled_placeholder",
                params={"text": first.group()},
                field=text_field.name,
                span=first.span(),
            )
