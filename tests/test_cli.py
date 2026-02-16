"""Smoke tests for CLI entry points."""

import json
from pathlib import Path

from click.testing import CliRunner

from safe_agent.cli import main

runner = CliRunner()


def test_safe_agent_help() -> None:
    """CLI responds to --help without error."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Safe Agent" in result.output or "safe-agent" in result.output.lower()
    assert "dry-run" in result.output or "dry_run" in result.output


def test_safe_agent_requires_task_without_args() -> None:
    """CLI exits non-zero when no task and no --file/--interactive."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert "task" in result.output.lower() or "ANTHROPIC" in result.output


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

    monkeypatch.setattr("safe_agent.cli.SafeAgent", DummyAgent)

    with runner.isolated_filesystem():
        summary_path = Path("out/summary.md")
        report_path = Path("out/policy.json")

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
            ],
            env={"ANTHROPIC_API_KEY": "test-key"},
        )

        assert result.exit_code == 0
        assert summary_path.exists()
        assert "Safe Agent CI Summary" in summary_path.read_text(encoding="utf-8")
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "passed"
