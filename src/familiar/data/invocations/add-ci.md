task: add continuous integration workflow for linting, testing, and static analysis.

## inputs

- $1 `platform` (required): CI platform (`github` or `gitlab`)
- $2 `language` (required): primary language (`python`, `rust`, `node`)

## preconditions

STOP and ask if:
- platform is not `github` or `gitlab`
- language is not `python`, `rust`, or `node`
- CI configuration already exists (ask: replace, merge, or abort?)
- the project structure doesn't match expectations (no pyproject.toml, Cargo.toml, or package.json)

## what gets created

### github actions
```
.github/
└── workflows/
    └── ci.yml
```

### gitlab ci
```
.gitlab-ci.yml
```

## steps

1. **detect**: check for existing CI and project structure
2. **create**: write workflow file for the language
3. **verify**: validate workflow syntax if possible

---

## python workflows

### github actions (python)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Lint
        run: |
          uv run ruff format --check .
          uv run ruff check .

      - name: Type check
        run: uv run mypy .

      - name: Test
        run: uv run pytest --cov
```

### gitlab ci (python)

```yaml
stages:
  - check
  - test

variables:
  UV_CACHE_DIR: .uv-cache

cache:
  paths:
    - .uv-cache/

.python:
  image: python:3.13
  before_script:
    - pip install uv
    - uv sync --all-extras --dev

lint:
  extends: .python
  stage: check
  script:
    - uv run ruff format --check .
    - uv run ruff check .

typecheck:
  extends: .python
  stage: check
  script:
    - uv run mypy .

test:
  extends: .python
  stage: test
  script:
    - uv run pytest --cov
  coverage: '/TOTAL.*\s+(\d+%)/'
```

---

## rust workflows

### github actions (rust)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  CARGO_TERM_COLOR: always

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy

      - name: Cache cargo
        uses: Swatinem/rust-cache@v2

      - name: Format
        run: cargo fmt --check

      - name: Clippy
        run: cargo clippy --all-targets --all-features -- -D warnings

      - name: Test
        run: cargo test --all-features
```

### gitlab ci (rust)

```yaml
stages:
  - check
  - test

variables:
  CARGO_HOME: ${CI_PROJECT_DIR}/.cargo

cache:
  paths:
    - .cargo/
    - target/

.rust:
  image: rust:1.84
  before_script:
    - rustup component add rustfmt clippy

format:
  extends: .rust
  stage: check
  script:
    - cargo fmt --check

clippy:
  extends: .rust
  stage: check
  script:
    - cargo clippy --all-targets --all-features -- -D warnings

test:
  extends: .rust
  stage: test
  script:
    - cargo test --all-features
```

---

## node workflows

### github actions (node)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run typecheck

      - name: Test
        run: npm test
```

### gitlab ci (node)

```yaml
stages:
  - check
  - test

cache:
  paths:
    - node_modules/

.node:
  image: node:20
  before_script:
    - npm ci

lint:
  extends: .node
  stage: check
  script:
    - npm run lint

typecheck:
  extends: .node
  stage: check
  script:
    - npm run typecheck

test:
  extends: .node
  stage: test
  script:
    - npm test
```

---

## output

```
## CI configured
platform: <github|gitlab>
language: <python|rust|node>

## file created
<path to workflow file>

## workflow contents
<the complete workflow file>

## next steps
- push to trigger the workflow
- verify scripts exist in package.json / pyproject.toml if needed
- add secrets if using protected actions
```
