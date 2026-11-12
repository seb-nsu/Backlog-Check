import json

import pytest

from backlog_check import InputError, Item, load_csv, load_file, load_json, to_items
from backlog_check.reader import detect_delimiter, split_list


def _error(func, *args, **kwargs) -> InputError:
    with pytest.raises(InputError) as info:
        func(*args, **kwargs)
    return info.value


def test_json_full_record():
    text = json.dumps(
        [
            {
                "id": "A-1",
                "kind": "Story",
                "title": " Login ",
                "description": "Text",
                "acceptance_criteria": ["one", " ", "two"],
                "estimate": 5.0,
                "priority": "MUST",
                "rank": 1,
                "status": "open",
                "depends_on": ["A-2", 7],
                "parent": "E-1",
                "extra": "ignored",
            },
            {"id": 7, "kind": "bug", "title": "Crash", "estimate": 2.5, "parent": 3},
        ]
    )
    first, second = load_json(text)
    assert first == Item(
        id="A-1",
        kind="story",
        title="Login",
        description="Text",
        acceptance_criteria=("one", "two"),
        estimate=5,
        priority="must",
        rank=1,
        status="open",
        depends_on=("A-2", "7"),
        parent="E-1",
    )
    assert isinstance(first.estimate, int)
    assert second == Item(id="7", kind="bug", title="Crash", estimate=2.5, parent="3")


def test_json_empty_values():
    text = '[{"id": "A", "kind": "epic", "title": "T", "description": null, "estimate": "",'
    text += ' "rank": "", "priority": " ", "status": "", "depends_on": null}]'
    (item,) = load_json(text)
    assert item == Item(id="A", kind="epic", title="T")


def test_json_lines_of_elements():
    text = '﻿[\n  {"id": "A", "kind": "story", "title": "T"},\n\n  {"id": "A",\n'
    text += '   "kind": "story", "title": "U"}\n]'
    error = _error(load_json, text)
    assert (error.message_key, error.params, error.line) == (
        "input.duplicate_id",
        {"id": "A", "first_line": 2},
        4,
    )


def test_json_empty_array_and_compact_layout():
    assert load_json("[]") == []
    items = load_json('[{"id":"A","kind":"bug","title":"T"},{"id":"B","kind":"bug","title":"T"}]')
    assert [i.id for i in items] == ["A", "B"]


def test_json_syntax_error_has_line():
    error = _error(load_json, '[\n{"id": "A",\n]')
    assert error.message_key == "input.json_syntax"
    assert error.line == 3


def test_json_not_a_list():
    assert _error(load_json, '{"id": "A"}').message_key == "input.not_a_list"


def test_json_element_not_an_object():
    error = _error(load_json, '[\n  {"id": "A", "kind": "bug", "title": "T"},\n  "text"\n]')
    assert (error.message_key, error.line) == ("input.not_an_object", 3)


def test_json_mapping():
    text = '[{"key": "A", "Summary": "T", "kind": "story"}]'
    (item,) = load_json(text, {"key": "id", "Summary": "title"})
    assert (item.id, item.title) == ("A", "T")


def test_json_mapping_conflict():
    text = '[{"key": "A", "id": "B", "kind": "story", "title": "T"}]'
    error = _error(load_json, text, {"key": "id"})
    assert (error.message_key, error.params, error.line) == (
        "input.duplicate_column",
        {"field": "id"},
        1,
    )


@pytest.mark.parametrize(
    ("record", "key", "params"),
    [
        ({"kind": "story", "title": "T"}, "input.missing_field", {"field": "id"}),
        ({"id": " ", "kind": "story", "title": "T"}, "input.missing_field", {"field": "id"}),
        ({"id": "A", "title": "T"}, "input.missing_field", {"field": "kind"}),
        ({"id": "A", "kind": "story", "title": ""}, "input.missing_field", {"field": "title"}),
        ({"id": "A", "kind": "task", "title": "T"}, "input.unknown_kind", {"kind": "task"}),
        ({"id": "A", "kind": 3, "title": "T"}, "input.invalid_value", {"field": "kind"}),
        ({"id": True, "kind": "bug", "title": "T"}, "input.invalid_value", {"field": "id"}),
        ({"id": "A", "kind": "bug", "title": 5}, "input.invalid_value", {"field": "title"}),
        (
            {"id": "A", "kind": "bug", "title": "T", "description": 5},
            "input.invalid_value",
            {"field": "description"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "acceptance_criteria": "x"},
            "input.invalid_value",
            {"field": "acceptance_criteria"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "acceptance_criteria": [1]},
            "input.invalid_value",
            {"field": "acceptance_criteria"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "depends_on": [None]},
            "input.invalid_value",
            {"field": "depends_on"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "estimate": "5"},
            "input.invalid_value",
            {"field": "estimate"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "estimate": -1},
            "input.invalid_value",
            {"field": "estimate"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "estimate": True},
            "input.invalid_value",
            {"field": "estimate"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "priority": "high"},
            "input.invalid_value",
            {"field": "priority"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "rank": 0},
            "input.invalid_value",
            {"field": "rank"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "rank": 1.5},
            "input.invalid_value",
            {"field": "rank"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "rank": False},
            "input.invalid_value",
            {"field": "rank"},
        ),
        (
            {"id": "A", "kind": "bug", "title": "T", "parent": []},
            "input.invalid_value",
            {"field": "parent"},
        ),
    ],
)
def test_json_invalid_records(record, key, params):
    error = _error(load_json, json.dumps([record]))
    assert error.message_key == key
    assert {k: error.params[k] for k in params} == params
    assert error.line == 1


CSV_TEXT = (
    "id,kind,title,acceptance_criteria,estimate,rank,depends_on,priority,unknown\n"
    'S-1,story,Login,"first\nsecond|third",2,1,S-2|S-3,should,x\n'
    "\n"
    'S-2,bug,Crash,,"2,5",,,,\n'
    "S-3,epic,Area\n"
)


def test_csv_reads_rows_lists_and_numbers():
    s1, s2, s3 = load_csv(CSV_TEXT)
    assert s1 == Item(
        id="S-1",
        kind="story",
        title="Login",
        acceptance_criteria=("first", "second", "third"),
        estimate=2,
        rank=1,
        depends_on=("S-2", "S-3"),
        priority="should",
    )
    assert s2 == Item(id="S-2", kind="bug", title="Crash", estimate=2.5)
    assert s3 == Item(id="S-3", kind="epic", title="Area")


def test_csv_line_numbers_count_multiline_cells():
    text = CSV_TEXT + "S-1,story,Again\n"
    error = _error(load_csv, text)
    assert (error.message_key, error.line) == ("input.duplicate_id", 7)
    assert error.params == {"id": "S-1", "first_line": 2}


def test_csv_custom_separator_and_delimiter():
    text = "id;kind;title;acceptance_criteria\nA;story;T;a, b|c\n"
    (item,) = load_csv(text, separator=",")
    assert item.acceptance_criteria == ("a", "b|c")
    (item,) = load_csv(text.replace(";", "\t"), delimiter="\t", separator=",")
    assert item.acceptance_criteria == ("a", "b|c")


def test_csv_mapping():
    text = "Issue key,Summary,Issue Type\nP-1,Do it,Story\n"
    (item,) = load_csv(text, {"Issue key": "id", "Summary": "title", "Issue Type": "kind"})
    assert (item.id, item.title, item.kind) == ("P-1", "Do it", "story")


@pytest.mark.parametrize(
    ("text", "key", "line"),
    [
        ("", "input.empty", 1),
        ("id,title\nA,T\n", "input.missing_column", 1),
        ("id,id,kind,title\n", "input.duplicate_column", 1),
        ("id,kind,title\nA,story,\n", "input.missing_field", 2),
        ("id,kind,title,estimate\nA,story,T,many\n", "input.invalid_value", 2),
        ("id,kind,title,rank\nA,story,T,first\n", "input.invalid_value", 2),
        ('id,kind,title\nA,story,"T\n', "input.csv_syntax", 2),
    ],
)
def test_csv_invalid(text, key, line):
    error = _error(load_csv, text)
    assert (error.message_key, error.line) == (key, line)


def test_detect_delimiter():
    assert detect_delimiter("a,b,c\n") == ","
    assert detect_delimiter("a;b;c\nx,y,z,w\n") == ";"
    assert detect_delimiter("a\tb\n") == "\t"
    assert detect_delimiter("single") == ","


def test_split_list():
    assert split_list("a|b\nc") == ["a", "b", "c"]
    assert split_list("a|b;c", ";") == ["a|b", "c"]


def test_load_file(tmp_path):
    json_file = tmp_path / "b.JSON"
    json_file.write_text('[{"id": "A", "kind": "bug", "title": "T"}]', encoding="utf-8")
    assert load_file(json_file)[0].id == "A"
    csv_file = tmp_path / "b.csv"
    csv_file.write_text("﻿Key,kind,title\nB,bug,T\n", encoding="utf-8")
    assert load_file(csv_file, {"Key": "id"})[0].id == "B"


def test_load_file_errors(tmp_path):
    assert _error(load_file, tmp_path / "b.xlsx").message_key == "input.unknown_format"
    assert _error(load_file, tmp_path / "missing.csv").message_key == "input.file_not_found"
    broken = tmp_path / "broken.csv"
    broken.write_bytes(b"id,kind,title\n\xff\xfe,bug,T\n")
    assert _error(load_file, broken).message_key == "input.encoding"


def test_to_items_accepts_items_and_mappings():
    item = Item(id="A", kind="bug", title="T")
    assert to_items([item, {"id": "B", "kind": "bug", "title": "U"}])[0] is item
    error = _error(to_items, [item, {"id": "A", "kind": "bug", "title": "U"}])
    assert (error.message_key, error.line) == ("input.duplicate_id", 2)


def test_error_string_contains_key():
    assert "input.empty" in str(_error(load_csv, " "))
