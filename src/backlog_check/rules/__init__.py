"""Registry of rules BC-01 to BC-12. Each rule takes a Context and yields findings."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from ..context import Context
from ..model import Finding

Rule = Callable[[Context], Iterable[Finding]]

RULES: dict[str, Rule] = {}
