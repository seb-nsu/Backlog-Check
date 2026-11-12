"""Shared, precomputed view of a backlog for the rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Config
from .model import Finding, Item


@dataclass(frozen=True)
class TextField:
    """A text field of an item, e.g. ``title`` or ``acceptance_criteria[0]``."""

    name: str
    text: str


class Context:
    """Items, lookups and the language-specific word lists for one check run."""

    def __init__(self, items: list[Item], config: Config) -> None:
        self.items = items
        self.config = config
        self.by_id = {item.id: item for item in items}
        self.position = {item.id: index for index, item in enumerate(items)}
        # Done items are not checked but still count as targets of dependencies.
        self.active = [item for item in items if not config.is_done(item.status)]
        self.active_ids = {item.id for item in self.active}
        self.children: dict[str, list[str]] = {}
        self.dependents: dict[str, list[str]] = {}
        for item in items:
            if item.parent is not None:
                self.children.setdefault(item.parent, []).append(item.id)
            for dep_id in item.depends_on:
                self.dependents.setdefault(dep_id, []).append(item.id)
        languages = config.languages()
        self.vague_words = _merge(config.vague_words[lang] for lang in languages)
        self.benefit_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in _merge(config.benefit_patterns[lang] for lang in languages)
        ]
        self.conjunctions = _merge(config.conjunctions[lang] for lang in languages)
        self.activity_patterns = [
            re.compile(p) for p in _merge(config.activity_patterns[lang] for lang in languages)
        ]
        self.units: dict[str, str] = {}
        for lang in languages:
            for spelling, unit in config.units[lang].items():
                self.units.setdefault(spelling, unit)
        self.term_stopwords = frozenset(
            w.casefold() for lang in languages for w in config.term_stopwords[lang]
        )

    def finding(self, rule: str, item: Item, message_key: str, **kwargs) -> Finding:
        """Create a finding with the configured severity of ``rule``."""
        return Finding(
            rule=rule,
            severity=self.config.rules[rule].severity,
            item=item.id,
            message_key=message_key,
            **kwargs,
        )


def text_fields(item: Item) -> list[TextField]:
    """Title, description and each acceptance criterion, in this order."""
    fields = [TextField("title", item.title), TextField("description", item.description)]
    fields.extend(
        TextField(f"acceptance_criteria[{index}]", text)
        for index, text in enumerate(item.acceptance_criteria)
    )
    return fields


def word_pattern(word: str) -> re.Pattern[str]:
    """Match ``word`` case-insensitively as a whole word (``-`` counts as part of a word)."""
    prefix = r"(?<![\w-])" if re.match(r"\w", word) else ""
    suffix = r"(?![\w-])" if re.search(r"\w$", word) else ""
    return re.compile(prefix + re.escape(word) + suffix, re.IGNORECASE)


UNIT_TOKEN = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*|[%€]")


def has_unit(text: str, units: dict[str, str]) -> bool:
    """Whether ``text`` contains a unit of measurement as a whole word (or ``%``, ``€``)."""
    return any(token.casefold() in units for token in UNIT_TOKEN.findall(text))


def _merge(lists) -> list[str]:
    result: list[str] = []
    for words in lists:
        result.extend(w for w in words if w not in result)
    return result
