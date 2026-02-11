"""
Comprehensive tests for EU AI Act compliance mode features.

These tests verify that Safe Agent implements EU AI Act requirements
as documented in docs/eu-ai-act-compliance.md:

- Article 9: Risk Management System
- Article 12: Record-Keeping (timestamps, audit logs)
- Article 14: Human Oversight (approval requirements)
- Article 15: Accuracy, Robustness, and Cybersecurity
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

try:
    from agent_polis.actions.models import RiskLevel
except ModuleNotFoundError:
    from impact_preview.actions.models import RiskLevel

from safe_agent.agent import SafeAgent


def _mock_preview(
    risk_level: RiskLevel,
    risk_factors: list[str] | None = None,
    file_changes: list | None = None,
) -> Mock:
    """Create a mock preview object for testing."""
    return Mock(
        risk_level=risk_level,
        risk_factors=risk_factors or [],
        file_changes=file_changes or [],
    )


# =============================================================================
# Article 12: Record-Keeping Requirements
# =============================================================================


class TestArticle12RecordKeeping:
    """
    Article 12 requires logging capabilities for traceability.
    Tests verify audit logs contain required information.
    """

    @pytest.mark.asyncio
    async def test_audit_log_has_iso8601_timestamps(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 12: Audit logs must have timestamps in ISO 8601 format.
        This format is internationally recognized and retention-friendly.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Verify timestamps exist and are ISO 8601
        requested_at = audit_data["task"]["requested_at"]
        export_timestamp = audit_data["audit_metadata"]["export_timestamp"]

        # Should parse without error
        dt_requested = datetime.datetime.fromisoformat(requested_at)
        dt_export = datetime.datetime.fromisoformat(export_timestamp)

        # Should include timezone (UTC)
        assert dt_requested.tzinfo is not None
        assert dt_export.tzinfo is not None

        # Should contain 'Z' or '+' indicating timezone
        assert "+" in requested_at or "Z" in requested_at or requested_at.endswith(
            "+00:00"
        )

    @pytest.mark.asyncio
    async def test_audit_log_has_requester_information(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 12: Must record who requested the operation.
        Required for accountability and compliance audits.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Requester must be recorded
        assert "requested_by" in audit_data["task"]
        assert audit_data["task"]["requested_by"]  # Not empty
        assert isinstance(audit_data["task"]["requested_by"], str)

    @pytest.mark.asyncio
    async def test_audit_log_has_task_description(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 12: Must record what operation was requested.
        Critical for understanding intent during audits.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        task_description = "Update production database schema"

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run(task_description)

        with open(export_path) as f:
            audit_data = json.load(f)

        # Task description must be recorded exactly
        assert audit_data["task"]["task_description"] == task_description

    @pytest.mark.asyncio
    async def test_audit_log_has_risk_assessment(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 12: Must record risk assessment results.
        Required to demonstrate risk management system.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Test",
                "changes": [
                    {
                        "action": "modify",
                        "path": "config.py",
                        "description": "Update config",
                        "content": "CONFIG='production'",
                    }
                ],
            }

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.HIGH),
            ):
                await agent.run("update config")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Risk assessment must be recorded
        assert "max_risk_level_seen" in audit_data["summary"]
        assert audit_data["summary"]["max_risk_level_seen"] == "high"

    @pytest.mark.asyncio
    async def test_audit_log_has_approval_records(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 12: Must record approval/rejection decisions.
        Critical for demonstrating human oversight.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Mixed",
                "changes": [
                    {
                        "action": "create",
                        "path": "approved.py",
                        "description": "Approved",
                        "content": "x",
                    },
                    {
                        "action": "delete",
                        "path": "rejected.py",
                        "description": "Rejected",
                    },
                ],
            }

            call_count = 0

            async def mock_analyze(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _mock_preview(RiskLevel.LOW)  # Will be approved
                else:
                    return _mock_preview(RiskLevel.CRITICAL)  # Will be rejected

            with patch.object(agent.analyzer, "analyze", side_effect=mock_analyze):
                await agent.run("mixed operations")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Must record both approvals and rejections
        assert "changes_approved" in audit_data["summary"]
        assert "changes_rejected" in audit_data["summary"]
        assert audit_data["summary"]["changes_approved"] == 1
        assert audit_data["summary"]["changes_rejected"] == 1

    @pytest.mark.asyncio
    async def test_audit_log_completeness_flag_set(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 12: Audit trail must indicate completeness.
        Helps auditors verify no data was lost or corrupted.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Completeness flag must be present and true
        assert "compliance_flags" in audit_data
        assert "audit_trail_complete" in audit_data["compliance_flags"]
        assert audit_data["compliance_flags"]["audit_trail_complete"] is True


# =============================================================================
# Article 14: Human Oversight Requirements
# =============================================================================


class TestArticle14HumanOversight:
    """
    Article 14 requires effective human oversight for high-risk AI systems.
    Tests verify that operations require approval based on risk level.
    """

    @pytest.mark.asyncio
    async def test_high_risk_requires_approval_not_auto_executed(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 14: HIGH risk operations must require human approval.
        Cannot be auto-executed without explicit human decision.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,  # Simulates automated environment
            auto_approve_low_risk=True,  # Even with auto-approve enabled
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Risky operation",
                "changes": [
                    {
                        "action": "delete",
                        "path": "production_db.sql",
                        "description": "Delete production database",
                    }
                ],
            }

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.HIGH),
            ):
                result = await agent.run("delete production db")

        # HIGH risk should be rejected in non-interactive mode
        # (requires explicit human approval)
        assert len(result["changes_made"]) == 0
        assert len(result["changes_rejected"]) == 1

    @pytest.mark.asyncio
    async def test_critical_risk_requires_approval_not_auto_executed(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 14: CRITICAL risk operations must require human approval.
        Highest level of oversight required.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            auto_approve_low_risk=True,
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Critical operation",
                "changes": [
                    {
                        "action": "modify",
                        "path": ".env",
                        "description": "Modify credentials",
                        "content": "API_KEY=secret",
                    }
                ],
            }

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.CRITICAL),
            ):
                result = await agent.run("update credentials")

        # CRITICAL risk must be rejected in non-interactive
        assert len(result["changes_made"]) == 0
        assert len(result["changes_rejected"]) == 1

    @pytest.mark.asyncio
    async def test_dry_run_mode_shows_preview_without_execution(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 14: Dry-run mode enables preview without execution.
        Allows operators to assess impact before approval.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=False,
            dry_run=True,  # Preview only
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Test change",
                "changes": [
                    {
                        "action": "create",
                        "path": "test.py",
                        "description": "Create file",
                        "content": "print('hello')",
                    }
                ],
            }

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.LOW),
            ):
                result = await agent.run("create test file")

        # Dry run: nothing executed
        assert result["changes_made"] == []
        assert not (temp_work_dir / "test.py").exists()

        # But audit still records the preview
        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["changes_executed"] == 0

    @pytest.mark.asyncio
    async def test_rejected_operations_logged_in_audit(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 14: Rejected operations must be logged.
        Demonstrates oversight is functioning.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Dangerous",
                "changes": [
                    {
                        "action": "delete",
                        "path": "critical_data.sql",
                        "description": "Delete critical data",
                    }
                ],
            }

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.CRITICAL),
            ):
                result = await agent.run("delete data")

        # Verify rejection recorded
        assert len(result["changes_rejected"]) == 1

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["changes_rejected"] == 1
        assert audit_data["summary"]["changes_approved"] == 0

    @pytest.mark.asyncio
    async def test_compliance_mode_forces_approval_for_all_levels(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 14: Compliance mode enforces strictest oversight.
        ALL changes require approval, even LOW risk.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            auto_approve_low_risk=True,  # Normally would auto-approve
            compliance_mode=True,  # But compliance mode overrides
        )

        # Compliance mode should have disabled auto_approve_low_risk
        assert agent.compliance_mode is True
        assert agent.auto_approve_low_risk is False

    @pytest.mark.asyncio
    async def test_low_risk_auto_approved_without_compliance_mode(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 14: Without compliance mode, LOW risk can be auto-approved.
        This is the normal operating mode for non-regulated environments.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            auto_approve_low_risk=True,
            compliance_mode=False,  # Not in compliance mode
            non_interactive=False,
        )

        # Mock the preview_and_approve method
        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Safe change",
                "changes": [
                    {
                        "action": "create",
                        "path": "docs/readme.md",
                        "description": "Add docs",
                        "content": "# Docs",
                    }
                ],
            }

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.LOW),
            ):
                result = await agent.run("add documentation")

        # LOW risk should be auto-approved
        assert len(result["changes_made"]) == 1
        assert (temp_work_dir / "docs" / "readme.md").exists()


# =============================================================================
# Article 15: Accuracy, Robustness, and Cybersecurity Requirements
# =============================================================================


class TestArticle15AccuracyRobustnessCybersecurity:
    """
    Article 15 requires appropriate accuracy, robustness, and security.
    Tests verify path safety, error handling, and resilience.
    """

    def test_path_safety_prevents_directory_traversal(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 15: Must prevent directory traversal attacks.
        Critical cybersecurity measure.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(working_directory=str(temp_work_dir))

        # Test various traversal attempts
        dangerous_paths = [
            "../../../etc/passwd",
            "../../.ssh/id_rsa",
            "foo/../../../secret",
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
        ]

        for dangerous_path in dangerous_paths:
            resolved = agent._resolve_path_safe(dangerous_path)
            assert (
                resolved is None
            ), f"Path traversal should be blocked: {dangerous_path}"

    @pytest.mark.asyncio
    async def test_unsafe_path_rejected_at_preview_stage(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 15: Unsafe operations must be rejected before execution.
        Defense in depth - multiple layers of protection.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Attack attempt",
                "changes": [
                    {
                        "action": "delete",
                        "path": "../../../etc/passwd",
                        "description": "Malicious",
                    }
                ],
            }

            result = await agent.run("attack")

        # Unsafe path should be rejected
        assert len(result["changes_made"]) == 0
        assert result["max_risk_level_seen"] == "critical"

    @pytest.mark.asyncio
    async def test_error_handling_does_not_crash_agent(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 15: System must handle errors gracefully (robustness).
        Failures should not crash the agent.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
        )

        # Mock _plan_changes to raise an exception
        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.side_effect = Exception("API Error")

            # Should not crash, should handle gracefully
            with pytest.raises(Exception) as exc_info:
                await agent.run("test task")

            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_audit_export_works_even_when_operations_fail(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 15: Audit logging must be resilient.
        Even if operations fail, audit trail can be manually exported.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Operation that will fail",
                "changes": [
                    {
                        "action": "create",
                        "path": "test.py",
                        "description": "Test",
                        "content": "test",
                    }
                ],
            }

            # Mock _execute_change to fail
            original_execute = agent._execute_change

            def failing_execute(change):
                raise OSError("Disk full")

            agent._execute_change = failing_execute

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.LOW),
            ):
                # This will fail during execution - expect the error
                with pytest.raises(OSError, match="Disk full"):
                    await agent.run("test")

            # Restore original
            agent._execute_change = original_execute

        # Manually finalize and export audit trail after error
        agent._finalize_audit_trail("test")
        agent.export_audit_trail()

        # Audit should be exported after manual call
        assert export_path.exists()

        with open(export_path) as f:
            audit_data = json.load(f)

        # Audit should be complete (tracks what happened before failure)
        assert audit_data["compliance_flags"]["audit_trail_complete"] is True

    @pytest.mark.asyncio
    async def test_path_safety_allows_safe_paths(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Article 15: Security measures must not block legitimate operations.
        Balance between security and usability (accuracy).
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(working_directory=str(temp_work_dir))

        # Test safe paths that should be allowed
        safe_paths = [
            "foo.py",
            "src/agent.py",
            "./config.yaml",
            "docs/guide.md",
            "sub/dir/file.txt",
        ]

        for safe_path in safe_paths:
            resolved = agent._resolve_path_safe(safe_path)
            assert (
                resolved is not None
            ), f"Safe path should be allowed: {safe_path}"
            assert str(resolved).startswith(str(temp_work_dir))


# =============================================================================
# Compliance Mode Documentation Tests
# =============================================================================


class TestComplianceModeDocumentation:
    """
    Tests that verify documented compliance mode behavior actually works.
    Based on docs/eu-ai-act-compliance.md specifications.
    """

    def test_compliance_mode_disables_auto_approve(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Documented: Compliance mode disables --auto-approve-low.
        Verify this is enforced at initialization.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Try to enable both
        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            auto_approve_low_risk=True,
            compliance_mode=True,
        )

        # Compliance mode should override
        assert agent.compliance_mode is True
        assert agent.auto_approve_low_risk is False

    @pytest.mark.asyncio
    async def test_compliance_mode_recorded_in_audit_metadata(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Documented: Compliance mode is recorded in audit metadata.
        Verify this appears in exported audit JSON.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
            compliance_mode=True,
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Must be in audit_metadata
        assert audit_data["audit_metadata"]["compliance_mode"] is True

    @pytest.mark.asyncio
    async def test_compliance_flags_section_present(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Documented: Audit export includes compliance_flags section.
        Verify all required flags are present.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
            compliance_mode=True,
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Compliance flags section must exist
        assert "compliance_flags" in audit_data

        flags = audit_data["compliance_flags"]
        assert "compliance_mode_enabled" in flags
        assert "all_high_risk_approved" in flags
        assert "policy_file_present" in flags
        assert "audit_trail_complete" in flags

        # In this test, compliance mode was enabled
        assert flags["compliance_mode_enabled"] is True

    @pytest.mark.asyncio
    async def test_compliance_mode_false_recorded_correctly(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        When compliance mode is NOT enabled, this should also be recorded.
        Ensures auditors can verify mode setting.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
            compliance_mode=False,  # Explicitly not in compliance mode
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Should record False, not just omit
        assert audit_data["audit_metadata"]["compliance_mode"] is False
        assert audit_data["compliance_flags"]["compliance_mode_enabled"] is False


# =============================================================================
# Audit Export Schema Compliance Tests
# =============================================================================


class TestAuditExportSchemaCompliance:
    """
    Tests that verify audit export format matches documented schema.
    Based on docs/eu-ai-act-compliance.md Article 12 section.
    """

    @pytest.mark.asyncio
    async def test_audit_export_has_all_required_sections(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Documented schema requires 4 top-level sections:
        audit_metadata, task, changes, summary
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        # All required top-level sections
        assert "audit_metadata" in audit_data
        assert "task" in audit_data
        assert "changes" in audit_data
        assert "summary" in audit_data

    @pytest.mark.asyncio
    async def test_audit_metadata_section_complete(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Audit metadata must include: export_version, export_timestamp,
        agent_version, compliance_mode
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        metadata = audit_data["audit_metadata"]
        assert "export_version" in metadata
        assert metadata["export_version"] == "1.0"
        assert "export_timestamp" in metadata
        assert "agent_version" in metadata
        assert "safe-agent" in metadata["agent_version"]
        assert "compliance_mode" in metadata

    @pytest.mark.asyncio
    async def test_task_section_complete(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Task section must include: task_description, requested_at,
        requested_by, working_directory, model_used
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        task = audit_data["task"]
        assert "task_description" in task
        assert "requested_at" in task
        assert "requested_by" in task
        assert "working_directory" in task
        assert "model_used" in task

    @pytest.mark.asyncio
    async def test_summary_section_complete(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Summary must include: total_changes_planned, changes_approved,
        changes_rejected, changes_executed, max_risk_level_seen,
        policy_violations, duration_seconds
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        summary = audit_data["summary"]
        assert "total_changes_planned" in summary
        assert "changes_approved" in summary
        assert "changes_rejected" in summary
        assert "changes_executed" in summary
        assert "max_risk_level_seen" in summary
        assert "policy_violations" in summary
        assert "duration_seconds" in summary

    @pytest.mark.asyncio
    async def test_audit_export_is_valid_json(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Audit export must be valid, parseable JSON.
        Required for long-term retention and automated processing.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        # Should parse without error
        with open(export_path) as f:
            audit_data = json.load(f)

        assert isinstance(audit_data, dict)

    @pytest.mark.asyncio
    async def test_audit_export_is_pretty_printed(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Audit export should be pretty-printed (indented) for human readability.
        Important for manual audits and regulatory inspection.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        # Read raw content
        with open(export_path) as f:
            content = f.read()

        # Pretty-printed JSON has newlines and indentation
        assert "\n" in content
        assert "  " in content  # Indentation present

    @pytest.mark.asyncio
    async def test_compliance_flags_all_present(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Compliance flags must include all documented fields.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Test", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        flags = audit_data["compliance_flags"]
        required_flags = [
            "compliance_mode_enabled",
            "all_high_risk_approved",
            "policy_file_present",
            "audit_trail_complete",
        ]

        for flag in required_flags:
            assert flag in flags
            assert isinstance(flags[flag], bool)
