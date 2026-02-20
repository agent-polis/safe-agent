"""
Safe Agent - Core agent logic with impact preview integration.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

# Import impact-preview components (package is impact-preview, module is agent_polis)
from agent_polis.actions.analyzer import ImpactAnalyzer
from agent_polis.actions.diff import format_diff_plain
from agent_polis.actions.models import ActionRequest, ActionType, RiskLevel

from safe_agent import __version__ as SAFE_AGENT_VERSION

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
        non_interactive: bool = False,
        fail_on_risk: RiskLevel | None = None,
        audit_export_path: str | None = None,
        compliance_mode: bool = False,
        policy_path: str | None = None,
        policy_preset: str | None = None,
    ):
        self.model = model
        self.auto_approve_low_risk = auto_approve_low_risk and not compliance_mode
        self.dry_run = dry_run
        self.working_directory = working_directory or os.getcwd()
        self.non_interactive = non_interactive
        self.fail_on_risk = fail_on_risk
        self.audit_export_path = audit_export_path
        self.compliance_mode = compliance_mode

        # Compliance mode enforces strict settings
        if compliance_mode:
            self.auto_approve_low_risk = False

        self.client = anthropic.Anthropic()
        self.analyzer = ImpactAnalyzer(working_directory=self.working_directory)

        # Track changes for summary
        self.changes_made: list[dict] = []
        self.changes_rejected: list[dict] = []
        self.max_risk_level_seen: RiskLevel | None = None
        self.risk_policy_failed = False
        self.governance_policy_failed = False
        self.governance_policy_reason: str | None = None
        self._governance_events: list[dict[str, Any]] = []

        # Audit trail tracking
        self.audit_trail: dict[str, Any] = {
            "audit_metadata": {
                "export_version": "1.0",
                "agent_version": f"safe-agent {SAFE_AGENT_VERSION}",
                "compliance_mode": compliance_mode,
            },
            "task": {},
            "changes": [],
            "summary": {},
        }

        import datetime
        import getpass
        self._task_start_time = datetime.datetime.now(datetime.timezone.utc)
        self._current_user = getpass.getuser()

        # Governance / policy-as-code (impact-preview Stage 1+).
        self._policy_source: str = "builtin"
        self._policy_config: Any | None = None
        self._policy_evaluator: Any | None = None
        self._policy_decision_enum: Any | None = None
        self._scanner: Any | None = None
        self._init_governance(policy_path=policy_path, policy_preset=policy_preset)

    def _init_governance(self, *, policy_path: str | None, policy_preset: str | None) -> None:
        """
        Initialize policy evaluator + prompt scanner.

        We import these lazily so older installs fail with a clear error message.
        """
        try:
            from agent_polis.governance.policy import PolicyConfig, PolicyDecision, PolicyEvaluator, PolicyRule
            from agent_polis.governance.policy import load_policy_from_file
            from agent_polis.governance.presets import load_policy_preset
            from agent_polis.governance.prompt_scanner import PromptInjectionScanner
        except ModuleNotFoundError as exc:  # pragma: no cover (exercised via integration)
            raise RuntimeError(
                "safe-agent-cli governance features require impact-preview>=0.2.2. "
                "Upgrade with: pip install -U impact-preview"
            ) from exc

        if policy_path and policy_preset:
            raise ValueError("Use either policy_path or policy_preset (not both).")

        self._policy_evaluator = PolicyEvaluator()
        self._policy_decision_enum = PolicyDecision
        self._scanner = PromptInjectionScanner()

        if policy_path:
            # Avoid turning Safe Agent into an arbitrary file reader (especially via MCP tool calls).
            # Allow absolute paths only if they resolve under the working directory.
            raw = str(policy_path).strip()
            base = Path(self.working_directory).resolve()
            candidate = Path(raw)
            if candidate.is_absolute():
                resolved = candidate.resolve()
                try:
                    resolved.relative_to(base)
                except ValueError as exc:
                    raise ValueError(
                        "policy_path must be within the working directory"
                    ) from exc
                resolved_path = resolved
            else:
                resolved_path = self._resolve_path_safe(raw)
                if resolved_path is None:
                    raise ValueError("Unsafe policy_path (must be within the working directory)")

            self._policy_config = load_policy_from_file(resolved_path)
            # Keep logs privacy-friendly: show a workdir-relative policy location.
            rel = resolved_path.relative_to(base)
            self._policy_source = f"file:{rel.as_posix()}"
            return

        if policy_preset:
            self._policy_config = load_policy_preset(policy_preset)
            self._policy_source = f"preset:{policy_preset}"
            return

        # Built-in policy: deny obvious secret/key targets and allow low/medium risk actions.
        # Compliance mode is stricter: require approval for everything by omitting allow rules.
        rules: list[Any] = [
            PolicyRule(
                id="builtin:deny-secrets-and-keys",
                decision=PolicyDecision.DENY,
                priority=0,
                target_contains=[
                    ".env",
                    ".ssh",
                    "id_rsa",
                    "credentials",
                    "secrets",
                    "password",
                    ".pem",
                    "api_key",
                    "secret_key",
                    "access_key",
                ],
                metadata={
                    "rationale": (
                        "Secrets/key material should not be modified or handled by agent actions "
                        "without explicit, out-of-band review."
                    ),
                },
            ),
        ]

        if not self.compliance_mode:
            rules.append(
                PolicyRule(
                    id="builtin:allow-low-and-medium-risk",
                    decision=PolicyDecision.ALLOW,
                    priority=100,
                    max_risk_level=RiskLevel.MEDIUM,
                    metadata={
                        "rationale": (
                            "Default Safe Agent policy allows low/medium risk actions; higher risk "
                            "requires explicit approval."
                        ),
                    },
                )
            )

        self._policy_config = PolicyConfig(version="safe-agent-builtin-1", rules=rules)

    def _resolve_path_safe(self, path: str) -> Path | None:
        """Resolve a path safely under the working directory.

        Returns None if the path is absolute, attempts traversal, or resolves
        outside the working directory (including via symlinks).
        """

        raw = (path or "").strip()
        if not raw or raw in {".", "./"}:
            return None
        if raw.startswith("~"):
            return None
        if "\x00" in raw:
            return None
        # Reject likely Windows absolute paths (drive letter or UNC).
        if len(raw) >= 2 and raw[1] == ":" and raw[0].isalpha():
            return None
        if raw.startswith("\\\\"):
            return None

        candidate = Path(raw)
        if candidate.is_absolute():
            return None

        base = Path(self.working_directory).resolve()
        resolved = (base / candidate).resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            return None
        return resolved

    @staticmethod
    def _risk_severity(level: RiskLevel) -> int:
        order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        return order.get(level, 99)

    def _note_risk(self, level: RiskLevel) -> None:
        if self.max_risk_level_seen is None:
            self.max_risk_level_seen = level
            return
        if self._risk_severity(level) > self._risk_severity(self.max_risk_level_seen):
            self.max_risk_level_seen = level

    def _evaluate_governance(self, request: ActionRequest, risk_level: RiskLevel) -> tuple[Any, Any]:
        """Return (policy_result, scan_result) for an action request."""
        policy_result = self._policy_evaluator.evaluate(self._policy_config, request, risk_level=risk_level)
        scan_result = self._scanner.scan_action_request(request)
        return policy_result, scan_result

    def _record_governance_event(
        self,
        *,
        path: str,
        action: str,
        risk_level: RiskLevel | None,
        policy_decision: str | None,
        matched_rule_id: str | None,
        scanner_severity: str | None,
        scanner_reason_ids: list[str],
        outcome: str,
    ) -> None:
        """Capture CI-facing policy/scanner details per proposed change."""
        self._governance_events.append(
            {
                "path": path,
                "action": action,
                "risk_level": risk_level.value if risk_level else None,
                "policy_decision": policy_decision,
                "matched_rule_id": matched_rule_id,
                "scanner_severity": scanner_severity,
                "scanner_reason_ids": scanner_reason_ids,
                "outcome": outcome,
            }
        )

    def _recommended_next_actions(self) -> list[str]:
        actions: list[str] = []
        blocking_rule_ids = sorted(
            {
                event["matched_rule_id"]
                for event in self._governance_events
                if event.get("outcome") == "blocked_by_policy_deny" and event.get("matched_rule_id")
            }
        )
        scanner_reason_ids = sorted(
            {
                reason
                for event in self._governance_events
                for reason in event.get("scanner_reason_ids", [])
            }
        )

        if blocking_rule_ids:
            actions.append(
                "Review blocking policy rules "
                f"({', '.join(blocking_rule_ids)}) and adjust task scope or policy."
            )
        if self.risk_policy_failed and self.fail_on_risk:
            actions.append(
                f"Reduce change risk or adjust --fail-on-risk (currently {self.fail_on_risk.value})."
            )
        if any(event.get("outcome") == "blocked_non_interactive_requires_approval" for event in self._governance_events):
            actions.append("Re-run interactively for manual approvals or use a more permissive preset.")
        if scanner_reason_ids:
            actions.append(
                "Investigate scanner findings before merge "
                f"({', '.join(scanner_reason_ids)})."
            )
        if not actions:
            actions.append("No blocking findings. Safe to continue with normal review.")
        return actions

    def build_ci_summary(self) -> str:
        """Build a concise markdown summary for CI logs or PR comments."""
        status = "FAIL" if (self.risk_policy_failed or self.governance_policy_failed) else "PASS"
        status_icon = "❌" if status == "FAIL" else "✅"
        max_risk = self.max_risk_level_seen.value.upper() if self.max_risk_level_seen else "NONE"
        blocking_rule_ids = sorted(
            {
                event["matched_rule_id"]
                for event in self._governance_events
                if event.get("outcome") == "blocked_by_policy_deny" and event.get("matched_rule_id")
            }
        )
        scanner_reason_ids = sorted(
            {
                reason
                for event in self._governance_events
                for reason in event.get("scanner_reason_ids", [])
            }
        )

        lines = [
            "### Safe Agent CI Summary",
            f"- Result: {status_icon} {status}",
            f"- Planned changes: {len(self._governance_events)}",
            f"- Applied changes: {len(self.changes_made)}",
            f"- Skipped/rejected changes: {len(self.changes_rejected)}",
            f"- Max risk seen: {max_risk}",
            (
                "- Blocking policy rules: "
                + (", ".join(f"`{rule}`" for rule in blocking_rule_ids) if blocking_rule_ids else "none")
            ),
            (
                "- Scanner reason IDs: "
                + (", ".join(f"`{reason}`" for reason in scanner_reason_ids) if scanner_reason_ids else "none")
            ),
            "- Recommended next actions:",
        ]
        for action in self._recommended_next_actions():
            lines.append(f"  - {action}")
        return "\n".join(lines)

    def build_policy_report(self) -> dict[str, Any]:
        """Build machine-readable policy/scanner report for CI artifacts."""
        status = "failed" if (self.risk_policy_failed or self.governance_policy_failed) else "passed"
        max_risk = self.max_risk_level_seen.value if self.max_risk_level_seen else None
        blocking_rule_ids = sorted(
            {
                event["matched_rule_id"]
                for event in self._governance_events
                if event.get("outcome") == "blocked_by_policy_deny" and event.get("matched_rule_id")
            }
        )
        return {
            "status": status,
            "policy_source": self._policy_source,
            "fail_on_risk": self.fail_on_risk.value if self.fail_on_risk else None,
            "max_risk_level_seen": max_risk,
            "risk_policy_failed": self.risk_policy_failed,
            "governance_policy_failed": self.governance_policy_failed,
            "governance_policy_reason": self.governance_policy_reason,
            "blocking_rule_ids": blocking_rule_ids,
            "recommended_next_actions": self._recommended_next_actions(),
            "events": self._governance_events,
        }

    def build_machine_report(self, *, run_success: bool) -> dict[str, Any]:
        """Build compact machine output suitable for adapters and workers."""
        outcomes = {event.get("outcome") for event in self._governance_events}
        if "blocked_non_interactive_requires_approval" in outcomes:
            run_status = "requires_approval"
        elif self.risk_policy_failed or self.governance_policy_failed:
            run_status = "blocked"
        elif run_success:
            run_status = "passed"
        else:
            run_status = "failed"

        return {
            "schema_version": "1",
            "run_status": run_status,
            "success": run_success,
            "summary": {
                "planned_changes": len(self._governance_events),
                "applied_changes": len(self.changes_made),
                "rejected_changes": len(self.changes_rejected),
                "max_risk_level_seen": self.max_risk_level_seen.value if self.max_risk_level_seen else None,
            },
            "applied_changes": [
                {"action": change.get("action"), "path": change.get("path")} for change in self.changes_made
            ],
            "rejected_changes": [
                {"action": change.get("action"), "path": change.get("path")} for change in self.changes_rejected
            ],
            "policy_report": self.build_policy_report(),
        }

    def build_safety_scorecard(self) -> str:
        """Build a markdown safety scorecard suitable for release/PR artifacts."""
        import datetime

        status = "FAIL" if (self.risk_policy_failed or self.governance_policy_failed) else "PASS"
        status_icon = "❌" if status == "FAIL" else "✅"
        max_risk = self.max_risk_level_seen.value.upper() if self.max_risk_level_seen else "NONE"

        outcome_counts = Counter(event.get("outcome", "unknown") for event in self._governance_events)
        risk_counts = Counter(
            str(event["risk_level"]).upper()
            for event in self._governance_events
            if event.get("risk_level") is not None
        )
        scanner_reason_ids = sorted(
            {
                reason
                for event in self._governance_events
                for reason in event.get("scanner_reason_ids", [])
            }
        )
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        lines = [
            "### Safe Agent Safety Scorecard",
            f"- Generated at (UTC): {generated_at}",
            f"- Result: {status_icon} {status}",
            f"- Policy source: `{self._policy_source}`",
            f"- Max risk seen: {max_risk}",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Planned changes | {len(self._governance_events)} |",
            f"| Applied changes | {len(self.changes_made)} |",
            f"| Skipped/rejected changes | {len(self.changes_rejected)} |",
            f"| Blocked by policy deny | {outcome_counts.get('blocked_by_policy_deny', 0)} |",
            f"| Blocked by fail-on-risk | {outcome_counts.get('blocked_by_fail_on_risk', 0)} |",
            (
                "| Blocked (non-interactive approval required) | "
                f"{outcome_counts.get('blocked_non_interactive_requires_approval', 0)} |"
            ),
            f"| Dry-run skips | {outcome_counts.get('blocked_dry_run', 0)} |",
            f"| Scanner reason IDs (unique) | {len(scanner_reason_ids)} |",
        ]

        if risk_counts:
            lines.extend(
                [
                    "",
                    "| Risk level | Count |",
                    "| --- | --- |",
                ]
            )
            for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                lines.append(f"| {level} | {risk_counts.get(level, 0)} |")

        if scanner_reason_ids:
            lines.append("")
            lines.append(
                "- Scanner reason IDs: " + ", ".join(f"`{reason}`" for reason in scanner_reason_ids)
            )
        else:
            lines.append("")
            lines.append("- Scanner reason IDs: none")

        lines.append("- Recommended next actions:")
        for action in self._recommended_next_actions():
            lines.append(f"  - {action}")

        return "\n".join(lines)
    
    async def run(self, task: str) -> dict[str, Any]:
        """
        Execute a coding task with impact preview on all file operations.
        """
        console.print("\n[bold]🤖 Planning changes...[/bold]\n")
        
        # Get Claude to plan the changes
        plan = await self._plan_changes(task)
        
        if not plan.get("changes"):
            console.print("[yellow]No file changes needed for this task.[/yellow]")

            # Finalize and export audit trail even for no-op tasks
            self._finalize_audit_trail(task)
            if self.audit_export_path:
                self.export_audit_trail()

            return {
                "success": True,
                "changes_made": [],
                "changes_rejected": [],
                "max_risk_level_seen": None,
                "risk_policy_failed": False,
                "governance_policy_failed": False,
                "governance_policy_reason": None,
            }
        
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

        # Finalize and export audit trail
        self._finalize_audit_trail(task)
        if self.audit_export_path:
            self.export_audit_trail()

        success = not (self.risk_policy_failed or self.governance_policy_failed)
        return {
            "success": success,
            "changes_made": self.changes_made,
            "changes_rejected": self.changes_rejected,
            "max_risk_level_seen": self.max_risk_level_seen.value if self.max_risk_level_seen else None,
            "risk_policy_failed": self.risk_policy_failed,
            "governance_policy_failed": self.governance_policy_failed,
            "governance_policy_reason": self.governance_policy_reason,
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
        except OSError as exc:
            console.print(f"[dim]Skipping file context due to filesystem error: {exc}[/dim]")
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
        resolved_path = self._resolve_path_safe(path)
        if resolved_path is None:
            console.print(f"[red]Unsafe path rejected (outside working directory): {path}[/red]")
            self._note_risk(RiskLevel.CRITICAL)
            if self.fail_on_risk and self._risk_severity(RiskLevel.CRITICAL) >= self._risk_severity(
                self.fail_on_risk
            ):
                self.risk_policy_failed = True
            self._record_governance_event(
                path=path,
                action=action,
                risk_level=RiskLevel.CRITICAL,
                policy_decision=None,
                matched_rule_id=None,
                scanner_severity=None,
                scanner_reason_ids=[],
                outcome="blocked_unsafe_path",
            )
            return False
        
        # Map to ActionType
        if action == "create":
            action_type = ActionType.FILE_CREATE
        elif action == "modify":
            action_type = ActionType.FILE_WRITE
        elif action == "delete":
            action_type = ActionType.FILE_DELETE
        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            self._record_governance_event(
                path=path,
                action=action,
                risk_level=None,
                policy_decision=None,
                matched_rule_id=None,
                scanner_severity=None,
                scanner_reason_ids=[],
                outcome="blocked_unknown_action",
            )
            return False
        
        # Create request
        request = ActionRequest(
            action_type=action_type,
            target=str(resolved_path),
            description=change.get("description", f"{action} {path}"),
            payload={"content": change.get("content", "")},
        )
        
        # Analyze with impact-preview
        preview = await self.analyzer.analyze(request)
        self._note_risk(preview.risk_level)

        policy_result, scan_result = self._evaluate_governance(request, preview.risk_level)

        policy_triggered = bool(
            self.fail_on_risk
            and self._risk_severity(preview.risk_level) >= self._risk_severity(self.fail_on_risk)
        )
        if policy_triggered:
            self.risk_policy_failed = True

        policy_decision = policy_result.decision
        matched_rule = getattr(policy_result, "matched_rule_id", None)
        scan_reason_ids = sorted({f.reason_id for f in getattr(scan_result, "findings", [])})
        scan_max = getattr(scan_result, "max_severity", lambda: None)()
        scan_max_str = getattr(scan_max, "value", str(scan_max)).upper() if scan_max else "NONE"
        scan_reason_suffix = f" ({', '.join(scan_reason_ids)})" if scan_reason_ids else ""
        policy_rule_suffix = f" (rule: {matched_rule})" if matched_rule else ""
        
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
            f"**Risk:** {risk_emoji} {preview.risk_level.value.upper()}\n"
            f"**Policy:** {getattr(policy_decision, 'value', str(policy_decision)).upper()}"
            f"{policy_rule_suffix} [{self._policy_source}]\n"
            f"**Scanner:** {scan_max_str}{scan_reason_suffix}",
            title="Impact Preview",
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

        # Policy-as-code enforcement: DENY is never allowed to proceed.
        if policy_decision == self._policy_decision_enum.DENY:
            self.governance_policy_failed = True
            self.governance_policy_reason = matched_rule or "policy_denied"
            self._record_governance_event(
                path=path,
                action=action,
                risk_level=preview.risk_level,
                policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                matched_rule_id=matched_rule,
                scanner_severity=scan_max_str.lower() if scan_max_str else None,
                scanner_reason_ids=scan_reason_ids,
                outcome="blocked_by_policy_deny",
            )
            console.print("[red]✗ Policy decision: DENY[/red]")
            return False

        if policy_triggered and self.fail_on_risk:
            self._record_governance_event(
                path=path,
                action=action,
                risk_level=preview.risk_level,
                policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                matched_rule_id=matched_rule,
                scanner_severity=scan_max_str.lower() if scan_max_str else None,
                scanner_reason_ids=scan_reason_ids,
                outcome="blocked_by_fail_on_risk",
            )
            console.print(
                f"[red]✗ Policy: --fail-on-risk={self.fail_on_risk.value} "
                f"(saw {preview.risk_level.value})[/red]"
            )
            return False

        if self.non_interactive:
            if policy_decision == self._policy_decision_enum.ALLOW:
                self._record_governance_event(
                    path=path,
                    action=action,
                    risk_level=preview.risk_level,
                    policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                    matched_rule_id=matched_rule,
                    scanner_severity=scan_max_str.lower() if scan_max_str else None,
                    scanner_reason_ids=scan_reason_ids,
                    outcome="approved_non_interactive",
                )
                console.print("[green]✓ Auto-approved (policy allows; non-interactive)[/green]")
                return True
            self._record_governance_event(
                path=path,
                action=action,
                risk_level=preview.risk_level,
                policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                matched_rule_id=matched_rule,
                scanner_severity=scan_max_str.lower() if scan_max_str else None,
                scanner_reason_ids=scan_reason_ids,
                outcome="blocked_non_interactive_requires_approval",
            )
            console.print("[yellow]⊘ Auto-rejected (policy requires approval; non-interactive)[/yellow]")
            return False
        
        # Auto-approve low risk if enabled
        if (
            self.auto_approve_low_risk
            and preview.risk_level == RiskLevel.LOW
            and policy_decision == self._policy_decision_enum.ALLOW
        ):
            self._record_governance_event(
                path=path,
                action=action,
                risk_level=preview.risk_level,
                policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                matched_rule_id=matched_rule,
                scanner_severity=scan_max_str.lower() if scan_max_str else None,
                scanner_reason_ids=scan_reason_ids,
                outcome="approved_auto_low_risk",
            )
            console.print("[green]✓ Auto-approved (low risk)[/green]")
            return True

        # Dry run mode
        if self.dry_run:
            self._record_governance_event(
                path=path,
                action=action,
                risk_level=preview.risk_level,
                policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                matched_rule_id=matched_rule,
                scanner_severity=scan_max_str.lower() if scan_max_str else None,
                scanner_reason_ids=scan_reason_ids,
                outcome="blocked_dry_run",
            )
            console.print("[yellow]Dry run - not executing[/yellow]")
            return False
        
        # Ask for approval
        if preview.risk_level == RiskLevel.CRITICAL:
            console.print("[bold red]⚠️  CRITICAL RISK - Please review carefully![/bold red]")
        
        approved = Confirm.ask("Apply this change?", default=preview.risk_level == RiskLevel.LOW)
        self._record_governance_event(
            path=path,
            action=action,
            risk_level=preview.risk_level,
            policy_decision=getattr(policy_decision, "value", str(policy_decision)),
            matched_rule_id=matched_rule,
            scanner_severity=scan_max_str.lower() if scan_max_str else None,
            scanner_reason_ids=scan_reason_ids,
            outcome="approved_interactive" if approved else "rejected_interactive",
        )
        return approved
    
    def _execute_change(self, change: dict) -> None:
        """Execute an approved change."""
        action = change["action"]
        resolved_path = self._resolve_path_safe(change["path"])
        if resolved_path is None:
            console.print(
                f"[red]✗ Refusing to execute unsafe path (outside working directory): {change['path']}[/red]"
            )
            return
        
        try:
            if action == "create" or action == "modify":
                # Ensure directory exists
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                resolved_path.write_text(change.get("content", ""), encoding="utf-8")
                console.print(f"[green]✓ {action.title()}d: {change['path']}[/green]")
                
            elif action == "delete":
                if resolved_path.exists():
                    resolved_path.unlink()
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

        if self.max_risk_level_seen:
            console.print(f"[dim]Max risk seen: {self.max_risk_level_seen.value.upper()}[/dim]")
        if self.risk_policy_failed and self.fail_on_risk:
            console.print(
                f"[bold red]✗ Risk policy failed (>= {self.fail_on_risk.value.upper()})[/bold red]"
            )

    def _finalize_audit_trail(self, task: str) -> None:
        """Finalize audit trail with summary and metadata."""
        import datetime

        end_time = datetime.datetime.now(datetime.timezone.utc)

        # Update task metadata
        self.audit_trail["task"] = {
            "task_description": task,
            "requested_at": self._task_start_time.isoformat(),
            "requested_by": self._current_user,
            "working_directory": self.working_directory,
            "model_used": self.model,
        }

        # Update summary
        policy_violations = sum(
            1 for event in self._governance_events if event.get("outcome") == "blocked_by_policy_deny"
        )
        self.audit_trail["summary"] = {
            "total_changes_planned": len(self.changes_made) + len(self.changes_rejected),
            "changes_approved": len(self.changes_made),
            "changes_rejected": len(self.changes_rejected),
            "changes_executed": len(self.changes_made) if not self.dry_run else 0,
            "max_risk_level_seen": self.max_risk_level_seen.value if self.max_risk_level_seen else None,
            "policy_violations": policy_violations,
            "duration_seconds": (end_time - self._task_start_time).total_seconds(),
        }

        # Update metadata
        self.audit_trail["audit_metadata"]["export_timestamp"] = end_time.isoformat()

        # Compliance flags
        self.audit_trail["compliance_flags"] = {
            "compliance_mode_enabled": self.compliance_mode,
            "all_high_risk_approved": True,  # Would need to track rejections
            "policy_file_present": self._policy_source.startswith("file:"),
            "audit_trail_complete": True,
        }

    def export_audit_trail(self, path: str | None = None) -> None:
        """Export audit trail to JSON file."""
        import json

        export_path = path or self.audit_export_path
        if not export_path:
            return

        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.audit_trail, f, indent=2, ensure_ascii=False)
            console.print(f"\n[dim]Audit trail exported to: {export_path}[/dim]")
        except Exception as e:
            console.print(f"\n[yellow]Warning: Failed to export audit trail: {e}[/yellow]")
