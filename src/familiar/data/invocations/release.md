task: prepare a release with version bump, changelog, and publish commands.

## inputs

- $1 `version` (required): version (`1.2.0`), bump type (`major`, `minor`, `patch`), or pre-release (`1.2.0-rc.1`)
- $2 `description` (optional): release summary for changelog

## preconditions

STOP and ask if:
- uncommitted changes exist
- tests are failing
- version/tag already exists

## steps

1. **validate**: clean state, tests pass, version doesn't exist
2. **detect**: find version files and current version
3. **bump**: update version in all relevant files
4. **changelog**: update CHANGELOG.md (create if missing)
5. **verify**: run tests
6. **output**: provide commit, tag, and publish commands

## files to update

- python: `pyproject.toml`, `__init__.py`
- rust: `Cargo.toml`
- node: `package.json`
- other: `VERSION` file

## changelog format

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
### Changed
### Fixed
### Removed
```

## output

```
## release prepared
version: <old> → <new>

## files updated
- <file>: <change>

## changelog entry
<added section>

## commands

### commit and tag
git add -A && git commit -m "release: v<version>"
git tag -a v<version> -m "Release v<version>"
git push origin main --tags

### publish
# python: python -m build && twine upload dist/*
# rust: cargo publish
# node: npm publish

### github release (optional)
gh release create v<version> --notes "<summary>"
```
