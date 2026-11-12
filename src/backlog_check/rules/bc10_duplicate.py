"""BC-10: two items whose title and description words are very similar (Jaccard index)."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterator

from ..context import Context
from ..model import Finding

RULE = "BC-10"
WORD = re.compile(r"\w+")


def word_set(text: str, stopwords: frozenset[str] = frozenset()) -> frozenset[str]:
    """Normalised word set: case-folded runs of letters, digits and "_" without stop words."""
    return frozenset(WORD.findall(text.casefold())) - stopwords


def check_bc10(ctx: Context) -> Iterator[Finding]:
    threshold = ctx.config.duplicate_threshold
    stopwords = ctx.similarity_stopwords
    entries = [
        (item, word_set(f"{item.title} {item.description}", stopwords)) for item in ctx.active
    ]
    frequency = Counter(word for _, words in entries for word in words)
    # Prefix filtering: with all word sets ordered by rarity, two sets whose similarity reaches
    # the threshold share at least one word within their prefixes. Only those pairs are compared.
    index: dict[str, list[int]] = defaultdict(list)
    for position, (item, words) in enumerate(entries):
        ordered = sorted(words, key=lambda word: (frequency[word], word))
        prefix = ordered[: len(ordered) - math.ceil(threshold * len(ordered) - 1e-9) + 1]
        candidates = sorted({other for word in prefix for other in index[word]})
        for other_position in candidates:
            other, other_words = entries[other_position]
            similarity = len(words & other_words) / len(words | other_words)
            # ASSUMPTION: the finding sits at the later item and names the earlier one.
            if similarity > threshold:
                yield ctx.finding(
                    RULE,
                    item,
                    "bc10.possible_duplicate",
                    params={"other": other.id, "similarity": round(similarity, 2)},
                    related=(other.id,),
                )
        for word in prefix:
            index[word].append(position)
