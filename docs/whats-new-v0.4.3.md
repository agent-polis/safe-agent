# What's New in Safe Agent v0.4.3

Published: February 18, 2026

This release focuses on Stage 3 trust signals: deterministic evaluation and better CI artifacts.

## Highlights

- Added a deterministic adversarial evaluation mode:
  - `safe-agent --adversarial-suite docs/adversarial-suite-v1.json`
  - Emits markdown + JSON reports and exits non-zero on failures.
- Added a new CI workflow:
  - `.github/workflows/adversarial-eval.yml`
  - Runs without an API key and uploads `.safe-agent-ci/adversarial.*` artifacts.
- Hardened the PR risk gate composite action:
  - Correct exit code propagation (`pipefail`) to avoid false-green gates.
  - Seeded fallback artifacts so failures still upload debuggable files.

## Notes

- Public release surface remains minimal: `safe-agent` and `safe-agent-mcp` only.
- Internal dev/marketing/demo tooling remains excluded from wheel/sdist artifacts.
