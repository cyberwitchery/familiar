"""linting for familiar conjurings and invocations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from ._plugins import load_plugins

from .render import _SNIPPET_INCLUDE, NotFoundError, list_items, load_snippet, load_text


@dataclass
class LintMessage:
    """a lint message."""

    level: Literal["error", "warning"]
    file: str
    line: int | None
    message: str

    def __str__(self) -> str:
        loc = f"{self.file}"
        if self.line is not None:
            loc += f":{self.line}"
        return f"{self.level}: {loc}: {self.message}"


_POSITIONAL_PLACEHOLDER = re.compile(r"\$(\d+|ARGUMENTS)")
_NAMED_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")

# accept various task verbs as first line
_TASK_LINE = re.compile(
    r"^(task|explain|review|analyze|check|audit|describe|create|generate|refactor|bootstrap|implement|add|fix)(\s|:)",
    re.IGNORECASE,
)
# accept inputs, input, arguments as input sections (with or without ## heading)
_INPUTS_SECTION = re.compile(
    r"^(##\s+)?(inputs?|arguments?)(\s*\([^)]+\))?:?\s*$", re.IGNORECASE | re.MULTILINE
)
_OUTPUT_SECTION = re.compile(
    r"^(##\s+)?(output|deliverables?):?\s*$", re.IGNORECASE | re.MULTILINE
)


def lint_template(content: str, name: str) -> list[LintMessage]:
    """lint a template (conjuring) file.

    templates should:
    - start with a markdown heading
    """
    messages: list[LintMessage] = []
    lines = content.split("\n")

    if not lines or not lines[0].strip():
        messages.append(
            LintMessage(
                level="error",
                file=name,
                line=1,
                message="template is empty",
            )
        )
        return messages

    first_line = lines[0].strip()
    if not first_line.startswith("#"):
        messages.append(
            LintMessage(
                level="warning",
                file=name,
                line=1,
                message="template should start with a markdown heading (# ...)",
            )
        )

    return messages


def lint_invocation(content: str, name: str) -> list[LintMessage]:
    """lint an invocation file.

    invocations should:
    - start with a task: line (or similar verb)
    - have an inputs section (warning if missing)
    - have an output section (warning if missing)
    - document all placeholders used
    """
    messages: list[LintMessage] = []
    lines = content.split("\n")

    if not lines or not lines[0].strip():
        messages.append(
            LintMessage(
                level="error",
                file=name,
                line=1,
                message="invocation is empty",
            )
        )
        return messages

    first_line = lines[0].strip()
    if not _TASK_LINE.match(first_line):
        messages.append(
            LintMessage(
                level="warning",
                file=name,
                line=1,
                message="invocation should start with 'task:' or similar verb",
            )
        )

    if not _INPUTS_SECTION.search(content):
        messages.append(
            LintMessage(
                level="warning",
                file=name,
                line=None,
                message="invocation should have an 'inputs' section",
            )
        )

    if not _OUTPUT_SECTION.search(content):
        messages.append(
            LintMessage(
                level="warning",
                file=name,
                line=None,
                message="invocation should have an 'output' or 'deliverables' section",
            )
        )

    positional = set(_POSITIONAL_PLACEHOLDER.findall(content))
    named = set(_NAMED_PLACEHOLDER.findall(content))

    # loose check: prefer the inputs section if it exists, else the whole file
    inputs_match = _INPUTS_SECTION.search(content)
    if inputs_match:
        start = inputs_match.end()
        # look ahead for the next markdown heading or end of file
        next_heading = re.search(r"^#", content[start:], re.MULTILINE)
        search_area = (
            content[start : start + next_heading.start()]
            if next_heading
            else content[start:]
        ).lower()
    else:
        search_area = content.lower()

    for placeholder in named:
        if placeholder.lower() not in search_area.replace(
            f"{{{{{placeholder.lower()}}}}}", ""
        ):
            messages.append(
                LintMessage(
                    level="warning",
                    file=name,
                    line=None,
                    message=f"placeholder '{{{{{placeholder}}}}}' may not be documented in inputs",
                )
            )

    for p in positional:
        if p == "ARGUMENTS":
            continue
        pattern = rf"(\w+[:\s]+\${p}|\${p}\s+[`\w]|\${p}\s*\()"
        if not re.search(pattern, search_area):
            messages.append(
                LintMessage(
                    level="warning",
                    file=name,
                    line=None,
                    message=f"placeholder '${p}' may not be documented in inputs",
                )
            )

    return messages


LinterFunc = Callable[[str, str], list[LintMessage]]


def load_linters(kind: Literal["conjurings", "invocations"]) -> list[LinterFunc]:
    """load linter plugins for the given kind.

    Args:
        kind: either "conjurings" or "invocations".

    Returns:
        list of linter functions from plugins.
    """
    return load_plugins(
        f"familiar.linters.{kind}",
        callable,
        label="linter plugin",
        invalid_msg="not callable",
    )


def lint_snippet_references(
    repo_root: Path, content: str, name: str
) -> list[LintMessage]:
    """check that all snippet includes reference existing snippets."""
    messages: list[LintMessage] = []
    for i, line in enumerate(content.split("\n"), 1):
        for m in _SNIPPET_INCLUDE.finditer(line):
            snippet_path = m.group(1).strip()
            try:
                load_snippet(repo_root, snippet_path)
            except NotFoundError:
                messages.append(
                    LintMessage(
                        level="error",
                        file=name,
                        line=i,
                        message=f"snippet not found: {snippet_path}",
                    )
                )
    return messages


def lint_collection(
    repo_root: Path,
    kind: Literal["conjurings", "invocations"],
    builtin_linter: LinterFunc,
    plugin_linters: list[LinterFunc],
) -> list[LintMessage]:
    """lint a collection of items (conjurings or invocations)."""
    messages: list[LintMessage] = []
    for name, _, is_local in list_items(repo_root, kind):
        try:
            content = load_text(repo_root, kind, name)
            prefix = (
                f".familiar/{kind}/{name}.md"
                if is_local
                else f"(builtin) {kind}/{name}.md"
            )
            messages.extend(builtin_linter(content, prefix))
            messages.extend(lint_snippet_references(repo_root, content, prefix))
            for linter in plugin_linters:
                try:
                    messages.extend(linter(content, prefix))
                except Exception as e:
                    messages.append(
                        LintMessage(
                            level="error",
                            file=prefix,
                            line=None,
                            message=f"plugin linter failed: {e}",
                        )
                    )
        except NotFoundError as e:
            messages.append(
                LintMessage(
                    level="error",
                    file=f"{kind}/{name}.md",
                    line=None,
                    message=f"failed to load: {e}",
                )
            )
    return messages


def lint_all(repo_root: Path) -> list[LintMessage]:
    """lint all conjurings and invocations.

    runs built-in linters and any plugin linters registered via entry points.

    returns a list of lint messages (errors and warnings).
    """
    messages: list[LintMessage] = []

    conjuring_linters = load_linters("conjurings")
    invocation_linters = load_linters("invocations")

    messages.extend(
        lint_collection(repo_root, "conjurings", lint_template, conjuring_linters)
    )
    messages.extend(
        lint_collection(repo_root, "invocations", lint_invocation, invocation_linters)
    )

    return messages
