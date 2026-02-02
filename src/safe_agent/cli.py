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
from rich.prompt import Confirm

from safe_agent.agent import SafeAgent

console = Console()


@click.command()
@click.argument("task", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read task from file")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--auto-approve-low", is_flag=True, help="Auto-approve low-risk changes")
@click.option("--dry-run", is_flag=True, help="Preview only, don't execute")
@click.option("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
def main(
    task: str | None,
    file: str | None,
    interactive: bool,
    auto_approve_low: bool,
    dry_run: bool,
    model: str,
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
    
    # Create agent and run
    agent = SafeAgent(
        model=model,
        auto_approve_low_risk=auto_approve_low,
        dry_run=dry_run,
    )
    
    try:
        asyncio.run(agent.run(task))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
