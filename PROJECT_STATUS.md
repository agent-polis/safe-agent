# Agent Polis / Safe Agent — Project Status

*Internal summary. Not for GitHub.*

---

## The Two Projects

### 1. Impact Preview (agent-polis/impact-preview)

**What it is:** A guardrail library and MCP server that analyses proposed AI actions before they run. Often described as “terraform plan for AI agents.”

**What it does:**
- **Risk analysis** — Flags dangerous targets (`.env`, production config, credentials, sensitive paths).
- **Diff preview** — Shows what would change for file writes/creates/deletes.
- **Shell and DB awareness** — Warns on dangerous commands (`rm -rf`, etc.) and destructive SQL.
- **MCP server** — Exposes tools (e.g. `preview_file_write`, `preview_file_delete`, `check_path_risk`) so Claude Desktop, Cursor, and other MCP clients can preview before acting.
- **Event-sourced audit trail** (in full server mode) for compliance-style use.

**Packaging:** PyPI `impact-preview` (Python module name: `agent_polis`). Listed on MCP Registry. Repo: `agent-polis/impact-preview`.

**Tech:** Python 3.11+, FastAPI (optional server), E2B sandbox (optional), event sourcing, PostgreSQL/Redis in full deployment. MCP server can run standalone (stdio) with no backend.

---

### 2. Safe Agent (agent-polis/safe-agent)

**What it is:** A reference “safe” coding agent: it uses Claude to plan file changes and impact-preview to gate every edit. The product that *uses* impact-preview.

**What it does:**
- **CLI** — `safe-agent "task"` plans changes with Claude, then runs each change through impact-preview; user approves/rejects per change (or uses `--dry-run`, `--auto-approve-low`).
- **Path safety** — Rejects paths outside the working directory (no traversal).
- **Non-interactive mode** — For MCP/headless: auto-approve LOW/MEDIUM, reject HIGH/CRITICAL so it never blocks on a missing TTY.
- **MCP server** — Other agents can call `run_coding_task`, `preview_coding_task`, `get_agent_status` to delegate work through Safe Agent.

**Packaging:** PyPI `safe-agent-cli`. Repo: `agent-polis/safe-agent`. Scripts: `safe-agent`, `safe-agent-mcp`, `safe-agent-demo`, `safe-agent-marketing`.

**Tech:** Python 3.11+, depends on `impact-preview`, Anthropic API, Click, Rich, MCP. Test suite (pytest) covers path resolution, return shape, non-interactive behaviour, CLI smoke.

---

## How They’re Faring

**Impact Preview**
- Shipped on PyPI and MCP Registry; usable without a backend via the MCP server.
- Fills a real gap (preview before execute; no equivalent “terraform plan” for agents in the stack).
- Market is early: many teams still run a handful of agents they control; “governance” and “impact preview” are not yet standard asks.
- Adoption likely to improve if: (1) EU AI Act or similar makes audit/preview expectations concrete, (2) a high-profile agent incident pushes demand for guardrails, (3) a major framework (e.g. CrewAI, LangGraph) or IDE integrates it.

**Safe Agent**
- Demonstrates impact-preview in a full flow (plan → preview → approve → execute).
- Useful as a reference implementation and as a concrete “safe” agent others can run or call via MCP.
- Same early-market dynamic: traction will depend on how much people want a dedicated “safe” agent vs. embedding guardrails into existing tools.
- Tests (12) passing; path safety and non-interactive behaviour in place for production use.

**Overall:** Both projects are in place and technically sound. Traction is uncertain and timing-dependent; the strongest angle is “impact preview” and compliance/audit, with Safe Agent as the flagship consumer of that capability.

---

## Possible Future Directions

**Impact Preview**
- **More action types** — DB write preview, API-call preview, container/exec preview.
- **Tighter IDE integration** — Cursor/VS Code extension or rules that route edits through preview by default.
- **Compliance packaging** — Presets and docs for EU AI Act / SOC2-style “auditable agent actions.”
- **Ecosystem plugs** — Official or blessed integrations for CrewAI, LangGraph, AutoGen (tools/callbacks that send proposed actions through impact-preview).
- **Hosted service** — Managed API + audit UI for teams that don’t want to run the server.

**Safe Agent**
- **Smarter defaults** — E.g. auto-approve low-risk in CI, or “batch approve” for a set of changes.
- **More models** — Support for other LLMs (OpenAI, local) for planning, not only Claude.
- **CI/GitHub integration** — Workflow that runs Safe Agent (e.g. `--dry-run`) on PRs and comments with a summary.
- **Moltbook / identity** — Optional “Sign in with Moltbook” or similar so agent identity/reputation can be used in approvals or logging.
- **Templates and playbooks** — Curated tasks (e.g. “add tests”, “harden config”) that teams can run through Safe Agent.

**Cross-cutting**
- **Agent marketplace / labour layer** — Use event-sourced outcomes from impact-preview and Safe Agent to track which agents (or teams) do what well; reputation, contracts, or “hire an agent” on top.
- **Two-tier product** — Open core (preview, MCP, basic audit) + paid tier (SSO, compliance export, SLAs, advanced analytics).
- **Content and distribution** — Show HN, short demo (e.g. “catching a critical config change”), posts in r/cursor, r/LocalLLaMA, Claude/Cursor Discords to test messaging and demand.

---

*Last updated: Feb 2026. For internal use only.*
