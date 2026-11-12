import json
import re
from pathlib import Path

import pytest

from backlog_check import render
from backlog_check.catalog import format_value, load_catalog
from backlog_check.model import RULE_IDS, SEVERITIES
from helpers import golden_cases

SOURCE = Path(__file__).parent.parent / "src" / "backlog_check"


def _keys_in_source() -> set[str]:
    pattern = re.compile(r"\"((?:bc\d\d|input|config|cli|report)\.[a-z_]+)\"")
    keys = set()
    for path in SOURCE.rglob("*.py"):
        keys.update(pattern.findall(path.read_text(encoding="utf-8")))
    return keys


def test_catalogs_have_the_same_keys():
    assert set(load_catalog("de")) == set(load_catalog("en"))


@pytest.mark.parametrize("language", ["de", "en"])
def test_every_key_used_in_code_exists(language):
    keys = _keys_in_source()
    assert len(keys) > 30
    catalog = load_catalog(language)
    assert sorted(keys - set(catalog)) == []
    for rule in RULE_IDS:
        assert f"rule.{rule}" in catalog
    for severity in SEVERITIES:
        assert f"severity.{severity}" in catalog


@pytest.mark.parametrize("language", ["de", "en"])
@pytest.mark.parametrize("rule", RULE_IDS)
def test_golden_findings_render_without_missing_params(language, rule):
    for case in golden_cases(rule):
        for finding in case["expected"]:
            text = render(finding["message_key"], finding["params"], language)
            assert "{" not in text


def test_placeholders_match_between_languages():
    de, en = load_catalog("de"), load_catalog("en")
    placeholder = re.compile(r"\{(\w+)\}")
    for key in de:
        assert set(placeholder.findall(de[key])) == set(placeholder.findall(en[key])), key


def test_format_value():
    assert format_value(0.89, "de") == "0,89"
    assert format_value(0.89, "en") == "0.89"
    assert format_value(["A", "B"], "de") == "A, B"
    assert format_value(13, "de") == "13"


def test_render_and_unknown_language():
    assert render("bc02.unmeasurable", {"word": "schnell"}, "de").startswith(
        "Das Kriterium enthält „schnell“"
    )
    with pytest.raises(ValueError):
        load_catalog("fr")


def test_catalog_files_are_valid_json():
    for language in ("de", "en"):
        path = SOURCE / "catalogs" / f"{language}.json"
        assert json.loads(path.read_text(encoding="utf-8"))
