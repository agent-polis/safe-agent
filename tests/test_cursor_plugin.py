"""Sanity checks for Cursor plugin packaging assets."""

from __future__ import annotations

import json
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _has_frontmatter(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 3:
        return False
    if lines[0].strip() != "---":
        return False
    try:
        end_index = lines.index("---", 1)
    except ValueError:
        return False
    return end_index > 1


def test_cursor_plugin_manifest_is_valid() -> None:
    repo = _repo_root()
    manifest_path = repo / ".cursor-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest["name"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert isinstance(manifest["description"], str) and manifest["description"].strip()
    assert manifest["license"] == "MIT"
    assert manifest["repository"].startswith("https://")

    logo = manifest.get("logo")
    assert isinstance(logo, str) and logo
    assert not logo.startswith("/")
    assert ".." not in logo
    assert (repo / logo).exists()


def test_cursor_plugin_mcp_server_config_is_safe() -> None:
    repo = _repo_root()
    mcp_path = repo / ".mcp.json"
    payload = json.loads(mcp_path.read_text(encoding="utf-8"))
    server = payload["mcpServers"]["safe-agent"]

    command = server["command"]
    assert command == "safe-agent-mcp"


def test_cursor_plugin_markdown_assets_have_frontmatter() -> None:
    repo = _repo_root()
    files = [
        repo / "rules" / "safe-agent-risk-gate.mdc",
        repo / "skills" / "safe-agent-ci" / "SKILL.md",
        repo / "commands" / "run-safe-agent-pr-gate.md",
        repo / "agents" / "safe-agent-reviewer.md",
    ]
    for path in files:
        assert path.exists(), f"missing plugin asset: {path}"
        assert _has_frontmatter(path), f"missing frontmatter: {path}"
