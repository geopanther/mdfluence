# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
