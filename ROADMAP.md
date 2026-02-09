# Safe Agent Roadmap (Agent-Driven)

This roadmap assumes two autonomous engineering agents operating in parallel:

- Agent-Platform: works in `/Users/danielwaterfield/Documents/Leviathan` (`impact-preview`).
- Agent-Product: works in `/Users/danielwaterfield/Documents/safe-agent` (`safe-agent-cli`).

## Ownership Model

- `impact-preview` owns risk policy, scanning, enforcement primitives, and audit interfaces.
- `safe-agent-cli` owns task UX, approval UX, CI packaging, and adoption tooling.
- No release is complete unless cross-repo compatibility checks pass.

## Stages

## Stage 0 (Week 0-1): Boundaries and Release Hygiene

Goals:
- Lock naming and project boundaries in docs.
- Standardize release checklist for both repos.
- Add a compatibility matrix and keep it current.

Exit criteria:
- Install and quickstart work from clean environment.
- Published compatibility matrix exists and is linked in README.
- Release checklist committed in both repos.

## Stage 1 (Weeks 1-4): Safety Hardening

Goals:
- Policy-as-code enforcement before execution.
- Descriptor integrity checks for MCP-facing tooling.
- Prompt-injection/risky-instruction scanning with explicit risk reasons.

Exit criteria:
- High-risk actions are blocked by deterministic policy.
- CLI preview shows policy decision and reason.
- Test coverage includes bypass attempts and regression fixtures.

## Stage 2 (Weeks 4-8): Distribution and CI Adoption

Goals:
- Strong PR-gate workflow via GitHub Actions.
- Policy presets for common environments.
- Weekly growth summary from analytics logs.

Exit criteria:
- One-click CI onboarding docs and working action.
- At least three policy presets available.
- Weekly summary generated automatically.

## Stage 3 (Weeks 8-12): Evaluation and Trust Signals

Goals:
- Adversarial evaluation harness.
- Published safety scorecard per release.
- Approval/audit export for external review.

Exit criteria:
- CI runs adversarial suite.
- Scorecard published with release notes.
- Audit export validated end-to-end.

## Stage 4 (Weeks 12+): Team Controls

Goals:
- Multi-reviewer approval and override policy.
- Central policy gateway mode.
- Alerting hooks for critical-risk actions.

Exit criteria:
- Role-based approvals work in at least one integration.
- Policy gateway controls tool allowlist centrally.
- Critical events trigger alert hooks.

## Stage 1 Ticket Backlog (Execution Ready)

## Agent-Platform Tickets (`impact-preview`)

1. AP-101 Policy schema and parser
- Implement versioned policy schema (`version`, `rules`, `defaults`, `metadata`).
- Add strict validation and readable errors.
- Acceptance: invalid policies fail fast with actionable diagnostics.

2. AP-102 Policy evaluator
- Evaluate `allow`, `deny`, `require_approval` by action type, path, and risk level.
- Add deterministic precedence rules and trace output.
- Acceptance: evaluator returns decision + matched rule ID.

3. AP-103 Descriptor integrity checks
- Add descriptor hash pinning and allowlist lookup for MCP tool descriptors.
- Acceptance: descriptor mismatch fails closed and emits explicit reason.

4. AP-104 Prompt-injection scanner
- Add scanner for suspicious instruction patterns in task/tool metadata.
- Emit risk factors compatible with existing preview surfaces.
- Acceptance: fixture set catches known malicious phrases with low false positives.

5. AP-105 Audit record extensions
- Record policy decision, rule ID, and scanner findings in audit output.
- Acceptance: audit event includes enough context for external review.

6. AP-106 Platform test suite
- Add tests for allow/deny/approval, descriptor mismatch, injection detection.
- Acceptance: CI includes new suite and passes on baseline fixtures.

## Agent-Product Tickets (`safe-agent-cli`)

1. AS-101 Policy decision enforcement
- Integrate policy decision before execution path.
- Block changes when platform decision is deny.
- Acceptance: denied actions never reach `_execute_change`.

2. AS-102 Preview reason rendering
- Show decision, matched rule ID, and scanner findings in CLI preview panel.
- Acceptance: operator sees clear reason without verbose logs.

3. AS-103 Non-interactive behavior alignment
- Ensure `--non-interactive` respects platform policy and `--fail-on-risk` behavior.
- Acceptance: high-risk deny path exits non-zero in CI mode.

4. AS-104 Compatibility guard
- Add startup check for minimum `impact-preview` version needed by Stage 1 features.
- Acceptance: clear error if dependency too old.

5. AS-105 Product tests
- Add tests for deny/allow/require-approval in interactive and non-interactive modes.
- Acceptance: tests cover success and failure exit codes.

6. AS-106 Docs and migration notes
- Update README usage and release notes for policy/scanner behavior.
- Acceptance: docs include one practical CI example.

## Integration Gate Tickets

1. INT-101 Cross-repo smoke test
- Run `safe-agent-cli` against latest `impact-preview` in clean env.
- Acceptance: smoke script exits zero and archives log.

2. INT-102 Compatibility matrix update
- Update `/Users/danielwaterfield/Documents/safe-agent/docs/compatibility-matrix.md` per release.
- Acceptance: matrix reflects tested versions and known caveats.

3. INT-103 Release checklist
- Confirm: tests green, docs updated, tags pushed, PyPI package verified.
- Acceptance: no-go if any checklist item missing.

## Agent Prompts (Operational)

### Prompt: Agent-Platform

You are Agent-Platform. Work only in `/Users/danielwaterfield/Documents/Leviathan`.
Implement AP-101 through AP-106.
For each ticket, return: changed files, tests executed, acceptance status, and risks.
Do not modify `safe-agent-cli`.

### Prompt: Agent-Product

You are Agent-Product. Work only in `/Users/danielwaterfield/Documents/safe-agent`.
Implement AS-101 through AS-106.
For each ticket, return: changed files, tests executed, acceptance status, and risks.
Assume latest compatible `impact-preview` unless blocked by matrix constraints.

### Prompt: Release-Integrator

You are Release-Integrator.
Take outputs from Agent-Platform and Agent-Product and run INT-101 through INT-103.
Return GO/NO-GO, blockers, and exact follow-up tickets.

## Weekly Cadence

- Monday: ticket planning and assignment.
- Wednesday: integration smoke check.
- Friday: release candidate cut and publish.

## KPI Targets

- Stage 1: critical-risk block rate and policy explainability coverage.
- Stage 2: PR-gate adoption count and time-to-first-value.
- Stage 3: false-positive rate and approval latency.
- Stage 4: policy coverage and audit completeness.
