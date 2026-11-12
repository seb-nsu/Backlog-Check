"""Registry of rules BC-01 to BC-12. Each rule takes a Context and yields findings."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from ..context import Context
from ..model import Finding
from .bc01_missing_criteria import check_bc01
from .bc02_unmeasurable import check_bc02
from .bc03_too_large import check_bc03
from .bc04_multiple_concerns import check_bc04

Rule = Callable[[Context], Iterable[Finding]]

RULES: dict[str, Rule] = {
    "BC-01": check_bc01,
    "BC-02": check_bc02,
    "BC-03": check_bc03,
    "BC-04": check_bc04,
}
