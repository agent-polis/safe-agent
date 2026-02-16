# What's New in Safe Agent v0.4.2

Published: February 16, 2026

This patch release hardens the public release surface.

## Highlights

- Public console scripts are now limited to:
  - `safe-agent`
  - `safe-agent-mcp`
- Internal development tooling (marketing/demo helpers) is no longer part of
  published wheel/sdist artifacts.
- Added release-surface tests to prevent accidental re-exposure in future
  releases.

## Why

Safe Agent should publish only user-facing runtime capabilities.
Internal growth/copy/demo tooling now stays internal by default.
