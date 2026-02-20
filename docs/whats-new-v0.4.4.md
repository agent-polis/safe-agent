# What's New in Safe Agent v0.4.4

Published: February 20, 2026

This release improves CI adoption by adding an API-keyless risk gate path.

## Highlights

- Added API-keyless diff analysis mode:
  - `safe-agent --diff-gate --non-interactive`
  - Optional base ref support with `--diff-ref` for PR-style comparisons.
- Added fork/no-secret CI fallback:
  - `.github/actions/safe-agent-review/action.yml` now uses task mode when `ANTHROPIC_API_KEY` is present.
  - Falls back to `--diff-gate` when the key is unavailable.
- Kept CI artifacts consistent across both modes:
  - `safe-agent-summary.md`
  - `safety-scorecard.md`
  - `policy-report.json`
  - `run-result.json`
  - `safe-agent.log`
- Hardened `--diff-ref` input validation for safer CLI operation.

## Notes

- Public release surface remains minimal: `safe-agent` and `safe-agent-mcp` only.
- Internal dev/marketing/demo tooling remains excluded from wheel/sdist artifacts.
