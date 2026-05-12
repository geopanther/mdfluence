# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [0.4.0] - 2026-05-12

### Added

- GFM alert/admonition support (`> [!NOTE]`, `> [!TIP]`, `> [!WARNING]`, `> [!CAUTION]`, `> [!IMPORTANT]`) mapped to Confluence structured macros
- Emoji shortcode support (`:smile:` → 😄) with 1913 GitHub-compatible mappings, enabled by default (`--disable-emoji` to turn off)
- Local diagram rendering for mermaid and PlantUML code blocks via `--render-diagrams` flag (requires `mmdc` and/or `plantuml` on PATH)
- `--mmdc-path` and `--plantuml-path` CLI flags for custom tool locations

### Changed

- Refactored anchor handling from post-processing HTML rewriting to pre-scan approach for better reliability

## [0.3.0] - 2026-05-08

### Added

- Enable mistune 3.x plugins with Confluence rendering
- Use native Confluence task list macros
- Add plugin feature tests and markdown showcase

### Changed

- Migrate to mistune 3.x API
- Replace setuptools with hatchling, adopt uv dependency-groups
- Migrate to bump-my-version with release helper scripts
- Rewrite workflows with uv, bump all action versions
- Add CodeQL analysis and Dependabot config
- Add pre-commit config with ruff, ty, bandit, osv-scanner
- Add uv.lock for reproducible installs
- Update mistune dependency to >=3.2.1

### Fixed

- Resolve all ty type-checker errors
- Exclude test fixtures from prettier, revert test.md
- Review feedback — consistent uv version, SHA-pin codeql, --no-edit
- Apply ruff format, prettier, fix bandit SHA1 warnings

### Documentation

- Document supported mistune plugins
- Note Confluence limitations for abbr, mark, spoiler
- Rewrite releasing guide for bump-my-version + helper scripts
- Require CI and publish checks before proceeding in release process

## 0.2.1 - 2026-04-16

### Security

- Switched deploy workflow to PyPI Trusted Publishers (OIDC) — eliminates long-lived API tokens
- Enabled digital attestations for published packages (provenance verification)
- Separated build and publish into isolated jobs to prevent credential leakage
- Pinned all GitHub Actions to full commit SHAs to prevent tag-hijacking attacks
- Added `pypi-publish-test` environment for TestPyPI deployments (with approval gate)
- Added `pypi-publish-prod` environment for PyPI deployments (with approval gate)
- Restricted workflow permissions to least privilege (`contents: read` default)

### Changed

- Renamed deploy workflow from `deploy.yml` to `deploy-test.yml`
- Separated build, release, and publish into isolated workflow jobs
- Replaced deprecated `actions/create-release` with `softprops/action-gh-release`
- Added `deploy-prod.yml` for production PyPI publishing with GitHub Release creation

### Added

- Added `docs/releasing.md` documenting the release process

## 0.2.0 - 2026-04-14

### Changed

- Migrated from `setup.py` to `pyproject.toml`
- Loosened dependency version pins to compatible ranges
- Bumped minimum Python version to 3.12
- Updated CI to test Python 3.12 and 3.13
- Updated deploy workflow to use `python -m build`

## 0.1.0 - 2026-04-14

### Added

- `--convert-anchors` flag to rewrite markdown anchors to Confluence format
- `--skip-subtrees-wo-markdown` option to skip directory subtrees without markdown files

### Changed

- Forked from [md2cf 2.3.0](https://github.com/iamjackg/md2cf) by Jack Gaino
- Renamed package from `md2cf` to `mdfluence`
