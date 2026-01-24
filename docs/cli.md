# cli reference

## familiar conjure

compose system instructions for an agent.

```
familiar conjure <agent> <conjurings...> [--into <path>]
```

**arguments:**

| argument | description |
|----------|-------------|
| `agent` | target agent: `codex` or `claude` |
| `conjurings` | one or more profile names |

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |

**behavior:**

- combines core profile with specified conjurings
- writes `AGENTS.md` (codex) or `CLAUDE.md` (claude) to repo root

**examples:**

```bash
# rust project with security focus
familiar conjure codex rust sec

# python project, different directory
familiar conjure claude python --into /path/to/repo
```

## familiar invoke

run a task prompt through the agent.

```
familiar invoke <agent> <invocation> [--into <path>] [--headless] [--kv <key=value>...] [args...]
```

**arguments:**

| argument | description |
|----------|-------------|
| `agent` | target agent: `codex` or `claude` |
| `invocation` | invocation name |
| `args` | positional arguments for the invocation |

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |
| `--headless` | run without interactive ui |
| `--worktree` | run in a separate git worktree to avoid interfering with local changes |
| `--kv` | named arguments as `key=value` pairs |

**behavior:**

- renders invocation with provided arguments
- if `--worktree` is specified:
    - creates a temporary git worktree from `HEAD`
    - copies the agent instruction file (`CLAUDE.md` or `AGENTS.md`) to the worktree
    - runs the agent in the worktree directory
- runs the agent with the prompt

**examples:**

```bash
# interactive mode
familiar invoke codex bootstrap-rust myapp bin

# headless mode
familiar invoke codex add-tests "parse_config" --headless

# with named arguments
familiar invoke codex implement-feature --kv spec="add caching"
```

## familiar list

list available conjurings and invocations.

```
familiar list [kind] [--into <path>] [-v|--verbose]
```

**arguments:**

| argument | description |
|----------|-------------|
| `kind` | what to list: `conjurings` or `invocations` (default: both) |

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |
| `-v`, `--verbose` | show first line of each file |

**behavior:**

- lists built-in and local items
- local overrides are marked with `(local)`
- items are sorted alphabetically

**examples:**

```bash
# list everything
familiar list

# list only conjurings
familiar list conjurings

# list invocations with descriptions
familiar list invocations -v

# list in specific repo
familiar list --into /path/to/repo
```

## familiar lint

lint templates and invocations.

```
familiar lint [--into <path>] [--errors-only]
```

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |
| `--errors-only` | show only errors, not warnings |

**behavior:**

- checks templates for proper markdown structure
- checks invocations for recommended sections and placeholder documentation
- errors cause non-zero exit code; warnings do not

see [linting](linting.md) for detailed rules.

**examples:**

```bash
# lint everything
familiar lint

# lint with only errors (no warnings)
familiar lint --errors-only

# lint specific repo
familiar lint --into /path/to/repo
```
