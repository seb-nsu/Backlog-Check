"""BC-11: two items give different numbers with the same unit for the same term."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

from ..context import Context, text_fields
from ..model import Finding, Item

RULE = "BC-11"
QUANTITY = re.compile(r"(?<![\w.,\-])(\d+(?:[.,]\d+)?)[ \u00a0]?([^\W\d_]+|[%€])(?!\w)")
WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
SENTENCE_END = re.compile(r"[.!?\n]")
TERM_LOOKBACK = 3


@dataclass(frozen=True)
class Quantity:
    term: str
    value: str
    amount: Decimal
    unit: str
    canonical_unit: str
    field: str
    span: tuple[int, int]

    @property
    def key(self) -> tuple[str, str]:
        return (self.term.casefold(), self.canonical_unit)


def quantities(ctx: Context, item: Item) -> list[Quantity]:
    """Numbers with a known unit and the term in front of them, e.g. "Frist 5 Tage"."""
    result = []
    for text_field in text_fields(item):
        text = text_field.text
        for match in QUANTITY.finditer(text):
            value, unit = match.groups()
            canonical = ctx.units.get(unit.casefold())
            term = _term(ctx, text[: match.start()])
            if canonical is None or term is None:
                continue
            # Convert to the base unit so that "2 Wochen" and "14 Tage" are equal.
            base, factor = ctx.config.unit_conversions.get(canonical, (canonical, 1))
            result.append(
                Quantity(
                    term=term,
                    value=value,
                    amount=Decimal(value.replace(",", ".")) * Decimal(str(factor)),
                    unit=unit,
                    canonical_unit=base,
                    field=text_field.name,
                    span=match.span(),
                )
            )
    return result


def _term(ctx: Context, before: str) -> str | None:
    # ASSUMPTION: the term is the nearest of the last three words in the same sentence in front
    # of the number that is not a stop word ("Frist beträgt 5 Tage" -> "Frist").
    sentence = SENTENCE_END.split(before)[-1]
    for word in reversed(WORD.findall(sentence)[-TERM_LOOKBACK:]):
        if word.casefold() not in ctx.term_stopwords:
            return word
    return None


def check_bc11(ctx: Context) -> Iterator[Finding]:
    seen: dict[tuple[str, str], list[tuple[Item, Quantity]]] = defaultdict(list)
    for item in ctx.active:
        found = quantities(ctx, item)
        reported: set[tuple[str, tuple[str, str]]] = set()
        for quantity in found:
            for other, other_quantity in seen.get(quantity.key, ()):
                pair = (other.id, quantity.key)
                if other_quantity.amount == quantity.amount or pair in reported:
                    continue
                # ASSUMPTION: one finding per pair of items and term, at the later item.
                reported.add(pair)
                yield ctx.finding(
                    RULE,
                    item,
                    "bc11.conflicting_values",
                    params={
                        "term": quantity.term,
                        "value": quantity.value,
                        "unit": quantity.unit,
                        "other": other.id,
                        "other_value": other_quantity.value,
                        "other_unit": other_quantity.unit,
                    },
                    related=(other.id,),
                    field=quantity.field,
                    span=quantity.span,
                )
        for quantity in found:
            seen[quantity.key].append((item, quantity))
