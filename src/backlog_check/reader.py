"""Reading and validating backlogs from JSON and CSV.

Invalid input raises :class:`InputError` with the line of the offending entry.
"""

from __future__ import annotations

import csv
import datetime
import io
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import InputError
from .model import KINDS, PRIORITIES, Item
from .presets import Preset

FIELDS = (
    "id",
    "kind",
    "title",
    "description",
    "acceptance_criteria",
    "estimate",
    "priority",
    "rank",
    "status",
    "depends_on",
    "parent",
    "updated",
)
REQUIRED = ("id", "kind", "title")
LIST_FIELDS = ("acceptance_criteria", "depends_on")
DEFAULT_LIST_SEPARATORS = ("\n", "|")
CSV_DELIMITERS = (",", ";", "\t")


def build_items(records: Iterable[tuple[int, Mapping[str, Any]]]) -> list[Item]:
    """Validate ``(line, record)`` pairs with typed values and turn them into items."""
    items: list[Item] = []
    first_line: dict[str, int] = {}
    for line, record in records:
        item = item_from_mapping(record, line)
        if item.id in first_line:
            raise InputError(
                "input.duplicate_id", {"id": item.id, "first_line": first_line[item.id]}, line
            )
        first_line[item.id] = line
        items.append(item)
    return items


def item_from_mapping(record: Any, line: int) -> Item:
    """Validate one record whose values have JSON types. Items pass through unchanged."""
    if isinstance(record, Item):
        return record
    if not isinstance(record, Mapping):
        raise InputError("input.not_an_object", line=line)
    for name in REQUIRED:
        value = record.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise InputError("input.missing_field", {"field": name}, line)
    kind = _text(record, "kind", line).strip().casefold()
    if kind not in KINDS:
        raise InputError("input.unknown_kind", {"kind": record["kind"]}, line)
    return Item(
        id=_identifier(record["id"], "id", line),
        kind=kind,
        title=_text(record, "title", line).strip(),
        description=_optional_text(record, "description", line) or "",
        acceptance_criteria=_text_list(record, "acceptance_criteria", line),
        estimate=_estimate(record.get("estimate"), line),
        priority=_priority(record, line),
        rank=_rank(record.get("rank"), line),
        status=_optional_text(record, "status", line),
        depends_on=_text_list(record, "depends_on", line),
        parent=_optional_text(record, "parent", line),
        updated=_date(_optional_text(record, "updated", line), line),
    )


MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
DATE_FORMATS = (
    # ISO 8601, optionally with time: 2026-11-12, 2026-11-12T10:00:00Z
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?"), (1, 2, 3)),
    # German: 12.11.2026, optionally with time
    (re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})(?: .*)?"), (3, 2, 1)),
)
JIRA_DATE = re.compile(r"(\d{1,2})/([A-Za-z]{3})/(\d{2})(?: .*)?")


def _date(value: str | None, line: int) -> str | None:
    """Normalise a date to ISO ``YYYY-MM-DD``; accepts ISO, German and Jira's default format."""
    if value is None:
        return None
    parts: tuple[int, int, int] | None = None
    for pattern, (year, month, day) in DATE_FORMATS:
        match = pattern.fullmatch(value)
        if match:
            parts = (int(match.group(year)), int(match.group(month)), int(match.group(day)))
            break
    else:
        match = JIRA_DATE.fullmatch(value)
        if match and match.group(2).casefold() in MONTHS:
            month = MONTHS.index(match.group(2).casefold()) + 1
            # ASSUMPTION: two-digit years in Jira dates are in 2000-2099.
            parts = (2000 + int(match.group(3)), month, int(match.group(1)))
    try:
        return datetime.date(*parts).isoformat()  # type: ignore[misc]
    except (TypeError, ValueError):
        raise _invalid("updated", value, line) from None


def _invalid(field: str, value: Any, line: int) -> InputError:
    return InputError("input.invalid_value", {"field": field, "value": str(value)}, line)


def _identifier(value: Any, field: str, line: int) -> str:
    # ASSUMPTION: integer ids (common in exports) are accepted and read as text.
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        raise _invalid(field, value, line)
    return value.strip()


def _text(record: Mapping[str, Any], field: str, line: int) -> str:
    value = record[field]
    if not isinstance(value, str):
        raise _invalid(field, value, line)
    return value


def _optional_text(record: Mapping[str, Any], field: str, line: int) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if field == "parent":
        value = _identifier(value, field, line)
    elif not isinstance(value, str):
        raise _invalid(field, value, line)
    value = value.strip()
    return value or None


def _text_list(record: Mapping[str, Any], field: str, line: int) -> tuple[str, ...]:
    value = record.get(field)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise _invalid(field, value, line)
    result = []
    for entry in value:
        text = _identifier(entry, field, line) if field == "depends_on" else entry
        if not isinstance(text, str):
            raise _invalid(field, entry, line)
        # ASSUMPTION: empty list entries are dropped, so indices count non-empty entries.
        if text.strip():
            result.append(text.strip())
    return tuple(result)


def _estimate(value: Any, line: int) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        raise _invalid("estimate", value, line)
    return int(value) if float(value).is_integer() else value


def _priority(record: Mapping[str, Any], line: int) -> str | None:
    value = _optional_text(record, "priority", line)
    if value is None:
        return None
    if value.casefold() not in PRIORITIES:
        raise _invalid("priority", value, line)
    return value.casefold()


def _rank(value: Any, line: int) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _invalid("rank", value, line)
    return value


# --- JSON ----------------------------------------------------------------------------------


def load_json(
    text: str, mapping: Mapping[str, str] | None = None, preset: Preset | None = None
) -> list[Item]:
    """Read a JSON array of objects. ``mapping`` renames source keys to field names and wins
    over the columns of ``preset``."""
    text = text.removeprefix("﻿")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError("input.json_syntax", {"detail": exc.msg}, exc.lineno) from None
    if not isinstance(data, list):
        raise InputError("input.not_a_list", line=1)
    records = []
    for line, record in zip(_json_element_lines(text), data, strict=True):
        if isinstance(record, Mapping):
            if preset is not None:
                record = _apply_mapping(record, {**preset.mapping(record), **(mapping or {})}, line)
                record = {
                    key: preset.text(key, value) if isinstance(value, str) else value
                    for key, value in record.items()
                }
                record["kind"] = preset.kind(record.get("kind"))
            else:
                record = _apply_mapping(record, mapping, line)
        records.append((line, record))
    return build_items(records)


def _json_element_lines(text: str) -> list[int]:
    """Line number where each element of a valid top-level JSON array starts."""
    decoder = json.JSONDecoder()
    whitespace = re.compile(r"[ \t\n\r]*")
    lines = []
    pos = whitespace.match(text, 0).end() + 1  # skip "["
    line = 1 + text.count("\n", 0, pos)
    while True:
        start = whitespace.match(text, pos).end()
        if text[start] == "]":
            return lines
        line += text.count("\n", pos, start)
        lines.append(line)
        _, end = decoder.raw_decode(text, start)
        line += text.count("\n", start, end)
        pos = whitespace.match(text, end).end()
        line += text.count("\n", end, pos)
        if text[pos] == ",":
            pos += 1


def _apply_mapping(
    record: Mapping[str, Any], mapping: Mapping[str, str] | None, line: int
) -> dict[str, Any]:
    if not mapping:
        return dict(record)
    result: dict[str, Any] = {}
    for key, value in record.items():
        target = mapping.get(key, key)
        if target in result:
            raise InputError("input.duplicate_column", {"field": target}, line)
        result[target] = value
    return result


# --- CSV -----------------------------------------------------------------------------------


def load_csv(
    text: str,
    mapping: Mapping[str, str] | None = None,
    separator: str | None = None,
    delimiter: str | None = None,
    preset: Preset | None = None,
) -> list[Item]:
    """Read CSV with a header row.

    ``mapping`` renames columns to field names, ``separator`` splits list fields (default: line
    break or ``|``), ``delimiter`` separates cells (default: detected from the header row).
    ``preset`` supplies the mapping of a known export; ``mapping`` wins over it.
    """
    text = text.removeprefix("﻿")
    if not text.strip():
        raise InputError("input.empty", line=1)
    if delimiter is None:
        delimiter = detect_delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        header = next(reader)
        if preset is not None:
            mapping = {**preset.mapping(header), **(mapping or {})}
        columns = _csv_columns(header, mapping)
        records = []
        start = reader.line_num + 1
        for row in reader:
            if any(cell.strip() for cell in row):
                record = _csv_record(row, columns, separator, start, preset)
                records.append((start, record))
            start = reader.line_num + 1
    except csv.Error as exc:
        raise InputError("input.csv_syntax", {"detail": str(exc)}, reader.line_num) from None
    return build_items(records)


def detect_delimiter(text: str) -> str:
    """Pick the delimiter that occurs most often in the first line (ties: ``,`` ``;`` tab)."""
    first_line = text.split("\n", 1)[0]
    return max(CSV_DELIMITERS, key=first_line.count)


def _csv_columns(header: Sequence[str], mapping: Mapping[str, str] | None) -> dict[str, int]:
    mapping = mapping or {}
    columns: dict[str, int] = {}
    for index, name in enumerate(header):
        name = name.strip()
        target = mapping.get(name, name)
        if target in FIELDS:
            if target in columns:
                raise InputError("input.duplicate_column", {"field": target}, 1)
            columns[target] = index
    for name in REQUIRED:
        if name not in columns:
            raise InputError("input.missing_column", {"field": name}, 1)
    return columns


def _csv_record(
    row: Sequence[str],
    columns: Mapping[str, int],
    separator: str | None,
    line: int,
    preset: Preset | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for name, index in columns.items():
        cell = row[index].strip() if index < len(row) else ""
        if preset is not None:
            cell = preset.text(name, cell).strip()
            if name == "kind":
                cell = preset.kind(cell)
        if name in LIST_FIELDS:
            record[name] = split_list(cell, separator)
        elif name == "estimate":
            record[name] = _parse_number(cell, name, line)
        elif name == "rank":
            record[name] = _parse_int(cell, name, line)
        else:
            record[name] = cell or None
    return record


def split_list(cell: str, separator: str | None = None) -> list[str]:
    """Split a list cell. Without a separator, line breaks and ``|`` both separate."""
    if separator is not None:
        return cell.split(separator)
    return re.split("|".join(re.escape(s) for s in DEFAULT_LIST_SEPARATORS), cell)


def _parse_number(cell: str, field: str, line: int) -> float | None:
    if not cell:
        return None
    # ASSUMPTION: a decimal comma is accepted in CSV ("2,5"), as Excel writes it in German.
    try:
        return float(cell.replace(",", "."))
    except ValueError:
        raise _invalid(field, cell, line) from None


def _parse_int(cell: str, field: str, line: int) -> int | None:
    if not cell:
        return None
    try:
        return int(cell)
    except ValueError:
        raise _invalid(field, cell, line) from None


# --- files ---------------------------------------------------------------------------------


def load_file(
    path: str | Path,
    mapping: Mapping[str, str] | None = None,
    separator: str | None = None,
    delimiter: str | None = None,
    preset: Preset | None = None,
) -> list[Item]:
    """Read a ``.json`` or ``.csv`` file (UTF-8, optional BOM)."""
    path = Path(path)
    suffix = path.suffix.casefold()
    if suffix not in (".json", ".csv"):
        raise InputError("input.unknown_format", {"path": str(path)})
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise InputError("input.file_not_found", {"path": str(path)}) from None
    except UnicodeDecodeError:
        raise InputError("input.encoding", {"path": str(path)}) from None
    if suffix == ".json":
        return load_json(text, mapping, preset)
    return load_csv(text, mapping, separator, delimiter, preset)
