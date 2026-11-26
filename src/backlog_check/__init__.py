"""backlog-check: checks a backlog against fixed, traceable rules (BC-01 to BC-18)."""

from .catalog import render
from .config import Config
from .engine import check, to_items
from .errors import BacklogCheckError, ConfigError, InputError
from .fix import Change, apply_fixes
from .model import Finding, Item
from .reader import load_csv, load_file, load_json
from .suggest import Suggestion, suggest, template
from .summary import summarize

__version__ = "0.1.0"

__all__ = [
    "BacklogCheckError",
    "Change",
    "Config",
    "ConfigError",
    "Finding",
    "InputError",
    "Item",
    "Suggestion",
    "__version__",
    "apply_fixes",
    "check",
    "load_csv",
    "load_file",
    "load_json",
    "render",
    "suggest",
    "summarize",
    "template",
    "to_items",
]
