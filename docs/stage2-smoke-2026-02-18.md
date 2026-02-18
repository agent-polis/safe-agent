# Stage 2 Smoke Record

Date: 2026-02-18

Status: PASS

## Environment

- `safe-agent-cli==0.4.3`
- `impact-preview==0.2.2`
- Script uses a temporary isolated venv during execution.

## Observations

- Policy preset listing works (`safe-agent --list-policy-presets`).
- CI artifact flags are present in CLI help (`--ci-summary-file`, `--safety-scorecard-file`, `--policy-report`).
- PR risk gate + adversarial workflow files are present, plus the composite action.

## Archived Artifacts

- `artifacts/integration/stage2-smoke-*.log`
