"""Improvement suggestions (one per finding) and templates for new items."""

import json
import re

import pytest

from backlog_check import Config, ConfigError, Finding, check, render, suggest, template
from backlog_check.catalog import load_catalog
from backlog_check.model import KINDS, RULE_IDS
from backlog_check.suggest import SUGGESTERS, _share_object
from helpers import GOLDEN_DIR

CASES = json.loads((GOLDEN_DIR / "suggestions.json").read_text(encoding="utf-8"))["cases"]
FINDING_KEY = re.compile(r"\"(bc\d\d\.[a-z_]+)\"")


def _config(case):
    rule = case["rule"]
    rules = {r: {"enabled": r == rule} for r in RULE_IDS}
    return {"language": case["language"], **case.get("config", {}), "rules": rules}


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_suggestions_golden(case):
    config = _config(case)
    findings = check(case["items"], config)
    suggestions = suggest(case["items"], findings, config)
    assert [s.to_dict() for s in suggestions] == case["expected"]
    assert [(s.rule, s.item, s.field) for s in suggestions] == [
        (f.rule, f.item, f.field) for f in findings
    ]


@pytest.mark.parametrize("rule", RULE_IDS)
def test_every_rule_has_suggestion_cases_in_both_languages(rule):
    languages = {c["language"] for c in CASES if c["rule"] == rule and c["expected"]}
    assert languages == {"de", "en"}


def test_every_finding_key_has_a_suggester_and_all_are_covered():
    source = "".join(
        p.read_text(encoding="utf-8")
        for p in (GOLDEN_DIR.parent.parent / "src" / "backlog_check" / "rules").glob("bc*.py")
    )
    assert set(FINDING_KEY.findall(source)) == set(SUGGESTERS)
    covered = {e["message_key"] for c in CASES for e in c["expected"]}
    keys_de = {k for k in load_catalog("de") if ".fix_" in k}
    assert covered == keys_de


@pytest.mark.parametrize("language", ["de", "en"])
def test_suggestions_render_without_missing_params(language):
    for case in CASES:
        for suggestion in case["expected"]:
            text = render(suggestion["message_key"], suggestion["params"], language)
            assert "{" not in text


def test_suggest_accepts_default_config_and_mappings():
    items = [{"id": "A", "kind": "story", "title": "T"}]
    findings = check(items)
    assert suggest(items, findings)[0].message_key == "bc01.fix_missing"


def test_bc03_split_criteria_with_threshold_zero():
    items = [{"id": "A", "kind": "story", "title": "T", "acceptance_criteria": ["x"]}]
    finding = Finding(
        "BC-03", "warning", "A", "bc03.too_many_criteria", {"count": 1, "max_criteria": 0}
    )
    assert suggest(items, [finding])[0].params == {"parts": 2, "max_criteria": 0}


def test_bc04_share_object_depends_on_language():
    assert _share_object(["Rechnung", "erstellen"], ["versenden"], "de") == (
        "Rechnung erstellen",
        "Rechnung versenden",
    )
    assert _share_object(["export"], ["print", "report"], "en") == ("export report", "print report")
    assert _share_object(["import", "data"], ["validate"], "en") == ("import data", "validate data")
    assert _share_object(["import", "data"], ["validate"], "auto") == ("import data", "validate")
    assert _share_object(["a", "b"], ["c", "d"], "en") == ("a b", "c d")


def test_bc12_candidate_ignores_done_epics_and_words_in_common_only():
    items = [
        {"id": "E1", "kind": "epic", "title": "Profil pflegen", "status": "done"},
        {"id": "E2", "kind": "epic", "title": "Rechnung"},
        {"id": "S1", "kind": "story", "title": "Profil ändern"},
        {"id": "S2", "kind": "story", "title": "Rechnung drucken"},
    ]
    config = {"rules": {r: {"enabled": r == "BC-12"} for r in RULE_IDS}}
    keys = [(s.item, s.message_key, s.params) for s in suggest(items, check(items, config), config)]
    assert keys == [
        ("E2", "bc12.fix_add_stories", {}),
        ("S1", "bc12.fix_assign_epic", {}),
        ("S2", "bc12.fix_assign_epic_candidate", {"epic": "E2"}),
    ]


def test_measurable_hints_config():
    config = Config.from_dict({"measurable_hints": {"de": {"Zügig": "binnen <n> Minuten"}}})
    assert config.measurable_hints["de"] == {"zügig": "binnen <n> Minuten"}
    assert config.measurable_hints["en"]["fast"] == "within <n> seconds"
    items = [{"id": "A", "kind": "story", "title": "T", "acceptance_criteria": ["Es ist zügig."]}]
    cfg = {
        "vague_words": {"de": ["zügig"]},
        "measurable_hints": {"de": {"zügig": "binnen <n> Minuten"}},
    }
    hint = next(s for s in suggest(items, check(items, cfg), cfg) if s.rule == "BC-02")
    assert hint.params == {"word": "zügig", "hint": "binnen <n> Minuten"}
    for bad in ([], {"fr": {}}, {"de": []}, {"de": {"x": ""}}):
        with pytest.raises(ConfigError):
            Config.from_dict({"measurable_hints": bad})


def test_auto_language_finds_hint_in_second_language():
    items = [{"id": "A", "kind": "story", "title": "T", "acceptance_criteria": ["It is easy."]}]
    config = {"language": "auto"}
    hint = next(s for s in suggest(items, check(items, config), config) if s.rule == "BC-02")
    assert hint.params == {"word": "easy", "hint": "in at most <n> clicks"}


@pytest.mark.parametrize("language", ["de", "en"])
@pytest.mark.parametrize("kind", KINDS)
def test_template_passes_the_content_rules(kind, language):
    item = template(kind, language)
    assert item["kind"] == kind
    findings = check([item], {"language": language})
    # BC-16 flags the placeholders until they are filled in; apart from that, the only
    # finding allowed for a template on its own is an epic without stories.
    assert {f.field for f in findings if f.rule == "BC-16"} == {
        "title",
        "description",
        *(f"acceptance_criteria[{n}]" for n in range(len(item.get("acceptance_criteria", [])))),
    } - ({"acceptance_criteria[1]"} if kind == "bug" else set())
    assert [f.message_key for f in findings if f.rule != "BC-16"] == (
        ["bc12.epic_without_stories"] if kind == "epic" else []
    )


def test_template_with_epic_and_story_and_unknown_kind():
    epic, story = template("epic", "de"), template("story", "de")
    story["parent"] = epic["id"]
    assert check([epic, story], {"rules": {"BC-16": {"enabled": False}}}) == []
    with pytest.raises(ValueError):
        template("task", "de")
