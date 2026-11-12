"""Text catalogs (German and English) that turn message keys and params into sentences."""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

CATALOG_LANGUAGES = ("de", "en")


@cache
def load_catalog(language: str) -> dict[str, str]:
    """Return the catalog of ``language`` ("de" or "en")."""
    if language not in CATALOG_LANGUAGES:
        raise ValueError(f"no catalog for language {language!r}")
    text = resources.files(__package__).joinpath(f"catalogs/{language}.json").read_text("utf-8")
    return json.loads(text)


def format_value(value: Any, language: str) -> str:
    """Format a parameter: lists joined by commas, decimal comma in German."""
    if isinstance(value, list | tuple):
        return ", ".join(format_value(v, language) for v in value)
    if isinstance(value, float):
        text = repr(value)
        return text.replace(".", ",") if language == "de" else text
    return str(value)


def render(message_key: str, params: dict[str, Any], language: str) -> str:
    """Build the sentence for ``message_key`` from the catalog of ``language``."""
    template = load_catalog(language)[message_key]
    return template.format(**{key: format_value(v, language) for key, v in params.items()})
