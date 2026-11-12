"""BC-04: title or benefit sentence joins several activities with "und" / "and"."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..context import Context, word_pattern
from ..model import Finding, Item

RULE = "BC-04"
SENTENCE = re.compile(r"[^.!?\n]+")
NEXT_WORD = re.compile(r"\s+([^\W\d_]+(?:-[^\W\d_]+)*)")


def check_bc04(ctx: Context) -> Iterator[Finding]:
    patterns = [word_pattern(word) for word in ctx.conjunctions]
    activities = ctx.activity_patterns
    for item in ctx.active:
        hit = _first_hit(patterns, activities, item.title)
        if hit:
            yield _finding(ctx, item, "title", hit)
        # ASSUMPTION: the benefit sentence is each sentence of the description that matches a
        # benefit pattern of BC-05; the conjunction is searched in the whole sentence.
        # ASSUMPTION: a conjunction joins activities if the word right after it is a verb
        # according to ``activity_patterns`` ("erstellen und versenden", "export and print").
        for sentence in SENTENCE.finditer(item.description):
            if any(p.search(sentence.group()) for p in ctx.benefit_patterns):
                hit = _first_hit(patterns, activities, sentence.group())
                if hit:
                    start, end, word = hit
                    offset = sentence.start()
                    yield _finding(ctx, item, "description", (start + offset, end + offset, word))
                    break


def _first_hit(
    patterns: list[re.Pattern[str]], activities: list[re.Pattern[str]], text: str
) -> tuple[int, int, str] | None:
    """First conjunction in ``text`` that is followed by a verb."""
    hits = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            following = NEXT_WORD.match(text, match.end())
            if following and any(a.fullmatch(following.group(1)) for a in activities):
                hits.append((match.start(), match.end(), match.group()))
                break
    return min(hits) if hits else None


def _finding(ctx: Context, item: Item, field: str, hit: tuple[int, int, str]) -> Finding:
    start, end, word = hit
    return ctx.finding(
        RULE, item, "bc04.multiple_concerns", params={"word": word}, field=field, span=(start, end)
    )
