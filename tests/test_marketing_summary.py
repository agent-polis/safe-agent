"""Tests for weekly analytics summary generation."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from safe_agent.marketing import generate_weekly_summary
from safe_agent.marketing_cli import main


def test_generate_weekly_summary_includes_metric_deltas_and_top_variant(tmp_path: Path) -> None:
    log_path = tmp_path / "experiments.csv"
    log_path.write_text(
        "\n".join(
            [
                "timestamp,repo,stars,forks,watchers,open_issues,views_14d,unique_views_14d,clones_14d,unique_clones_14d,utm_clicks,variant_id,variant_clicks,variant_notes",
                "2026-02-01T00:00:00+00:00,agent-polis/safe-agent,10,0,0,0,100,80,20,10,40,v1,20,early safety angle",
                "2026-02-04T00:00:00+00:00,agent-polis/safe-agent,12,0,0,0,120,90,22,11,50,v2,early speed angle",
                "2026-02-10T00:00:00+00:00,agent-polis/safe-agent,12,0,0,0,130,95,23,11,50,v1,30,lean into reliability",
                "2026-02-12T00:00:00+00:00,agent-polis/safe-agent,15,0,0,0,150,98,24,12,60,v2,32,speed follow-up",
                "2026-02-14T00:00:00+00:00,agent-polis/safe-agent,18,0,0,0,180,105,25,12,70,v1,42,reliability framing works",
            ]
        ),
        encoding="utf-8",
    )

    summary = generate_weekly_summary(log_path=log_path)

    assert "| Stars | +6 | +2 | +4 | 18 |" in summary
    assert "| Traffic Views (14d) | +50 | +20 | +30 | 180 |" in summary
    assert "| UTM Clicks | +20 | +10 | +10 | 70 |" in summary
    assert "Top variant: `v1` (+12 click delta)." in summary
    assert "Top variant note: reliability framing works" in summary


def test_generate_weekly_summary_handles_missing_variant_columns(tmp_path: Path) -> None:
    log_path = tmp_path / "experiments.csv"
    log_path.write_text(
        "\n".join(
            [
                "timestamp,repo,stars,forks,watchers,open_issues,views_14d,unique_views_14d,clones_14d,unique_clones_14d,utm_clicks",
                "2026-02-10T00:00:00+00:00,agent-polis/safe-agent,1,0,0,0,10,8,2,1,1",
                "2026-02-14T00:00:00+00:00,agent-polis/safe-agent,3,0,0,0,20,12,3,1,4",
            ]
        ),
        encoding="utf-8",
    )

    summary = generate_weekly_summary(log_path=log_path)
    assert "No variant tracking columns detected" in summary


def test_weekly_summary_cli_writes_output(tmp_path: Path) -> None:
    log_path = tmp_path / "experiments.csv"
    out_path = tmp_path / "weekly-summary.md"
    log_path.write_text(
        "\n".join(
            [
                "timestamp,repo,stars,forks,watchers,open_issues,views_14d,unique_views_14d,clones_14d,unique_clones_14d,utm_clicks",
                "2026-02-10T00:00:00+00:00,agent-polis/safe-agent,1,0,0,0,10,8,2,1,1",
                "2026-02-14T00:00:00+00:00,agent-polis/safe-agent,3,0,0,0,20,12,3,1,4",
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(main, ["weekly-summary", "--log", str(log_path), "--out", str(out_path)])

    assert result.exit_code == 0
    assert out_path.exists()
    contents = out_path.read_text(encoding="utf-8")
    assert "# Weekly Growth Summary" in contents
