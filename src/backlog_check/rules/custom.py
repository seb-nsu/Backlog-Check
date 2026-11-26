"""Custom rules from the configuration (``custom_rules``): a regular expression that must not
(``forbid``) or must (``require``) match in the chosen fields of the chosen kinds of items."""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..config import CustomRule
from ..context import Context, TextField, text_fields
from ..model import Finding


def check_custom(ctx: Context, rule: CustomRule) -> Iterator[Finding]:
    pattern = re.compile(rule.pattern)
    for item in ctx.active:
        if item.kind not in rule.kinds:
            continue
        fields = [f for f in text_fields(item) if _base(f) in rule.fields]
        if rule.mode == "forbid":
            for text_field in fields:
                match = pattern.search(text_field.text)
                if match:
                    # Like BC-16: one finding per field, at the first match.
                    yield _finding(
                        rule,
                        item.id,
                        {"text": match.group()},
                        text_field.name,
                        match.span(),
                    )
        elif not any(pattern.search(f.text) for f in fields):
            # ASSUMPTION: "require" is met if any of the chosen fields matches. The finding
            # names the field only when the rule checks exactly one.
            field = rule.fields[0] if len(rule.fields) == 1 else None
            yield _finding(rule, item.id, {}, field, None)


def _base(text_field: TextField) -> str:
    return text_field.name.partition("[")[0]


def _finding(
    rule: CustomRule,
    item: str,
    params: dict[str, str],
    field: str | None,
    span: tuple[int, int] | None,
) -> Finding:
    return Finding(
        rule=rule.id,
        severity=rule.severity,
        item=item,
        message_key=rule.message_key,
        params=params,
        field=field,
        span=span,
    )
