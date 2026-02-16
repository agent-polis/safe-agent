"""Tests for CI summary and machine-readable policy reporting."""

from __future__ import annotations

from agent_polis.actions.models import RiskLevel

from safe_agent.agent import SafeAgent


def test_ci_summary_includes_blocking_rules_and_actions(safe_agent: SafeAgent) -> None:
    safe_agent.max_risk_level_seen = RiskLevel.HIGH
    safe_agent.governance_policy_failed = True
    safe_agent.governance_policy_reason = "deny-secrets"
    safe_agent._record_governance_event(
        path=".env",
        action="modify",
        risk_level=RiskLevel.HIGH,
        policy_decision="deny",
        matched_rule_id="deny-secrets",
        scanner_severity="medium",
        scanner_reason_ids=["prompt_injection"],
        outcome="blocked_by_policy_deny",
    )

    summary = safe_agent.build_ci_summary()

    assert "Safe Agent CI Summary" in summary
    assert "❌ FAIL" in summary
    assert "`deny-secrets`" in summary
    assert "prompt_injection" in summary
    assert "Recommended next actions" in summary


def test_policy_report_contains_expected_fields(safe_agent: SafeAgent) -> None:
    safe_agent.max_risk_level_seen = RiskLevel.MEDIUM
    safe_agent._record_governance_event(
        path="foo.py",
        action="modify",
        risk_level=RiskLevel.MEDIUM,
        policy_decision="allow",
        matched_rule_id=None,
        scanner_severity="none",
        scanner_reason_ids=[],
        outcome="approved_non_interactive",
    )

    report = safe_agent.build_policy_report()

    assert report["status"] == "passed"
    assert report["max_risk_level_seen"] == "medium"
    assert report["blocking_rule_ids"] == []
    assert isinstance(report["recommended_next_actions"], list)
    assert report["events"][0]["path"] == "foo.py"
