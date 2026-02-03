"""
CLI helpers to prepare and record a Safe Agent demo.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from safe_agent import __version__
from safe_agent.demo import (
    DEMO_TASK,
    build_asciinema_command,
    convert_cast_to_gif,
    ensure_tools_available,
    prepare_demo_repo,
)

console = Console()


@click.group()
def main() -> None:
    """Create and record the Safe Agent demo scenario."""


@main.command()
@click.option(
    "--output",
    "-o",
    default=None,
    help="Directory to place the demo repo (default: temp dir).",
)
def prepare(output: str | None) -> None:
    """Set up a throwaway repo with the risky config change."""

    repo = prepare_demo_repo(output)
    console.print(
        Panel(
            f"Demo repo ready at: {repo}\n\n"
            f"Task: \"{DEMO_TASK}\"\n"
            "Next: run `safe-agent --dry-run \"{task}\"` inside that directory.\n"
            "To record, see `safe-agent-demo record`.",
            title="Demo Prepared",
        )
    )


@main.command()
@click.option(
    "--repo",
    default=None,
    help="Path to the prepared demo repo (defaults to CWD).",
)
def record(repo: str | None) -> None:
    """
    Print record commands (asciinema + GIF) for the demo.

    We don't auto-run to avoid messing with user terminals; copy/paste instead.
    """

    repo_path = Path(repo) if repo else Path.cwd()
    tools = ensure_tools_available(["asciinema", "agg"])
    missing = [name for name, ok in tools.items() if not ok]

    cmd = build_asciinema_command(repo_path)
    gif_cmds = convert_cast_to_gif(Path("demo.cast"), Path("demo.gif"))

    console.print(Panel("Recording commands", title="Demo"))
    console.print(f"Repo: {repo_path}")
    console.print("\nRun to record:")
    console.print(" ".join(cmd))
    console.print("\nConvert to GIF (requires agg):")
    console.print(" ".join(gif_cmds[1]))

    if missing:
        console.print(
            f"[yellow]Missing tools:[/yellow] {', '.join(missing)}. "
            "Install asciinema (and agg for GIF) before recording."
        )
    else:
        console.print("[green]All required tools detected.[/green]")


@main.command()
def version() -> None:
    """Show version for scripting."""

    console.print(f"safe-agent-demo {__version__}")


if __name__ == "__main__":
    main()
