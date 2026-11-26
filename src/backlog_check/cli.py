"""Command line: ``backlog-check FILE [--format text|json|csv] [--lang de|en] [--suggest] ...``.

``backlog-check --template story|bug|epic`` prints a new item with placeholders instead.

Exit codes: 0 without a finding of severity error, 1 with one, 2 for invalid input or
configuration. ``--fail-on warning|info|none`` moves the threshold for exit code 1.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from . import __version__
from .catalog import CATALOG_LANGUAGES, format_value, load_catalog, render
from .config import Config
from .engine import check
from .errors import BacklogCheckError, ConfigError
from .model import KINDS, RULE_IDS, SEVERITIES, Finding, Item
from .presets import PRESETS
from .reader import FIELDS, load_file
from .suggest import Suggestion, suggest, template
from .summary import summarize

EXIT_OK = 0
EXIT_ERRORS = 1
EXIT_INVALID = 2
FORMATS = ("text", "json", "csv", "markdown", "sarif")
FAIL_ON = ("error", "warning", "info", "none")
SARIF_LEVELS = {"error": "error", "warning": "warning", "info": "note"}
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
PROJECT_URL = "https://github.com/seb-nsu/Backlog-Check"
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
SUGGESTION_COLUMNS = ("suggestion_key", "suggestion_params", "suggestion")
LIST_INDEX = re.compile(r"^(\w+)\[(\d+)\]$")


@dataclass(frozen=True)
class Report:
    """Everything an output format needs."""

    items: Sequence[Item]
    findings: Sequence[Finding]
    summary: dict[str, Any]
    language: str
    config: Config
    source: str
    suggestions: Sequence[Suggestion] | None = None  # one per finding, only with --suggest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backlog-check", description="Check a backlog against the rules BC-01 to BC-15."
    )
    parser.add_argument("file", nargs="?", help="backlog as .csv or .json")
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
    parser.add_argument(
        "--preset", choices=sorted(PRESETS), help="column mapping of a Jira or Azure DevOps export"
    )
    parser.add_argument("--separator", help="separator of list fields in CSV cells")
    parser.add_argument("--delimiter", help="cell delimiter of the CSV file (default: detected)")
    parser.add_argument(
        "--reference-date",
        metavar="YYYY-MM-DD",
        help="reference date for BC-13 (stale items), unless the configuration sets one",
    )
    parser.add_argument(
        "--suggest", action="store_true", help="add an improvement suggestion to each finding"
    )
    parser.add_argument(
        "--template",
        choices=KINDS,
        help="print a new item of this kind with placeholders (JSON) instead of checking",
    )
    parser.add_argument(
        "--fail-on",
        choices=FAIL_ON,
        default="error",
        help="lowest severity that makes the exit code 1 (none: always 0)",
    )
    parser.add_argument("--output", help="write the result to this file instead of stdout")
    return parser


def main(argv: Sequence[str] | None = None, stdout: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.template is not None:
        output = json.dumps([template(args.template, args.lang)], ensure_ascii=False, indent=2)
        _write_output(output + "\n", args.output, stdout)
        return EXIT_OK
    if args.file is None:
        parser.error("the following arguments are required: file")
    try:
        config = _load_config(args.config, args.lang, args.reference_date)
        mapping = _parse_mapping(args.map)
        items = load_file(
            args.file,
            mapping,
            args.separator if args.separator is not None else config.list_separator,
            args.delimiter,
            PRESETS[args.preset] if args.preset else None,
        )
    except BacklogCheckError as error:
        sys.stderr.write(format_error(error, args.lang) + "\n")
        return EXIT_INVALID
    findings = check(items, config)
    summary = summarize(items, findings, config)
    suggestions = suggest(items, findings, config) if args.suggest else None
    report = Report(items, findings, summary, args.lang, config, args.file, suggestions)
    _write_output(FORMATTERS[args.format](report), args.output, stdout)
    return exit_code(findings, args.fail_on)


def exit_code(findings: Sequence[Finding], fail_on: str = "error") -> int:
    """1 if a finding has severity ``fail_on`` or higher, else 0; ``none`` never fails."""
    if fail_on == "none":
        return EXIT_OK
    threshold = SEVERITIES.index(fail_on)
    failed = any(SEVERITIES.index(f.severity) >= threshold for f in findings)
    return EXIT_ERRORS if failed else EXIT_OK


def _write_output(output: str, path: str | None, stdout: TextIO) -> None:
    if path:
        Path(path).write_text(output, encoding="utf-8", newline="")
    else:
        stdout.write(output)


def _load_config(path: str | None, language: str, reference_date: str | None = None) -> Config:
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
        if reference_date is not None:
            data.setdefault("reference_date", reference_date)
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


def format_json(report: Report) -> str:
    data: dict[str, Any] = {"findings": [f.to_dict() for f in report.findings]}
    if report.suggestions is not None:
        data["suggestions"] = [s.to_dict() for s in report.suggestions]
    data["summary"] = report.summary
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def format_csv(report: Report) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    with_suggestions = report.suggestions is not None
    writer.writerow(CSV_COLUMNS + (SUGGESTION_COLUMNS if with_suggestions else ()))
    for index, finding in enumerate(report.findings):
        span = finding.span or ("", "")
        extra = []
        if report.suggestions is not None:
            hint = report.suggestions[index]
            extra = [
                hint.message_key,
                json.dumps(hint.to_dict()["params"], ensure_ascii=False),
                render(hint.message_key, hint.params, report.language),
            ]
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
                render(finding.message_key, finding.params, report.language),
                *extra,
            ]
        )
    return buffer.getvalue()


def format_text(report: Report) -> str:
    items, findings, summary, language = (
        report.items,
        report.findings,
        report.summary,
        report.language,
    )
    catalog = load_catalog(language)
    by_id = {item.id: item for item in items}
    lines = [render("report.header", summary, language), ""]
    if not findings:
        lines += [catalog["report.no_findings"], ""]
    for index, finding in enumerate(findings):
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
        if report.suggestions is not None:
            lines.append("    " + _suggestion_text(report.suggestions[index], language))
        lines.append("")
    lines.append(catalog["report.summary"])
    lines += _summary_lines(summary, catalog, language)
    return "\n".join(lines) + "\n"


def _suggestion_text(suggestion: Suggestion, language: str) -> str:
    text = render(suggestion.message_key, suggestion.params, language)
    return render("report.suggestion", {"text": text}, language)


def _summary_lines(summary: dict[str, Any], catalog: dict[str, str], language: str) -> list[str]:
    lines = ["    " + render("report.by_severity", summary["by_severity"], language)]
    for rule, counts in summary["by_rule"].items():
        parts = ", ".join(f"{catalog[f'severity.{s}']}: {n}" for s, n in counts.items())
        lines.append(f"    {rule} {catalog[f'rule.{rule}']}: {parts}")
    if summary["ready_ratio"] is None:
        lines.append("    " + catalog["report.ready_none"])
    else:
        percent = format_value(round(summary["ready_ratio"] * 100, 1), language)
        params = {"ready": summary["ready_stories"], "stories": summary["stories"]}
        lines.append("    " + render("report.ready", {**params, "percent": percent}, language))
    return lines


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


def format_markdown(report: Report) -> str:
    language, summary = report.language, report.summary
    catalog = load_catalog(language)
    lines = ["# backlog-check", "", render("report.header", summary, language), ""]
    if report.findings:
        columns = ("item", "severity", "rule", "finding", "field")
        if report.suggestions is not None:
            columns += ("suggestion",)
        lines.append("| " + " | ".join(catalog[f"report.column_{c}"] for c in columns) + " |")
        lines.append("|" + " --- |" * len(columns))
        for index, finding in enumerate(report.findings):
            cells = [
                finding.item,
                catalog[f"severity.{finding.severity}"],
                f"{finding.rule} {catalog[f'rule.{finding.rule}']}",
                render(finding.message_key, finding.params, language),
                f"`{finding.field}`" if finding.field else "",
            ]
            if report.suggestions is not None:
                hint = report.suggestions[index]
                cells.append(render(hint.message_key, hint.params, language))
            lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    else:
        lines.append(catalog["report.no_findings"])
    lines += ["", f"## {catalog['report.summary']}", ""]
    lines += [f"- {line.strip()}" for line in _summary_lines(summary, catalog, language)]
    return "\n".join(lines) + "\n"


def format_sarif(report: Report) -> str:
    """SARIF 2.1.0 for code platforms; each finding points to the line of its item."""
    catalog = load_catalog(report.language)
    by_id = {item.id: item for item in report.items}
    rules = [
        {
            "id": rule,
            "name": catalog[f"rule.{rule}"],
            "shortDescription": {"text": catalog[f"rule.{rule}"]},
            "defaultConfiguration": {
                "level": SARIF_LEVELS[report.config.rules[rule].severity],
                "enabled": report.config.rules[rule].enabled,
            },
        }
        for rule in RULE_IDS
    ]
    uri = Path(report.source).as_posix()
    results = []
    for index, finding in enumerate(report.findings):
        location: dict[str, Any] = {"artifactLocation": {"uri": uri}}
        line = by_id[finding.item].line
        if line is not None:
            location["region"] = {"startLine": line}
        data = finding.to_dict()
        properties = {
            key: data[key] for key in ("item", "related", "field", "span", "message_key", "params")
        }
        if report.suggestions is not None:
            hint = report.suggestions[index]
            properties["suggestion"] = {
                "message_key": hint.message_key,
                "params": hint.to_dict()["params"],
                "text": render(hint.message_key, hint.params, report.language),
            }
        results.append(
            {
                "ruleId": finding.rule,
                "ruleIndex": RULE_IDS.index(finding.rule),
                "level": SARIF_LEVELS[finding.severity],
                "message": {"text": render(finding.message_key, finding.params, report.language)},
                "locations": [
                    {
                        "physicalLocation": location,
                        "logicalLocations": [{"name": finding.item, "kind": "object"}],
                    }
                ],
                "properties": properties,
            }
        )
    sarif = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "backlog-check",
                        "version": __version__,
                        "informationUri": PROJECT_URL,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, ensure_ascii=False, indent=2) + "\n"


FORMATTERS = {
    "json": format_json,
    "csv": format_csv,
    "text": format_text,
    "markdown": format_markdown,
    "sarif": format_sarif,
}


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
