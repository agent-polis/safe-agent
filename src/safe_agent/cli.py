"""
Safe Agent CLI - Run AI coding tasks with built-in safety.

Usage:
    safe-agent "refactor auth to use JWT"
    safe-agent --file task.md
    safe-agent --interactive
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

from safe_agent import __version__
from safe_agent.agent import SafeAgent

console = Console()


def _write_json_artifact(path: str, payload: dict) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def _build_machine_output(agent: Any, result: dict) -> dict:
    if hasattr(agent, "build_machine_report"):
        report = agent.build_machine_report(run_success=bool(result.get("success", False)))  # type: ignore[attr-defined]
        if isinstance(report, dict):
            return report

    # Compatibility fallback for tests/mocks that don't implement build_machine_report.
    policy_report = {}
    if hasattr(agent, "build_policy_report"):
        candidate = agent.build_policy_report()  # type: ignore[attr-defined]
        if isinstance(candidate, dict):
            policy_report = candidate
    return {
        "schema_version": "1",
        "run_status": "passed" if result.get("success", False) else "failed",
        "success": bool(result.get("success", False)),
        "policy_report": policy_report,
    }


@click.command()
@click.version_option(version=__version__, prog_name="safe-agent")
@click.argument("task", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read task from file")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--auto-approve-low", is_flag=True, help="Auto-approve low-risk changes")
@click.option("--dry-run", is_flag=True, help="Preview only, don't execute")
@click.option("--non-interactive", is_flag=True, help="Run without prompts (CI-friendly)")
@click.option(
    "--fail-on-risk",
    type=click.Choice(["low", "medium", "high", "critical"], case_sensitive=False),
    default=None,
    help="Exit non-zero if any change meets/exceeds this risk level",
)
@click.option(
    "--policy",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to a policy file (JSON/YAML) within the working directory.",
)
@click.option(
    "--policy-preset",
    type=str,
    default=None,
    help="Use a bundled impact-preview policy preset (e.g. startup, fintech, games).",
)
@click.option(
    "--list-policy-presets",
    is_flag=True,
    help="List available policy presets and exit.",
)
@click.option(
    "--adversarial-suite",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Run adversarial evaluation from a suite JSON file and exit.",
)
@click.option(
    "--adversarial-json-out",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write adversarial evaluation JSON report to a file.",
)
@click.option(
    "--adversarial-markdown-out",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write adversarial evaluation markdown report to a file.",
)
@click.option(
    "--adversarial-verbose",
    is_flag=True,
    help="Print full impact preview output during adversarial runs (default: quiet).",
)
@click.option(
    "--diff-gate",
    is_flag=True,
    help="Analyze current git diff without calling an LLM (no API key required).",
)
@click.option(
    "--diff-ref",
    type=str,
    default=None,
    help="Base git ref for --diff-gate (e.g. origin/main, HEAD~1).",
)
@click.option("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
@click.option("--audit-export", type=click.Path(), help="Export audit trail to JSON file")
@click.option("--compliance-mode", is_flag=True, help="Enable strict compliance mode (disables auto-approve)")
@click.option(
    "--ci-summary",
    is_flag=True,
    help="Print a concise markdown CI summary block.",
)
@click.option(
    "--ci-summary-file",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write CI summary markdown to a file.",
)
@click.option(
    "--policy-report",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write machine-readable policy/scanner report JSON.",
)
@click.option(
    "--safety-scorecard",
    is_flag=True,
    help="Print a markdown safety scorecard block.",
)
@click.option(
    "--safety-scorecard-file",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write markdown safety scorecard to a file.",
)
@click.option(
    "--json-out",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write machine-readable run result JSON.",
)
def main(
    task: str | None,
    file: str | None,
    interactive: bool,
    auto_approve_low: bool,
    dry_run: bool,
    non_interactive: bool,
    fail_on_risk: str | None,
    policy: str | None,
    policy_preset: str | None,
    list_policy_presets: bool,
    adversarial_suite: str | None,
    adversarial_json_out: str | None,
    adversarial_markdown_out: str | None,
    adversarial_verbose: bool,
    diff_gate: bool,
    diff_ref: str | None,
    model: str,
    audit_export: str | None,
    compliance_mode: bool,
    ci_summary: bool,
    ci_summary_file: str | None,
    policy_report: str | None,
    safety_scorecard: bool,
    safety_scorecard_file: str | None,
    json_out: str | None,
):
    """
    Safe Agent - An AI coding agent you can actually trust.
    
    Run coding tasks with built-in impact preview. See exactly what will
    change before any file is modified.
    
    Examples:
    
        safe-agent "add error handling to api.py"
        
        safe-agent "refactor the auth module" --dry-run
        
        safe-agent --interactive
    """
    if list_policy_presets:
        try:
            from agent_polis.governance.presets import list_policy_presets as _list_policy_presets
        except ModuleNotFoundError:
            console.print(
                "[red]Policy presets require impact-preview>=0.2.2.[/red] "
                "Upgrade with: pip install -U impact-preview"
            )
            sys.exit(1)

        presets = _list_policy_presets()
        if not presets:
            console.print("No presets available.")
            sys.exit(0)
        console.print("Available policy presets:")
        for preset in presets:
            console.print(f"- {preset.id}: {preset.name} — {preset.description}")
        sys.exit(0)

    if adversarial_suite:
        from safe_agent.adversarial import (
            render_adversarial_markdown,
            run_adversarial_suite_from_file,
        )

        result = run_adversarial_suite_from_file(
            adversarial_suite,
            workdir=os.getcwd(),
            verbose=adversarial_verbose,
        )
        markdown = render_adversarial_markdown(result)
        console.print(markdown)

        if adversarial_json_out:
            json_path = Path(adversarial_json_out)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            console.print(f"[dim]Adversarial JSON report written to: {json_path}[/dim]")
        if adversarial_markdown_out:
            md_path = Path(adversarial_markdown_out)
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(markdown + "\n", encoding="utf-8")
            console.print(f"[dim]Adversarial markdown report written to: {md_path}[/dim]")

        if not result.get("all_passed", False):
            sys.exit(3)
        sys.exit(0)

    inferred_non_interactive = non_interactive or bool(os.environ.get("CI")) or (
        not sys.stdin.isatty() or not sys.stdout.isatty()
    )
    fail_on_risk_level = None
    if fail_on_risk:
        from agent_polis.actions.models import RiskLevel

        fail_on_risk_level = RiskLevel(fail_on_risk.lower())
    
    runner: Any
    task_for_runner: str | None = None

    if diff_gate:
        if task or file or interactive:
            console.print("[yellow]Ignoring task input in --diff-gate mode.[/yellow]")
        console.print(
            Panel(
                f"Analyzing git diff in: {os.getcwd()}\n"
                f"Base ref: {diff_ref or 'HEAD + working tree'}",
                title="🧪 Diff Gate",
                border_style="cyan",
            )
        )
    else:
        # Check for API key
        if not os.environ.get("ANTHROPIC_API_KEY"):
            console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set[/red]")
            console.print("\nGet your API key at: https://console.anthropic.com/")
            console.print("Then run: export ANTHROPIC_API_KEY=your-key-here")
            sys.exit(1)

        # Get task
        if file:
            with open(file) as f:
                task = f.read().strip()
        elif interactive:
            console.print(Panel(
                "[bold]Safe Agent[/bold] - Interactive Mode\n\n"
                "Type your coding task, then press Enter twice to submit.\n"
                "Type 'quit' to exit.",
                title="🛡️ Safe Agent",
            ))
            lines = []
            while True:
                try:
                    line = input()
                    if line.lower() == "quit":
                        sys.exit(0)
                    if line == "" and lines and lines[-1] == "":
                        break
                    lines.append(line)
                except EOFError:
                    break
            task = "\n".join(lines).strip()

        if not task:
            console.print("[red]Error: No task provided[/red]")
            console.print("\nUsage: safe-agent \"your task here\"")
            sys.exit(1)

        task_for_runner = task
        console.print(Panel(task_for_runner, title="📋 Task", border_style="blue"))

    # Create runner and execute
    try:
        if diff_gate:
            from safe_agent.diff_gate import DiffGateRunner

            runner = DiffGateRunner(
                working_directory=os.getcwd(),
                diff_ref=diff_ref,
                fail_on_risk=fail_on_risk_level,
                policy_path=policy,
                policy_preset=policy_preset,
                compliance_mode=compliance_mode,
            )
        else:
            runner = SafeAgent(
                model=model,
                auto_approve_low_risk=auto_approve_low,
                dry_run=dry_run,
                non_interactive=inferred_non_interactive,
                fail_on_risk=fail_on_risk_level,
                audit_export_path=audit_export,
                compliance_mode=compliance_mode,
                policy_path=policy,
                policy_preset=policy_preset,
            )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        if policy_preset:
            console.print("Use [bold]safe-agent --list-policy-presets[/bold] to see valid preset IDs.")
        sys.exit(1)
    except RuntimeError as exc:
        if json_out:
            output_path = _write_json_artifact(
                json_out,
                {
                    "schema_version": "1",
                    "run_status": "error",
                    "success": False,
                    "error": str(exc),
                },
            )
            console.print(f"[dim]Machine run report written to: {output_path}[/dim]")
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    
    try:
        if diff_gate:
            result = asyncio.run(runner.run())
        else:
            if task_for_runner is None:
                raise RuntimeError("Task missing in task mode.")
            result = asyncio.run(runner.run(task_for_runner))
        if ci_summary or ci_summary_file:
            summary = runner.build_ci_summary()
            if ci_summary:
                console.print()
                console.print(summary)
            if ci_summary_file:
                summary_path = Path(ci_summary_file)
                summary_path.parent.mkdir(parents=True, exist_ok=True)
                summary_path.write_text(summary + "\n", encoding="utf-8")
                console.print(f"[dim]CI summary written to: {summary_path}[/dim]")

        if policy_report:
            report = runner.build_policy_report()
            report_path = Path(policy_report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            console.print(f"[dim]Policy report written to: {report_path}[/dim]")

        if safety_scorecard or safety_scorecard_file:
            scorecard = runner.build_safety_scorecard()
            if safety_scorecard:
                console.print()
                console.print(scorecard)
            if safety_scorecard_file:
                scorecard_path = Path(safety_scorecard_file)
                scorecard_path.parent.mkdir(parents=True, exist_ok=True)
                scorecard_path.write_text(scorecard + "\n", encoding="utf-8")
                console.print(f"[dim]Safety scorecard written to: {scorecard_path}[/dim]")

        if json_out:
            machine_output = _build_machine_output(runner, result)
            output_path = _write_json_artifact(json_out, machine_output)
            console.print(f"[dim]Machine run report written to: {output_path}[/dim]")

        if not result.get("success", False):
            sys.exit(2)
    except RuntimeError as exc:
        if json_out:
            output_path = _write_json_artifact(
                json_out,
                {
                    "schema_version": "1",
                    "run_status": "error",
                    "success": False,
                    "error": str(exc),
                },
            )
            console.print(f"[dim]Machine run report written to: {output_path}[/dim]")
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        if json_out:
            output_path = _write_json_artifact(
                json_out,
                {
                    "schema_version": "1",
                    "run_status": "interrupted",
                    "success": False,
                    "error": "Interrupted by user",
                },
            )
            console.print(f"[dim]Machine run report written to: {output_path}[/dim]")
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
