"""CLI for generating and queuing marketing assets."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from safe_agent.marketing import (
    MarketingAssets,
    append_experiment_log,
    assets_markdown,
    generate_marketing_assets,
    queue_posts,
    update_readme_hero,
    write_assets_json,
    write_assets_markdown,
)

console = Console()


def _require_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]ANTHROPIC_API_KEY is not set.[/red] Set it to generate copy.")
        sys.exit(1)


@click.group()
def main() -> None:
    """Marketing helper commands for Safe Agent launches."""


@main.command()
@click.option("--product", default="Safe Agent", show_default=True, help="Product name")
@click.option("--audience", required=True, help="Target audience description")
@click.option("--hypothesis", required=True, help="Hypothesis or angle to test")
@click.option(
    "--base-url",
    default="https://github.com/agent-polis/safe-agent",
    show_default=True,
    help="Canonical link to promote",
)
@click.option("--campaign", default=None, help="Campaign slug; defaults to today's date")
@click.option("--variants", default=2, show_default=True, help="Number of headline variants")
@click.option(
    "--utm-medium",
    multiple=True,
    default=["hn", "twitter", "linkedin"],
    show_default=True,
    help="Channels to embed in UTM links",
)
@click.option("--json-out", default="marketing/latest_assets.json", show_default=True)
@click.option("--md-out", default="marketing/latest_assets.md", show_default=True)
@click.option("--update-readme", is_flag=True, help="Apply README hero update using best variant")
@click.option(
    "--readme-path",
    default="README.md",
    show_default=True,
    help="README to update when --update-readme is set",
)
@click.option("--model", default=None, help="Override Anthropic model")
@click.option("--dry-run", is_flag=True, help="Skip file writes; print to console only")
def generate(
    product: str,
    audience: str,
    hypothesis: str,
    base_url: str,
    campaign: Optional[str],
    variants: int,
    utm_medium: tuple[str, ...],
    json_out: str,
    md_out: str,
    update_readme: bool,
    readme_path: str,
    model: Optional[str],
    dry_run: bool,
) -> None:
    """Generate a bundle of headlines + channel copy."""

    _require_api_key()
    campaign_slug = campaign or datetime.utcnow().strftime("%Y-%m-%d")
    bundle = generate_marketing_assets(
        product=product,
        audience=audience,
        hypothesis=hypothesis,
        base_url=base_url,
        campaign=campaign_slug,
        utm_mediums=utm_medium,
        variants=variants,
        model=model or os.environ.get("SAFE_AGENT_MODEL") or "claude-sonnet-4-20250514",
    )

    console.print(Panel("Generated marketing assets", title="Marketing"))
    console.print(assets_markdown(bundle))

    if dry_run:
        return

    json_path = write_assets_json(bundle, json_out)
    md_path = write_assets_markdown(bundle, md_out)
    console.print(f"Saved JSON -> {json_path}")
    console.print(f"Saved Markdown -> {md_path}")

    if update_readme and bundle.readme_hero:
        update_readme_hero(readme_path, bundle.readme_hero)
        console.print(f"Updated README hero in {readme_path}")
    elif update_readme:
        console.print("[yellow]No readme_hero provided by the model; README left untouched.[/yellow]")


@main.command()
@click.option("--assets", default="marketing/latest_assets.json", show_default=True, help="Asset JSON")
@click.option(
    "--slot",
    multiple=True,
    required=True,
    help="ISO datetime slot (UTC or with offset). Can be passed multiple times.",
)
@click.option(
    "--channel",
    multiple=True,
    default=["hn", "twitter", "linkedin"],
    show_default=True,
    help="Channels to queue",
)
@click.option("--out", default="marketing/queue.csv", show_default=True, help="CSV output")
def queue(assets: str, slot: tuple[str, ...], channel: tuple[str, ...], out: str) -> None:
    """Create a CSV posting queue with UTM links."""

    path = Path(assets)
    if not path.exists():
        console.print(f"[red]Asset file not found: {path}")
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    bundle = MarketingAssets.from_dict(data)

    # Basic validation of slots
    for s in slot:
        try:
            datetime.fromisoformat(s)
        except ValueError:
            console.print(f"[red]Invalid slot datetime: {s}. Use ISO 8601, e.g. 2026-02-05T15:00:00Z")
            sys.exit(1)

    out_path = queue_posts(bundle=bundle, slots=slot, channels=channel, out_path=out)
    console.print(f"Queued posts -> {out_path}")


@main.command()
@click.option("--repo", default="agent-polis/safe-agent", show_default=True, help="GitHub repo slug")
@click.option(
    "--token",
    default=None,
    help="GitHub token (defaults to GITHUB_TOKEN env)",
)
@click.option(
    "--clicks-csv",
    default=None,
    help="Optional CSV with `clicks` column to include in log (e.g., UTM export)",
)
@click.option(
    "--log",
    default="experiments/experiments.csv",
    show_default=True,
    help="Path to append experiment metrics",
)
def analytics(repo: str, token: str | None, clicks_csv: str | None, log: str) -> None:
    """
    Append GitHub metrics (and optional click data) to experiments log.
    """

    gh_token = token or os.environ.get("GITHUB_TOKEN")
    try:
        log_path = append_experiment_log(
            log_path=log,
            repo=repo,
            channel_clicks_csv=clicks_csv,
            token=gh_token,
        )
    except Exception as exc:
        console.print(f"[red]Failed to append analytics: {exc}[/red]")
        sys.exit(1)

    console.print(f"[green]Appended metrics to {log_path}[/green]")


if __name__ == "__main__":
    main()
