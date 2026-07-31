# getting started

## installation

```bash
pip install familiar-cli
```

## basic workflow

familiar has four commands: `conjure`, `invoke`, `list`, and `lint`.

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

to also save a reusable subagent from conjurings:

```bash
familiar conjure claude python sec --save-subagent
familiar conjure codex rust infra --save-subagent --subagent-name ship_ops
```

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

to save an invocation as a reusable skill instead of running it:

```bash
familiar invoke claude code-review --save-skill
familiar invoke codex refactor src/foo.py --save-skill --skill-name cleanup_refactor
```

### list

`list` shows available conjurings and invocations.

```bash
familiar list [kind]
```

example:

```bash
familiar list
familiar list conjurings
familiar list invocations -v
```

omit `kind` to list everything. use `-v` to see descriptions. local overrides are marked with `(local)`.

### lint

`lint` validates conjurings and invocations, including local `.familiar/` overrides:

```bash
familiar lint
familiar lint --errors-only
```

see [linting](linting.md) for the rules.

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
