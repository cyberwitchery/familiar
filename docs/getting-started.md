# getting started

## installation

```bash
pip install familiar-cli
```

## basic workflow

familiar has three main commands: `conjure`, `invoke`, and `list`.

### conjure

`conjure` creates a system prompt file for your agent by combining conjurings.

```bash
familiar conjure <agent> <conjurings...>
```

example:

```bash
familiar conjure codex rust infra sec
```

this creates an `AGENTS.md` file (for codex) or `CLAUDE.md` file (for claude) in your repository root with combined instructions from the rust, infra, and sec conjurings.

the selected conjurings are saved to `.familiar/<agent>.json` so you don't need to specify them again.

### invoke

`invoke` runs a task prompt through the agent.

```bash
familiar invoke <agent> <invocation> [args...]
```

example:

```bash
familiar invoke codex bootstrap-rust myapp bin 1.78 mit
```

this renders the `bootstrap-rust` invocation with the provided arguments and sends it to codex.

### list

`list` shows available conjurings and invocations.

```bash
familiar list <kind>
```

example:

```bash
familiar list conjurings
familiar list invocations -v
```

use `-v` to see the first line of each file as a description. local overrides are marked with `(local)`.

## supported agents

| agent | system file | interactive | headless |
|-------|-------------|-------------|----------|
| codex | AGENTS.md | `codex <prompt>` | `codex exec` |
| claude | CLAUDE.md | `claude <prompt>` | `claude -p` |

use `--headless` to run without interactive ui:

```bash
familiar invoke codex bootstrap-rust --headless myapp bin
familiar invoke claude code-review --headless
```

## next steps

- explore the [built-in conjurings](conjurings.md)
- see available [invocations](invocations.md)
- learn how to [customize](customization.md) for your needs
