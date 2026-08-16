# Changelog

## [0.2.1] - 2026-08-16

### Fixed

- Visual explanation SVG cleanup now requires a caller-provided `REMOVE_VISUALS_MAIN` token so cleanup pushes can authenticate as a ruleset bypass user instead of `github-actions[bot]`.

## [0.2.0] - 2026-07-29

### Added

- Added a reusable Python mutation testing workflow that reports and rejects surviving or inconclusive mutants.
- Added a reusable Python coverage workflow with a caller-defined minimum coverage threshold.

## [0.1.2] - 2026-07-10

### Added

- Added a reusable secret and sensitive data scanning workflow.

## [0.1.1] - 2026-06-29

### Fixed

- Added reusable workflow triggers to every shared workflow and run the changelog check through a repo-local reusable workflow caller.

## [0.1] - 2026-06-29

### Added

- Added a reusable workflow that deletes merged visual explanation SVG artifacts from `visual-explanations/`.
