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
- saves profile selection to `.familiar/<agent>.json`

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
familiar invoke <agent> <invocation> [--into <path>] [--headless] [--conjurings <conjurings...>] [--kv <key=value>...] [args...]
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
| `--conjurings` | override saved conjurings |
| `--kv` | named arguments as `key=value` pairs |

**behavior:**

- loads conjurings from `.familiar/<agent>.json` (or uses `--conjurings`)
- renders invocation with provided arguments
- runs the agent with the composed prompt

**examples:**

```bash
# interactive mode
familiar invoke codex bootstrap-rust myapp bin

# headless mode
familiar invoke codex add-tests "parse_config" --headless

# with named arguments
familiar invoke codex implement-feature --kv spec="add caching"

# override conjurings
familiar invoke codex security-review --conjurings sec
```

## familiar list

list available conjurings or invocations.

```
familiar list <kind> [--into <path>] [-v|--verbose]
```

**arguments:**

| argument | description |
|----------|-------------|
| `kind` | what to list: `conjurings` or `invocations` |

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
# list all conjurings
familiar list conjurings

# list invocations with descriptions
familiar list invocations -v

# list conjurings in specific repo
familiar list conjurings --into /path/to/repo
```
