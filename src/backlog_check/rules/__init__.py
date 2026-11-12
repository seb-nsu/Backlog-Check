"""Registry of rules BC-01 to BC-12. Each rule takes a Context and yields findings."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from ..context import Context
from ..model import Finding
from .bc01_missing_criteria import check_bc01
from .bc02_unmeasurable import check_bc02

Rule = Callable[[Context], Iterable[Finding]]

RULES: dict[str, Rule] = {
    "BC-01": check_bc01,
    "BC-02": check_bc02,
}
