"""Tests for SafeAgent path traversal protections."""

from __future__ import annotations

from pathlib import Path

import pytest

from safe_agent.agent import SafeAgent


def test_resolve_path_safe_accepts_relative_paths(safe_agent: SafeAgent) -> None:
    resolved = safe_agent._resolve_path_safe("foo.py")
    assert resolved is not None
    assert resolved.name == "foo.py"


def test_resolve_path_safe_rejects_absolute_paths(safe_agent: SafeAgent) -> None:
    assert safe_agent._resolve_path_safe("/etc/passwd") is None


def test_resolve_path_safe_rejects_traversal(safe_agent: SafeAgent) -> None:
    assert safe_agent._resolve_path_safe("../etc/passwd") is None
    assert safe_agent._resolve_path_safe("foo/../../bar") is None


def test_resolve_path_safe_rejects_windows_absolute(safe_agent: SafeAgent) -> None:
    assert safe_agent._resolve_path_safe("C:\\Windows\\System32\\drivers\\etc\\hosts") is None
    assert safe_agent._resolve_path_safe("\\\\server\\share\\file.txt") is None


def test_resolve_path_safe_rejects_home_expansion(safe_agent: SafeAgent) -> None:
    assert safe_agent._resolve_path_safe("~/.bashrc") is None


def test_resolve_path_safe_stays_within_working_directory(
    safe_agent: SafeAgent, tmp_path: Path
) -> None:
    safe_agent.working_directory = str(tmp_path)
    resolved = safe_agent._resolve_path_safe("subdir/file.txt")
    assert resolved is not None
    assert resolved == tmp_path.resolve() / "subdir" / "file.txt"

