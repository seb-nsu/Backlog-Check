"""Custom rules defined in the configuration (custom_rules)."""

import io
import json

import pytest

from backlog_check import Config, ConfigError, check, render, suggest, summarize
from backlog_check.cli import main

TICKET = {
    "id": "TEAM-01",
    "pattern": r"\bASAP\b",
    "title": {"de": "Dringlichkeit ohne Termin", "en": "Urgency without a date"},
    "message": {"de": "„{text}“ nennt keinen Termin.", "en": '"{text}" names no date.'},
    "suggestion": {
        "de": "Nenne ein Datum statt „{text}“.",
        "en": 'Give a date instead of "{text}".',
    },
}
REQUIRE = {
    "id": "TEAM-02",
    "pattern": r"(?i)dsgvo|gdpr",
    "mode": "require",
    "fields": ["acceptance_criteria"],
    "kinds": ["story"],
    "severity": "info",
    "title": {"de": "Datenschutz fehlt"},
    "message": {"de": "Kein Kriterium nennt die DSGVO."},
}
ITEMS = [
    {
        "id": "S-1",
        "kind": "story",
        "title": "Export ASAP",
        "description": "Bitte ASAP liefern.",
        "acceptance_criteria": ["Der Export enthält alle Felder.", "ASAP"],
    },
    {"id": "S-2", "kind": "story", "title": "Löschen", "acceptance_criteria": ["Gemäß DSGVO."]},
    {"id": "B-1", "kind": "bug", "title": "Absturz"},
    {"id": "S-3", "kind": "story", "title": "ASAP", "status": "done"},
]
ONLY_CUSTOM = {r: {"enabled": False} for r in Config().rules}


def _config(*rules, **extra):
    return {"rules": ONLY_CUSTOM, "custom_rules": list(rules), **extra}


def _pairs(findings):
    return [(f.rule, f.item, f.field, f.span, f.params) for f in findings]


def test_forbid_one_finding_per_field_at_first_match():
    findings = check(ITEMS, _config(TICKET))
    assert _pairs(findings) == [
        ("TEAM-01", "S-1", "title", (7, 11), {"text": "ASAP"}),
        ("TEAM-01", "S-1", "description", (6, 10), {"text": "ASAP"}),
        ("TEAM-01", "S-1", "acceptance_criteria[1]", (0, 4), {"text": "ASAP"}),
    ]
    assert {f.severity for f in findings} == {"warning"}
    assert findings[0].message_key == "custom.TEAM-01"


def test_require_with_kinds_and_single_field():
    findings = check(ITEMS, _config(REQUIRE))
    assert _pairs(findings) == [("TEAM-02", "S-1", "acceptance_criteria", None, {})]
    assert findings[0].severity == "info"


def test_require_over_several_fields_names_no_field():
    rule = {**REQUIRE, "fields": ["title", "description"], "kinds": ["bug", "story"]}
    found = _pairs(check(ITEMS, _config(rule)))
    assert found == [
        ("TEAM-02", "S-1", None, None, {}),
        ("TEAM-02", "S-2", None, None, {}),
        ("TEAM-02", "B-1", None, None, {}),
    ]


def test_fields_restrict_forbid_and_disabled_rule_is_silent():
    rule = {**TICKET, "fields": ["description"]}
    assert [f.field for f in check(ITEMS, _config(rule))] == ["description"]
    assert check(ITEMS, _config({**TICKET, "enabled": False})) == []


def test_findings_sort_with_builtin_rules_and_ignore_works():
    findings = check(ITEMS[:1], {"custom_rules": [TICKET]})
    assert [f.rule for f in findings] == sorted(f.rule for f in findings)
    ignored = check(ITEMS[:1], _config(TICKET, ignore=[["TEAM-01", "S-1"]]))
    assert ignored == []
    one = {"rule": "TEAM-01", "item": "S-1", "field": "title"}
    assert len(check(ITEMS[:1], _config(TICKET, ignore=[one]))) == 2


def test_summary_counts_custom_rules_after_builtin_rules():
    config = {"custom_rules": [TICKET, REQUIRE]}
    findings = check(ITEMS, config)
    by_rule = list(summarize(ITEMS, findings, config)["by_rule"])
    assert by_rule[-2:] == ["TEAM-01", "TEAM-02"]


def test_texts_and_render_with_language_fallback():
    config = Config.from_dict({"custom_rules": [TICKET, REQUIRE]})
    assert config.rule_ids()[-2:] == ("TEAM-01", "TEAM-02")
    en = config.texts("en")
    assert en["rule.TEAM-02"] == "Datenschutz fehlt"  # only German given
    assert "custom.TEAM-02.fix" not in en
    assert render("custom.TEAM-01", {"text": "ASAP"}, "en", en) == '"ASAP" names no date.'
    assert render("bc01.missing", {}, "en", en) == render("bc01.missing", {}, "en")


def test_suggestions_for_custom_rules():
    config = _config(TICKET, REQUIRE)
    findings = check(ITEMS, config)
    hints = suggest(ITEMS, findings, config)
    assert [(h.message_key, h.params) for h in hints] == [
        ("custom.TEAM-01.fix", {"text": "ASAP"}),
        ("custom.TEAM-01.fix", {"text": "ASAP"}),
        ("custom.TEAM-01.fix", {"text": "ASAP"}),
        ("custom.no_suggestion", {}),
    ]


@pytest.mark.parametrize(
    ("rule", "key"),
    [
        ("x", "custom_rules[0]"),
        ({"id": "A-1", "pattern": "x", "title": {"de": "T"}}, "custom_rules[0]"),
        ({**TICKET, "id": "BC-20"}, "custom_rules[0].id"),
        ({**TICKET, "id": "bc-20"}, "custom_rules[0].id"),
        ({**TICKET, "id": "TEAM"}, "custom_rules[0].id"),
        ({**TICKET, "id": 1}, "custom_rules[0].id"),
        ({**TICKET, "pattern": "("}, "custom_rules[0].pattern"),
        ({**TICKET, "pattern": ""}, "custom_rules[0].pattern"),
        ({**TICKET, "pattern": "x*"}, "custom_rules[0].pattern"),
        ({**TICKET, "pattern": 3}, "custom_rules[0].pattern"),
        ({**TICKET, "mode": "warn"}, "custom_rules[0].mode"),
        ({**TICKET, "fields": ["status"]}, "custom_rules[0].fields"),
        ({**TICKET, "fields": []}, "custom_rules[0].fields"),
        ({**TICKET, "kinds": "story"}, "custom_rules[0].kinds"),
        ({**TICKET, "severity": "fatal"}, "custom_rules[0].severity"),
        ({**TICKET, "enabled": "yes"}, "custom_rules[0].enabled"),
        ({**TICKET, "title": {}}, "custom_rules[0].title"),
        ({**TICKET, "title": {"fr": "T"}}, "custom_rules[0].title"),
        ({**TICKET, "title": {"de": ""}}, "custom_rules[0].title"),
        ({**TICKET, "title": "T"}, "custom_rules[0].title"),
        ({**TICKET, "message": {"de": "{word}"}}, "custom_rules[0].message.de"),
        ({**TICKET, "message": {"de": "{0}"}}, "custom_rules[0].message.de"),
        ({**TICKET, "message": {"de": "{text"}}, "custom_rules[0].message.de"),
        ({**TICKET, "message": {"de": "{text.x}"}}, "custom_rules[0].message.de"),
        ({**REQUIRE, "message": {"de": "{text}"}}, "custom_rules[0].message.de"),
        ({**TICKET, "suggestion": {"en": "{x}"}}, "custom_rules[0].suggestion.en"),
    ],
)
def test_invalid_custom_rules(rule, key):
    with pytest.raises(ConfigError) as info:
        Config.from_dict({"custom_rules": [rule]})
    assert info.value.message_key == "config.invalid_value"
    assert info.value.params["key"] == key


def test_invalid_custom_rule_list_duplicates_and_unknown_keys():
    with pytest.raises(ConfigError) as info:
        Config.from_dict({"custom_rules": {}})
    assert info.value.params["key"] == "custom_rules"
    with pytest.raises(ConfigError) as info:
        Config.from_dict({"custom_rules": [TICKET, TICKET]})
    assert info.value.params["key"] == "custom_rules[1].id"
    with pytest.raises(ConfigError) as info:
        Config.from_dict({"custom_rules": [{**TICKET, "colour": 1}]})
    assert info.value.message_key == "config.unknown_key"
    assert info.value.params == {"key": "custom_rules[0].colour"}
    with pytest.raises(ConfigError) as info:
        Config.from_dict({"custom_rules": [TICKET], "ignore": [["TEAM-09", "S-1"]]})
    assert info.value.message_key == "config.invalid_value"


def test_field_and_kind_order_does_not_depend_on_the_file():
    rule = {**TICKET, "fields": ["description", "title"], "kinds": ["story", "epic"]}
    parsed = Config.from_dict({"custom_rules": [rule]}).custom_rules[0]
    assert parsed.fields == ("title", "description")
    assert parsed.kinds == ("epic", "story")


@pytest.mark.parametrize("fmt", ["text", "markdown", "csv", "json", "sarif"])
def test_command_line_renders_custom_rules(tmp_path, fmt):
    backlog = tmp_path / "b.json"
    backlog.write_text(json.dumps(ITEMS[:1]), "utf-8")
    config = tmp_path / "c.json"
    config.write_text(json.dumps(_config(TICKET, REQUIRE)), "utf-8")
    out = io.StringIO()
    code = main([str(backlog), "--config", str(config), "--format", fmt, "--suggest"], out)
    assert code == 0
    text = out.getvalue()
    if fmt == "json":
        assert json.loads(text)["summary"]["by_rule"] == {
            "TEAM-01": {"warning": 3},
            "TEAM-02": {"info": 1},
        }
    elif fmt == "sarif":
        run = json.loads(text)["runs"][0]
        rules = run["tool"]["driver"]["rules"]
        assert [r["id"] for r in rules[-2:]] == ["TEAM-01", "TEAM-02"]
        assert rules[-1]["defaultConfiguration"] == {"level": "note", "enabled": True}
        assert run["results"][0]["ruleIndex"] == len(rules) - 2
        assert run["results"][0]["message"]["text"] == "„ASAP“ nennt keinen Termin."
    else:
        assert "„ASAP“ nennt keinen Termin." in text
        assert "Nenne ein Datum statt „ASAP“." in text
        assert "Für diese eigene Regel ist kein Vorschlag hinterlegt." in text
        if fmt != "csv":
            assert "Dringlichkeit ohne Termin" in text
