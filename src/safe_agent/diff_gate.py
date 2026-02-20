"""
Git-diff based safety gate for API-keyless CI checks.
"""

from __future__ import annotations

import datetime
import re
import subprocess  # nosec B404
from collections import Counter
from pathlib import Path
from typing import Any

from agent_polis.actions.analyzer import ImpactAnalyzer
from agent_polis.actions.models import ActionRequest, ActionType, RiskLevel
from agent_polis.governance.policy import PolicyConfig, PolicyDecision, PolicyEvaluator, PolicyRule
from agent_polis.governance.policy import load_policy_from_file
from agent_polis.governance.presets import load_policy_preset
from agent_polis.governance.prompt_scanner import PromptInjectionScanner


class DiffGateRunner:
    """Analyze Git diff changes with impact-preview, without LLM planning."""

    def __init__(
        self,
        *,
        working_directory: str,
        diff_ref: str | None = None,
        fail_on_risk: RiskLevel | None = None,
        policy_path: str | None = None,
        policy_preset: str | None = None,
        compliance_mode: bool = False,
    ) -> None:
        self.working_directory = working_directory
        self.diff_ref = diff_ref
        self.fail_on_risk = fail_on_risk
        self.compliance_mode = compliance_mode
        if self.diff_ref:
            self.diff_ref = self._validate_diff_ref(self.diff_ref)

        self.analyzer = ImpactAnalyzer(working_directory=self.working_directory)
        self._policy_evaluator = PolicyEvaluator()
        self._scanner = PromptInjectionScanner()
        self._policy_decision_enum = PolicyDecision
        self._policy_config, self._policy_source = self._build_policy_config(
            policy_path=policy_path,
            policy_preset=policy_preset,
        )

        self.changes_made: list[dict[str, Any]] = []
        self.changes_rejected: list[dict[str, Any]] = []
        self.max_risk_level_seen: RiskLevel | None = None
        self.risk_policy_failed = False
        self.governance_policy_failed = False
        self.governance_policy_reason: str | None = None
        self._governance_events: list[dict[str, Any]] = []

    @staticmethod
    def _validate_diff_ref(raw_ref: str) -> str:
        ref = (raw_ref or "").strip()
        if not ref:
            raise ValueError("diff_ref cannot be empty.")
        if ref.startswith("-"):
            raise ValueError("diff_ref cannot start with '-'.")
        if "\x00" in ref:
            raise ValueError("diff_ref contains invalid characters.")
        if re.search(r"\s", ref):
            raise ValueError("diff_ref cannot contain whitespace.")
        return ref

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

    def _resolve_path_safe(self, path: str) -> Path | None:
        raw = (path or "").strip()
        if not raw or raw in {".", "./"}:
            return None
        if raw.startswith("~") or "\x00" in raw:
            return None
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

    def _build_policy_config(
        self, *, policy_path: str | None, policy_preset: str | None
    ) -> tuple[PolicyConfig, str]:
        if policy_path and policy_preset:
            raise ValueError("Use either policy_path or policy_preset (not both).")

        base = Path(self.working_directory).resolve()
        if policy_path:
            raw = str(policy_path).strip()
            candidate = Path(raw)
            if candidate.is_absolute():
                resolved_path = candidate.resolve()
                try:
                    resolved_path.relative_to(base)
                except ValueError as exc:
                    raise ValueError("policy_path must be within the working directory") from exc
            else:
                resolved_path = self._resolve_path_safe(raw)
                if resolved_path is None:
                    raise ValueError("Unsafe policy_path (must be within the working directory)")
            config = load_policy_from_file(resolved_path)
            rel = resolved_path.relative_to(base)
            return config, f"file:{rel.as_posix()}"

        if policy_preset:
            return load_policy_preset(policy_preset), f"preset:{policy_preset}"

        rules: list[PolicyRule] = [
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
                )
            )
        return PolicyConfig(version="safe-agent-builtin-1", rules=rules), "builtin"

    def _run_git(self, *args: str) -> str:
        cmd = ["git", "-C", self.working_directory, *args]
        completed = subprocess.run(  # nosec B603
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
            raise RuntimeError(f"Git command failed ({' '.join(args)}): {detail}")
        return completed.stdout

    def _collect_diff_changes(self) -> list[dict[str, Any]]:
        self._run_git("rev-parse", "--is-inside-work-tree")

        if self.diff_ref:
            self._run_git("rev-parse", "--verify", "--quiet", "--end-of-options", f"{self.diff_ref}^{{commit}}")
            raw = self._run_git(
                "diff",
                "--name-status",
                "--find-renames",
                "--diff-filter=ACDMR",
                f"{self.diff_ref}...HEAD",
            )
        else:
            raw = self._run_git("diff", "--name-status", "--find-renames", "--diff-filter=ACDMR", "HEAD")

        changes: list[dict[str, Any]] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0]
            code = status[0]
            if code == "A" and len(parts) >= 2:
                changes.append({"action": "create", "path": parts[1], "description": f"create {parts[1]}"})
            elif code == "M" and len(parts) >= 2:
                changes.append({"action": "modify", "path": parts[1], "description": f"modify {parts[1]}"})
            elif code == "D" and len(parts) >= 2:
                changes.append({"action": "delete", "path": parts[1], "description": f"delete {parts[1]}"})
            elif code == "R" and len(parts) >= 3:
                old_path, new_path = parts[1], parts[2]
                changes.append({"action": "delete", "path": old_path, "description": f"rename-delete {old_path}"})
                changes.append({"action": "create", "path": new_path, "description": f"rename-create {new_path}"})

        if self.diff_ref:
            return changes

        tracked_paths = {change["path"] for change in changes}
        untracked_raw = self._run_git("ls-files", "--others", "--exclude-standard")
        for path in (line.strip() for line in untracked_raw.splitlines() if line.strip()):
            if path in tracked_paths:
                continue
            changes.append({"action": "create", "path": path, "description": f"create {path}"})

        return changes

    @staticmethod
    def _read_content(path: Path) -> str:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_bytes().decode("utf-8", errors="replace")
        except OSError:
            return ""
        if len(text) > 200_000:
            return text[:200_000]
        return text

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
            actions.append("Re-run in task mode (with API key) for manual approvals.")
        if scanner_reason_ids:
            actions.append(
                "Investigate scanner findings before merge "
                f"({', '.join(scanner_reason_ids)})."
            )
        if not actions:
            actions.append("No blocking findings. Safe to continue with normal review.")
        return actions

    async def run(self) -> dict[str, Any]:
        changes = self._collect_diff_changes()
        if not changes:
            return {
                "success": True,
                "changes_made": [],
                "changes_rejected": [],
                "max_risk_level_seen": None,
                "risk_policy_failed": False,
                "governance_policy_failed": False,
                "governance_policy_reason": None,
            }

        for change in changes:
            action = change["action"]
            path = change["path"]
            resolved_path = self._resolve_path_safe(path)
            if resolved_path is None:
                self._note_risk(RiskLevel.CRITICAL)
                if self.fail_on_risk and self._risk_severity(RiskLevel.CRITICAL) >= self._risk_severity(
                    self.fail_on_risk
                ):
                    self.risk_policy_failed = True
                self.changes_rejected.append(change)
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
                continue

            if action == "create":
                action_type = ActionType.FILE_CREATE
                payload = {"content": self._read_content(resolved_path)}
            elif action == "modify":
                action_type = ActionType.FILE_WRITE
                payload = {"content": self._read_content(resolved_path)}
            elif action == "delete":
                action_type = ActionType.FILE_DELETE
                payload = {"content": ""}
            else:
                self.changes_rejected.append(change)
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
                continue

            request = ActionRequest(
                action_type=action_type,
                target=str(resolved_path),
                description=change.get("description", f"{action} {path}"),
                payload=payload,
            )

            preview = await self.analyzer.analyze(request)
            self._note_risk(preview.risk_level)

            policy_result = self._policy_evaluator.evaluate(
                self._policy_config,
                request,
                risk_level=preview.risk_level,
            )
            scan_result = self._scanner.scan_action_request(request)

            policy_decision = policy_result.decision
            matched_rule = getattr(policy_result, "matched_rule_id", None)
            scan_reason_ids = sorted({finding.reason_id for finding in getattr(scan_result, "findings", [])})
            scan_max = getattr(scan_result, "max_severity", lambda: None)()
            scan_max_str = getattr(scan_max, "value", str(scan_max)).lower() if scan_max else None

            if policy_decision == self._policy_decision_enum.DENY:
                self.governance_policy_failed = True
                self.governance_policy_reason = matched_rule or "policy_denied"
                self.changes_rejected.append(change)
                self._record_governance_event(
                    path=path,
                    action=action,
                    risk_level=preview.risk_level,
                    policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                    matched_rule_id=matched_rule,
                    scanner_severity=scan_max_str,
                    scanner_reason_ids=scan_reason_ids,
                    outcome="blocked_by_policy_deny",
                )
                continue

            if self.fail_on_risk and self._risk_severity(preview.risk_level) >= self._risk_severity(self.fail_on_risk):
                self.risk_policy_failed = True
                self.changes_rejected.append(change)
                self._record_governance_event(
                    path=path,
                    action=action,
                    risk_level=preview.risk_level,
                    policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                    matched_rule_id=matched_rule,
                    scanner_severity=scan_max_str,
                    scanner_reason_ids=scan_reason_ids,
                    outcome="blocked_by_fail_on_risk",
                )
                continue

            if policy_decision == self._policy_decision_enum.ALLOW:
                self.changes_made.append(change)
                self._record_governance_event(
                    path=path,
                    action=action,
                    risk_level=preview.risk_level,
                    policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                    matched_rule_id=matched_rule,
                    scanner_severity=scan_max_str,
                    scanner_reason_ids=scan_reason_ids,
                    outcome="approved_non_interactive",
                )
            else:
                self.changes_rejected.append(change)
                self._record_governance_event(
                    path=path,
                    action=action,
                    risk_level=preview.risk_level,
                    policy_decision=getattr(policy_decision, "value", str(policy_decision)),
                    matched_rule_id=matched_rule,
                    scanner_severity=scan_max_str,
                    scanner_reason_ids=scan_reason_ids,
                    outcome="blocked_non_interactive_requires_approval",
                )

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

    def build_policy_report(self) -> dict[str, Any]:
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
                "approved_changes": len(self.changes_made),
                "rejected_changes": len(self.changes_rejected),
                "max_risk_level_seen": self.max_risk_level_seen.value if self.max_risk_level_seen else None,
            },
            "approved_changes": [
                {"action": change.get("action"), "path": change.get("path")} for change in self.changes_made
            ],
            "rejected_changes": [
                {"action": change.get("action"), "path": change.get("path")} for change in self.changes_rejected
            ],
            "policy_report": self.build_policy_report(),
        }

    def build_ci_summary(self) -> str:
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
            "- Mode: API-keyless diff gate",
            f"- Planned changes: {len(self._governance_events)}",
            f"- Approved changes: {len(self.changes_made)}",
            f"- Rejected changes: {len(self.changes_rejected)}",
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

    def build_safety_scorecard(self) -> str:
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
            "- Mode: API-keyless diff gate",
            f"- Policy source: `{self._policy_source}`",
            f"- Max risk seen: {max_risk}",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Planned changes | {len(self._governance_events)} |",
            f"| Approved changes | {len(self.changes_made)} |",
            f"| Rejected changes | {len(self.changes_rejected)} |",
            f"| Blocked by policy deny | {outcome_counts.get('blocked_by_policy_deny', 0)} |",
            f"| Blocked by fail-on-risk | {outcome_counts.get('blocked_by_fail_on_risk', 0)} |",
            (
                "| Blocked (non-interactive approval required) | "
                f"{outcome_counts.get('blocked_non_interactive_requires_approval', 0)} |"
            ),
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
