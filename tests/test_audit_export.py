"""Comprehensive tests for audit export and compliance mode features."""

from __future__ import annotations

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


class TestAuditExportJSONFormat:
    """Tests for audit export JSON format validation."""

    @pytest.mark.asyncio
    async def test_audit_export_has_required_top_level_keys(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Audit export JSON contains all required top-level keys."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        # Mock _plan_changes to return no changes
        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing to do", "changes": []}
            await agent.run("test task")

        assert export_path.exists()
        with open(export_path) as f:
            audit_data = json.load(f)

        # Required top-level keys per insurance-integration.md spec
        assert "audit_metadata" in audit_data
        assert "task" in audit_data
        assert "changes" in audit_data
        assert "summary" in audit_data

    @pytest.mark.asyncio
    async def test_audit_metadata_has_required_fields(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Audit metadata contains all required fields."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
            compliance_mode=True,
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        metadata = audit_data["audit_metadata"]
        assert "export_version" in metadata
        assert metadata["export_version"] == "1.0"
        assert "agent_version" in metadata
        assert "safe-agent" in metadata["agent_version"]
        assert "compliance_mode" in metadata
        assert metadata["compliance_mode"] is True
        assert "export_timestamp" in metadata

    @pytest.mark.asyncio
    async def test_task_metadata_has_required_fields(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Task metadata contains all required fields."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("refactor the auth module")

        with open(export_path) as f:
            audit_data = json.load(f)

        task = audit_data["task"]
        assert "task_description" in task
        assert task["task_description"] == "refactor the auth module"
        assert "requested_at" in task
        assert "requested_by" in task
        assert "working_directory" in task
        assert task["working_directory"] == str(temp_work_dir)
        assert "model_used" in task

    @pytest.mark.asyncio
    async def test_summary_has_required_fields(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Summary contains all required fields."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test task")

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
    async def test_compliance_flags_present(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Compliance flags section is present with required fields."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        flags = audit_data["compliance_flags"]
        assert "compliance_mode_enabled" in flags
        assert "all_high_risk_approved" in flags
        assert "policy_file_present" in flags
        assert "audit_trail_complete" in flags


class TestComplianceModeEnforcement:
    """Tests for compliance mode strict settings enforcement."""

    def test_compliance_mode_disables_auto_approve(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Compliance mode disables auto-approve-low even when requested."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Try to enable both compliance_mode and auto_approve_low_risk
        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            auto_approve_low_risk=True,
            compliance_mode=True,
        )

        # Compliance mode should override auto_approve_low_risk
        assert agent.compliance_mode is True
        assert agent.auto_approve_low_risk is False

    def test_compliance_mode_false_allows_auto_approve(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without compliance mode, auto-approve can be enabled."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            auto_approve_low_risk=True,
            compliance_mode=False,
        )

        assert agent.compliance_mode is False
        assert agent.auto_approve_low_risk is True

    def test_compliance_mode_recorded_in_audit_metadata(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Compliance mode status is recorded in audit trail metadata."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent_compliant = SafeAgent(
            working_directory=str(temp_work_dir),
            compliance_mode=True,
        )
        assert agent_compliant.audit_trail["audit_metadata"]["compliance_mode"] is True

        agent_normal = SafeAgent(
            working_directory=str(temp_work_dir),
            compliance_mode=False,
        )
        assert agent_normal.audit_trail["audit_metadata"]["compliance_mode"] is False

    @pytest.mark.asyncio
    async def test_compliance_mode_recorded_in_export(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Compliance mode is correctly recorded in exported audit."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-compliant.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
            compliance_mode=True,
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["audit_metadata"]["compliance_mode"] is True
        assert audit_data["compliance_flags"]["compliance_mode_enabled"] is True


class TestAuditExportNoOpTasks:
    """Tests for audit export when no changes are made."""

    @pytest.mark.asyncio
    async def test_audit_export_for_noop_task(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Audit is exported even when no changes are planned."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-noop.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing to do", "changes": []}
            result = await agent.run("analyze code")

        # Should succeed
        assert result["success"] is True
        assert result["changes_made"] == []

        # Audit file should exist
        assert export_path.exists()

        with open(export_path) as f:
            audit_data = json.load(f)

        # Should have all required sections
        assert audit_data["task"]["task_description"] == "analyze code"
        assert audit_data["summary"]["total_changes_planned"] == 0
        assert audit_data["summary"]["changes_approved"] == 0
        assert audit_data["summary"]["changes_rejected"] == 0
        assert audit_data["changes"] == []

    @pytest.mark.asyncio
    async def test_max_risk_level_null_for_noop(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Max risk level is null when no changes are analyzed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-noop-risk.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            result = await agent.run("list files")

        assert result["max_risk_level_seen"] is None

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["max_risk_level_seen"] is None


class TestAuditExportWithApprovedChanges:
    """Tests for audit export when changes are approved and executed."""

    @pytest.mark.asyncio
    async def test_audit_tracks_approved_changes(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Approved changes are tracked in summary."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-approved.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        # Mock plan with one low-risk change
        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Create test file",
                "changes": [
                    {
                        "action": "create",
                        "path": "test.py",
                        "description": "Add test file",
                        "content": "# test",
                    }
                ],
            }

            # Mock analyzer to return low risk
            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.LOW),
            ):
                result = await agent.run("create test file")

        # Non-interactive mode auto-approves low risk
        assert result["success"] is True
        assert len(result["changes_made"]) == 1
        assert len(result["changes_rejected"]) == 0

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["total_changes_planned"] == 1
        assert audit_data["summary"]["changes_approved"] == 1
        assert audit_data["summary"]["changes_rejected"] == 0
        assert audit_data["summary"]["changes_executed"] == 1
        assert audit_data["summary"]["max_risk_level_seen"] == "low"

    @pytest.mark.asyncio
    async def test_max_risk_level_tracks_highest(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Max risk level tracks the highest risk seen across all changes."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-max-risk.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Multiple changes",
                "changes": [
                    {
                        "action": "create",
                        "path": "low.py",
                        "description": "Low risk",
                        "content": "x",
                    },
                    {
                        "action": "modify",
                        "path": "medium.py",
                        "description": "Medium risk",
                        "content": "y",
                    },
                ],
            }

            # Mock analyzer to return different risk levels
            call_count = 0
            async def mock_analyze(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _mock_preview(RiskLevel.LOW)
                else:
                    return _mock_preview(RiskLevel.MEDIUM)

            with patch.object(
                agent.analyzer,
                "analyze",
                side_effect=mock_analyze,
            ):
                result = await agent.run("multiple changes")

        assert result["max_risk_level_seen"] == "medium"

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["max_risk_level_seen"] == "medium"


class TestAuditExportWithRejectedChanges:
    """Tests for audit export when changes are rejected."""

    @pytest.mark.asyncio
    async def test_audit_tracks_rejected_changes(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rejected changes are tracked separately from approved."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-rejected.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Risky change",
                "changes": [
                    {
                        "action": "delete",
                        "path": "important.py",
                        "description": "Delete important file",
                    }
                ],
            }

            # Non-interactive mode rejects HIGH risk
            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.HIGH),
            ):
                result = await agent.run("delete files")

        assert result["success"] is True
        assert len(result["changes_made"]) == 0
        assert len(result["changes_rejected"]) == 1

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["total_changes_planned"] == 1
        assert audit_data["summary"]["changes_approved"] == 0
        assert audit_data["summary"]["changes_rejected"] == 1
        assert audit_data["summary"]["changes_executed"] == 0

    @pytest.mark.asyncio
    async def test_mixed_approved_and_rejected(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Audit correctly counts mix of approved and rejected changes."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-mixed.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Mixed changes",
                "changes": [
                    {
                        "action": "create",
                        "path": "safe.py",
                        "description": "Safe change",
                        "content": "safe",
                    },
                    {
                        "action": "delete",
                        "path": "risky.py",
                        "description": "Risky change",
                    },
                ],
            }

            call_count = 0
            async def mock_analyze(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _mock_preview(RiskLevel.LOW)
                else:
                    return _mock_preview(RiskLevel.CRITICAL)

            with patch.object(
                agent.analyzer,
                "analyze",
                side_effect=mock_analyze,
            ):
                result = await agent.run("mixed changes")

        assert len(result["changes_made"]) == 1
        assert len(result["changes_rejected"]) == 1

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["total_changes_planned"] == 2
        assert audit_data["summary"]["changes_approved"] == 1
        assert audit_data["summary"]["changes_rejected"] == 1


class TestAuditExportDryRun:
    """Tests for audit export in dry-run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_changes_executed_is_zero(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dry run mode reports zero changes executed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-dry-run.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=False,  # Must be False for dry_run check to be reached
            dry_run=True,  # Dry run mode
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Test change",
                "changes": [
                    {
                        "action": "create",
                        "path": "test.py",
                        "description": "Test",
                        "content": "test",
                    }
                ],
            }

            with patch.object(
                agent.analyzer,
                "analyze",
                new_callable=AsyncMock,
                return_value=_mock_preview(RiskLevel.LOW),
            ):
                result = await agent.run("test task")

        # In dry-run mode, _preview_and_approve returns False (line 390-392)
        # So changes are neither approved nor executed
        assert len(result["changes_made"]) == 0
        # In this case they're marked as rejected
        assert len(result["changes_rejected"]) == 1

        with open(export_path) as f:
            audit_data = json.load(f)

        # Total planned = approved + rejected
        assert audit_data["summary"]["total_changes_planned"] == 1
        assert audit_data["summary"]["changes_approved"] == 0
        assert audit_data["summary"]["changes_rejected"] == 1
        assert audit_data["summary"]["changes_executed"] == 0


class TestAuditExportErrorHandling:
    """Tests for error handling during audit export."""

    @pytest.mark.asyncio
    async def test_invalid_export_path_warns_but_continues(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        """Invalid export path logs warning but doesn't crash."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Use invalid path (non-existent directory)
        invalid_path = "/nonexistent/directory/audit.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=invalid_path,
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            result = await agent.run("test task")

        # Should succeed despite export failure
        assert result["success"] is True

        # Export file should not exist
        assert not Path(invalid_path).exists()

    @pytest.mark.asyncio
    async def test_no_export_path_no_file_created(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no export path is specified, no file is created."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=None,  # No export
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            result = await agent.run("test task")

        assert result["success"] is True

        # No audit file should be created
        audit_files = list(temp_work_dir.glob("*.json"))
        assert len(audit_files) == 0

    @pytest.mark.asyncio
    async def test_export_can_be_called_manually(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Audit can be exported manually to different path."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=None,  # Not set during init
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test task")

        # Manually export after run
        manual_path = temp_work_dir / "manual-audit.json"
        agent.export_audit_trail(str(manual_path))

        assert manual_path.exists()
        with open(manual_path) as f:
            audit_data = json.load(f)

        assert "task" in audit_data
        assert audit_data["task"]["task_description"] == "test task"


class TestAuditExportIntegration:
    """Integration tests for complete workflow with audit export."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_audit(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Complete workflow from plan to execution produces valid audit."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-complete.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        # Simulate realistic workflow
        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Refactor authentication",
                "changes": [
                    {
                        "action": "create",
                        "path": "auth/jwt.py",
                        "description": "Add JWT auth",
                        "content": "import jwt\n\ndef verify_token(token):\n    pass",
                    },
                    {
                        "action": "modify",
                        "path": "config/settings.py",
                        "description": "Update settings",
                        "content": "JWT_SECRET = 'secret'",
                    },
                ],
            }

            call_count = 0
            async def mock_analyze(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _mock_preview(RiskLevel.LOW, risk_factors=["New file creation"])
                else:
                    return _mock_preview(
                        RiskLevel.MEDIUM,
                        risk_factors=["Configuration change", "Credential pattern"],
                    )

            with patch.object(
                agent.analyzer,
                "analyze",
                side_effect=mock_analyze,
            ):
                result = await agent.run("refactor auth to use JWT")

        # Verify result
        assert result["success"] is True
        assert len(result["changes_made"]) == 2
        assert result["max_risk_level_seen"] == "medium"

        # Verify audit export
        assert export_path.exists()
        with open(export_path) as f:
            audit_data = json.load(f)

        # Verify all sections are complete
        assert audit_data["task"]["task_description"] == "refactor auth to use JWT"
        assert audit_data["summary"]["total_changes_planned"] == 2
        assert audit_data["summary"]["changes_approved"] == 2
        assert audit_data["summary"]["changes_executed"] == 2
        assert audit_data["summary"]["max_risk_level_seen"] == "medium"
        assert audit_data["summary"]["duration_seconds"] > 0
        assert audit_data["compliance_flags"]["audit_trail_complete"] is True

        # Verify files were actually created
        assert (temp_work_dir / "auth" / "jwt.py").exists()
        assert (temp_work_dir / "config" / "settings.py").exists()

    @pytest.mark.asyncio
    async def test_audit_duration_is_positive(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Audit duration is tracked and positive."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-duration.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["summary"]["duration_seconds"] >= 0
        assert isinstance(audit_data["summary"]["duration_seconds"], (int, float))

    @pytest.mark.asyncio
    async def test_audit_timestamps_are_iso_format(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All timestamps in audit are in ISO 8601 format."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-timestamps.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test task")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Check timestamp formats
        import datetime

        requested_at = audit_data["task"]["requested_at"]
        export_timestamp = audit_data["audit_metadata"]["export_timestamp"]

        # Should parse as ISO format
        datetime.datetime.fromisoformat(requested_at)
        datetime.datetime.fromisoformat(export_timestamp)

        # Should contain timezone info
        assert "+" in requested_at or "Z" in requested_at or requested_at.endswith("+00:00")


class TestAuditExportEdgeCases:
    """Tests for edge cases and corner cases."""

    @pytest.mark.asyncio
    async def test_unsafe_path_rejected_does_not_crash_audit(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unsafe path rejection doesn't break audit export."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-unsafe.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {
                "summary": "Dangerous operation",
                "changes": [
                    {
                        "action": "delete",
                        "path": "../../../etc/passwd",  # Unsafe path
                        "description": "Delete system file",
                    }
                ],
            }

            # This should be rejected by _resolve_path_safe
            result = await agent.run("delete system files")

        assert result["success"] is True  # Task completes, just rejects unsafe change
        assert export_path.exists()

        with open(export_path) as f:
            audit_data = json.load(f)

        # Should record the rejected change
        assert audit_data["summary"]["changes_rejected"] == 1

    @pytest.mark.asyncio
    async def test_empty_task_description_handled(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty task description doesn't break audit export."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-empty-task.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("")  # Empty task

        assert export_path.exists()
        with open(export_path) as f:
            audit_data = json.load(f)

        assert audit_data["task"]["task_description"] == ""

    @pytest.mark.asyncio
    async def test_audit_export_path_with_spaces(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Export path with spaces is handled correctly."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Create directory with spaces
        dir_with_spaces = temp_work_dir / "audit reports"
        dir_with_spaces.mkdir(exist_ok=True)
        export_path = dir_with_spaces / "audit report.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test")

        assert export_path.exists()
        with open(export_path) as f:
            audit_data = json.load(f)

        assert "task" in audit_data

    @pytest.mark.asyncio
    async def test_unicode_in_task_description_exported_correctly(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unicode characters in task description are preserved in export."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-unicode.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        unicode_task = "Fix bug with emojis 🐛 and unicode characters: 日本語, العربية"

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run(unicode_task)

        with open(export_path, encoding="utf-8") as f:
            audit_data = json.load(f)

        assert audit_data["task"]["task_description"] == unicode_task


class TestAuditExportJSONSchemaStrictness:
    """Tests that would catch bugs if implementation is wrong."""

    @pytest.mark.asyncio
    async def test_changes_is_list_not_dict(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Changes field must be a list, not a dict."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-schema.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        assert isinstance(audit_data["changes"], list)

    @pytest.mark.asyncio
    async def test_summary_values_are_correct_types(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Summary values must be correct types (int, str, float)."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-types.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        summary = audit_data["summary"]
        assert isinstance(summary["total_changes_planned"], int)
        assert isinstance(summary["changes_approved"], int)
        assert isinstance(summary["changes_rejected"], int)
        assert isinstance(summary["changes_executed"], int)
        assert isinstance(summary["policy_violations"], int)
        assert isinstance(summary["duration_seconds"], (int, float))
        assert summary["max_risk_level_seen"] is None or isinstance(
            summary["max_risk_level_seen"], str
        )

    @pytest.mark.asyncio
    async def test_compliance_flags_are_booleans(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Compliance flags must be boolean values, not strings."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-bool.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        flags = audit_data["compliance_flags"]
        assert isinstance(flags["compliance_mode_enabled"], bool)
        assert isinstance(flags["all_high_risk_approved"], bool)
        assert isinstance(flags["policy_file_present"], bool)
        assert isinstance(flags["audit_trail_complete"], bool)

    @pytest.mark.asyncio
    async def test_working_directory_is_absolute_path(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Working directory in audit must be absolute path."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-path.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        working_dir = audit_data["task"]["working_directory"]
        assert Path(working_dir).is_absolute()

    @pytest.mark.asyncio
    async def test_policy_violations_always_present_even_if_zero(
        self, temp_work_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Policy violations field must always be present, even if 0."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        export_path = temp_work_dir / "audit-policy.json"

        agent = SafeAgent(
            working_directory=str(temp_work_dir),
            non_interactive=True,
            audit_export_path=str(export_path),
        )

        with patch.object(agent, "_plan_changes", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = {"summary": "Nothing", "changes": []}
            await agent.run("test")

        with open(export_path) as f:
            audit_data = json.load(f)

        # Field must exist
        assert "policy_violations" in audit_data["summary"]
        # Should be 0 when no policy is present
        assert audit_data["summary"]["policy_violations"] == 0
