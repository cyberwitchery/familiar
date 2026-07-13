# cli reference

## familiar conjure

compose system instructions for an agent.

```
familiar conjure <agent> <conjurings...> [--into <path>] [--dry-run]
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
| `--dry-run` | print what would be written (with its target path) and exit without touching the filesystem |
| `--save-subagent` | write composed conjurings as a reusable subagent |
| `--subagent-name` | override subagent name (default: joined conjuring names) |

**behavior:**

- combines core profile with specified conjurings
- writes `AGENTS.md` (codex) or `CLAUDE.md` (claude) to repo root
- with `--dry-run`, prints the instruction file's target path and rendered content, then exits without writing anything
- with `--save-subagent`, also writes a subagent file:
    - claude: `.claude/subagents/<name>/AGENT.md`
    - codex: `.codex/subagents/<name>/AGENT.md`

**examples:**

```bash
# rust project with security focus
familiar conjure codex rust sec

# python project, different directory
familiar conjure claude python --into /path/to/repo

# preview what would be written without touching the filesystem
familiar conjure claude python sec --dry-run

# export conjurings as subagents
familiar conjure claude python sec --save-subagent
familiar conjure codex rust infra --save-subagent --subagent-name ship_ops

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
| `--auto` | skip agent permission prompts (`--full-auto` for codex, `--dangerously-skip-permissions` for claude) |
| `--dry-run` | print rendered prompt and exit (does not run the agent) |
| `--worktree` | run in a separate git worktree to avoid interfering with local changes |
| `--save-skill` | write rendered invocation as a reusable skill and exit |
| `--skill-name` | override skill name (default: invocation name) |
| `--kv` | named arguments as `key=value` pairs |

**behavior:**

- renders invocation with provided arguments
- with `--save-skill`, writes a skill file and exits:
    - claude: `.claude/skills/<name>/SKILL.md`
    - codex: `.codex/skills/<name>/SKILL.md`
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

# preview rendered prompt without running the agent
familiar invoke codex bootstrap-python myapp cli --dry-run

# export invocation as a reusable skill
familiar invoke claude code-review --save-skill
familiar invoke codex refactor src/foo.py --save-skill --skill-name cleanup_refactor
```

## familiar list

list available conjurings, invocations, and snippets.

```
familiar list [kind] [--into <path>] [-v|--verbose]
```

**arguments:**

| argument | description |
|----------|-------------|
| `kind` | what to list: `conjurings`, `invocations`, or `snippets` (default: all) |

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

# list available snippets
familiar list snippets

# list in specific repo
familiar list --into /path/to/repo
```

## familiar lint

lint conjurings and invocations.

```
familiar lint [--into <path>] [--errors-only]
```

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |
| `--errors-only` | show only errors, not warnings |

**behavior:**

- checks conjurings for proper markdown structure
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
