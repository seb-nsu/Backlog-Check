"""Project-level acceptance criteria: standard library only, README content."""

import ast
import re
import sys
import tomllib
from pathlib import Path

from backlog_check.cli import build_parser
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


def test_github_action_and_pre_commit_hook_use_existing_options():
    options = {o for action in build_parser()._actions for o in action.option_strings}
    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    command = action[action.index("cmd=(") :]
    used = set(re.findall(r"(?<![\w-])--[a-z][a-z-]+", command))
    assert used and used <= options
    assert "using: composite" in action
    hook = (ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "entry: backlog-check" in hook
    assert "backlog-check" in scripts["scripts"]
