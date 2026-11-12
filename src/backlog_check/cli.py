"""Command line: ``backlog-check FILE [--format text|json|csv] [--lang de|en] ...``.

Exit codes: 0 without a finding of severity error, 1 with one, 2 for invalid input or
configuration.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TextIO

from .catalog import CATALOG_LANGUAGES, format_value, load_catalog, render
from .config import Config
from .engine import check
from .errors import BacklogCheckError, ConfigError
from .model import Finding, Item
from .reader import FIELDS, load_file
from .summary import summarize

EXIT_OK = 0
EXIT_ERRORS = 1
EXIT_INVALID = 2
FORMATS = ("text", "json", "csv")
CSV_COLUMNS = (
    "rule",
    "severity",
    "item",
    "related",
    "field",
    "span_start",
    "span_end",
    "message_key",
    "params",
    "message",
)
LIST_INDEX = re.compile(r"^(\w+)\[(\d+)\]$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backlog-check", description="Check a backlog against the rules BC-01 to BC-12."
    )
    parser.add_argument("file", help="backlog as .csv or .json")
    parser.add_argument("--format", choices=FORMATS, default="text", help="output format")
    parser.add_argument(
        "--lang", choices=CATALOG_LANGUAGES, default="de", help="language of the report"
    )
    parser.add_argument("--config", help="configuration as JSON file")
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        metavar="COLUMN=FIELD",
        help='map a source column to a field, e.g. "Summary=title" (repeatable)',
    )
    parser.add_argument("--separator", help="separator of list fields in CSV cells")
    parser.add_argument("--delimiter", help="cell delimiter of the CSV file (default: detected)")
    parser.add_argument("--output", help="write the result to this file instead of stdout")
    return parser


def main(argv: Sequence[str] | None = None, stdout: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        config = _load_config(args.config, args.lang)
        mapping = _parse_mapping(args.map)
        items = load_file(
            args.file,
            mapping,
            args.separator if args.separator is not None else config.list_separator,
            args.delimiter,
        )
    except BacklogCheckError as error:
        sys.stderr.write(format_error(error, args.lang) + "\n")
        return EXIT_INVALID
    findings = check(items, config)
    summary = summarize(items, findings, config)
    output = FORMATTERS[args.format](items, findings, summary, args.lang)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8", newline="")
    else:
        stdout.write(output)
    return EXIT_ERRORS if summary["by_severity"]["error"] else EXIT_OK


def _load_config(path: str | None, language: str) -> Config:
    data: dict[str, Any] = {}
    if path is not None:
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            raise ConfigError("config.file_not_found", {"path": path}) from None
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError("config.json_syntax", {"detail": exc.msg}, exc.lineno) from None
    if isinstance(data, dict):
        # ASSUMPTION: --lang also selects the word lists unless the file sets "language".
        data.setdefault("language", language)
    return Config.from_dict(data)


def _parse_mapping(entries: Sequence[str]) -> dict[str, str]:
    mapping = {}
    for entry in entries:
        source, separator, target = entry.partition("=")
        if not separator or not source.strip() or target.strip() not in FIELDS:
            raise ConfigError("cli.invalid_map", {"value": entry, "fields": list(FIELDS)})
        mapping[source.strip()] = target.strip()
    return mapping


def format_error(error: BacklogCheckError, language: str) -> str:
    message = render(error.message_key, error.params, language)
    if error.line is not None:
        return render("report.error_line", {"line": error.line, "message": message}, language)
    return render("report.error", {"message": message}, language)


# --- output --------------------------------------------------------------------------------


def format_json(
    items: Sequence[Item], findings: Sequence[Finding], summary: dict[str, Any], language: str
) -> str:
    data = {"findings": [f.to_dict() for f in findings], "summary": summary}
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def format_csv(
    items: Sequence[Item], findings: Sequence[Finding], summary: dict[str, Any], language: str
) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for finding in findings:
        span = finding.span or ("", "")
        writer.writerow(
            [
                finding.rule,
                finding.severity,
                finding.item,
                "|".join(finding.related),
                finding.field or "",
                span[0],
                span[1],
                finding.message_key,
                json.dumps(finding.to_dict()["params"], ensure_ascii=False),
                render(finding.message_key, finding.params, language),
            ]
        )
    return buffer.getvalue()


def format_text(
    items: Sequence[Item], findings: Sequence[Finding], summary: dict[str, Any], language: str
) -> str:
    catalog = load_catalog(language)
    by_id = {item.id: item for item in items}
    lines = [render("report.header", summary, language), ""]
    if not findings:
        lines += [catalog["report.no_findings"], ""]
    for finding in findings:
        rule_title = catalog[f"rule.{finding.rule}"]
        severity = catalog[f"severity.{finding.severity}"]
        lines.append(f"{finding.item}  {severity}  {finding.rule} {rule_title}")
        lines.append("    " + render(finding.message_key, finding.params, language))
        details = []
        if finding.field:
            details.append(render("report.field", {"field": finding.field}, language))
        excerpt = field_excerpt(by_id[finding.item], finding)
        if excerpt is not None:
            details.append(render("report.excerpt", {"text": excerpt}, language))
        if finding.related:
            details.append(render("report.related", {"related": list(finding.related)}, language))
        if details:
            lines.append("    (" + "; ".join(details) + ")")
        lines.append("")
    lines.append(catalog["report.summary"])
    lines.append("    " + render("report.by_severity", summary["by_severity"], language))
    for rule, counts in summary["by_rule"].items():
        parts = ", ".join(f"{catalog[f'severity.{s}']}: {n}" for s, n in counts.items())
        lines.append(f"    {rule} {catalog[f'rule.{rule}']}: {parts}")
    if summary["ready_ratio"] is None:
        lines.append("    " + catalog["report.ready_none"])
    else:
        percent = format_value(round(summary["ready_ratio"] * 100, 1), language)
        params = {"ready": summary["ready_stories"], "stories": summary["stories"]}
        lines.append("    " + render("report.ready", {**params, "percent": percent}, language))
    return "\n".join(lines) + "\n"


def field_excerpt(item: Item, finding: Finding) -> str | None:
    """The text a finding's span points to, e.g. the vague word in a criterion."""
    if finding.span is None or finding.field is None:
        return None
    match = LIST_INDEX.match(finding.field)
    if match:
        text = getattr(item, match.group(1))[int(match.group(2))]
    else:
        text = getattr(item, finding.field)
    start, end = finding.span
    return text[start:end]


FORMATTERS = {"json": format_json, "csv": format_csv, "text": format_text}


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
