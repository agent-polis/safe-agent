"""
Safe Agent - An AI coding agent you can actually trust.

Uses impact-preview to show exactly what will change before any action executes.
"""

from __future__ import annotations

__version__ = "0.2.0"

__all__ = ["SafeAgent", "main", "__version__"]


def __getattr__(name: str):
    """Lazy imports so ancillary CLIs don't pull in heavy deps at import time."""

    if name == "SafeAgent":
        from .agent import SafeAgent

        return SafeAgent
    if name == "main":
        from .cli import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
