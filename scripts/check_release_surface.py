#!/usr/bin/env python3
"""Validate that built distributions expose only approved public surface."""

from __future__ import annotations

import configparser
import sys
import tarfile
import zipfile
from pathlib import Path

ALLOWED_CONSOLE_SCRIPTS = {"safe-agent", "safe-agent-mcp"}
ALLOWED_PUBLIC_MODULES = {"__init__.py", "agent.py", "cli.py", "mcp_server.py"}
DISALLOWED_SOURCE_TOKENS = ("marketing", "demo", "copy", "devtool", "internal")
DISALLOWED_SDIST_DIRS = ("marketing/", "experiments/")


def _strip_sdist_root(path: str) -> str:
    if "/" not in path:
        return path
    return path.split("/", 1)[1]


def _collect_public_modules(paths: list[str], prefix: str) -> set[str]:
    modules: set[str] = set()
    for raw in paths:
        if not raw.startswith(prefix):
            continue
        rel = raw[len(prefix) :]
        if "/" in rel or not rel.endswith(".py"):
            continue
        modules.add(rel)
    return modules


def _find_disallowed_sources(paths: list[str], prefix: str) -> list[str]:
    hits: list[str] = []
    for raw in paths:
        if not raw.startswith(prefix):
            continue
        rel = raw[len(prefix) :]
        if "/" in rel:
            continue
        lowered = rel.lower()
        if any(token in lowered for token in DISALLOWED_SOURCE_TOKENS):
            hits.append(raw)
    return sorted(hits)


def _parse_console_scripts(entry_points_text: str) -> set[str]:
    parser = configparser.ConfigParser()
    parser.read_string(entry_points_text)
    if not parser.has_section("console_scripts"):
        return set()
    return set(parser["console_scripts"].keys())


def _check_wheel(path: Path, errors: list[str]) -> None:
    with zipfile.ZipFile(path) as zf:
        names = [name for name in zf.namelist() if not name.endswith("/")]
        modules = _collect_public_modules(names, "safe_agent/")
        extras = modules - ALLOWED_PUBLIC_MODULES
        if extras:
            errors.append(
                f"{path.name}: unexpected modules in wheel: {', '.join(sorted(extras))}"
            )

        missing = ALLOWED_PUBLIC_MODULES - modules
        if missing:
            errors.append(
                f"{path.name}: expected public modules missing from wheel: {', '.join(sorted(missing))}"
            )

        disallowed = _find_disallowed_sources(names, "safe_agent/")
        if disallowed:
            errors.append(
                f"{path.name}: disallowed internal source files in wheel: {', '.join(disallowed)}"
            )

        ep_member = next(
            (name for name in names if name.endswith(".dist-info/entry_points.txt")),
            None,
        )
        if ep_member is None:
            errors.append(f"{path.name}: missing entry_points.txt")
            return

        entry_points_text = zf.read(ep_member).decode("utf-8")
        scripts = _parse_console_scripts(entry_points_text)
        if scripts != ALLOWED_CONSOLE_SCRIPTS:
            errors.append(
                f"{path.name}: console scripts mismatch: found {sorted(scripts)}, "
                f"expected {sorted(ALLOWED_CONSOLE_SCRIPTS)}"
            )


def _check_sdist(path: Path, errors: list[str]) -> None:
    with tarfile.open(path, "r:gz") as tf:
        names = [
            member.name
            for member in tf.getmembers()
            if member.isfile() and member.name and member.name != "."
        ]

    stripped = [_strip_sdist_root(name) for name in names]
    modules = _collect_public_modules(stripped, "src/safe_agent/")
    extras = modules - ALLOWED_PUBLIC_MODULES
    if extras:
        errors.append(f"{path.name}: unexpected modules in sdist: {', '.join(sorted(extras))}")

    missing = ALLOWED_PUBLIC_MODULES - modules
    if missing:
        errors.append(
            f"{path.name}: expected public modules missing from sdist: {', '.join(sorted(missing))}"
        )

    disallowed = _find_disallowed_sources(stripped, "src/safe_agent/")
    if disallowed:
        errors.append(
            f"{path.name}: disallowed internal source files in sdist: {', '.join(disallowed)}"
        )

    for disallowed_dir in DISALLOWED_SDIST_DIRS:
        if any(name.startswith(disallowed_dir) for name in stripped):
            errors.append(f"{path.name}: disallowed directory present in sdist: {disallowed_dir}")


def main(argv: list[str]) -> int:
    dist_dir = Path(argv[1]) if len(argv) > 1 else Path("dist")
    if not dist_dir.exists():
        print(f"error: dist directory does not exist: {dist_dir}", file=sys.stderr)
        return 1

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    errors: list[str] = []

    if not wheels:
        errors.append(f"no wheel files found in {dist_dir}")
    if not sdists:
        errors.append(f"no sdist files found in {dist_dir}")

    for wheel in wheels:
        _check_wheel(wheel, errors)
    for sdist in sdists:
        _check_sdist(sdist, errors)

    if errors:
        print("Release surface check failed:")
        for err in errors:
            print(f" - {err}")
        return 1

    print(
        "Release surface check passed for "
        f"{len(wheels)} wheel(s) and {len(sdists)} sdist(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
