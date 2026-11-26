"""Improvement suggestions for findings, and templates for new items.

Like findings, suggestions carry no sentences: each has a ``message_key`` and ``params`` that
the caller turns into text with the catalogs. They are derived from the findings and the
items only, so the same input always gives the same suggestions.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .catalog import load_catalog
from .config import Config
from .context import Context
from .engine import to_items
from .model import KINDS, Finding, Item
from .rules.bc10_duplicate import word_set

SPLIT_STRIP = " ,;:-\u2013"


@dataclass(frozen=True)
class Suggestion:
    """How to resolve one finding. Text is built by the caller from ``message_key``."""

    rule: str
    item: str
    message_key: str
    params: dict[str, Any] = field(default_factory=dict)
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the suggestion with a fixed key order."""
        return {
            "rule": self.rule,
            "item": self.item,
            "field": self.field,
            "message_key": self.message_key,
            "params": {key: self.params[key] for key in sorted(self.params)},
        }


def suggest(
    items: Iterable[Item | Mapping[str, Any]],
    findings: Sequence[Finding],
    config: Config | Mapping[str, Any] | None = None,
) -> list[Suggestion]:
    """Return one suggestion per finding, in the order of ``findings``."""
    cfg = config if isinstance(config, Config) else Config.from_dict(config)
    ctx = Context(to_items(items), cfg)
    return [_suggest_one(ctx, finding) for finding in findings]


def _suggest_one(ctx: Context, finding: Finding) -> Suggestion:
    item = ctx.by_id[finding.item]
    key, params = SUGGESTERS[finding.message_key](ctx, item, finding)
    return Suggestion(finding.rule, finding.item, key, params, finding.field)


Result = tuple[str, dict[str, Any]]


def _suggest_bc01(ctx: Context, item: Item, finding: Finding) -> Result:
    if item.kind == "bug":
        return "bc01.fix_missing_bug", {}
    return "bc01.fix_missing", {}


def _suggest_bc02(ctx: Context, item: Item, finding: Finding) -> Result:
    word = finding.params["word"]
    # ASSUMPTION: measurable wordings come from the configuration (``measurable_hints``),
    # like the word lists; without an entry the suggestion stays general.
    for lang in ctx.config.languages():
        hint = ctx.config.measurable_hints[lang].get(word.casefold())
        if hint is not None:
            return "bc02.fix_replace_word", {"word": word, "hint": hint}
    return "bc02.fix_unmeasurable", {"word": word}


def _suggest_bc03_estimate(ctx: Context, item: Item, finding: Finding) -> Result:
    params = finding.params
    parts = max(2, math.ceil(params["estimate"] / params["max_estimate"]))
    return "bc03.fix_split_estimate", {"parts": parts, "max_estimate": params["max_estimate"]}


def _suggest_bc03_criteria(ctx: Context, item: Item, finding: Finding) -> Result:
    count, max_criteria = finding.params["count"], finding.params["max_criteria"]
    parts = max(2, math.ceil(count / max_criteria)) if max_criteria else 2
    return "bc03.fix_split_criteria", {"parts": parts, "max_criteria": max_criteria}


def _suggest_bc04(ctx: Context, item: Item, finding: Finding) -> Result:
    if finding.field == "title" and finding.span is not None:
        start, end = finding.span
        first = item.title[:start].strip(SPLIT_STRIP)
        second = item.title[end:].strip(SPLIT_STRIP)
        if first and second:
            first, second = _share_object(first.split(), second.split(), ctx.config.language)
            return "bc04.fix_split_title", {"first": first, "second": second}
    return "bc04.fix_split", {"word": finding.params["word"]}


def _share_object(first: list[str], second: list[str], language: str) -> tuple[str, str]:
    """Give a lone verb the object of the other part.

    German puts the object first: "Rechnung erstellen" + "versenden" -> "Rechnung versenden".
    English puts the verb first: "export" + "print report" -> "export report", and
    "import data" + "validate" -> "validate data".
    """
    # ASSUMPTION: a part of one word is a verb whose object is in the other part. With
    # language "auto" the word order is unknown and the parts stay as they are.
    if language == "de" and len(second) == 1 < len(first):
        second = first[:-1] + second
    elif language == "en" and len(first) == 1 < len(second):
        first = first + second[1:]
    elif language == "en" and len(second) == 1 < len(first):
        second = second + first[1:]
    return " ".join(first), " ".join(second)


def _suggest_bc05(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc05.fix_add_benefit", {"title": item.title}


def _suggest_bc06(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc06.fix_estimate", {"max_estimate": ctx.config.max_estimate}


def _suggest_bc07(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc07.fix_add_dependency", {"id": finding.params["id"]}


BC08_KEYS = {
    "bc08.rank_order": "bc08.fix_rank_order",
    "bc08.priority_order": "bc08.fix_priority_order",
    "bc08.rank_and_priority_order": "bc08.fix_rank_and_priority_order",
}


def _suggest_bc08(ctx: Context, item: Item, finding: Finding) -> Result:
    return BC08_KEYS[finding.message_key], dict(finding.params)


def _suggest_bc09(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc09.fix_break_cycle", {"items": finding.params["items"]}


def _suggest_bc10(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc10.fix_merge", {"other": finding.params["other"]}


def _suggest_bc11(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc11.fix_align", {"term": finding.params["term"], "other": finding.params["other"]}


def _suggest_bc12_epic(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc12.fix_add_stories", {}


def _suggest_bc12_story(ctx: Context, item: Item, finding: Finding) -> Result:
    epic = _closest_epic(ctx, item)
    if epic is None:
        return "bc12.fix_assign_epic", {}
    return "bc12.fix_assign_epic_candidate", {"epic": epic}


def _closest_epic(ctx: Context, item: Item) -> str | None:
    """The open epic sharing the most words with the story (Jaccard); earliest on a tie."""
    # ASSUMPTION: the candidate epic must share at least one word; done epics are skipped.
    words = word_set(f"{item.title} {item.description}", ctx.similarity_stopwords)
    best, best_score = None, 0.0
    for epic in ctx.active:
        if epic.kind != "epic":
            continue
        epic_words = word_set(f"{epic.title} {epic.description}", ctx.similarity_stopwords)
        union = words | epic_words
        score = len(words & epic_words) / len(union) if union else 0.0
        if score > best_score:
            best, best_score = epic.id, score
    return best


def _suggest_bc13(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc13.fix_review", {"updated": finding.params["updated"]}


def _suggest_bc14(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc14.fix_add_steps", {}


def _suggest_bc15(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc15.fix_add_goal", {"min_words": finding.params["min_words"]}


def _suggest_bc16(ctx: Context, item: Item, finding: Finding) -> Result:
    return "bc16.fix_fill_placeholder", {"text": finding.params["text"]}


SUGGESTERS = {
    "bc01.missing": _suggest_bc01,
    "bc02.unmeasurable": _suggest_bc02,
    "bc03.estimate_too_large": _suggest_bc03_estimate,
    "bc03.too_many_criteria": _suggest_bc03_criteria,
    "bc04.multiple_concerns": _suggest_bc04,
    "bc05.missing_benefit": _suggest_bc05,
    "bc06.missing_estimate": _suggest_bc06,
    "bc07.hidden_dependency": _suggest_bc07,
    "bc08.rank_order": _suggest_bc08,
    "bc08.priority_order": _suggest_bc08,
    "bc08.rank_and_priority_order": _suggest_bc08,
    "bc09.cycle": _suggest_bc09,
    "bc10.possible_duplicate": _suggest_bc10,
    "bc11.conflicting_values": _suggest_bc11,
    "bc12.epic_without_stories": _suggest_bc12_epic,
    "bc12.story_without_epic": _suggest_bc12_story,
    "bc13.stale": _suggest_bc13,
    "bc14.missing_repro_steps": _suggest_bc14,
    "bc15.missing_goal": _suggest_bc15,
    "bc16.unfilled_placeholder": _suggest_bc16,
}

# Catalog keys of the templates; acceptance criteria are numbered from 1.
TEMPLATE_CRITERIA = {"story": 3, "bug": 2, "epic": 0}


def template(kind: str, language: str) -> dict[str, Any]:
    """A new item of ``kind`` in the input format, with placeholders in ``language``.

    A filled-in story template passes BC-01, BC-02, BC-04 and BC-05, a bug template also
    BC-14, an epic template BC-15.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    catalog = load_catalog(language)
    criteria = [
        catalog[f"template.{kind}_criterion_{n}"] for n in range(1, TEMPLATE_CRITERIA[kind] + 1)
    ]
    item: dict[str, Any] = {
        "id": catalog[f"template.{kind}_id"],
        "kind": kind,
        "title": catalog[f"template.{kind}_title"],
        "description": catalog[f"template.{kind}_description"],
    }
    if criteria:
        item["acceptance_criteria"] = criteria
    return item
