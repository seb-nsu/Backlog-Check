"""BC-18: an acceptance criterion repeats an earlier criterion of the same item."""

from __future__ import annotations

from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-18"
TRAILING = " .!;:"


def normalize_criterion(text: str) -> str:
    """Case-folded text with collapsed white space and without closing punctuation."""
    return " ".join(text.casefold().split()).rstrip(TRAILING)


def check_bc18(ctx: Context) -> Iterator[Finding]:
    for item in ctx.active:
        # ASSUMPTION: criteria count as the same when they are equal after normalising case,
        # white space and closing punctuation. The finding is at the later criterion.
        first: dict[str, int] = {}
        for index, text in enumerate(item.acceptance_criteria):
            key = normalize_criterion(text)
            if not key:
                continue
            if key in first:
                yield ctx.finding(
                    RULE,
                    item,
                    "bc18.duplicate_criterion",
                    params={"first": f"acceptance_criteria[{first[key]}]"},
                    field=f"acceptance_criteria[{index}]",
                )
            else:
                first[key] = index
