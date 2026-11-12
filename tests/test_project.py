"""Project-level acceptance criteria: standard library only, README content."""

import ast
import sys
import tomllib
from pathlib import Path

from backlog_check.model import RULE_IDS

ROOT = Path(__file__).parent.parent


def test_package_imports_only_the_standard_library():
    for path in (ROOT / "src" / "backlog_check").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module]
            else:
                continue
            for name in names:
                assert name.split(".")[0] in sys.stdlib_module_names, f"{path}: {name}"


def test_no_runtime_dependencies_declared():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == []


def test_readme_has_installation_example_and_rule_tables_in_both_languages():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Installation" in readme and "### Installation" in readme
    assert "## Regeln" in readme and "### Rules" in readme
    for rule in RULE_IDS:
        assert readme.count(f"| {rule} |") == 2
