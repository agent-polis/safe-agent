"""
Safe Agent - An AI coding agent you can actually trust.

Uses impact-preview to show exactly what will change before any action executes.
"""

__version__ = "0.1.0"

from safe_agent.agent import SafeAgent
from safe_agent.cli import main

__all__ = ["SafeAgent", "main", "__version__"]
