"""Tests for non-interactive approvals and risk policy enforcement."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent_polis.actions.models import RiskLevel

from safe_agent.agent import SafeAgent


def _mock_preview(level: RiskLevel) -> object:
    return type("Preview", (), {"risk_level": level, "risk_factors": [], "file_changes": []})()


@pytest.mark.asyncio
async def test_non_interactive_approves_low_and_medium(safe_agent: SafeAgent) -> None:
    safe_agent.non_interactive = True
    safe_agent.fail_on_risk = None

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
async def test_non_interactive_rejects_high_and_critical(safe_agent: SafeAgent) -> None:
    safe_agent.non_interactive = True
    safe_agent.fail_on_risk = None

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


@pytest.mark.asyncio
async def test_fail_on_risk_blocks_changes_and_marks_run_failed(safe_agent: SafeAgent) -> None:
    safe_agent.non_interactive = True
    safe_agent.fail_on_risk = RiskLevel.HIGH

    with patch.object(
        safe_agent.analyzer,
        "analyze",
        new_callable=AsyncMock,
        return_value=_mock_preview(RiskLevel.HIGH),
    ):
        approved = await safe_agent._preview_and_approve(
            {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
        )

    assert approved is False
    assert safe_agent.risk_policy_failed is True


@pytest.mark.asyncio
async def test_fail_on_risk_allows_lower_risk(safe_agent: SafeAgent) -> None:
    safe_agent.non_interactive = True
    safe_agent.fail_on_risk = RiskLevel.HIGH

    with patch.object(
        safe_agent.analyzer,
        "analyze",
        new_callable=AsyncMock,
        return_value=_mock_preview(RiskLevel.MEDIUM),
    ):
        approved = await safe_agent._preview_and_approve(
            {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
        )

    assert approved is True
    assert safe_agent.risk_policy_failed is False

