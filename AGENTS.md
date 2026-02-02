# Agent Instructions for Safe Agent

This file provides instructions for AI agents (like Cursor, Claude, GPT) working with this codebase.

## Project Overview

Safe Agent is an AI coding assistant with built-in safety checks. It uses the `impact-preview` library to analyze file changes before executing them.

## Architecture

```
safe-agent/
├── src/safe_agent/
│   ├── __init__.py    # Exports SafeAgent class
│   ├── cli.py         # Click-based CLI entry point
│   └── agent.py       # Core SafeAgent class with Claude integration
├── pyproject.toml     # Package config, dependencies
└── README.md          # User documentation
```

## Key Components

### SafeAgent Class (`agent.py`)

The main class that orchestrates:
1. Task planning via Claude API
2. Impact analysis via `agent_polis.actions.analyzer`
3. User approval flow via Rich console
4. File execution

### CLI (`cli.py`)

Entry point `safe-agent` with options:
- `--dry-run`: Preview only
- `--auto-approve-low`: Skip approval for low-risk changes
- `--interactive`: Multi-line input mode

## Development Guidelines

1. **Imports**: The package `impact-preview` on PyPI uses module name `agent_polis` internally
2. **Async**: The `SafeAgent.run()` method is async
3. **Testing**: Use `--dry-run` flag to test without making changes

## How to Extend

To add new action types:
1. Add handling in `_preview_and_approve()` method
2. Map to appropriate `ActionType` from `agent_polis.actions.models`

## Related Projects

- `impact-preview`: Safety analysis library (https://github.com/agent-polis/impact-preview)
- MCP server available in impact-preview for Claude Desktop integration
