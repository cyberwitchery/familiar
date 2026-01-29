task: bootstrap a new python project with modern tooling.

## inputs

- $1 `package_name` (required): name of the package (e.g., `myapp`)
- $2 `package_type` (required): `cli` or `lib`
- $3 `python_version` (optional): minimum python version (default: `3.13`)
- $4 `license` (optional): license identifier (e.g., `MIT`, `Apache-2.0`)

## preconditions

STOP and ask if:
- package_name is missing or invalid (not a valid python identifier)
- package_type is not `cli` or `lib`
- the target directory already exists (ask: abort, overwrite, or integrate?)

## what gets created

```
<package_name>/
├── pyproject.toml       # modern python packaging with ruff, mypy, pytest
├── README.md            # one-line description + quickstart
├── src/
│   └── <package_name>/
│       ├── __init__.py  # version and public API
│       ├── main.py      # (cli) entry point with argument parsing
│       └── core.py      # (lib) core module placeholder
└── tests/
    ├── __init__.py
    └── test_<package_name>.py  # minimal test
```

## steps

1. **validate**: confirm inputs are valid and directory doesn't conflict.
2. **create**: set up directory structure with src layout.
3. **configure**: create pyproject.toml with metadata and tool configs.
4. **readme**: create README.md with purpose and quickstart.
5. **code**: add minimal implementation with type hints.
6. **test**: add a minimal passing test.
7. **verify**: run format, lint, type check, and tests.

## pyproject.toml structure

```toml
{{> snippet:python/pyproject.toml}}
```

## acceptance criteria

all must pass:
```
ruff format --check .
ruff check .
mypy .
pytest -q
```

## output

```
## project created
<package_name> (<package_type>)

## files
<list of files created with brief description>

## changes
<diff of all created files>

## setup
pip install -e ".[dev]"

## verification
ruff format --check . && ruff check . && mypy . && pytest -q

## next steps
<suggested next actions: add dependencies, implement features, publish, etc.>
```
