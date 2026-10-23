# cli reference

## familiar conjure

compose system instructions for an agent.

```
familiar conjure <agent> <conjurings...> [--into <path>]
```

**arguments:**

| argument | description |
|----------|-------------|
| `agent` | target agent: `codex`, `claude`, or any plugin-provided agent |
| `conjurings` | one or more profile names |

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |
| `--save-subagent` | write composed conjurings as a reusable subagent |
| `--subagent-name` | override subagent name (default: joined conjuring names) |

**behavior:**

- combines core profile with specified conjurings
- writes `AGENTS.md` (codex) or `CLAUDE.md` (claude) to repo root
- with `--save-subagent`, also writes a subagent file:
    - claude: `.claude/agents/<name>.md`
    - codex: not supported, familiar reports an error
- a subagent file starts with `name` and `description` frontmatter; the description lists the first line of each conjuring, as `familiar list -v` shows it

**examples:**

```bash
# rust project with security focus
familiar conjure codex rust sec

# python project, different directory
familiar conjure claude python --into /path/to/repo

# export conjurings as subagents
familiar conjure claude python sec --save-subagent
familiar conjure claude rust infra --save-subagent --subagent-name ship_ops

```

## familiar invoke

run a task prompt through the agent.

```
familiar invoke <agent> <invocation> [args...] [--into <path>] [--headless] [--kv <key=value>...]
```

**arguments:**

| argument | description |
|----------|-------------|
| `agent` | target agent: `codex`, `claude`, or any plugin-provided agent |
| `invocation` | invocation name |
| `args` | positional arguments for the invocation |

**options:**

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |
| `--headless` | run without interactive ui |
| `--auto` | skip agent permission prompts (`--sandbox workspace-write` for codex, plus `--ask-for-approval on-request` when interactive; `--dangerously-skip-permissions` for claude) |
| `--dry-run` | print rendered prompt and exit (does not run the agent) |
| `--worktree` | run in a separate git worktree to avoid interfering with local changes |
| `--save-skill` | write rendered invocation as a reusable skill and exit |
| `--skill-name` | override skill name (default: invocation name) |
| `--kv` | named arguments as `key=value` pairs; takes every value up to the next option, so `args` go before it |

**behavior:**

- renders invocation with provided arguments
- with `--save-skill`, writes a skill file and exits:
    - claude: `.claude/skills/<name>/SKILL.md`
    - codex: `.codex/skills/<name>/SKILL.md`
- a skill file starts with `name` and `description` frontmatter; the description is the first line of the rendered invocation, without its `task:` label
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
| `-v`, `--verbose` | show first non-blank line of each file |

**behavior:**

- lists built-in and local items
- local overrides are marked with `(local)`
- local files that cannot be read, and anything other than a file where one belongs (a directory, a FIFO), are marked with `(local, unreadable)`; `familiar lint` reports why
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
