"""BC-07: text names the id of another item that is not in ``depends_on``."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..context import Context, text_fields
from ..model import Finding

RULE = "BC-07"
# ASSUMPTION: ids are recognised as whole words made of letters, digits, "_", "-" and ".",
# starting and ending with a letter or digit. Ids with other characters are never matched.
ID_TOKEN = re.compile(r"\w(?:[\w.\-]*\w)?")


def check_bc07(ctx: Context) -> Iterator[Finding]:
    for item in ctx.active:
        # ASSUMPTION: the item's own parent and children are already linked and do not count.
        # Items that depend on this item are linked in the other direction and do not count
        # either: naming them states what this item enables, not what it needs.
        linked = {
            item.id,
            *item.depends_on,
            *ctx.children.get(item.id, ()),
            *ctx.dependents.get(item.id, ()),
        }
        if item.parent:
            linked.add(item.parent)
        seen: set[str] = set()
        for text_field in text_fields(item):
            for match in ID_TOKEN.finditer(text_field.text):
                other = match.group()
                if other in ctx.by_id and other not in linked and other not in seen:
                    # ASSUMPTION: one finding per named id, at its first occurrence.
                    seen.add(other)
                    yield ctx.finding(
                        RULE,
                        item,
                        "bc07.hidden_dependency",
                        params={"id": other},
                        related=(other,),
                        field=text_field.name,
                        span=match.span(),
                    )
