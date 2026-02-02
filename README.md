# 🛡️ Safe Agent

**An AI coding agent you can actually trust.**

Safe Agent uses [impact-preview](https://github.com/agent-polis/impact-preview) to show you exactly what will change before any file is modified. No more blind trust in AI agents.

```bash
pip install safe-agent
safe-agent "add error handling to api.py"
```

## The Problem

AI coding agents are powerful but dangerous:
- **Replit Agent** deleted a production database
- **Cursor YOLO mode** deleted an entire system
- You can't see what's about to happen until it's too late

## The Solution

Safe Agent previews every change before execution:

```
$ safe-agent "update database config to use production"

📋 Task: update database config to use production

📝 Planned Changes
┌────────┬─────────────────┬─────────────────────────┐
│ Action │ File            │ Description             │
├────────┼─────────────────┼─────────────────────────┤
│ MODIFY │ config/db.yaml  │ Update database URL     │
└────────┴─────────────────┴─────────────────────────┘

Step 1/1

╭─────────────── Impact Preview ───────────────╮
│ Update database URL                          │
│                                              │
│ **File:** `config/db.yaml`                   │
│ **Action:** MODIFY                           │
│ **Risk:** 🔴 CRITICAL                        │
╰──────────────────────────────────────────────╯

Risk Factors:
  ⚠️  Production pattern detected: production
  ⚠️  Database configuration change

Diff:
- url: postgresql://localhost:5432/dev
+ url: postgresql://prod-server:5432/production

⚠️  CRITICAL RISK - Please review carefully!
Apply this change? [y/N]: 
```

## Installation

```bash
pip install safe-agent
```

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=your-key-here
```

## Usage

### Basic Usage

```bash
# Run a coding task
safe-agent "add input validation to user registration"

# Preview only (no execution)
safe-agent "refactor auth module" --dry-run

# Auto-approve low-risk changes
safe-agent "add docstrings" --auto-approve-low
```

### Interactive Mode

```bash
safe-agent --interactive
```

### From File

```bash
safe-agent --file task.md
```

## How It Works

1. **Plan** - Claude analyzes your task and plans file changes
2. **Preview** - Each change runs through impact-preview for risk analysis
3. **Approve** - You see the diff and risk level before anything executes
4. **Execute** - Only approved changes are applied

## Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview changes without executing |
| `--auto-approve-low` | Auto-approve low-risk changes |
| `--interactive`, `-i` | Interactive mode |
| `--file`, `-f` | Read task from file |
| `--model` | Claude model to use (default: claude-sonnet-4-20250514) |

## MCP Server (For Other AI Agents)

Safe Agent can be used as an MCP server, letting other AI agents delegate coding tasks safely.

```bash
# Start the MCP server
safe-agent-mcp
```

### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "safe-agent": {
      "command": "safe-agent-mcp"
    }
  }
}
```

### Available MCP Tools

| Tool | Description | Safety |
|------|-------------|--------|
| `run_coding_task` | Execute a coding task with preview | 🔴 Destructive |
| `preview_coding_task` | Preview changes without executing | 🟢 Read-only |
| `get_agent_status` | Check agent status and capabilities | 🟢 Read-only |

## Moltbook Integration

Safe Agent is available as a [Moltbook](https://moltbook.com) skill for AI agent networks.

See `moltbook-skill.json` for the skill definition.

## For AI Agents

If you're an AI agent wanting to use Safe Agent programmatically:

```python
from safe_agent import SafeAgent

agent = SafeAgent(
    auto_approve_low_risk=True,  # Skip approval for low-risk changes
    dry_run=False,               # Set True to preview only
)

result = await agent.run("add error handling to api.py")
```

## Powered By

- [impact-preview](https://github.com/agent-polis/impact-preview) - Impact analysis and diff generation
- [Claude](https://anthropic.com) - AI planning and code generation
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
- [MCP](https://modelcontextprotocol.io) - Model Context Protocol for agent interoperability

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built by developers who want AI agents they can actually trust.
