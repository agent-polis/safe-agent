# GitHub Action Guide

Safe Agent includes a PR risk gate workflow and a reusable local composite action.

## What ships

- Workflow: `.github/workflows/safe-agent-pr-review.yml`
- Workflow: `.github/workflows/adversarial-eval.yml`
- Composite action: `.github/actions/safe-agent-review/action.yml`

## Setup

1. Add repository secret `ANTHROPIC_API_KEY`.
2. Ensure `safe-agent-cli` is available in your repo (this action installs from source with `pip install .`).
3. Keep a policy file in-repo if you want custom rules (optional).

## Default behavior

- Triggered on `pull_request` and `workflow_dispatch`.
- Runs `safe-agent` in non-interactive mode.
- Defaults to `--dry-run` with no fail threshold (advisory mode).
- Set `fail_on_risk` on manual runs when you want strict blocking behavior.
- Uploads five artifacts:
  - `safe-agent-summary.md`
  - `safety-scorecard.md`
  - `policy-report.json`
  - `run-result.json`
  - `safe-agent.log`
- Propagates `safe-agent` exit status correctly (`pipefail`) so CI gates fail when they should.
- Seeds fallback summary/scorecard/report files, so failed runs still upload debuggable artifacts.

Fork PRs are skipped because GitHub does not expose secrets to untrusted forks.

## Adversarial fixture workflow

- `adversarial-eval.yml` runs a deterministic fixture suite from `docs/adversarial-suite-v1.json`.
- No model API key is required; it validates governance decisions against expected outcomes.
- Uploads:
  - `.safe-agent-ci/adversarial.md`
  - `.safe-agent-ci/adversarial.json`

## Manual run

Use the workflow dispatch inputs to override:

- `task`
- `fail_on_risk`
- `dry_run`
- `policy_file`
- `policy_preset`

## Policy report format (high level)

`policy-report.json` includes:

- pass/fail status
- max risk observed
- blocking policy rule IDs
- per-change event outcomes
- recommended next actions
