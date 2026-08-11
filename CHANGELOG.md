# Changelog

All notable changes follow the principles of [Keep a Changelog](https://keepachangelog.com/).
This project uses semantic versioning.

## [Unreleased]

## [0.3.0] - 2026-08-11

### Added

- Explicit `individual` and `consensus` assessment records, plus an `agreement` command and
  report section that expose unresolved multi-reviewer decisions.
- Structured audit findings for filename/ID mismatches, workspace-wide duplicate IDs, malformed
  artifact files, and unresolved assessment conflicts.
- CodeQL analysis, immutable GitHub Action references, pinned direct build tools, and GitHub artifact
  attestations for wheel and source distributions.

### Changed

- Multiple individual assessments now require one explicit consensus covering every current
  individual assessment and binding each source card's canonical SHA-256. Scores, matrices,
  triage, and backlogs no longer average or silently select competing reviews; changed source
  cards make an earlier consensus stale.
- JSON reading and writing reject `NaN` and infinities; task effort rejects booleans and non-finite
  numbers.
- Release tags must point to a commit on `main` and pass the full Windows/Linux CI matrix before
  packaging. GitHub Release publication is independent of PyPI availability.
- Audit continues through malformed artifacts and returns all discovered file-scoped findings in
  one structured result.

### Compatibility

- Existing workspaces with zero or one assessment per paper remain valid when filenames match IDs,
  IDs are workspace-wide unique, and stored JSON meets the stricter finite/portable field contract.
- Existing workspaces with multiple assessments for one paper must label those records as
  `individual` and add one `consensus` record before derived ranking commands can run.
- Before upgrading, run `reproweave audit`. Rename cross-kind duplicate IDs and update their
  references; rename mismatched files; replace explicit `null` list fields with `[]` or remove
  them; and bound task estimates. Audit reports these repairs without mutating source files.

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

[Unreleased]: https://github.com/CAOShurong/reproweave/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/CAOShurong/reproweave/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/CAOShurong/reproweave/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/CAOShurong/reproweave/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/CAOShurong/reproweave/releases/tag/v0.1.0
