# 🛡️ Safe Agent

<!-- HERO_START -->
**Guardrails for AI code agents.**

Safe Agent previews every file edit with [impact-preview](https://github.com/agent-polis/impact-preview) so AI helpers can’t quietly ship risky changes. Drop it into CI or run locally and require approvals before writes.

```bash
pip install safe-agent-cli
safe-agent "add error handling to api.py" --dry-run
```
<!-- HERO_END -->

### ✨ New in v0.4.0

- 🧭 **Policy-as-code enforcement** - Deterministic allow/deny/require-approval decisions before execution
- 🎛️ **Policy presets** - `--policy-preset startup|fintech|games` plus `--list-policy-presets`
- 🕵️ **Prompt injection scan surfaced** - Preview shows scanner severity + reason IDs

## Project Map

- **impact-preview (Agent Polis)**: the guardrail layer that previews and scores risky actions.
- **safe-agent-cli (this repo)**: a reference coding agent that uses impact-preview for approvals.
- **Roadmap**: staged execution plan in [`ROADMAP.md`](ROADMAP.md).
- **Compatibility Matrix**: version contract in [`docs/compatibility-matrix.md`](docs/compatibility-matrix.md).
- **Monday Packet**: current assignment bundle in [`docs/monday-assignment-packet.md`](docs/monday-assignment-packet.md).

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
│ **Policy:** REQUIRE_APPROVAL [builtin]       │
│ **Scanner:** LOW                             │
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
pip install safe-agent-cli
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

### CI / Non-interactive mode

Use `--non-interactive` to avoid prompts (auto-approves when policy allows; skips anything requiring
approval). Combine with `--fail-on-risk` to fail the process if risky changes are proposed:

```bash
safe-agent "scan repository for risky config changes" --dry-run --non-interactive --fail-on-risk high
```

### Policy (allow/deny/require approval)

By default Safe Agent enforces a built-in policy that:
- denies obvious secret/key targets (e.g. `.env`, `.ssh`, `.pem`)
- allows LOW/MEDIUM risk actions
- requires approval for HIGH/CRITICAL risk actions

Override with a bundled preset:

```bash
safe-agent --list-policy-presets
safe-agent "update auth flow" --policy-preset fintech
```

Or load a policy file (JSON/YAML):

```bash
safe-agent "update auth flow" --policy ./policy.json
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

## Enterprise & Compliance Features

Safe Agent now includes features for insurance partnerships, regulatory compliance, and enterprise deployments.

### Audit Export for Insurance

Export complete audit trails for insurance underwriting and claims:

```bash
safe-agent "update production config" --audit-export audit.json
```

The audit export includes:
- Complete task history with timestamps
- Risk assessments for all operations
- Approval/rejection records (human oversight)
- Change execution status
- Compliance flags for regulatory requirements

Perfect for working with AI liability insurance carriers like [AIUC](https://www.aiunderwritingconsortium.com/), [Armilla AI](https://www.armilla.ai/), and [Beazley](https://www.beazley.com/).

See [docs/insurance-integration.md](docs/insurance-integration.md) for details on insurance partnerships and premium rate factors.

### EU AI Act Compliance Mode

Enable strict compliance mode for EU AI Act requirements:

```bash
safe-agent "modify user data" --compliance-mode --audit-export audit.json
```

Compliance mode:
- Disables all auto-approve features (Article 14: Human Oversight)
- Requires explicit approval for every operation
- Records all compliance flags in audit exports
- Supports Article 12 (Record-Keeping) requirements

Ready for the **August 2, 2026 enforcement deadline**.

See [docs/eu-ai-act-compliance.md](docs/eu-ai-act-compliance.md) for complete compliance guide and requirements mapping.

### Incident Documentation

We maintain a comprehensive database of AI agent incidents to raise awareness and demonstrate prevention mechanisms:

- [Replit SaaStr Database Deletion](docs/incident-reports/2025-07-replit-saastr.md) - Production database deleted during demo
- [Cursor YOLO Mode Bypass](docs/incident-reports/2025-07-cursor-yolo-mode.md) - Security controls circumvented

[Submit an incident report](.github/ISSUE_TEMPLATE/incident-report.md) to help the community.

## Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview changes without executing |
| `--auto-approve-low` | Auto-approve low-risk changes |
| `--non-interactive` | Run without prompts (CI-friendly) |
| `--fail-on-risk` | Exit non-zero if any change meets/exceeds risk level |
| `--policy` | Path to a policy file (JSON/YAML) for deterministic allow/deny/approval |
| `--policy-preset` | Use a bundled policy preset (startup, fintech, games) |
| `--list-policy-presets` | List available policy presets and exit |
| `--interactive`, `-i` | Interactive mode |
| `--file`, `-f` | Read task from file |
| `--model` | Claude model to use (default: claude-sonnet-4-20250514) |
| `--audit-export` | Export audit trail to JSON file (insurance/compliance) |
| `--compliance-mode` | Enable strict compliance mode (disables auto-approve) |

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

## Demo Producer

Set up a canned risky-edit scenario and print recording commands:

```bash
safe-agent-demo prepare  # creates a demo repo with config/db.yaml
cd /tmp/safe-agent-demo-*  # or your chosen path
safe-agent-demo record     # shows asciinema + GIF commands
```

By default the demo runs `safe-agent --dry-run "switch database config to production"` against the prepared repo.

![Safe Agent demo](marketing/demo.gif)

## For AI Agents

If you're an AI agent wanting to use Safe Agent programmatically:

```python
from safe_agent import SafeAgent

agent = SafeAgent(
    auto_approve_low_risk=True,      # Skip approval for low-risk changes
    dry_run=False,                   # Set True to preview only
    audit_export_path="audit.json",  # Export audit trail for compliance
    compliance_mode=False,           # Enable for EU AI Act compliance
)

result = await agent.run("add error handling to api.py")
```

For insurance and compliance use cases:

```python
# EU AI Act compliant configuration
agent = SafeAgent(
    compliance_mode=True,              # Strict compliance mode
    audit_export_path="audit.json",    # Required for Article 12
    non_interactive=False,             # Human oversight required
)
```

## Powered By

- [impact-preview](https://github.com/agent-polis/impact-preview) - Impact analysis and diff generation
- [Claude](https://anthropic.com) - AI planning and code generation
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal output
- [MCP](https://modelcontextprotocol.io) - Model Context Protocol for agent interoperability

## Known Incidents

AI coding agents without proper safeguards have caused real damage. We document these incidents to raise awareness and demonstrate why preview-before-execute architecture matters.

### Recent Incidents

- **[Replit SaaStr Database Deletion (July 2025)](docs/incident-reports/2025-07-replit-saastr.md)** - Production database deleted, 1,200+ executives affected
- **[Cursor YOLO Mode Bypass (July 2025)](docs/incident-reports/2025-07-cursor-yolo-mode.md)** - Security controls bypassed, arbitrary command execution possible

### Submit an Incident

Experienced an AI agent incident? Help the community by [submitting an incident report](.github/ISSUE_TEMPLATE/incident-report.md).

Browse all documented incidents in [docs/incident-reports/](docs/incident-reports/).

## Marketing Helpers

A lightweight CLI to generate headline variants, channel-specific copy (HN, Twitter/X, LinkedIn), and README hero blocks:

```bash
safe-agent-marketing generate --audience "Teams running AI code agents in CI" \
  --hypothesis "Guardrail that blocks risky edits" --update-readme
```

This writes JSON/Markdown bundles to `marketing/` and (optionally) refreshes the README hero block. Queue posts with:

```bash
safe-agent-marketing queue --slot 2026-02-05T15:00:00Z --slot 2026-02-05T20:00:00Z
```

Log traction daily:

```bash
safe-agent-marketing analytics --repo agent-polis/safe-agent --log experiments/experiments.csv
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built by developers who want AI agents they can actually trust.
