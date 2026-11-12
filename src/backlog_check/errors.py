"""Error types. Errors carry a catalog key and parameters, never a finished sentence."""

from __future__ import annotations

from typing import Any


class BacklogCheckError(Exception):
    """Base class for all errors raised by backlog_check."""

    def __init__(
        self, message_key: str, params: dict[str, Any] | None = None, line: int | None = None
    ) -> None:
        self.message_key = message_key
        self.params = dict(params or {})
        self.line = line
        super().__init__(f"{message_key} {self.params} line={line}")


class InputError(BacklogCheckError):
    """The backlog is invalid: missing required field, duplicate id, unknown kind, bad value."""


class ConfigError(BacklogCheckError):
    """The configuration is invalid."""
