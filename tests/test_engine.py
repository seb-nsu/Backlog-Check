from backlog_check import Config, check
from backlog_check.context import Context, has_unit, text_fields, word_pattern
from backlog_check.model import Finding, Item


def test_check_accepts_mappings_and_config_objects():
    rules = {f"BC-{n:02d}": {"enabled": False} for n in range(1, 13)}
    assert check([{"id": "A", "kind": "epic", "title": "T"}], {"rules": rules}) == []
    assert check([], Config()) == []


def test_finding_to_dict_has_fixed_key_order():
    finding = Finding(
        rule="BC-02",
        severity="warning",
        item="A",
        message_key="bc02.unmeasurable",
        params={"word": "schnell", "a": 1},
        field="acceptance_criteria[0]",
        span=(4, 11),
    )
    data = finding.to_dict()
    assert list(data) == [
        "rule", "severity", "item", "related", "field", "span", "message_key", "params",
    ]  # fmt: skip
    assert list(data["params"]) == ["a", "word"]
    assert data["span"] == [4, 11]
    assert Finding("BC-01", "error", "A", "bc01.missing").to_dict()["span"] is None


def test_context_language_lists():
    items = [Item(id="A", kind="story", title="T", status="Done"), Item("B", "bug", "U")]
    ctx = Context(items, Config.from_dict({"language": "auto"}))
    assert [i.id for i in ctx.active] == ["B"]
    assert ctx.vague_words.count("fast") == 1
    assert "easy" in ctx.vague_words and "schnell" in ctx.vague_words
    assert ctx.units["tage"] == "d" and ctx.units["days"] == "d"
    assert "the" in ctx.term_stopwords and "von" in ctx.term_stopwords
    finding = ctx.finding("BC-01", items[1], "bc01.missing")
    assert (finding.severity, finding.item) == ("error", "B")


def test_text_fields_and_word_pattern():
    item = Item("A", "story", "T", "D", ("x", "y"))
    assert [f.name for f in text_fields(item)] == [
        "title", "description", "acceptance_criteria[0]", "acceptance_criteria[1]",
    ]  # fmt: skip
    assert word_pattern("etc.").search("Farben, Formen etc. sind")
    assert not word_pattern("fast").search("fast-track")
    assert word_pattern("Fast").search("Ist fast fertig")
    assert word_pattern("%").search("5 %")


def test_context_children_and_units():
    items = [Item("E", "epic", "Epic"), Item("A", "story", "T", parent="E"), Item("B", "bug", "U")]
    ctx = Context(items, Config())
    assert ctx.children == {"E": ["A"]}
    assert has_unit("in drei Sekunden", ctx.units)
    assert has_unit("unter 5 %", ctx.units)
    assert not has_unit("it's easy", Context([], Config.from_dict({"language": "en"})).units)
