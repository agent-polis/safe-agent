"""Tests for policy-as-code enforcement and scanner integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agent_polis.actions.models import RiskLevel

from safe_agent.agent import SafeAgent


def _mock_preview(level: RiskLevel) -> object:
    return type(
        "Preview",
        (),
        {
            "risk_level": level,
            "risk_factors": [],
            "file_changes": [],
        },
    )()


def _write_policy(base_dir: Path, policy: dict) -> Path:
    path = base_dir / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_policy_deny_blocks_without_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    workdir = tmp_path / "repo"
    workdir.mkdir(parents=True, exist_ok=True)

    policy_path = _write_policy(
        workdir,
        {
            "version": "test-1",
            "defaults": {"decision": "require_approval"},
            "rules": [
                {
                    "id": "deny-foo",
                    "decision": "deny",
                    "priority": 0,
                    "path_globs": ["*foo.py"],
                }
            ],
        },
    )

    agent = SafeAgent(
        working_directory=str(workdir),
        non_interactive=False,
        policy_path=str(policy_path),
    )

    with patch.object(
        agent.analyzer,
        "analyze",
        new_callable=AsyncMock,
        return_value=_mock_preview(RiskLevel.LOW),
    ):
        with patch("safe_agent.agent.Confirm.ask", return_value=True) as confirm:
            approved = await agent._preview_and_approve(
                {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
            )

    assert approved is False
    assert agent.governance_policy_failed is True
    assert agent.governance_policy_reason == "deny-foo"
    confirm.assert_not_called()


@pytest.mark.asyncio
async def test_policy_require_approval_prompts_in_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    workdir = tmp_path / "repo"
    workdir.mkdir(parents=True, exist_ok=True)

    policy_path = _write_policy(
        workdir,
        {
            "version": "test-1",
            "defaults": {"decision": "require_approval"},
            "rules": [],
        },
    )

    agent = SafeAgent(
        working_directory=str(workdir),
        non_interactive=False,
        policy_path=str(policy_path),
    )

    with patch.object(
        agent.analyzer,
        "analyze",
        new_callable=AsyncMock,
        return_value=_mock_preview(RiskLevel.LOW),
    ):
        with patch("safe_agent.agent.Confirm.ask", return_value=True) as confirm:
            approved = await agent._preview_and_approve(
                {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
            )

    assert approved is True
    assert agent.governance_policy_failed is False
    confirm.assert_called_once()


@pytest.mark.asyncio
async def test_policy_require_approval_rejects_in_non_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    workdir = tmp_path / "repo"
    workdir.mkdir(parents=True, exist_ok=True)

    policy_path = _write_policy(
        workdir,
        {
            "version": "test-1",
            "defaults": {"decision": "require_approval"},
            "rules": [],
        },
    )

    agent = SafeAgent(
        working_directory=str(workdir),
        non_interactive=True,
        policy_path=str(policy_path),
    )

    with patch.object(
        agent.analyzer,
        "analyze",
        new_callable=AsyncMock,
        return_value=_mock_preview(RiskLevel.LOW),
    ):
        approved = await agent._preview_and_approve(
            {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
        )

    assert approved is False
    assert agent.governance_policy_failed is False


@pytest.mark.asyncio
async def test_policy_allow_auto_approves_in_non_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    workdir = tmp_path / "repo"
    workdir.mkdir(parents=True, exist_ok=True)

    policy_path = _write_policy(
        workdir,
        {
            "version": "test-1",
            "defaults": {"decision": "require_approval"},
            "rules": [
                {
                    "id": "allow-foo",
                    "decision": "allow",
                    "priority": 0,
                    "path_globs": ["*foo.py"],
                }
            ],
        },
    )

    agent = SafeAgent(
        working_directory=str(workdir),
        non_interactive=True,
        policy_path=str(policy_path),
    )

    with patch.object(
        agent.analyzer,
        "analyze",
        new_callable=AsyncMock,
        return_value=_mock_preview(RiskLevel.HIGH),
    ):
        approved = await agent._preview_and_approve(
            {"action": "modify", "path": "foo.py", "description": "x", "content": "x"}
        )

    assert approved is True
