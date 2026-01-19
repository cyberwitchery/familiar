# familiar

compose and invoke ai agent prompts from reusable templates.

familiar helps you build consistent, reusable prompts for ai coding agents like codex and claude. instead of writing ad-hoc instructions every time, you define **conjurings** (system-level guidelines) and **invocations** (task-specific prompts) that can be mixed and matched.

## features

- **conjurings** - reusable system instructions (rust, python, infra, security, etc.)
- **invocations** - task templates with placeholder substitution
- **local overrides** - customize built-ins per repository
- **agent support** - works with codex, claude, and plugin agents

## quick example

```bash
# set up a rust + infra + security agent
familiar conjure codex rust infra sec

# run a bootstrap task
familiar invoke codex bootstrap-rust myapp bin 1.78 mit
```

## installation

```bash
pip install familiar-cli
```

## next steps

- [getting started](getting-started.md) - first-time setup
- [conjurings](conjurings.md) - available conjurings and what they do
- [invocations](invocations.md) - available task templates
- [customization](customization.md) - add your own conjurings and invocations
- [plugins](plugins.md) - create agent plugins
- [cli reference](cli.md) - all commands and options
- [linting](linting.md) - validation rules and recommended structure
