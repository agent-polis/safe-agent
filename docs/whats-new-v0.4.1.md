# What's New in Safe Agent v0.4.1

Published: February 16, 2026

Safe Agent v0.4.1 is a release focused on adoption in real CI workflows.

## Highlights

- PR risk gate workflow for pull requests:
  - `.github/workflows/safe-agent-pr-review.yml`
- CI-friendly artifacts from `safe-agent` runs:
  - markdown summary (`--ci-summary-file`)
  - machine-readable policy report (`--policy-report`)
- Weekly growth summary command:
  - `safe-agent-marketing weekly-summary`
- Improved policy preset experience:
  - clearer docs and preset quickstarts
  - better invalid-preset guidance in CLI output

## Why this release matters

v0.4.0 made policy and scanner enforcement practical.
v0.4.1 makes those controls easier to operationalize in team workflows.

## Quick start

```bash
pip install -U safe-agent-cli
safe-agent "scan repository for risky configuration changes" \
  --dry-run \
  --non-interactive \
  --ci-summary-file .safe-agent-ci/summary.md \
  --policy-report .safe-agent-ci/policy-report.json
```

## Short launch copy

### X / Twitter

Safe Agent v0.4.1 is out: PR risk gate workflow, CI summary + policy-report artifacts, and weekly growth summaries. If you want AI coding guardrails that fit CI without friction, this is the release.  
https://github.com/agent-polis/safe-agent

### LinkedIn

We just shipped Safe Agent v0.4.1.

This release is about making safety controls easier to adopt in real engineering workflows:
- PR risk gate workflow
- CI markdown + JSON artifacts for reviews
- weekly growth summary command

If you're running AI coding agents in CI, this should reduce setup friction while keeping guardrails visible.

Repo: https://github.com/agent-polis/safe-agent

### Show HN title + body

Title: Show HN: Safe Agent v0.4.1 — PR risk gate + CI policy artifacts for AI coding workflows

Body:
- v0.4.1 adds a production PR risk gate workflow and CI artifacts (markdown summary + machine-readable policy report)
- keeps policy/scanner decisions explicit in non-interactive mode
- adds a weekly summary command for experiment tracking

Would love feedback from teams running coding agents in CI.
