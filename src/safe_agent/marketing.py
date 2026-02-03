"""Utilities to generate and queue marketing assets for Safe Agent launches.

The goal is to let a "content + distribution" pair of agents create channel-
specific copy, update the README hero block, and queue posts with UTM tracking.

This module is intentionally side-effect-light: network calls are limited to
Anthropic for text generation; file writes are explicit and opt-in.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import anthropic
import httpx

DEFAULT_MODEL = "claude-sonnet-4-20250514"


@dataclass
class HeadlineVariant:
    """Represents a headline/angle pair for experimentation."""

    id: str
    headline: str
    angle: str
    notes: str | None = None


@dataclass
class ChannelCopy:
    """Copy tailored to a specific distribution channel."""

    hn_title: str
    hn_body: str
    tweet: str
    linkedin: str | None = None


@dataclass
class MarketingAssets:
    """Full bundle of marketing collateral for a single campaign."""

    product: str
    campaign: str
    audience: str
    hypothesis: str
    base_url: str
    utm_mediums: list[str]
    variants: list[HeadlineVariant] = field(default_factory=list)
    channel_copy: ChannelCopy | None = None
    readme_hero: str | None = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "product": self.product,
            "campaign": self.campaign,
            "audience": self.audience,
            "hypothesis": self.hypothesis,
            "base_url": self.base_url,
            "utm_mediums": self.utm_mediums,
            "variants": [vars(v) for v in self.variants],
            "channel_copy": vars(self.channel_copy) if self.channel_copy else None,
            "readme_hero": self.readme_hero,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MarketingAssets":
        variants = [HeadlineVariant(**v) for v in data.get("variants", [])]
        channel = data.get("channel_copy")
        channel_copy = ChannelCopy(**channel) if channel else None
        return cls(
            product=data["product"],
            campaign=data["campaign"],
            audience=data["audience"],
            hypothesis=data["hypothesis"],
            base_url=data["base_url"],
            utm_mediums=data.get("utm_mediums", []),
            variants=variants,
            channel_copy=channel_copy,
            readme_hero=data.get("readme_hero"),
            generated_at=data.get("generated_at", datetime.utcnow().isoformat()),
        )


def build_utm_url(base_url: str, medium: str, campaign: str, variant_id: str) -> str:
    """Attach UTM params to a URL for tracking purposes."""

    delimiter = "&" if "?" in base_url else "?"
    return (
        f"{base_url}{delimiter}utm_source={medium}"
        f"&utm_medium={medium}&utm_campaign={campaign}&utm_content={variant_id}"
    )


def _generation_prompt(product: str, audience: str, hypothesis: str, base_url: str) -> str:
    return f"""
You are a focused B2B copywriter creating concise launch assets.
Return JSON ONLY. No markdown, no commentary.
Schema:
{{
  "variants": [
    {{"id": "v1", "headline": "...", "angle": "...", "notes": "..."}},
    ...
  ],
  "hn_title": "Show HN: ...",
  "hn_body": "Short, scannable body with 3 bullets and a demo link to {base_url}.",
  "tweet": "Concise tweet with hook + link",
  "linkedin": "Optional LinkedIn blurb",
  "readme_hero": "40-60 word hero block for README"
}}
Rules:
- Target audience: {audience}
- Hypothesis to test: {hypothesis}
- Product: {product}
- Show two distinct angles: safety/guardrail and productivity/speed.
- Keep everything under 240 characters where reasonable; bullets allowed in hn_body.
"""


def generate_marketing_assets(
    *,
    product: str,
    audience: str,
    hypothesis: str,
    base_url: str,
    campaign: str,
    utm_mediums: Iterable[str],
    variants: int = 2,
    model: str = DEFAULT_MODEL,
) -> MarketingAssets:
    """Call Anthropic to build an asset bundle.

    We keep parsing simple and tolerant so the CLI can run unattended.
    """

    client = anthropic.Anthropic()
    system = _generation_prompt(product, audience, hypothesis, base_url)
    response = client.messages.create(
        model=model,
        system=system,
        max_tokens=1500,
        messages=[{"role": "user", "content": "Return the JSON now."}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`\n")
        text = text.split("\n", 1)[-1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse Anthropic response as JSON: {exc}: {text[:200]}")

    found_variants = data.get("variants", [])[:variants]
    headline_variants = [
        HeadlineVariant(
            id=item.get("id", f"v{i+1}"),
            headline=item.get("headline", ""),
            angle=item.get("angle", ""),
            notes=item.get("notes"),
        )
        for i, item in enumerate(found_variants)
    ]

    channel_copy = ChannelCopy(
        hn_title=data.get("hn_title", ""),
        hn_body=data.get("hn_body", ""),
        tweet=data.get("tweet", ""),
        linkedin=data.get("linkedin", ""),
    )

    return MarketingAssets(
        product=product,
        campaign=campaign,
        audience=audience,
        hypothesis=hypothesis,
        base_url=base_url,
        utm_mediums=list(utm_mediums),
        variants=headline_variants,
        channel_copy=channel_copy,
        readme_hero=data.get("readme_hero"),
    )


def write_assets_json(bundle: MarketingAssets, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(bundle.to_dict(), f, indent=2)
    return path


def assets_markdown(bundle: MarketingAssets) -> str:
    lines: list[str] = []
    lines.append(f"## Campaign: {bundle.campaign}")
    lines.append(f"Audience: {bundle.audience}")
    lines.append(f"Hypothesis: {bundle.hypothesis}")
    lines.append("")
    lines.append("### Headline Variants")
    for variant in bundle.variants:
        lines.append(f"- **{variant.id}** — {variant.headline} (_{variant.angle}_)")
        if variant.notes:
            lines.append(f"  - Notes: {variant.notes}")
    lines.append("")
    if bundle.channel_copy:
        cc = bundle.channel_copy
        lines.append("### Channel Copy")
        lines.append(f"- HN Title: {cc.hn_title}")
        lines.append(f"- HN Body: {cc.hn_body}")
        lines.append(f"- Tweet: {cc.tweet}")
        if cc.linkedin:
            lines.append(f"- LinkedIn: {cc.linkedin}")
        lines.append("")
    if bundle.readme_hero:
        lines.append("### README Hero")
        lines.append(bundle.readme_hero)
        lines.append("")
    lines.append(f"Generated at: {bundle.generated_at}")
    return "\n".join(lines)


def write_assets_markdown(bundle: MarketingAssets, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(assets_markdown(bundle), encoding="utf-8")
    return path


def update_readme_hero(readme_path: str | Path, new_hero: str) -> None:
    """Replace the hero block in README delimited by markers.

    Markers:
    <!-- HERO_START -->
    ... content ...
    <!-- HERO_END -->
    """

    path = Path(readme_path)
    text = path.read_text(encoding="utf-8")
    start = text.find("<!-- HERO_START -->")
    end = text.find("<!-- HERO_END -->")

    if start == -1 or end == -1 or end <= start:
        return  # Markers missing; leave README untouched.

    before = text[: start + len("<!-- HERO_START -->")]
    after = text[end:]
    hero_block = f"\n\n{new_hero.strip()}\n\n"
    path.write_text(before + hero_block + after, encoding="utf-8")


def queue_posts(
    *,
    bundle: MarketingAssets,
    slots: Iterable[str],
    channels: Iterable[str],
    out_path: str | Path,
) -> Path:
    """Create a CSV queue with scheduled posts and UTM links."""

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    slots_list = list(slots)
    channels_list = list(channels)

    # Cycle through variants for fairness
    variant_cycle = bundle.variants or [HeadlineVariant(id="v1", headline="", angle="")]

    rows: list[list[str]] = []
    idx = 0
    for slot in slots_list:
        for channel in channels_list:
            variant = variant_cycle[idx % len(variant_cycle)]
            idx += 1
            url = build_utm_url(bundle.base_url, channel, bundle.campaign, variant.id)
            copy = _copy_for_channel(bundle, channel)
            rows.append([slot, channel, variant.id, url, copy])

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["scheduled_at", "channel", "variant_id", "url", "copy"])
        writer.writerows(rows)

    return out


def _copy_for_channel(bundle: MarketingAssets, channel: str) -> str:
    cc = bundle.channel_copy
    if not cc:
        return ""
    channel = channel.lower()
    if channel in {"hn", "hackernews"}:
        return f"{cc.hn_title} — {cc.hn_body}"
    if channel in {"twitter", "x"}:
        return cc.tweet
    if channel in {"linkedin", "li"}:
        return cc.linkedin or ""
    return cc.hn_body


# ------------ Analytics helpers ------------

def fetch_github_repo_stats(repo: str, token: Optional[str] = None) -> dict:
    """
    Fetch high-level GitHub repo stats (stars, forks, watchers, issues).
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return {
        "stargazers_count": data.get("stargazers_count", 0),
        "forks_count": data.get("forks_count", 0),
        "watchers_count": data.get("subscribers_count", 0) or data.get("watchers_count", 0),
        "open_issues_count": data.get("open_issues_count", 0),
    }


def fetch_github_traffic(repo: str, token: Optional[str] = None) -> dict:
    """
    Fetch 14-day traffic views/clones (requires repo access).
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url_views = f"https://api.github.com/repos/{repo}/traffic/views"
    url_clones = f"https://api.github.com/repos/{repo}/traffic/clones"
    stats = {"views": 0, "unique_views": 0, "clones": 0, "unique_clones": 0}
    with httpx.Client(timeout=15) as client:
        r_views = client.get(url_views, headers=headers)
        if r_views.status_code == 200:
            v = r_views.json()
            stats["views"] = v.get("count", 0)
            stats["unique_views"] = v.get("uniques", 0)
        r_clones = client.get(url_clones, headers=headers)
        if r_clones.status_code == 200:
            c = r_clones.json()
            stats["clones"] = c.get("count", 0)
            stats["unique_clones"] = c.get("uniques", 0)
    return stats


def parse_clicks(csv_path: Optional[str]) -> int:
    """
    Sum clicks from a CSV with a `clicks` column; returns 0 if file missing.
    """
    if not csv_path:
        return 0
    path = Path(csv_path)
    if not path.exists():
        return 0
    import csv

    total = 0
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                total += int(row.get("clicks", 0))
            except ValueError:
                continue
    return total


def append_experiment_log(
    *,
    log_path: str | Path,
    repo: str,
    channel_clicks_csv: Optional[str] = None,
    token: Optional[str] = None,
) -> Path:
    """
    Append a row of metrics to experiments log.
    """
    stats = fetch_github_repo_stats(repo, token)
    traffic = fetch_github_traffic(repo, token)
    clicks = parse_clicks(channel_clicks_csv)

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()

    timestamp = datetime.utcnow().isoformat()
    row = [
        timestamp,
        repo,
        stats["stargazers_count"],
        stats["forks_count"],
        stats["watchers_count"],
        stats["open_issues_count"],
        traffic["views"],
        traffic["unique_views"],
        traffic["clones"],
        traffic["unique_clones"],
        clicks,
    ]

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                [
                    "timestamp",
                    "repo",
                    "stars",
                    "forks",
                    "watchers",
                    "open_issues",
                    "views_14d",
                    "unique_views_14d",
                    "clones_14d",
                    "unique_clones_14d",
                    "utm_clicks",
                ]
            )
        writer.writerow(row)

    return path
