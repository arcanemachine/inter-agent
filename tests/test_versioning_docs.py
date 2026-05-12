from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_changelog_has_entry_for_package_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = str(project["version"])
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert re.search(rf"^## {re.escape(version)}$", changelog, flags=re.MULTILINE)


def test_readme_points_to_changelog_and_version_source() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "pyproject.toml" in readme
    assert "CHANGELOG.md" in readme
