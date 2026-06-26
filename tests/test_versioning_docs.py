from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]


def package_version() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return str(project["version"])


def read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_release_metadata_versions_match_package_version() -> None:
    version = package_version()

    root_pi_package = read_json(ROOT / "package.json")
    pi_package = read_json(ROOT / "integrations" / "pi" / "package.json")
    claude_plugin = read_json(
        ROOT / "integrations" / "claude-code" / ".claude-plugin" / "plugin.json"
    )
    claude_marketplace = read_json(ROOT / ".claude-plugin" / "marketplace.json")
    marketplace_plugins = claude_marketplace["plugins"]

    assert root_pi_package["version"] == version
    assert pi_package["version"] == version
    assert claude_plugin["version"] == version
    assert claude_marketplace["version"] == version
    assert isinstance(marketplace_plugins, list)
    assert len(marketplace_plugins) == 1
    assert marketplace_plugins[0]["version"] == version


def test_changelog_has_entry_for_package_version() -> None:
    version = package_version()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert re.search(rf"^## {re.escape(version)}$", changelog, flags=re.MULTILINE)


def test_changelog_documents_versioning_policy() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Versioning policy" in changelog
    assert "pyproject.toml" in changelog
    assert "package.json" in changelog
    assert "marketplace.json" in changelog
    assert "plugin.json" in changelog
    assert "core.version" in changelog


def test_readme_points_to_changelog_and_version_source() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Versioning and release notes" in readme
    assert "pyproject.toml" in readme
    assert "CHANGELOG.md" in readme
