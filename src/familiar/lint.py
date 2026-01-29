"""Linting for familiar conjurings and invocations."""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Callable, Literal

from .render import _SNIPPET_INCLUDE, NotFoundError, list_items, load_snippet, load_text


@dataclass
class LintMessage:
    """A lint message."""

    level: Literal["error", "warning"]
    file: str
    line: int | None
    message: str

    def __str__(self) -> str:
        loc = f"{self.file}"
        if self.line is not None:
            loc += f":{self.line}"
        return f"{self.level}: {loc}: {self.message}"


# Regex patterns for placeholders
_POSITIONAL_PLACEHOLDER = re.compile(r"\$(\d+|ARGUMENTS)")
_NAMED_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")

# Section patterns for invocations
# Accept various task verbs as first line
_TASK_LINE = re.compile(
    r"^(task|explain|review|analyze|check|audit|describe|create|generate|refactor|bootstrap|implement|add|fix)(\s|:)",
    re.IGNORECASE,
)
# Accept inputs, input, arguments as input sections (with or without ## heading)
_INPUTS_SECTION = re.compile(
    r"^(##\s+)?(inputs?|arguments?)(\s*\([^)]+\))?:?\s*$", re.IGNORECASE | re.MULTILINE
)
_OUTPUT_SECTION = re.compile(
    r"^(##\s+)?(output|deliverables?):?\s*$", re.IGNORECASE | re.MULTILINE
)


def lint_template(content: str, name: str) -> list[LintMessage]:
    """Lint a template (conjuring) file.

    Templates should:
    - Start with a markdown heading
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
    """Lint an invocation file.

    Invocations should:
    - Start with a task: line (or similar verb)
    - Have an inputs section (warning if missing)
    - Have an output section (warning if missing)
    - Document all placeholders used
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

    # Check first line is a task line
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

    # Check for inputs section
    if not _INPUTS_SECTION.search(content):
        messages.append(
            LintMessage(
                level="warning",
                file=name,
                line=None,
                message="invocation should have an 'inputs' section",
            )
        )

    # Check for output section
    if not _OUTPUT_SECTION.search(content):
        messages.append(
            LintMessage(
                level="warning",
                file=name,
                line=None,
                message="invocation should have an 'output' or 'deliverables' section",
            )
        )

    # Find all placeholders and check if they're documented
    positional = set(_POSITIONAL_PLACEHOLDER.findall(content))
    named = set(_NAMED_PLACEHOLDER.findall(content))

    # Check if placeholders are mentioned in content (loose check)
    # Prefer checking the inputs section if it exists
    inputs_match = _INPUTS_SECTION.search(content)
    if inputs_match:
        start = inputs_match.end()
        # Look ahead for the next markdown heading or end of file
        next_heading = re.search(r"^#", content[start:], re.MULTILINE)
        search_area = (
            content[start : start + next_heading.start()]
            if next_heading
            else content[start:]
        ).lower()
    else:
        search_area = content.lower()

    for placeholder in named:
        # Check if placeholder name appears in search area
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

    # Check for undocumented positional args
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


# Type alias for linter functions
LinterFunc = Callable[[str, str], list[LintMessage]]


def load_linters(kind: Literal["conjurings", "invocations"]) -> list[LinterFunc]:
    """Load linter plugins for the given kind.

    Args:
        kind: Either "conjurings" or "invocations".

    Returns:
        List of linter functions from plugins.
    """
    linters: list[LinterFunc] = []
    group = f"familiar.linters.{kind}"
    eps = entry_points(group=group)

    for ep in eps:
        try:
            func = ep.load()
            if not callable(func):
                warnings.warn(
                    f"linter plugin '{ep.name}': not callable",
                    stacklevel=2,
                )
                continue
            linters.append(func)
        except Exception as e:
            warnings.warn(
                f"failed to load linter plugin '{ep.name}': {e}",
                stacklevel=2,
            )

    return linters


def lint_snippet_references(
    repo_root: Path, content: str, name: str
) -> list[LintMessage]:
    """Check that all snippet includes reference existing snippets."""
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
    """Lint a collection of items (conjurings or invocations)."""
    messages: list[LintMessage] = []
    for name, _, is_local in list_items(repo_root, kind):
        try:
            content = load_text(repo_root, kind, name)
            prefix = (
                f".familiar/{kind}/{name}.md"
                if is_local
                else f"(builtin) {kind}/{name}.md"
            )
            # Built-in linter
            messages.extend(builtin_linter(content, prefix))
            # Snippet reference validation
            messages.extend(lint_snippet_references(repo_root, content, prefix))
            # Plugin linters
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
        except Exception as e:
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
    """Lint all conjurings and invocations.

    Runs built-in linters and any plugin linters registered via entry points.

    Returns a list of lint messages (errors and warnings).
    """
    messages: list[LintMessage] = []

    # Load plugin linters
    conjuring_linters = load_linters("conjurings")
    invocation_linters = load_linters("invocations")

    # Lint conjurings
    messages.extend(
        lint_collection(repo_root, "conjurings", lint_template, conjuring_linters)
    )

    # Lint invocations
    messages.extend(
        lint_collection(repo_root, "invocations", lint_invocation, invocation_linters)
    )

    return messages
