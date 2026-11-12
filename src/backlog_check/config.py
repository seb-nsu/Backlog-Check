"""Configuration with defaults. Every threshold and word list of the rules lives here."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import ConfigError
from .model import RULE_IDS, SEVERITIES

LANGUAGES = ("de", "en")
LANGUAGE_SETTINGS = ("de", "en", "auto")

DEFAULT_SEVERITY: dict[str, str] = {
    "BC-01": "error",
    "BC-02": "warning",
    "BC-03": "warning",
    "BC-04": "info",
    "BC-05": "info",
    "BC-06": "warning",
    "BC-07": "warning",
    "BC-08": "warning",
    "BC-09": "error",
    "BC-10": "info",
    "BC-11": "info",
    "BC-12": "info",
}

# Text heuristics of BC-10 and BC-11 may not be raised above warning (KONZEPT.md).
MAX_SEVERITY: dict[str, str] = {"BC-10": "warning", "BC-11": "warning"}

DEFAULT_VAGUE_WORDS: dict[str, list[str]] = {
    "de": ["schnell", "einfach", "benutzerfreundlich", "möglichst", "etc.", "fast"],
    "en": ["fast", "easy", "user-friendly", "etc."],
}

# Regular expressions, matched case-insensitively against title and description.
DEFAULT_BENEFIT_PATTERNS: dict[str, list[str]] = {
    "de": [r"\bdamit\b", r"\bum\b[^.!?\n]*?\bzu\b"],
    "en": [r"\bso that\b", r"\bin order to\b"],
}

DEFAULT_CONJUNCTIONS: dict[str, list[str]] = {"de": ["und"], "en": ["and"]}

# BC-04: the word right after a conjunction must fully match one of these regular expressions
# for the conjunction to join two activities. German verbs in user stories are lower-case
# infinitives; English verbs come from a list of common backlog verbs.
DEFAULT_ACTIVITY_PATTERNS: dict[str, list[str]] = {
    "de": [r"[a-zäöüß]+(?:en|ern|eln)"],
    "en": [
        r"(?i:add|approve|archive|assign|book|borrow|calculate|cancel|change|check|close|"
        r"configure|connect|copy|create|delete|display|download|edit|enter|export|filter|"
        r"generate|import|invite|list|load|log|manage|merge|move|notify|open|pay|print|"
        r"publish|read|register|reject|remove|renew|reserve|reset|restore|return|review|save|"
        r"schedule|search|select|send|share|show|sign|sort|split|submit|sync|track|update|"
        r"upload|validate|verify|view|write)(?:s|es|ed|d|ing)?"
    ],
}

# Unit spelling -> canonical unit. Used by BC-02 (unit present?) and BC-11 (same unit?).
DEFAULT_UNITS: dict[str, dict[str, str]] = {
    "de": {
        "ms": "ms",
        "millisekunde": "ms",
        "millisekunden": "ms",
        "s": "s",
        "sek": "s",
        "sekunde": "s",
        "sekunden": "s",
        "min": "min",
        "minute": "min",
        "minuten": "min",
        "h": "h",
        "std": "h",
        "stunde": "h",
        "stunden": "h",
        "tag": "d",
        "tage": "d",
        "tagen": "d",
        "werktag": "workday",
        "werktage": "workday",
        "werktagen": "workday",
        "woche": "week",
        "wochen": "week",
        "monat": "month",
        "monate": "month",
        "monaten": "month",
        "jahr": "year",
        "jahre": "year",
        "jahren": "year",
        "%": "%",
        "prozent": "%",
        "kb": "kb",
        "mb": "mb",
        "gb": "gb",
        "tb": "tb",
        "px": "px",
        "€": "eur",
        "eur": "eur",
        "euro": "eur",
        "klick": "click",
        "klicks": "click",
        "zeichen": "char",
        "einträge": "entry",
        "einträgen": "entry",
    },
    "en": {
        "ms": "ms",
        "millisecond": "ms",
        "milliseconds": "ms",
        "s": "s",
        "sec": "s",
        "second": "s",
        "seconds": "s",
        "min": "min",
        "minute": "min",
        "minutes": "min",
        "h": "h",
        "hr": "h",
        "hour": "h",
        "hours": "h",
        "day": "d",
        "days": "d",
        "week": "week",
        "weeks": "week",
        "month": "month",
        "months": "month",
        "year": "year",
        "years": "year",
        "%": "%",
        "percent": "%",
        "kb": "kb",
        "mb": "mb",
        "gb": "gb",
        "tb": "tb",
        "px": "px",
        "€": "eur",
        "eur": "eur",
        "euro": "eur",
        "euros": "eur",
        "click": "click",
        "clicks": "click",
        "character": "char",
        "characters": "char",
        "entries": "entry",
    },
}

# Words skipped when BC-11 looks for the term in front of a number.
DEFAULT_TERM_STOPWORDS: dict[str, list[str]] = {
    "de": [
        "ab", "auf", "beträgt", "betragen", "bis", "binnen", "ca", "das", "dem", "den", "der",
        "des", "die", "ein", "eine", "einer", "etwa", "für", "höchstens", "im", "in",
        "innerhalb", "ist", "liegt", "max", "maximal", "mindestens", "mit", "nach", "sind",
        "spätestens", "über", "um", "unter", "vom", "von", "zu",
        "dauert", "erfolgt", "gilt", "gelten", "hat", "haben", "kommt", "kommen", "läuft",
        "wird", "werden",
    ],
    "en": [
        "a", "about", "after", "an", "approximately", "are", "at", "by", "for", "in", "is",
        "least", "less", "max", "maximum", "minimum", "more", "most", "of", "over", "than",
        "the", "to", "under", "up", "within",
        "arrives", "be", "comes", "has", "have", "is", "lasts", "runs", "takes", "will",
    ],
}  # fmt: skip

# Words left out when BC-10 compares titles and descriptions: articles, conjunctions and the
# fixed phrases of a user story.
DEFAULT_SIMILARITY_STOPWORDS: dict[str, list[str]] = {
    "de": [
        "als", "am", "an", "auf", "aus", "bei", "damit", "das", "dem", "den", "der", "des",
        "die", "ein", "eine", "einem", "einen", "einer", "es", "für", "ich", "im", "in", "ist",
        "kann", "können", "mit", "möchte", "oder", "sind", "um", "und", "von", "werden",
        "wird", "zu", "zum", "zur",
    ],
    "en": [
        "a", "an", "and", "as", "at", "be", "by", "can", "for", "from", "i", "in", "is", "it",
        "of", "on", "or", "so", "that", "the", "to", "want", "with",
    ],
}  # fmt: skip

DEFAULT_DONE_STATUSES = ("done", "closed", "erledigt", "abgeschlossen")


@dataclass(frozen=True)
class RuleSettings:
    enabled: bool
    severity: str


@dataclass(frozen=True)
class Config:
    """Validated configuration. Build it with :meth:`from_dict`; unset values use defaults."""

    language: str = "de"
    rules: Mapping[str, RuleSettings] = field(
        default_factory=lambda: {r: RuleSettings(True, DEFAULT_SEVERITY[r]) for r in RULE_IDS}
    )
    max_estimate: float = 13
    max_criteria: int = 8
    estimate_required_top: int = 20
    duplicate_threshold: float = 0.8
    done_statuses: tuple[str, ...] = DEFAULT_DONE_STATUSES
    vague_words: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: _freeze_lists(DEFAULT_VAGUE_WORDS)
    )
    benefit_patterns: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: _freeze_lists(DEFAULT_BENEFIT_PATTERNS)
    )
    conjunctions: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: _freeze_lists(DEFAULT_CONJUNCTIONS)
    )
    activity_patterns: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: _freeze_lists(DEFAULT_ACTIVITY_PATTERNS)
    )
    units: Mapping[str, Mapping[str, str]] = field(
        default_factory=lambda: {lang: dict(units) for lang, units in DEFAULT_UNITS.items()}
    )
    term_stopwords: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: _freeze_lists(DEFAULT_TERM_STOPWORDS)
    )
    similarity_stopwords: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: _freeze_lists(DEFAULT_SIMILARITY_STOPWORDS)
    )
    ignore: tuple[tuple[str, str], ...] = ()
    list_separator: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> Config:
        """Build a configuration from a JSON-like mapping, validating every value."""
        if data is None:
            data = {}
        if not isinstance(data, Mapping):
            raise ConfigError("config.not_an_object")
        unknown = sorted(set(data) - set(_PARSERS))
        if unknown:
            raise ConfigError("config.unknown_key", {"key": unknown[0]})
        values = {key: _PARSERS[key](data[key]) for key in sorted(data)}
        return cls(**values)

    def languages(self) -> tuple[str, ...]:
        """Languages whose word lists and patterns apply."""
        return LANGUAGES if self.language == "auto" else (self.language,)

    def is_done(self, status: str | None) -> bool:
        return status is not None and status.strip().casefold() in {
            s.casefold() for s in self.done_statuses
        }


def _freeze_lists(data: Mapping[str, list[str]]) -> dict[str, tuple[str, ...]]:
    return {lang: tuple(words) for lang, words in data.items()}


def _invalid(key: str, value: Any) -> ConfigError:
    return ConfigError("config.invalid_value", {"key": key, "value": repr(value)})


def _number(key: str, minimum: float, integer: bool = False):
    def parse(value: Any) -> float:
        valid_type = int if integer else (int, float)
        if isinstance(value, bool) or not isinstance(value, valid_type) or value < minimum:
            raise _invalid(key, value)
        return value

    return parse


def _parse_language(value: Any) -> str:
    if value not in LANGUAGE_SETTINGS:
        raise _invalid("language", value)
    return value


def _parse_rules(value: Any) -> dict[str, RuleSettings]:
    if not isinstance(value, Mapping):
        raise _invalid("rules", value)
    result = {r: RuleSettings(True, DEFAULT_SEVERITY[r]) for r in RULE_IDS}
    for rule_id in sorted(value):
        settings = value[rule_id]
        if rule_id not in result:
            raise ConfigError("config.unknown_rule", {"rule": rule_id})
        if not isinstance(settings, Mapping) or set(settings) - {"enabled", "severity"}:
            raise _invalid(f"rules.{rule_id}", settings)
        enabled = settings.get("enabled", True)
        if not isinstance(enabled, bool):
            raise _invalid(f"rules.{rule_id}.enabled", enabled)
        severity = settings.get("severity", DEFAULT_SEVERITY[rule_id])
        if severity not in SEVERITIES:
            raise _invalid(f"rules.{rule_id}.severity", severity)
        limit = MAX_SEVERITY.get(rule_id)
        if limit and SEVERITIES.index(severity) > SEVERITIES.index(limit):
            raise ConfigError(
                "config.severity_too_high", {"rule": rule_id, "severity": severity, "max": limit}
            )
        result[rule_id] = RuleSettings(enabled, severity)
    return result


def _string_list(key: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise _invalid(key, value)
    return tuple(value)


def _per_language(key: str, defaults: Mapping[str, list[str]], check_regex: bool = False):
    def parse(value: Any) -> dict[str, tuple[str, ...]]:
        if not isinstance(value, Mapping) or set(value) - set(LANGUAGES):
            raise _invalid(key, value)
        # ASSUMPTION: a list given for a language replaces the default list of that
        # language; languages not given keep their defaults.
        result = _freeze_lists(defaults)
        for lang in sorted(value):
            result[lang] = _string_list(f"{key}.{lang}", value[lang])
            if check_regex:
                for pattern in result[lang]:
                    try:
                        re.compile(pattern)
                    except re.error:
                        raise _invalid(f"{key}.{lang}", pattern) from None
        return result

    return parse


def _parse_units(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, Mapping) or set(value) - set(LANGUAGES):
        raise _invalid("units", value)
    result = {lang: dict(units) for lang, units in DEFAULT_UNITS.items()}
    for lang in sorted(value):
        units = value[lang]
        if not isinstance(units, Mapping) or not all(
            isinstance(k, str) and k and isinstance(v, str) and v for k, v in units.items()
        ):
            raise _invalid(f"units.{lang}", units)
        result[lang] = {k.casefold(): v for k, v in units.items()}
    return result


def _parse_ignore(value: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise _invalid("ignore", value)
    result = []
    for entry in value:
        if isinstance(entry, Mapping) and set(entry) == {"rule", "item"}:
            pair = (entry["rule"], entry["item"])
        elif isinstance(entry, list) and len(entry) == 2:
            pair = (entry[0], entry[1])
        else:
            raise _invalid("ignore", entry)
        if pair[0] not in RULE_IDS or not isinstance(pair[1], str):
            raise _invalid("ignore", entry)
        result.append(pair)
    return tuple(result)


def _parse_separator(value: Any) -> str | None:
    if value is not None and not (isinstance(value, str) and value):
        raise _invalid("list_separator", value)
    return value


_PARSERS = {
    "language": _parse_language,
    "rules": _parse_rules,
    "max_estimate": _number("max_estimate", 0),
    "max_criteria": _number("max_criteria", 0, integer=True),
    "estimate_required_top": _number("estimate_required_top", 0, integer=True),
    "duplicate_threshold": _number("duplicate_threshold", 0),
    "done_statuses": lambda v: _string_list("done_statuses", v),
    "vague_words": _per_language("vague_words", DEFAULT_VAGUE_WORDS),
    "benefit_patterns": _per_language("benefit_patterns", DEFAULT_BENEFIT_PATTERNS, True),
    "conjunctions": _per_language("conjunctions", DEFAULT_CONJUNCTIONS),
    "activity_patterns": _per_language("activity_patterns", DEFAULT_ACTIVITY_PATTERNS, True),
    "units": _parse_units,
    "term_stopwords": _per_language("term_stopwords", DEFAULT_TERM_STOPWORDS),
    "similarity_stopwords": _per_language("similarity_stopwords", DEFAULT_SIMILARITY_STOPWORDS),
    "ignore": _parse_ignore,
    "list_separator": _parse_separator,
}
