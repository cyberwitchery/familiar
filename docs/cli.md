# cli reference

## familiar conjure

compose system instructions for an agent.

```
familiar conjure <agent> <profiles...> [--into <path>]
```

**arguments:**

| argument | description |
|----------|-------------|
| `agent` | target agent: `codex` or `claude` |
| `profiles` | one or more profile names |

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |

**behavior:**

- combines core profile with specified profiles
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
familiar invoke <agent> <invocation> [--into <path>] [--headless] [--profiles <profiles...>] [--kv <key=value>...] [args...]
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
| `--profiles` | override saved profiles |
| `--kv` | named arguments as `key=value` pairs |

**behavior:**

- loads profiles from `.familiar/<agent>.json` (or uses `--profiles`)
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

# override profiles
familiar invoke codex security-review --profiles sec
```
