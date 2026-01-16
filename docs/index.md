# familiar

compose and invoke ai agent prompts from reusable templates.

familiar helps you build consistent, reusable prompts for ai coding agents like codex and claude. instead of writing ad-hoc instructions every time, you define **profiles** (system-level guidelines) and **invocations** (task-specific prompts) that can be mixed and matched.

## features

- **profiles** - reusable system instructions (rust, python, infra, security, etc.)
- **invocations** - task templates with placeholder substitution
- **local overrides** - customize built-ins per repository
- **agent support** - works with codex and claude cli

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
- [profiles](profiles.md) - available profiles and what they do
- [invocations](invocations.md) - available task templates
- [customization](customization.md) - add your own profiles and invocations
