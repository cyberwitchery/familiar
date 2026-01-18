# familiar

[![pypi](https://img.shields.io/pypi/v/familiar-cli)](https://pypi.org/project/familiar-cli/)
[![docs](https://readthedocs.org/projects/familiar/badge/?version=latest)](https://familiar.readthedocs.io/)

compose and invoke ai agent prompts from reusable templates.

ships with a standard set of templates and invocations, or bring your own (mine are
very much wip).

## installation

```
pip install familiar-cli
```

## usage

```
usage: familiar [-h] {conjure,invoke,list} ...

conjure and invoke familiars

positional arguments:
  {conjure,invoke,list}
    conjure             compose system instructions for an agent
    invoke              render an invocation and run the agent
    list                list available conjurings or invocations

options:
  -h, --help            show this help message and exit
```

conjure conjurings to create system instructions for an agent:

```
familiar conjure codex rust infra sec
```

invoke an action prompt:

```
familiar invoke codex bootstrap-rust myapp lib 1.78 mit
```

list available conjurings and invocations:

```
familiar list conjurings
familiar list invocations -v
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

## documentation

full docs at [familiar.readthedocs.io](https://familiar.readthedocs.io/).

## license

mit
