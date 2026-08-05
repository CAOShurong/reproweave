# Changelog

All notable changes follow the principles of [Keep a Changelog](https://keepachangelog.com/).
This project uses semantic versioning.

## [Unreleased]

## [0.2.1] - 2026-08-05

### Added

- PyPI Trusted Publishing with short-lived GitHub OIDC credentials and publish attestations.
- PyPI-safe README graphics and links, a large social preview, and direct pip/pipx entry points.
- A community discussion route for real replication-planning workflows.

### Changed

- Split package construction, PyPI publication, and GitHub Release publication into separate
  least-privilege jobs that share one verified distribution artifact.
- Extended repository checks to cover all three figures and the social preview.

## [0.2.0] - 2026-08-05

### Added

- Rule-based replication candidate triage that combines evidence gaps, required resources,
  task dependencies, remaining effort, and an explicit next action.
- Non-mutating resource availability scenarios through repeatable
  `--resource RESOURCE=AVAILABILITY` overrides.
- JSON, CSV, and meeting-ready Markdown triage exports.
- A release workflow that builds, checks, smoke-tests, checksums, and publishes distributions.

### Changed

- Reworked the README, website, graphical abstract, workflow figure, and portable report around a
  restrained academic visual system with square panels, thin rules, and print-safe colors.
- Updated CI and Pages actions to their current major versions.
- Replaced the unsupported PyPI install claim with a versioned public GitHub Release wheel.
- Expanded the deterministic demonstration and report with a candidate decision table.

## [0.1.0] - 2026-08-04

### Added

- Local-first workspaces with seven validated artifact types.
- Offline BibTeX and CSL JSON bibliography import.
- An evidence-anchored, eight-dimension reconstructability rubric.
- Typed evidence graphs, gap backlogs, and dependency-aware replication waves.
- Cross-reference and task-cycle audits.
- SHA-256 evidence seals with later verification.
- Self-contained interactive HTML reports and portable CSV, Markdown, and JSON exports.
- A deterministic, fully synthetic EE/AI demonstration with 55 artifacts.
- Seventy-five standard-library tests, cross-platform CI, package smoke tests, and Pages.

[Unreleased]: https://github.com/CAOShurong/reproweave/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/CAOShurong/reproweave/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/CAOShurong/reproweave/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/CAOShurong/reproweave/releases/tag/v0.1.0
