# familiar

compose and invoke ai agent prompts from reusable templates.

## installation

```
pip install familiar-cli
```

## usage

conjure profiles to create system instructions for an agent:

```
familiar conjure codex rust infra sec
```

invoke an action prompt:

```
familiar invoke codex bootstrap-rust myapp lib 1.78 mit
```

## customization

add your own templates and invocations by creating files in `.familiar/` in your repo:

```
.familiar/
  templates/
    myprofile.md      # new profile
    rust.md           # override built-in
  invocations/
    my-task.md        # new invocation
```

local files take precedence over built-ins.

### placeholders

invocations support placeholders:
- `$1`, `$2`, ... - positional arguments
- `$ARGUMENTS` - all positional arguments joined
- `{{key}}` - named arguments passed via `--kv key=value`

## license

mit
