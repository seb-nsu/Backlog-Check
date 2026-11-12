"""BC-04: title or benefit sentence joins several activities with "und" / "and"."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..context import Context, word_pattern
from ..model import Finding, Item

RULE = "BC-04"
SENTENCE = re.compile(r"[^.!?\n]+")


def check_bc04(ctx: Context) -> Iterator[Finding]:
    patterns = [word_pattern(word) for word in ctx.conjunctions]
    for item in ctx.active:
        hit = _first_hit(patterns, item.title)
        if hit:
            yield _finding(ctx, item, "title", hit)
        # ASSUMPTION: the benefit sentence is each sentence of the description that matches a
        # benefit pattern of BC-05; the conjunction is searched in the whole sentence. Without
        # grammar analysis any conjunction counts as joining activities (severity info).
        for sentence in SENTENCE.finditer(item.description):
            if any(p.search(sentence.group()) for p in ctx.benefit_patterns):
                hit = _first_hit(patterns, sentence.group())
                if hit:
                    start, end, word = hit
                    offset = sentence.start()
                    yield _finding(ctx, item, "description", (start + offset, end + offset, word))
                    break


def _first_hit(patterns: list[re.Pattern[str]], text: str) -> tuple[int, int, str] | None:
    hits = [(m.start(), m.end(), m.group()) for p in patterns for m in [p.search(text)] if m]
    return min(hits) if hits else None


def _finding(ctx: Context, item: Item, field: str, hit: tuple[int, int, str]) -> Finding:
    start, end, word = hit
    return ctx.finding(
        RULE, item, "bc04.multiple_concerns", params={"word": word}, field=field, span=(start, end)
    )
