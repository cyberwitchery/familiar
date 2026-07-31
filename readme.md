# familiar

[![pypi](https://img.shields.io/pypi/v/familiar-cli)](https://pypi.org/project/familiar-cli/)
[![docs](https://readthedocs.org/projects/familiar/badge/?version=latest)](https://familiar.readthedocs.io/)

compose and invoke ai agent prompts from reusable conjurings and invocations.

ships with a standard set of conjurings and invocations, or bring your own (mine are
very much wip).

## installation

```
pip install familiar-cli
```

## usage

```
usage: familiar [-h] [--version] [--debug] {conjure,invoke,list,lint} ...

conjure and invoke familiars

positional arguments:
  {conjure,invoke,list,lint}
    conjure             compose system instructions for an agent
    invoke              render an invocation and run the agent
    list                list available conjurings and invocations
    lint                lint conjurings and invocations

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --debug               show full traceback on error
```

conjure conjurings to create system instructions for an agent:

```
familiar conjure codex rust infra sec
```

save composed conjurings as a reusable subagent:

```bash
familiar conjure claude python sec --save-subagent
familiar conjure codex rust infra --save-subagent --subagent-name ship_ops
```

save an invocation as a reusable skill:

```bash
familiar invoke claude code-review --save-skill
familiar invoke codex refactor src/foo.py --save-skill --skill-name cleanup_refactor
```

invoke an action prompt:

```bash
familiar invoke codex bootstrap-rust myapp lib 1.78 mit
```

run in a separate git worktree to avoid interfering with local changes:

```bash
familiar invoke --worktree codex bootstrap-rust myapp lib
```

list available conjurings and invocations:

```
familiar list
```

lint conjurings and invocations, including local `.familiar/` overrides:

```
familiar lint
```

## customization

add your own conjurings and invocations by creating files in `.familiar/` in your repo:

```
.familiar/
  conjurings/
    myprofile.md      # new conjuring
    rust.md           # override built-in
  invocations/
    my-task.md        # new invocation
```

local files take precedence over built-ins.

## plugins

add new agents via plugins:

```bash
pip install familiar-gemini
familiar invoke gemini bootstrap-python myapp cli
```

see the [plugin docs](https://familiar.readthedocs.io/en/latest/plugins/) for creating your own.

### placeholders

invocations support placeholders:
- `$1`, `$2`, ... - positional arguments
- `$ARGUMENTS` - all positional arguments joined
- `{{key}}` - named arguments passed via `--kv key=value`

## documentation

full docs at [familiar.readthedocs.io](https://familiar.readthedocs.io/).

## license

mit
