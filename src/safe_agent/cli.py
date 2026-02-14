"""
Safe Agent CLI - Run AI coding tasks with built-in safety.

Usage:
    safe-agent "refactor auth to use JWT"
    safe-agent --file task.md
    safe-agent --interactive
"""

import asyncio
import os
import sys

import click
from rich.console import Console
from rich.panel import Panel

from safe_agent.agent import SafeAgent

console = Console()


@click.command()
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
@click.option("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
@click.option("--audit-export", type=click.Path(), help="Export audit trail to JSON file")
@click.option("--compliance-mode", is_flag=True, help="Enable strict compliance mode (disables auto-approve)")
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
    model: str,
    audit_export: str | None,
    compliance_mode: bool,
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
    
    # Show task
    console.print(Panel(task, title="📋 Task", border_style="blue"))

    inferred_non_interactive = non_interactive or bool(os.environ.get("CI")) or (
        not sys.stdin.isatty() or not sys.stdout.isatty()
    )
    fail_on_risk_level = None
    if fail_on_risk:
        from agent_polis.actions.models import RiskLevel

        fail_on_risk_level = RiskLevel(fail_on_risk.lower())
    
    # Create agent and run
    agent = SafeAgent(
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
    
    try:
        result = asyncio.run(agent.run(task))
        if not result.get("success", False):
            sys.exit(2)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
