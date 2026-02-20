"""
Demo scaffolding for recording Safe Agent in action.

Goals:
- Quickly create a throwaway repo that demonstrates a risky edit being blocked.
- Provide a repeatable command script users can record via asciinema/ffmpeg.

We keep side effects minimal and self-contained under a temporary directory.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Iterable

DEMO_TASK = "switch database config to production"


def prepare_demo_repo(target_dir: str | None = None) -> Path:
    """
    Create a minimal demo repo with a risky config change.

    Structure:
      demo/
        config/db.yaml   # contains a dev URL
        README.md        # short instructions for the demo
    """

    base = Path(target_dir) if target_dir else Path(tempfile.mkdtemp(prefix="safe-agent-demo-"))
    base.mkdir(parents=True, exist_ok=True)

    config_path = base / "config"
    config_path.mkdir(parents=True, exist_ok=True)

    (config_path / "db.yaml").write_text(
        "url: postgresql://localhost:5432/dev\n", encoding="utf-8"
    )

    (base / "README.md").write_text(
        "# Safe Agent Demo\n\n"
        "Goal: show Safe Agent flagging a risky production DB change.\n\n"
        "Steps:\n"
        "1) Run the command from demo_script.sh (or below) inside this directory.\n"
        "2) Approve/deny when prompted.\n"
        "3) Record with `asciinema rec demo.cast -- safe-agent ...`.\n",
        encoding="utf-8",
    )

    (base / "demo_task.txt").write_text(DEMO_TASK, encoding="utf-8")
    (base / ".gitignore").write_text("*.cast\n*.gif\n", encoding="utf-8")

    # Provide a helper shell script the user can copy/paste.
    (base / "demo_script.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n\n"
        'echo "Running Safe Agent demo..."\n'
        f"safe-agent --dry-run \"{DEMO_TASK}\"\n",
        encoding="utf-8",
    )

    return base


def build_asciinema_command(repo: Path) -> list[str]:
    """
    Return a recommended asciinema record command for the demo repo.
    """
    return [
        "asciinema",
        "rec",
        "demo.cast",
        "--title",
        "Safe Agent Guardrail Demo",
        "--cwd",
        str(repo),
        "--",
        "safe-agent",
        "--dry-run",
        DEMO_TASK,
    ]


def convert_cast_to_gif(cast_file: Path, out_gif: Path) -> list[str]:
    """
    Provide a suggested command to convert asciinema cast to GIF.

    We do not invoke the command automatically; we return it so the caller
    can decide when/how to run (e.g., ffmpeg/asciinema-scenario).
    """
    return [
        "asciinema",
        "play",
        "--speed",
        "1.1",
        str(cast_file),
    ], [
        "agg",
        str(cast_file),
        str(out_gif),
    ]


def ensure_tools_available(tools: Iterable[str]) -> dict[str, bool]:
    """
    Check for presence of required binaries in PATH.
    """
    available: dict[str, bool] = {}
    for tool in tools:
        available[tool] = shutil.which(tool) is not None
    return available


def run_if_available(cmd: list[str]) -> int:
    """
    Execute a command if the binary is present. Return exit code (0 if skipped).
    """
    if shutil.which(cmd[0]) is None:
        return 0
    result = subprocess.run(cmd, check=False)  # nosec B603
    return result.returncode
