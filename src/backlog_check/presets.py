"""Ready-made column mappings for exports from Jira and Azure DevOps."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Preset:
    """How an export maps to the input format.

    ``columns`` lists candidate column names per field; the first one present is used.
    ``kinds`` maps the tool's item types (case-insensitive) to ``epic``, ``story`` or ``bug``.
    """

    columns: Mapping[str, tuple[str, ...]]
    kinds: Mapping[str, str]
    html_fields: tuple[str, ...] = field(default=())

    def mapping(self, available: Iterable[str]) -> dict[str, str]:
        """Source column -> field for the columns that are present."""
        present = {name.strip() for name in available}
        result = {}
        for target, candidates in self.columns.items():
            for candidate in candidates:
                if candidate in present:
                    result[candidate] = target
                    break
        return result

    def kind(self, value: object) -> object:
        if isinstance(value, str):
            return self.kinds.get(value.strip().casefold(), value)
        return value

    def text(self, name: str, value: str) -> str:
        """Turn HTML cells (Azure DevOps) into plain text with one line per paragraph."""
        if name not in self.html_fields:
            return value
        value = BLOCK_END.sub("\n", value)
        value = TAG.sub("", value)
        return html.unescape(value)


BLOCK_END = re.compile(r"<br\s*/?>|</(?:p|div|li|h\d)>", re.IGNORECASE)
TAG = re.compile(r"<[^>]*>")

# ASSUMPTION: priority, rank and links are not mapped: Jira and Azure DevOps priorities are not
# MoSCoW, ranks are not integers and links come in several columns of the same name. Jira's
# "Parent" column holds an internal number, so the epic comes from "Parent key" or "Epic Link".
# Tasks and sub-tasks count as stories, Azure DevOps features as epics.
PRESETS: dict[str, Preset] = {
    "jira": Preset(
        columns={
            "id": ("Issue key",),
            "kind": ("Issue Type",),
            "title": ("Summary",),
            "description": ("Description",),
            "acceptance_criteria": ("Custom field (Acceptance Criteria)", "Acceptance Criteria"),
            "estimate": (
                "Custom field (Story Points)",
                "Custom field (Story point estimate)",
                "Story Points",
            ),
            "status": ("Status",),
            "parent": ("Parent key", "Custom field (Epic Link)"),
            "updated": ("Updated",),
        },
        kinds={
            "story": "story",
            "bug": "bug",
            "epic": "epic",
            "task": "story",
            "sub-task": "story",
            "subtask": "story",
            "aufgabe": "story",
            "unteraufgabe": "story",
            "fehler": "bug",
        },
    ),
    "azure-devops": Preset(
        columns={
            "id": ("ID",),
            "kind": ("Work Item Type",),
            "title": ("Title",),
            "description": ("Description", "Repro Steps"),
            "acceptance_criteria": ("Acceptance Criteria",),
            "estimate": ("Story Points", "Effort", "Size"),
            "status": ("State",),
            "parent": ("Parent",),
        },
        kinds={
            "user story": "story",
            "product backlog item": "story",
            "requirement": "story",
            "task": "story",
            "issue": "story",
            "bug": "bug",
            "epic": "epic",
            "feature": "epic",
        },
        html_fields=("description", "acceptance_criteria"),
    ),
}
