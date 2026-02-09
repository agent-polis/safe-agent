# Compatibility Matrix

This document tracks tested compatibility between:

- `safe-agent-cli` (this repository)
- `impact-preview` (`/Users/danielwaterfield/Documents/Leviathan`)

## Version Matrix

| safe-agent-cli | impact-preview | Status | Notes |
|---|---|---|---|
| 0.2.x | >=0.2.1 | Supported | Baseline support for preview + risk analysis APIs. |

## Stage Feature Gates

| Feature | safe-agent-cli min | impact-preview min | Status |
|---|---|---|---|
| Basic change preview and approval | 0.2.0 | 0.2.1 | Available |
| Policy-as-code decision enforcement | TBD | TBD | Planned (Stage 1) |
| Descriptor integrity checks | TBD | TBD | Planned (Stage 1) |
| Injection scanner risk factors | TBD | TBD | Planned (Stage 1) |

## Validation Checklist (Per Release)

1. Install clean env with target versions.
2. Run quickstart preview command.
3. Run non-interactive mode with fail-on-risk behavior.
4. Confirm expected risk levels and exit codes.
5. Record results in release notes.

## Known Caveats

- `safe-agent-cli` currently requires `ANTHROPIC_API_KEY` even in `--dry-run`, because planning still calls Anthropic.
- CI runs should use `--non-interactive` and `--fail-on-risk` for deterministic behavior.
