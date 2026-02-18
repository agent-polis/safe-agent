# Release Go/No-Go Checklist

Use this checklist before every Safe Agent release.

## Cross-Repo Compatibility

- [ ] `impact-preview` minimum version for target release is published.
- [ ] `safe-agent-cli` dependency constraint matches tested platform version.
- [ ] Compatibility matrix updated in `docs/compatibility-matrix.md`.

## Product Validation

- [ ] Test suite passes (`uv run pytest -q`).
- [ ] CLI help reflects shipped flags.
- [ ] Policy presets list loads successfully (`safe-agent --list-policy-presets`).
- [ ] Public release surface check passes (no internal tooling scripts exposed):
  - `python -m build && python scripts/check_release_surface.py dist`

## Stage 2 CI Adoption Gates

- [ ] PR risk gate workflow runs successfully:
  - `.github/workflows/safe-agent-pr-review.yml`
- [ ] Workflow artifacts are present:
  - `safe-agent-summary.md`
  - `safety-scorecard.md`
  - `policy-report.json`
  - `safe-agent.log`
- [ ] CI summary content includes rule IDs and recommended next actions.

## Publishing and Traceability

- [ ] Release workflow is green:
  - `.github/workflows/release.yml`
- [ ] Tag matches `pyproject.toml` version.
- [ ] GitHub release notes include compatibility + caveats.
- [ ] PyPI package version appears after publish.

## Decision

- GO if all checks are complete.
- NO-GO if any required check fails; create blocker issue with owner + ETA.
