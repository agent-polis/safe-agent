"""
Safe Agent - Core agent logic with impact preview integration.
"""

import os
from pathlib import Path
from typing import Any

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

# Import impact-preview components
from agent_polis.actions.analyzer import ImpactAnalyzer
from agent_polis.actions.diff import format_diff_plain
from agent_polis.actions.models import ActionRequest, ActionType, RiskLevel

console = Console()


class SafeAgent:
    """
    An AI coding agent with built-in impact preview.
    
    Every file operation is analyzed and previewed before execution.
    """
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        auto_approve_low_risk: bool = False,
        dry_run: bool = False,
        working_directory: str | None = None,
    ):
        self.model = model
        self.auto_approve_low_risk = auto_approve_low_risk
        self.dry_run = dry_run
        self.working_directory = working_directory or os.getcwd()
        
        self.client = anthropic.Anthropic()
        self.analyzer = ImpactAnalyzer(working_directory=self.working_directory)
        
        # Track changes for summary
        self.changes_made: list[dict] = []
        self.changes_rejected: list[dict] = []
    
    async def run(self, task: str) -> dict[str, Any]:
        """
        Execute a coding task with impact preview on all file operations.
        """
        console.print("\n[bold]🤖 Planning changes...[/bold]\n")
        
        # Get Claude to plan the changes
        plan = await self._plan_changes(task)
        
        if not plan.get("changes"):
            console.print("[yellow]No file changes needed for this task.[/yellow]")
            return {"success": True, "changes": []}
        
        # Show plan
        self._show_plan(plan)
        
        # Execute each change with preview
        for i, change in enumerate(plan["changes"], 1):
            console.print(f"\n[bold]Step {i}/{len(plan['changes'])}[/bold]")
            
            approved = await self._preview_and_approve(change)
            
            if approved and not self.dry_run:
                self._execute_change(change)
                self.changes_made.append(change)
            elif not approved:
                self.changes_rejected.append(change)
                console.print("[yellow]Skipped[/yellow]")
        
        # Summary
        self._show_summary()
        
        return {
            "success": True,
            "changes_made": self.changes_made,
            "changes_rejected": self.changes_rejected,
        }
    
    async def _plan_changes(self, task: str) -> dict[str, Any]:
        """Use Claude to plan what file changes are needed."""
        
        system_prompt = """You are a coding assistant that plans file changes.

Given a task, analyze what file changes are needed and output a structured plan.

IMPORTANT: You must respond with ONLY a valid JSON object, no markdown, no explanation.

The JSON must have this structure:
{
    "summary": "Brief description of what you'll do",
    "changes": [
        {
            "action": "create" | "modify" | "delete",
            "path": "relative/path/to/file.py",
            "description": "What this change does",
            "content": "Full file content (for create/modify)"
        }
    ]
}

Rules:
- Only include file changes, not commands to run
- Use relative paths from the current directory
- For modifications, include the COMPLETE new file content
- Keep changes minimal and focused on the task
"""
        
        # List current files for context
        files_context = self._get_files_context()
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Current directory: {self.working_directory}\n\nFiles:\n{files_context}\n\nTask: {task}"
                }
            ],
        )
        
        # Parse response
        try:
            import json
            text = response.content[0].text.strip()
            # Handle markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except Exception as e:
            console.print(f"[red]Failed to parse plan: {e}[/red]")
            console.print(f"Response: {response.content[0].text[:500]}")
            return {"summary": "Failed to plan", "changes": []}
    
    def _get_files_context(self) -> str:
        """Get a summary of files in the working directory."""
        lines = []
        try:
            for item in Path(self.working_directory).rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(self.working_directory)
                    # Skip hidden files and common ignores
                    parts = str(rel_path).split("/")
                    if any(p.startswith(".") or p in ["node_modules", "__pycache__", "venv", ".venv"] for p in parts):
                        continue
                    lines.append(str(rel_path))
        except Exception:
            pass
        return "\n".join(lines[:100])  # Limit to 100 files
    
    def _show_plan(self, plan: dict[str, Any]) -> None:
        """Display the planned changes."""
        table = Table(title="📝 Planned Changes")
        table.add_column("Action", style="cyan")
        table.add_column("File", style="white")
        table.add_column("Description", style="dim")
        
        for change in plan.get("changes", []):
            action_color = {
                "create": "green",
                "modify": "yellow",
                "delete": "red",
            }.get(change["action"], "white")
            
            table.add_row(
                f"[{action_color}]{change['action'].upper()}[/{action_color}]",
                change["path"],
                change.get("description", "")[:50],
            )
        
        console.print(table)
    
    async def _preview_and_approve(self, change: dict) -> bool:
        """Preview a change using impact-preview and get approval."""
        
        action = change["action"]
        path = change["path"]
        full_path = os.path.join(self.working_directory, path)
        
        # Map to ActionType
        if action == "create":
            action_type = ActionType.FILE_CREATE
        elif action == "modify":
            action_type = ActionType.FILE_WRITE
        elif action == "delete":
            action_type = ActionType.FILE_DELETE
        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            return False
        
        # Create request
        request = ActionRequest(
            action_type=action_type,
            target=full_path,
            description=change.get("description", f"{action} {path}"),
            payload={"content": change.get("content", "")},
        )
        
        # Analyze with impact-preview
        preview = await self.analyzer.analyze(request)
        
        # Display preview
        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🟠",
            RiskLevel.CRITICAL: "🔴",
        }.get(preview.risk_level, "⚪")
        
        console.print(Panel(
            f"[bold]{change.get('description', path)}[/bold]\n\n"
            f"**File:** `{path}`\n"
            f"**Action:** {action.upper()}\n"
            f"**Risk:** {risk_emoji} {preview.risk_level.value.upper()}",
            title=f"Impact Preview",
            border_style="yellow" if preview.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else "blue",
        ))
        
        # Show risk factors
        if preview.risk_factors:
            console.print("[bold]Risk Factors:[/bold]")
            for factor in preview.risk_factors:
                console.print(f"  ⚠️  {factor}")
        
        # Show diff
        if preview.file_changes:
            console.print("\n[bold]Diff:[/bold]")
            diff_text = format_diff_plain(preview.file_changes)
            console.print(Syntax(diff_text, "diff", theme="monokai"))
        elif action == "create" and change.get("content"):
            console.print("\n[bold]New file content:[/bold]")
            # Guess language from extension
            ext = Path(path).suffix.lstrip(".")
            lang = {"py": "python", "js": "javascript", "ts": "typescript", "json": "json", "md": "markdown"}.get(ext, "text")
            console.print(Syntax(change["content"][:1000], lang, theme="monokai", line_numbers=True))
            if len(change["content"]) > 1000:
                console.print(f"[dim]... ({len(change['content'])} total characters)[/dim]")
        
        console.print()
        
        # Auto-approve low risk if enabled
        if self.auto_approve_low_risk and preview.risk_level == RiskLevel.LOW:
            console.print("[green]✓ Auto-approved (low risk)[/green]")
            return True
        
        # Dry run mode
        if self.dry_run:
            console.print("[yellow]Dry run - not executing[/yellow]")
            return False
        
        # Ask for approval
        if preview.risk_level == RiskLevel.CRITICAL:
            console.print("[bold red]⚠️  CRITICAL RISK - Please review carefully![/bold red]")
        
        return Confirm.ask("Apply this change?", default=preview.risk_level == RiskLevel.LOW)
    
    def _execute_change(self, change: dict) -> None:
        """Execute an approved change."""
        action = change["action"]
        path = os.path.join(self.working_directory, change["path"])
        
        try:
            if action == "create" or action == "modify":
                # Ensure directory exists
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(change.get("content", ""))
                console.print(f"[green]✓ {action.title()}d: {change['path']}[/green]")
                
            elif action == "delete":
                if os.path.exists(path):
                    os.remove(path)
                    console.print(f"[green]✓ Deleted: {change['path']}[/green]")
                else:
                    console.print(f"[yellow]File not found: {change['path']}[/yellow]")
                    
        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]")
    
    def _show_summary(self) -> None:
        """Show a summary of all changes."""
        console.print("\n" + "=" * 50)
        console.print("[bold]Summary[/bold]\n")
        
        if self.changes_made:
            console.print(f"[green]✓ {len(self.changes_made)} changes applied[/green]")
            for change in self.changes_made:
                console.print(f"  - {change['action']}: {change['path']}")
        
        if self.changes_rejected:
            console.print(f"[yellow]⊘ {len(self.changes_rejected)} changes skipped[/yellow]")
            for change in self.changes_rejected:
                console.print(f"  - {change['action']}: {change['path']}")
        
        if not self.changes_made and not self.changes_rejected:
            console.print("[dim]No changes to report[/dim]")
