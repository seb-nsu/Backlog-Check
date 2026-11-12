import pytest

from backlog_check import Config, ConfigError
from backlog_check.config import DEFAULT_SEVERITY, RuleSettings


def _error(data) -> ConfigError:
    with pytest.raises(ConfigError) as info:
        Config.from_dict(data)
    return info.value


def test_defaults():
    config = Config.from_dict(None)
    assert config == Config()
    assert config.language == "de"
    assert config.languages() == ("de",)
    assert config.max_estimate == 13
    assert config.max_criteria == 8
    assert config.estimate_required_top == 20
    assert config.duplicate_threshold == 0.8
    assert config.rules["BC-01"] == RuleSettings(True, "error")
    assert {r: s.severity for r, s in config.rules.items()} == DEFAULT_SEVERITY
    assert "schnell" in config.vague_words["de"]
    assert "user-friendly" in config.vague_words["en"]


def test_overrides():
    config = Config.from_dict(
        {
            "language": "auto",
            "rules": {"BC-02": {"enabled": False}, "BC-10": {"severity": "warning"}},
            "max_estimate": 8.5,
            "max_criteria": 5,
            "estimate_required_top": 0,
            "duplicate_threshold": 0.5,
            "done_statuses": ["fertig"],
            "vague_words": {"de": ["zügig"]},
            "benefit_patterns": {"en": ["benefit"]},
            "conjunctions": {"de": ["sowie"]},
            "units": {"en": {"Pages": "page"}},
            "term_stopwords": {"en": ["the"]},
            "ignore": [["BC-01", "A"], {"rule": "BC-02", "item": "B"}],
            "list_separator": ";",
        }
    )
    assert config.languages() == ("de", "en")
    assert config.rules["BC-02"] == RuleSettings(False, "warning")
    assert config.rules["BC-10"] == RuleSettings(True, "warning")
    assert config.rules["BC-01"] == RuleSettings(True, "error")
    assert config.vague_words == {"de": ("zügig",), "en": ("fast", "easy", "user-friendly", "etc.")}
    assert config.units["en"] == {"pages": "page"}
    assert "tage" in config.units["de"]
    assert config.ignore == (("BC-01", "A"), ("BC-02", "B"))
    assert config.is_done(" Fertig ")
    assert not config.is_done("done")
    assert not config.is_done(None)


@pytest.mark.parametrize(
    ("data", "key"),
    [
        ([], "config.not_an_object"),
        ({"colour": 1}, "config.unknown_key"),
        ({"language": "fr"}, "config.invalid_value"),
        ({"rules": []}, "config.invalid_value"),
        ({"rules": {"BC-13": {}}}, "config.unknown_rule"),
        ({"rules": {"BC-01": True}}, "config.invalid_value"),
        ({"rules": {"BC-01": {"enable": True}}}, "config.invalid_value"),
        ({"rules": {"BC-01": {"enabled": "yes"}}}, "config.invalid_value"),
        ({"rules": {"BC-01": {"severity": "fatal"}}}, "config.invalid_value"),
        ({"rules": {"BC-10": {"severity": "error"}}}, "config.severity_too_high"),
        ({"rules": {"BC-11": {"severity": "error"}}}, "config.severity_too_high"),
        ({"max_estimate": -1}, "config.invalid_value"),
        ({"max_estimate": "13"}, "config.invalid_value"),
        ({"max_criteria": 2.5}, "config.invalid_value"),
        ({"estimate_required_top": True}, "config.invalid_value"),
        ({"done_statuses": "done"}, "config.invalid_value"),
        ({"done_statuses": [""]}, "config.invalid_value"),
        ({"vague_words": ["x"]}, "config.invalid_value"),
        ({"vague_words": {"fr": ["x"]}}, "config.invalid_value"),
        ({"benefit_patterns": {"de": ["("]}}, "config.invalid_value"),
        ({"units": []}, "config.invalid_value"),
        ({"units": {"de": {"x": 1}}}, "config.invalid_value"),
        ({"units": {"de": []}}, "config.invalid_value"),
        ({"ignore": {}}, "config.invalid_value"),
        ({"ignore": [["BC-01"]]}, "config.invalid_value"),
        ({"ignore": [["BC-99", "A"]]}, "config.invalid_value"),
        ({"ignore": [["BC-01", 1]]}, "config.invalid_value"),
        ({"list_separator": ""}, "config.invalid_value"),
    ],
)
def test_invalid(data, key):
    assert _error(data).message_key == key


def test_list_separator_none_is_default():
    assert Config.from_dict({"list_separator": None}).list_separator is None
