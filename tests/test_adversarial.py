"""Tests for adversarial evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path

from safe_agent.adversarial import render_adversarial_markdown, run_adversarial_suite_from_file


def _write_suite(path: Path, expected_outcome: str) -> None:
    payload = {
        "cases": [
            {
                "id": "case-1",
                "risk_level": "low",
                "change": {
                    "action": "modify",
                    "path": "src/example.py",
                    "description": "example",
                    "content": "print('ok')\n",
                },
                "agent": {"non_interactive": True, "dry_run": False},
                "expected": {"outcome": expected_outcome, "approved": True},
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_adversarial_suite_report_passes(tmp_path: Path) -> None:
    suite = tmp_path / "suite.json"
    _write_suite(suite, expected_outcome="approved_non_interactive")

    report = run_adversarial_suite_from_file(suite, workdir=str(tmp_path))

    assert report["all_passed"] is True
    assert report["passed_cases"] == 1
    md = render_adversarial_markdown(report)
    assert "Safe Agent Adversarial Evaluation" in md
    assert "✅ PASS" in md


def test_adversarial_suite_report_fails_when_expectation_mismatch(tmp_path: Path) -> None:
    suite = tmp_path / "suite.json"
    _write_suite(suite, expected_outcome="blocked_by_policy_deny")

    report = run_adversarial_suite_from_file(suite, workdir=str(tmp_path))

    assert report["all_passed"] is False
    assert report["failed_cases"] == 1
