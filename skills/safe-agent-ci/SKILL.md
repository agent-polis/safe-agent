---
name: safe-agent-ci
description: Run Safe Agent in CI-friendly mode and return actionable artifact paths.
---

# Safe Agent CI Operator

Use this skill when a task needs deterministic risk gating output for PRs or automation.

## Workflow

1. Run Safe Agent in non-interactive dry-run mode.
2. Emit summary, scorecard, policy report, and machine run result artifacts.
3. Report:
   - max risk seen
   - blocking policy rules (if any)
   - recommended next actions
   - exact artifact paths

## Standard command

```bash
safe-agent "scan repository for risky configuration and secret-handling changes; do not edit files" \
  --dry-run \
  --non-interactive \
  --ci-summary-file .safe-agent-ci/summary.md \
  --safety-scorecard-file .safe-agent-ci/safety-scorecard.md \
  --policy-report .safe-agent-ci/policy-report.json \
  --json-out .safe-agent-ci/run-result.json
```
