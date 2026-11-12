"""Registry of rules BC-01 to BC-12. Each rule takes a Context and yields findings."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from ..context import Context
from ..model import Finding
from .bc01_missing_criteria import check_bc01
from .bc02_unmeasurable import check_bc02
from .bc03_too_large import check_bc03
from .bc04_multiple_concerns import check_bc04
from .bc05_missing_benefit import check_bc05
from .bc06_missing_estimate import check_bc06
from .bc07_hidden_dependency import check_bc07
from .bc08_dependency_order import check_bc08
from .bc09_cycle import check_bc09
from .bc10_duplicate import check_bc10
from .bc11_conflicting_values import check_bc11
from .bc12_structure import check_bc12

Rule = Callable[[Context], Iterable[Finding]]

RULES: dict[str, Rule] = {
    "BC-01": check_bc01,
    "BC-02": check_bc02,
    "BC-03": check_bc03,
    "BC-04": check_bc04,
    "BC-05": check_bc05,
    "BC-06": check_bc06,
    "BC-07": check_bc07,
    "BC-08": check_bc08,
    "BC-09": check_bc09,
    "BC-10": check_bc10,
    "BC-11": check_bc11,
    "BC-12": check_bc12,
}
