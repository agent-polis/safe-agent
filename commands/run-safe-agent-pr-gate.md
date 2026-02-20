---
description: Run the Safe Agent PR risk gate and emit review artifacts.
---

Run:

```bash
safe-agent "scan repository for risky configuration and secret-handling changes; do not edit files" \
  --dry-run \
  --non-interactive \
  --policy-preset startup \
  --ci-summary-file .safe-agent-ci/summary.md \
  --safety-scorecard-file .safe-agent-ci/safety-scorecard.md \
  --policy-report .safe-agent-ci/policy-report.json \
  --json-out .safe-agent-ci/run-result.json
```

Then summarize:

- Result from `.safe-agent-ci/run-result.json`
- Max risk and blockers from `.safe-agent-ci/policy-report.json`
- Suggested next actions from scorecard/summary artifacts
