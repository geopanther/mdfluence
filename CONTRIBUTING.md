# Contributing to mdfluence

mdfluence is a fork of [md2cf](https://github.com/iamjackg/md2cf) by Jack Gaino. Requires Python 3.12+.

## Setup

```bash
# Clone the repo
git clone https://github.com/geopanther/mdfluence.git
cd mdfluence

# Create a virtual environment
python3.12 -m venv .venv --prompt mdfluence
source .venv/bin/activate

# Install the package with dev and test dependencies
pip install -e ".[dev,test]"

# Set up pre-commit hooks
pre-commit install
```

## Testing

Tests run against Python 3.12 and 3.13 via [tox](https://tox.wiki/):

```bash
# Run tests against all configured Python versions (requires local Python 3.13 installation)
tox

# Run against a single version
tox -e py312

# Run pytest directly (current venv only)
pytest
```

Tests live in `test_package/`. The test suite uses pytest, pytest-mock, pyfakefs, and requests-mock.

## Linting

Linting runs automatically on `git push` via [pre-commit](https://pre-commit.com/) (configured with `pre-push` stage). To run manually:

```bash
pre-commit run --all-files
```

## Version bumping

Version management uses [bump2version](https://github.com/c4urself/bump2version). It updates `pyproject.toml`, `mdfluence/__init__.py`, and `CHANGELOG.md` in one step:

```bash
bumpversion patch   # 0.1.0 → 0.1.1
bumpversion minor   # 0.1.0 → 0.2.0
bumpversion major   # 0.1.0 → 1.0.0
```

After bumping, add a new `## Unreleased` section to `CHANGELOG.md`, then commit and tag:

```bash
git commit -am "chore: bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

Pushing a `v*` tag triggers the deploy workflow which builds and publishes to PyPI.

## Project structure

```
mdfluence/          # Package source
test_package/       # Tests (unit + functional)
pyproject.toml      # Build config, dependencies, tool settings
.bumpversion.cfg    # Version bump configuration
.github/workflows/  # CI (lint + test) and deploy (PyPI + GitHub Release)
```
