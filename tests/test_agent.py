"""Tests for SafeAgent core logic."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

try:
    from agent_polis.actions.models import RiskLevel
except ModuleNotFoundError:
    from impact_preview.actions.models import RiskLevel

from safe_agent.agent import SafeAgent


class TestResolvePathSafe:
    """Tests for _resolve_path_safe (path traversal safety)."""

    def test_accepts_relative_file(self, safe_agent: SafeAgent, temp_work_dir: Path) -> None:
        resolved = safe_agent._resolve_path_safe("foo.py")
        assert resolved is not None
        assert resolved == temp_work_dir / "foo.py"

    def test_accepts_nested_path(self, safe_agent: SafeAgent, temp_work_dir: Path) -> None:
        resolved = safe_agent._resolve_path_safe("src/safe_agent/__init__.py")
        assert resolved is not None
        assert resolved == temp_work_dir / "src" / "safe_agent" / "__init__.py"

    def test_accepts_dot_path(self, safe_agent: SafeAgent, temp_work_dir: Path) -> None:
        resolved = safe_agent._resolve_path_safe("./config.yaml")
        assert resolved is not None
        assert resolved == temp_work_dir / "config.yaml"

    def test_rejects_traversal_up(self, safe_agent: SafeAgent) -> None:
        assert safe_agent._resolve_path_safe("../../../etc/passwd") is None
        assert safe_agent._resolve_path_safe("..") is None
        assert safe_agent._resolve_path_safe("foo/../../bar") is None

    def test_rejects_traversal_within_path(self, safe_agent: SafeAgent) -> None:
        # Path that goes up then back down (still outside base)
        assert safe_agent._resolve_path_safe("sub/../../../other/file.txt") is None

    def test_accepts_path_under_work_dir(self, safe_agent: SafeAgent, temp_work_dir: Path) -> None:
        (temp_work_dir / "sub").mkdir(parents=True, exist_ok=True)
        resolved = safe_agent._resolve_path_safe("sub/file.txt")
        assert resolved is not None
        assert resolved == temp_work_dir / "sub" / "file.txt"


class TestRunReturnShape:
    """Tests for consistent return shape from run()."""

    @pytest.mark.asyncio
    async def test_returns_changes_made_and_rejected_when_no_plan_changes(
        self, safe_agent: SafeAgent
    ) -> None:
        with patch.object(safe_agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing to do", "changes": []}
            result = await safe_agent.run("do nothing")
        assert "changes_made" in result
        assert "changes_rejected" in result
        assert result["changes_made"] == []
        assert result["changes_rejected"] == []
        assert result["success"] is True


class TestNonInteractive:
    """Tests for non-interactive approval behaviour (no TTY)."""

    @pytest.mark.asyncio
    async def test_non_interactive_approves_low_and_medium(
        self, safe_agent: SafeAgent, temp_work_dir: Path
    ) -> None:
        safe_agent.non_interactive = True
        safe_agent.dry_run = False
        for level in (RiskLevel.LOW, RiskLevel.MEDIUM):
            with patch.object(
                safe_agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(level),
            ):
                approved = await safe_agent._preview_and_approve(
                    {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
                )
            assert approved is True

    @pytest.mark.asyncio
    async def test_non_interactive_rejects_high_and_critical(
        self, safe_agent: SafeAgent, temp_work_dir: Path
    ) -> None:
        safe_agent.non_interactive = True
        safe_agent.dry_run = False
        for level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            with patch.object(
                safe_agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(level),
            ):
                approved = await safe_agent._preview_and_approve(
                    {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
                )
            assert approved is False


def _mock_preview(risk_level: RiskLevel) -> object:
    """Minimal preview object for testing."""
    return type("Preview", (), {"risk_level": risk_level, "risk_factors": [], "file_changes": []})()
