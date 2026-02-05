"""Smoke tests for CLI entry points."""

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
