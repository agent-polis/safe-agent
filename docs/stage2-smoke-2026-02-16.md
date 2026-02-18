# Stage 2 Smoke Run (2026-02-16)

Command:

```bash
./scripts/run_stage2_smoke.sh
```

Status: PASS

## Environment

- `safe-agent-cli==0.4.2`
- `impact-preview==0.2.2`
- Script uses a temporary isolated venv during execution.

## Validated

- Policy preset listing works (`safe-agent --list-policy-presets`).
- CI artifact flags are present in CLI help (`--ci-summary-file`, `--safety-scorecard-file`, `--policy-report`).
- PR risk gate workflow + composite action files are present.

## Archived Artifacts

- `artifacts/integration/stage2-smoke-*.log`
