# Monday Assignment Packet

Date: 2026-02-09

This packet assigns Stage 1 work to two autonomous engineering agents.

## Repositories

- Product repo: `agent-polis/safe-agent`
- Platform repo: `agent-polis/impact-preview`

## Issue Backlog

### Agent-Platform (`impact-preview`)

1. AP-101 Policy schema and parser
- https://github.com/agent-polis/impact-preview/issues/1

2. AP-102 Policy evaluator with deterministic precedence
- https://github.com/agent-polis/impact-preview/issues/2

3. AP-103 MCP descriptor integrity checks (hash pinning)
- https://github.com/agent-polis/impact-preview/issues/3

4. AP-104 Prompt-injection and risky-instruction scanner
- https://github.com/agent-polis/impact-preview/issues/4

5. AP-105 Extend audit records with policy/scanner context
- https://github.com/agent-polis/impact-preview/issues/5

6. AP-106 Stage 1 platform test suite
- https://github.com/agent-polis/impact-preview/issues/6

### Agent-Product (`safe-agent`)

1. AS-101 Enforce policy decision before execution
- https://github.com/agent-polis/safe-agent/issues/1

2. AS-102 Render policy/scanner reasons in CLI preview
- https://github.com/agent-polis/safe-agent/issues/2

3. AS-103 Align non-interactive and fail-on-risk behavior
- https://github.com/agent-polis/safe-agent/issues/3

4. AS-104 Add impact-preview compatibility guard
- https://github.com/agent-polis/safe-agent/issues/4

5. AS-105 Stage 1 product test coverage
- https://github.com/agent-polis/safe-agent/issues/5

6. AS-106 Docs and migration notes for Stage 1
- https://github.com/agent-polis/safe-agent/issues/6

### Integration

1. INT-101 Cross-repo smoke test
- https://github.com/agent-polis/safe-agent/issues/7

2. INT-102 Keep compatibility matrix release-accurate
- https://github.com/agent-polis/safe-agent/issues/8

3. INT-103 Release go/no-go checklist enforcement
- https://github.com/agent-polis/safe-agent/issues/9

## Prompts To Run

### Prompt for Agent-Platform

```text
You are Agent-Platform.
Work only in /Users/danielwaterfield/Documents/Leviathan and target repo agent-polis/impact-preview.
Execute AP-101 through AP-106 in order.
For each issue:
- Implement minimal coherent change.
- Add/adjust tests.
- Open or update PR with issue reference.
- Post a completion comment with: changed files, tests run, acceptance status, risks.
Constraints:
- Do not change safe-agent repo.
- Keep API changes explicit and documented.
```

### Prompt for Agent-Product

```text
You are Agent-Product.
Work only in /Users/danielwaterfield/Documents/safe-agent and target repo agent-polis/safe-agent.
Execute AS-101 through AS-106 in order.
For each issue:
- Implement behavior and tests.
- Keep CLI output concise and actionable.
- Open or update PR with issue reference.
- Post a completion comment with: changed files, tests run, acceptance status, risks.
Constraints:
- Respect compatibility constraints from docs/compatibility-matrix.md.
- Do not implement platform-only internals locally.
```

### Prompt for Release-Integrator

```text
You are Release-Integrator.
Run after both agents report completion.
Execute INT-101, INT-102, INT-103:
- Validate safe-agent against latest compatible impact-preview.
- Update compatibility matrix with tested versions and caveats.
- Run go/no-go checklist and publish decision.
Output:
- GO or NO-GO.
- Blocking issues with owner and issue ID.
- Required follow-up tasks.
```

## Monday Runbook

1. 09:00 Assign AP and AS issue sets to each agent.
2. 12:00 Midday checkpoint: confirm AP-102 and AS-101 status.
3. 15:00 Integration dry run for INT-101 if both sides are near complete.
4. 17:00 Final status rollup and next-day carryover list.

## Completion Definition

- All AP and AS issues are either complete or explicitly deferred with rationale.
- INT-101 smoke run completed with archived output.
- Compatibility matrix updated if behavior changed.
- No unresolved blocker without assigned owner and ETA.
