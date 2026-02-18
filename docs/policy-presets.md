# Policy Presets

Safe Agent ships with three policy presets from `impact-preview`.

List available presets:

```bash
safe-agent --list-policy-presets
```

## Preset Selection

| Preset | Use when | Behavior |
|---|---|---|
| `startup` | You want guardrails with minimum friction | Balanced defaults for fast teams |
| `fintech` | You are in regulated/security-heavy environments | Stricter decisions for secrets and production-like risk |
| `games` | You iterate quickly on assets/content | More iteration-friendly defaults |

## CI Commands

Startup:

```bash
safe-agent "scan repo for risky config edits" \
  --dry-run \
  --non-interactive \
  --policy-preset startup \
  --ci-summary-file .safe-agent-ci/startup-summary.md \
  --safety-scorecard-file .safe-agent-ci/startup-safety-scorecard.md \
  --policy-report .safe-agent-ci/startup-policy-report.json
```

Fintech:

```bash
safe-agent "scan repo for risky config edits" \
  --dry-run \
  --non-interactive \
  --policy-preset fintech \
  --fail-on-risk high \
  --ci-summary-file .safe-agent-ci/fintech-summary.md \
  --safety-scorecard-file .safe-agent-ci/fintech-safety-scorecard.md \
  --policy-report .safe-agent-ci/fintech-policy-report.json
```

Games:

```bash
safe-agent "scan repo for risky config edits" \
  --dry-run \
  --non-interactive \
  --policy-preset games \
  --ci-summary-file .safe-agent-ci/games-summary.md \
  --safety-scorecard-file .safe-agent-ci/games-safety-scorecard.md \
  --policy-report .safe-agent-ci/games-policy-report.json
```

## Common Pattern

Use `startup` first, then tighten to `fintech` if review burden is acceptable.
Use `games` when iteration speed matters more than strict CI blocking.
