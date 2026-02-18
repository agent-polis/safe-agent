"""Adversarial evaluation harness for Safe Agent governance behavior."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from agent_polis.actions.models import RiskLevel

from safe_agent.agent import SafeAgent


@dataclass
class _Preview:
    """Minimal preview object compatible with SafeAgent._preview_and_approve."""

    risk_level: RiskLevel
    risk_factors: list[str]
    file_changes: list[Any]


def _parse_risk_level(value: str) -> RiskLevel:
    key = str(value).strip().upper()
    return RiskLevel[key]


async def _run_case(case: dict[str, Any], *, workdir: str) -> dict[str, Any]:
    agent_cfg = case.get("agent", {})
    expected = case.get("expected", {})
    change = case["change"]
    risk_level = _parse_risk_level(case.get("risk_level", "low"))

    fail_on_risk = None
    if agent_cfg.get("fail_on_risk"):
        fail_on_risk = _parse_risk_level(str(agent_cfg["fail_on_risk"]))

    agent = SafeAgent(
        working_directory=workdir,
        non_interactive=bool(agent_cfg.get("non_interactive", True)),
        dry_run=bool(agent_cfg.get("dry_run", False)),
        fail_on_risk=fail_on_risk,
        policy_preset=agent_cfg.get("policy_preset"),
    )

    preview = _Preview(risk_level=risk_level, risk_factors=[], file_changes=[])

    async def _fake_analyze(_: Any) -> _Preview:
        return preview

    agent.analyzer.analyze = _fake_analyze  # type: ignore[assignment]

    approved = await agent._preview_and_approve(change)
    outcome = agent._governance_events[-1]["outcome"] if agent._governance_events else "no_event"

    checks = {
        "approved": approved == bool(expected.get("approved")),
        "outcome": outcome == expected.get("outcome"),
    }
    if "risk_policy_failed" in expected:
        checks["risk_policy_failed"] = agent.risk_policy_failed == bool(expected["risk_policy_failed"])
    if "governance_policy_failed" in expected:
        checks["governance_policy_failed"] = (
            agent.governance_policy_failed == bool(expected["governance_policy_failed"])
        )

    passed = all(checks.values())
    return {
        "id": case["id"],
        "description": case.get("description", ""),
        "approved": approved,
        "expected_approved": bool(expected.get("approved")),
        "outcome": outcome,
        "expected_outcome": expected.get("outcome"),
        "risk_policy_failed": agent.risk_policy_failed,
        "governance_policy_failed": agent.governance_policy_failed,
        "checks": checks,
        "passed": passed,
    }


def run_adversarial_suite(cases: list[dict[str, Any]], *, workdir: str | None = None) -> dict[str, Any]:
    """Run adversarial fixtures against SafeAgent and return a structured report."""
    previous_key = os.environ.get("ANTHROPIC_API_KEY")
    if not previous_key:
        os.environ["ANTHROPIC_API_KEY"] = "adversarial-suite-placeholder"

    try:
        if workdir is not None:
            results = [asyncio.run(_run_case(case, workdir=workdir)) for case in cases]
        else:
            with TemporaryDirectory(prefix="safe-agent-adversarial-") as tmp:
                results = [asyncio.run(_run_case(case, workdir=tmp)) for case in cases]
    finally:
        if previous_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)

    passed = sum(1 for item in results if item["passed"])
    failed = len(results) - passed
    return {
        "suite_version": "1",
        "total_cases": len(results),
        "passed_cases": passed,
        "failed_cases": failed,
        "all_passed": failed == 0,
        "results": results,
    }


def run_adversarial_suite_from_file(path: str | Path, *, workdir: str | None = None) -> dict[str, Any]:
    """Load a JSON suite file and run the adversarial evaluation."""
    suite_path = Path(path)
    payload = json.loads(suite_path.read_text(encoding="utf-8"))
    cases = payload.get("cases", payload)
    if not isinstance(cases, list):
        raise ValueError("Adversarial suite JSON must contain a list of cases or a {'cases': [...]} object.")
    result = run_adversarial_suite(cases, workdir=workdir)
    result["source"] = str(suite_path)
    return result


def render_adversarial_markdown(report: dict[str, Any]) -> str:
    """Render adversarial report as a markdown table."""
    status = "PASS" if report.get("all_passed") else "FAIL"
    status_icon = "✅" if report.get("all_passed") else "❌"
    lines = [
        "### Safe Agent Adversarial Evaluation",
        f"- Result: {status_icon} {status}",
        f"- Cases: {report.get('passed_cases', 0)}/{report.get('total_cases', 0)} passed",
        "",
        "| Case | Expected | Actual | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in report.get("results", []):
        expected = f"{item.get('expected_outcome')} / approved={item.get('expected_approved')}"
        actual = f"{item.get('outcome')} / approved={item.get('approved')}"
        mark = "✅" if item.get("passed") else "❌"
        lines.append(f"| {item.get('id')} | `{expected}` | `{actual}` | {mark} |")
    return "\n".join(lines)
