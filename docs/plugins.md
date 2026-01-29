# plugins

familiar supports plugins via Python entry points:

- **agent plugins** - add new agents (gemini, aider, etc.)
- **linter plugins** - add custom lint rules for conjurings and invocations

---

## agent plugins

### using agent plugins

install a plugin package and the agent becomes available:

```bash
pip install familiar-gemini
familiar invoke gemini bootstrap-python myapp cli
```

installed agents appear in `familiar invoke --help` and `familiar conjure --help`.

### creating an agent plugin

#### 1. create the agent class

subclass `Agent` and implement the required interface:

```python
# src/my_plugin/__init__.py
from __future__ import annotations

import subprocess
from pathlib import Path

from familiar.agents import Agent


class MyAgent(Agent):
    """Agent that uses the my-cli tool."""

    name = "myagent"           # CLI name: familiar invoke myagent ...
    output_file = "MYAGENT.md" # where conjure writes instructions

    def run(self, repo_root: Path, prompt: str, headless: bool) -> int:
        """Run the agent with the given prompt.

        Args:
            repo_root: Repository root directory.
            prompt: The rendered invocation text.
            headless: If True, run without interactive UI.

        Returns:
            Exit code from the underlying CLI tool.
        """
        if headless:
            cmd = ["my-cli", "-p", prompt]
        else:
            cmd = ["my-cli", prompt]
        return subprocess.call(cmd, cwd=repo_root)
```

#### 2. register the entry point

add to your `pyproject.toml`:

```toml
[project.entry-points."familiar.agents"]
myagent = "my_plugin:MyAgent"
```

#### 3. install and test

```bash
pip install -e .
familiar invoke --help  # should show myagent in choices
```

### agent interface

| attribute/method | type | description |
|------------------|------|-------------|
| `name` | `str` | agent name for CLI |
| `output_file` | `str` | filename for conjured instructions |
| `run(repo_root, prompt, headless)` | `-> int` | execute the agent, return exit code |

---

## linter plugins

linter plugins add custom validation rules to `familiar lint`.

### creating a linter plugin

#### 1. create the linter function

linters are functions that take content and filename, returning a list of messages:

```python
# src/my_plugin/linters.py
from familiar.lint import LintMessage


def check_max_length(content: str, name: str) -> list[LintMessage]:
    """Warn if any line exceeds 100 characters."""
    messages = []
    for i, line in enumerate(content.split("\n"), 1):
        if len(line) > 100:
            messages.append(
                LintMessage(
                    level="warning",
                    file=name,
                    line=i,
                    message=f"line exceeds 100 characters ({len(line)})",
                )
            )
    return messages
```

#### 2. register the entry point

use `familiar.linters.conjurings` for conjuring linters, `familiar.linters.invocations` for invocation linters:

```toml
[project.entry-points."familiar.linters.conjurings"]
max-length = "my_plugin.linters:check_max_length"

[project.entry-points."familiar.linters.invocations"]
max-length = "my_plugin.linters:check_max_length"
```

#### 3. test it

```bash
pip install -e .
familiar lint  # your rules now run
```

### linter interface

linters are callables with signature:

```python
def my_linter(content: str, name: str) -> list[LintMessage]:
    ...
```

| parameter | type | description |
|-----------|------|-------------|
| `content` | `str` | full text content of the file |
| `name` | `str` | display name (e.g., `.familiar/conjurings/foo.md`) |
| returns | `list[LintMessage]` | list of warnings/errors |

### LintMessage

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class LintMessage:
    level: Literal["error", "warning"]
    file: str
    line: int | None  # None if not line-specific
    message: str
```

---

## example plugins

- [familiar-gemini](https://github.com/cyberwitchery/familiar-gemini) - gemini CLI agent
