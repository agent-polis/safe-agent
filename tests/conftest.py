"""Pytest fixtures for safe-agent."""

from __future__ import annotations

from pathlib import Path

import pytest

from safe_agent.agent import SafeAgent


@pytest.fixture
def temp_work_dir(tmp_path: Path) -> Path:
    """Temporary working directory for SafeAgent."""
    return tmp_path.resolve()


@pytest.fixture
def safe_agent(temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch) -> SafeAgent:
    """SafeAgent instance configured for offline tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    return SafeAgent(working_directory=str(temp_work_dir), non_interactive=True, dry_run=False)
