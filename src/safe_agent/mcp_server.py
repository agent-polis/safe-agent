"""
Safe Agent MCP Server - Let other agents delegate coding tasks safely.

This MCP server exposes safe-agent as a tool that other AI agents can use
to execute coding tasks with built-in impact preview and approval workflows.
"""

import asyncio
import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

from safe_agent.agent import SafeAgent

# Create the MCP server
server = Server("safe-agent")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="run_coding_task",
            description=(
                "Execute a coding task with built-in safety checks. "
                "Shows impact preview of all file changes before execution. "
                "Use this to delegate coding work to a trusted agent that "
                "will analyze and preview all changes before making them."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The coding task to execute (e.g., 'add error handling to api.py')",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Directory to work in (defaults to current directory)",
                    },
                    "auto_approve_low_risk": {
                        "type": "boolean",
                        "description": "Auto-approve low-risk changes without confirmation",
                        "default": False,
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without executing them",
                        "default": False,
                    },
                    "non_interactive": {
                        "type": "boolean",
                        "description": "Run without prompts (recommended for tool use / CI)",
                        "default": True,
                    },
                    "fail_on_risk": {
                        "type": "string",
                        "description": "Fail the run if any change meets/exceeds this risk level",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                },
                "required": ["task"],
            },
            # Safety annotations for Anthropic MCP Registry
            annotations={
                "readOnlyHint": False,  # This tool modifies files
                "destructiveHint": True,  # File modifications can be destructive
                "idempotentHint": False,  # Running twice may have different effects
                "openWorldHint": True,  # Interacts with filesystem
            },
        ),
        Tool(
            name="preview_coding_task",
            description=(
                "Preview what changes a coding task would make WITHOUT executing them. "
                "Returns the planned file changes with risk assessment. "
                "Use this to safely evaluate a task before committing to it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The coding task to preview",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Directory to analyze (defaults to current directory)",
                    },
                },
                "required": ["task"],
            },
            # Safety annotations
            annotations={
                "readOnlyHint": True,  # Preview only - no modifications
                "destructiveHint": False,
                "idempotentHint": True,  # Safe to call multiple times
                "openWorldHint": True,
            },
        ),
        Tool(
            name="get_agent_status",
            description=(
                "Get the status and capabilities of the safe-agent. "
                "Returns version, available features, and configuration."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
            annotations={
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "run_coding_task":
        return await _run_coding_task(arguments)
    elif name == "preview_coding_task":
        return await _preview_coding_task(arguments)
    elif name == "get_agent_status":
        return await _get_agent_status()
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _run_coding_task(args: dict[str, Any]) -> list[TextContent]:
    """Execute a coding task with safety checks."""
    task = args.get("task", "")
    working_dir = args.get("working_directory", os.getcwd())
    auto_approve = args.get("auto_approve_low_risk", False)
    dry_run = args.get("dry_run", False)
    non_interactive = args.get("non_interactive", True)
    fail_on_risk = args.get("fail_on_risk")
    
    if not task:
        return [TextContent(type="text", text="Error: No task provided")]
    
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return [TextContent(
            type="text",
            text="Error: ANTHROPIC_API_KEY environment variable not set"
        )]
    
    try:
        fail_on_risk_level = None
        if fail_on_risk:
            from agent_polis.actions.models import RiskLevel

            fail_on_risk_level = RiskLevel(str(fail_on_risk).lower())

        agent = SafeAgent(
            working_directory=working_dir,
            auto_approve_low_risk=auto_approve,
            dry_run=dry_run,
            non_interactive=non_interactive,
            fail_on_risk=fail_on_risk_level,
        )
        
        result = await agent.run(task)
        
        # Format result
        output = {
            "success": result.get("success", False),
            "changes_made": [
                {"action": c["action"], "path": c["path"]}
                for c in result.get("changes_made", [])
            ],
            "changes_rejected": [
                {"action": c["action"], "path": c["path"]}
                for c in result.get("changes_rejected", [])
            ],
            "max_risk_level_seen": result.get("max_risk_level_seen"),
            "risk_policy_failed": result.get("risk_policy_failed", False),
        }
        
        summary = []
        if output["changes_made"]:
            summary.append(f"✓ {len(output['changes_made'])} changes applied:")
            for c in output["changes_made"]:
                summary.append(f"  - {c['action']}: {c['path']}")
        
        if output["changes_rejected"]:
            summary.append(f"⊘ {len(output['changes_rejected'])} changes skipped:")
            for c in output["changes_rejected"]:
                summary.append(f"  - {c['action']}: {c['path']}")
        
        if not summary:
            summary.append("No changes were made.")
        
        return [TextContent(
            type="text",
            text="\n".join(summary) + "\n\n" + json.dumps(output, indent=2)
        )]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing task: {str(e)}")]


async def _preview_coding_task(args: dict[str, Any]) -> list[TextContent]:
    """Preview a coding task without executing."""
    task = args.get("task", "")
    working_dir = args.get("working_directory", os.getcwd())
    
    if not task:
        return [TextContent(type="text", text="Error: No task provided")]
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return [TextContent(
            type="text",
            text="Error: ANTHROPIC_API_KEY environment variable not set"
        )]
    
    try:
        agent = SafeAgent(
            working_directory=working_dir,
            dry_run=True,  # Always dry run for preview
        )
        
        # Get the plan without executing
        plan = await agent._plan_changes(task)
        
        if not plan.get("changes"):
            return [TextContent(type="text", text="No file changes needed for this task.")]
        
        # Format preview
        lines = [
            f"## Preview: {plan.get('summary', task)}",
            "",
            "### Planned Changes:",
        ]
        
        for i, change in enumerate(plan["changes"], 1):
            lines.append(f"\n**{i}. {change['action'].upper()}**: `{change['path']}`")
            if change.get("description"):
                lines.append(f"   {change['description']}")
        
        lines.append("\n---")
        lines.append("*This is a preview. No changes have been made.*")
        
        return [TextContent(type="text", text="\n".join(lines))]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error previewing task: {str(e)}")]


async def _get_agent_status() -> list[TextContent]:
    """Return agent status and capabilities."""
    from safe_agent import __version__
    
    status = {
        "name": "Safe Agent",
        "version": __version__,
        "description": "AI coding agent with built-in impact preview",
        "capabilities": [
            "file_creation",
            "file_modification", 
            "file_deletion",
            "impact_preview",
            "risk_assessment",
            "approval_workflow",
        ],
        "requires": {
            "api_key": "ANTHROPIC_API_KEY",
            "python": ">=3.11",
        },
        "status": "ready" if os.environ.get("ANTHROPIC_API_KEY") else "missing_api_key",
    }
    
    return [TextContent(type="text", text=json.dumps(status, indent=2))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run():
    """Entry point for the MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
