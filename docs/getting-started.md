# getting started

## installation

```bash
pip install familiar-cli
```

## basic workflow

familiar has two main commands: `conjure` and `invoke`.

### conjure

`conjure` creates a system prompt file for your agent by combining profiles.

```bash
familiar conjure <agent> <profiles...>
```

example:

```bash
familiar conjure codex rust infra sec
```

this creates an `AGENTS.md` file (for codex) or `CLAUDE.md` file (for claude) in your repository root with combined instructions from the rust, infra, and sec profiles.

the selected profiles are saved to `.familiar/<agent>.json` so you don't need to specify them again.

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

- explore the [built-in profiles](profiles.md)
- see available [invocations](invocations.md)
- learn how to [customize](customization.md) for your needs
