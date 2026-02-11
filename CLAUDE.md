# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Safe Agent is an AI coding agent with built-in guardrails. It previews every file change using impact-preview before execution, showing risk levels and diffs to prevent dangerous operations. This is the product layer (`safe-agent-cli`) that provides CLI, MCP server, and user-facing workflows.

## Architecture

### Core Components

- **SafeAgent class** (`src/safe_agent/agent.py`): Orchestrates the full workflow:
  1. Planning changes via Claude API (`_plan_changes`)
  2. Risk analysis via impact-preview library (`_preview_and_approve`)
  3. Path safety validation (`_resolve_path_safe`)
  4. User approval flow (interactive/non-interactive modes)
  5. File execution (`_execute_change`)

- **CLI** (`src/safe_agent/cli.py`): Click-based interface with flags for dry-run, auto-approval, non-interactive mode, and risk policies

- **MCP Server** (`src/safe_agent/mcp_server.py`): Model Context Protocol server exposing safe-agent as tools for other AI agents (run_coding_task, preview_coding_task, get_agent_status)

- **Marketing CLI** (`src/safe_agent/marketing_cli.py`): Generates marketing copy variants and README hero blocks

- **Demo Producer** (`src/safe_agent/demo_cli.py`): Creates canned demo scenarios for asciinema recordings

### Critical Import Pattern

**IMPORTANT**: The package is named `impact-preview` on PyPI but the module name is `agent_polis`:

```python
from agent_polis.actions.analyzer import ImpactAnalyzer
from agent_polis.actions.models import ActionRequest, ActionType, RiskLevel
```

Tests handle both import patterns for compatibility:
```python
try:
    from agent_polis.actions.models import RiskLevel
except ModuleNotFoundError:
    from impact_preview.actions.models import RiskLevel
```

### Multi-Repository Architecture

This repository is part of a two-repo system:
- **safe-agent-cli** (this repo): Product UX, approval workflows, CLI/MCP packaging
- **impact-preview** (`/Users/danielwaterfield/Documents/Leviathan`): Risk policy engine, scanning, enforcement primitives

Compatibility between versions is tracked in `docs/compatibility-matrix.md`. Always check compatibility when working across repos.

## Development Commands

### Setup
```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Requires Python >=3.11
```

### Testing
```bash
# Run all tests with verbose output
pytest tests -v

# Run specific test file
pytest tests/test_agent.py -v

# Run tests with specific markers
pytest tests -k test_path_safety -v
```

### Linting
```bash
# Format and lint (ruff is configured in pyproject.toml)
ruff check .
ruff format .
```

### Running the CLI
```bash
# Basic usage (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=your-key-here
safe-agent "add error handling to api.py"

# Preview only (dry run)
safe-agent "refactor auth module" --dry-run

# Non-interactive mode (CI-friendly)
safe-agent "task" --non-interactive --fail-on-risk high

# Interactive mode
safe-agent --interactive

# MCP server
safe-agent-mcp

# Demo producer
safe-agent-demo prepare
safe-agent-demo record
```

### CI/CD
- GitHub Actions runs on push/PR to master
- Test workflow: `.github/workflows/tests.yml`
- Requires `pip install -e ".[dev]"` then `pytest tests -v`

## Key Implementation Details

### Path Safety
All file paths go through `_resolve_path_safe()` which prevents:
- Absolute paths
- Path traversal (`../../../etc/passwd`)
- Paths outside working directory (including symlinks)
- Windows absolute paths and UNC paths
- Null bytes in paths

### Risk Levels and Approval Logic
Risk levels (from `agent_polis.actions.models.RiskLevel`):
- `LOW`: Green, safe changes
- `MEDIUM`: Yellow, moderate risk
- `HIGH`: Orange, dangerous
- `CRITICAL`: Red, very dangerous

**Approval behavior**:
- **Interactive mode**: Prompts user for approval (except with `--auto-approve-low`)
- **Non-interactive mode** (`--non-interactive` or CI environment):
  - Auto-approves: LOW, MEDIUM
  - Auto-rejects: HIGH, CRITICAL
- **Fail-on-risk policy** (`--fail-on-risk <level>`): Exits non-zero if any change meets/exceeds the specified risk level

### Async Pattern
The `SafeAgent.run()` method is async. All code calling it must use `await` or `asyncio.run()`:

```python
# CLI usage
result = asyncio.run(agent.run(task))

# In async context
result = await agent.run(task)
```

### Return Value Structure
`SafeAgent.run()` always returns a dict with:
```python
{
    "success": bool,                    # False if risk_policy_failed
    "changes_made": list[dict],         # Applied changes
    "changes_rejected": list[dict],     # Rejected changes
    "max_risk_level_seen": str | None,  # "low"/"medium"/"high"/"critical"
    "risk_policy_failed": bool          # True if --fail-on-risk triggered
}
```

## Project Management

### Roadmap
The roadmap is staged and agent-driven (see `ROADMAP.md`):
- **Stage 0**: Boundaries and release hygiene
- **Stage 1**: Safety hardening (policy-as-code, injection scanning, descriptor checks)
- **Stage 2**: Distribution and CI adoption
- **Stage 3**: Evaluation and trust signals
- **Stage 4**: Team controls

Stage 1 tickets are in `ROADMAP.md` with clear acceptance criteria. Tickets prefixed:
- `AP-*`: Agent-Platform tickets (work in impact-preview repo)
- `AS-*`: Agent-Product tickets (work in this repo)
- `INT-*`: Integration gate tickets (cross-repo validation)

### Monday Assignment Packets
Current week's assignment bundle is in `docs/monday-assignment-packet.md`.

### Compatibility Requirements
Before releasing:
1. Check `docs/compatibility-matrix.md` for version compatibility
2. Update matrix with new version combinations
3. Run cross-repo smoke tests (INT-101 from ROADMAP.md)

## Testing Strategy

### Test Organization
- `tests/test_agent.py`: SafeAgent core logic, path safety, approval workflows
- `tests/test_cli.py`: CLI argument parsing and entry points
- `tests/test_policy.py`: Risk policy enforcement
- `tests/test_path_safety.py`: Path traversal protection
- `tests/conftest.py`: Shared fixtures (temp directories, safe_agent instances)

### Key Test Patterns
- Use `temp_work_dir` fixture for isolated file operations
- Mock `_plan_changes` to test approval logic without API calls
- Mock `analyzer.analyze` to test different risk levels
- Test both interactive and non-interactive modes
- Validate return value shape from `run()`

## Important Constraints

1. **API Key Required**: Even `--dry-run` requires `ANTHROPIC_API_KEY` because planning calls Claude API
2. **Package Naming**: Always import from `agent_polis`, not `impact_preview`
3. **Async Required**: All SafeAgent operations are async
4. **Path Safety**: Never bypass `_resolve_path_safe()` - it prevents path traversal attacks
5. **Cross-Repo Dependencies**: Changes may require coordinated updates in impact-preview repo
