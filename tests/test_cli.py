"""Smoke tests for CLI entry points."""

import json
from pathlib import Path

from click.testing import CliRunner

from safe_agent import __version__
from safe_agent.cli import main

runner = CliRunner()


def test_safe_agent_help() -> None:
    """CLI responds to --help without error."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Safe Agent" in result.output or "safe-agent" in result.output.lower()
    assert "dry-run" in result.output or "dry_run" in result.output


def test_safe_agent_version_option() -> None:
    """CLI responds to --version with package version."""
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "safe-agent" in result.output.lower()
    assert __version__ in result.output


def test_safe_agent_requires_task_without_args() -> None:
    """CLI exits non-zero when no task and no --file/--interactive."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert "task" in result.output.lower() or "ANTHROPIC" in result.output


def test_adversarial_suite_runs_without_api_key() -> None:
    payload = {
        "cases": [
            {
                "id": "adversarial-low",
                "risk_level": "low",
                "change": {
                    "action": "modify",
                    "path": "src/foo.py",
                    "description": "low risk",
                    "content": "print('ok')\n",
                },
                "agent": {"non_interactive": True, "dry_run": False},
                "expected": {"outcome": "approved_non_interactive", "approved": True},
            }
        ]
    }

    with runner.isolated_filesystem():
        suite_path = Path("suite.json")
        suite_path.write_text(json.dumps(payload), encoding="utf-8")

        result = runner.invoke(main, ["--adversarial-suite", str(suite_path)])
        assert result.exit_code == 0
        assert "Safe Agent Adversarial Evaluation" in result.output
        assert "Impact Preview" not in result.output


def test_adversarial_suite_exits_3_when_case_fails() -> None:
    payload = {
        "cases": [
            {
                "id": "adversarial-fail",
                "risk_level": "low",
                "change": {
                    "action": "modify",
                    "path": "src/foo.py",
                    "description": "low risk",
                    "content": "print('ok')\n",
                },
                "agent": {"non_interactive": True, "dry_run": False},
                "expected": {"outcome": "blocked_by_policy_deny", "approved": True},
            }
        ]
    }

    with runner.isolated_filesystem():
        suite_path = Path("suite.json")
        suite_path.write_text(json.dumps(payload), encoding="utf-8")
        json_out = Path("out/report.json")
        md_out = Path("out/report.md")

        result = runner.invoke(
            main,
            [
                "--adversarial-suite",
                str(suite_path),
                "--adversarial-json-out",
                str(json_out),
                "--adversarial-markdown-out",
                str(md_out),
            ],
        )
        assert result.exit_code == 3
        assert json_out.exists()
        assert md_out.exists()


def test_safe_agent_mcp_imports() -> None:
    """MCP server module can be imported and has run entry point."""
    from safe_agent.mcp_server import run
    assert callable(run)


def test_ci_summary_and_policy_report_files_are_written(monkeypatch) -> None:
    """CLI writes CI summary and policy report artifacts when requested."""

    class DummyAgent:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def run(self, task: str) -> dict:
            return {"success": True}

        def build_ci_summary(self) -> str:
            return "### Safe Agent CI Summary\n- Result: ✅ PASS\n"

        def build_policy_report(self) -> dict:
            return {"status": "passed", "events": []}

        def build_safety_scorecard(self) -> str:
            return "### Safe Agent Safety Scorecard\n- Result: ✅ PASS\n"

    monkeypatch.setattr("safe_agent.cli.SafeAgent", DummyAgent)

    with runner.isolated_filesystem():
        summary_path = Path("out/summary.md")
        report_path = Path("out/policy.json")
        scorecard_path = Path("out/scorecard.md")

        result = runner.invoke(
            main,
            [
                "scan repo",
                "--non-interactive",
                "--dry-run",
                "--ci-summary-file",
                str(summary_path),
                "--policy-report",
                str(report_path),
                "--safety-scorecard-file",
                str(scorecard_path),
            ],
            env={"ANTHROPIC_API_KEY": "test-key"},
        )

        assert result.exit_code == 0
        assert summary_path.exists()
        assert "Safe Agent CI Summary" in summary_path.read_text(encoding="utf-8")
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "passed"
        assert scorecard_path.exists()
        assert "Safety Scorecard" in scorecard_path.read_text(encoding="utf-8")


def test_invalid_policy_preset_shows_guidance(monkeypatch) -> None:
    """CLI should surface actionable guidance when preset lookup fails."""

    class BadPresetAgent:
        def __init__(self, **kwargs) -> None:
            raise ValueError("Unknown policy preset: nope")

    monkeypatch.setattr("safe_agent.cli.SafeAgent", BadPresetAgent)
    result = runner.invoke(
        main,
        ["scan repo", "--policy-preset", "nope", "--dry-run", "--non-interactive"],
        env={"ANTHROPIC_API_KEY": "test-key"},
    )

    assert result.exit_code == 1
    assert "Unknown policy preset" in result.output
    assert "list-policy-presets" in result.output


def test_policy_preset_is_passed_to_agent(monkeypatch) -> None:
    """CLI wires --policy-preset through to SafeAgent constructor."""

    captured: dict[str, object] = {}

    class DummyAgent:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        async def run(self, task: str) -> dict:
            return {"success": True}

        def build_ci_summary(self) -> str:
            return "ok"

        def build_policy_report(self) -> dict:
            return {"status": "passed"}

    monkeypatch.setattr("safe_agent.cli.SafeAgent", DummyAgent)
    result = runner.invoke(
        main,
        ["scan repo", "--policy-preset", "fintech", "--dry-run", "--non-interactive"],
        env={"ANTHROPIC_API_KEY": "test-key"},
    )

    assert result.exit_code == 0
    assert captured.get("policy_preset") == "fintech"


def test_policy_report_written_even_when_run_fails(monkeypatch) -> None:
    """CI artifacts should still be written when SafeAgent exits non-success."""

    class FailingAgent:
        def __init__(self, **kwargs) -> None:
            pass

        async def run(self, task: str) -> dict:
            return {"success": False}

        def build_ci_summary(self) -> str:
            return "### Safe Agent CI Summary\n- Result: FAIL\n"

        def build_policy_report(self) -> dict:
            return {"status": "failed", "events": [{"outcome": "blocked_by_fail_on_risk"}]}

        def build_safety_scorecard(self) -> str:
            return "### Safe Agent Safety Scorecard\n- Result: ❌ FAIL\n"

    monkeypatch.setattr("safe_agent.cli.SafeAgent", FailingAgent)

    with runner.isolated_filesystem():
        report_path = Path("out/policy.json")
        scorecard_path = Path("out/scorecard.md")
        result = runner.invoke(
            main,
            [
                "scan repo",
                "--non-interactive",
                "--dry-run",
                "--policy-report",
                str(report_path),
                "--safety-scorecard-file",
                str(scorecard_path),
            ],
            env={"ANTHROPIC_API_KEY": "test-key"},
        )
        assert result.exit_code == 2
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "failed"
        assert scorecard_path.exists()
        assert "❌ FAIL" in scorecard_path.read_text(encoding="utf-8")
