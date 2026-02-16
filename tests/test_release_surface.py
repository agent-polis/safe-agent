"""Guardrails for public release surface.

These tests intentionally fail if internal tooling (marketing/demo/copy helpers)
is accidentally exposed in package scripts or build artifacts.
"""

from __future__ import annotations

import tomllib
from pathlib import Path


def _load_pyproject() -> dict:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)


def test_public_console_scripts_are_minimal() -> None:
    data = _load_pyproject()
    scripts = data["project"]["scripts"]
    assert set(scripts.keys()) == {"safe-agent", "safe-agent-mcp"}


def test_internal_tooling_is_excluded_from_wheel_and_sdist() -> None:
    data = _load_pyproject()
    wheel_excludes = set(data["tool"]["hatch"]["build"]["targets"]["wheel"]["exclude"])
    sdist_excludes = set(data["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"])

    required = {
        "src/safe_agent/marketing.py",
        "src/safe_agent/marketing_cli.py",
        "src/safe_agent/demo.py",
        "src/safe_agent/demo_cli.py",
    }
    assert required.issubset(wheel_excludes)
    assert required.issubset(sdist_excludes)
