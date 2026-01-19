"""Linting for familiar templates and invocations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .render import list_items, load_text


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
    content_lower = content.lower()
    for placeholder in named:
        # Check if placeholder name appears somewhere (likely in inputs section)
        # Remove the placeholder itself (lowercased to match content_lower) before checking
        if placeholder.lower() not in content_lower.replace(
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

    # Check for undocumented positional args (heuristic: $N should appear with description)
    for p in positional:
        if p == "ARGUMENTS":
            continue
        # Look for patterns indicating the placeholder is documented:
        #   - "name: $1" or "name $1" (description before)
        #   - "$1 name" or "$1 `name`" (description after, plain or backtick-quoted)
        #   - "$1 (" (placeholder with parenthetical like "required")
        pattern = rf"(\w+[:\s]+\${p}|\${p}\s+[`\w]|\${p}\s*\()"
        if not re.search(pattern, content):
            messages.append(
                LintMessage(
                    level="warning",
                    file=name,
                    line=None,
                    message=f"placeholder '${p}' may not be documented in inputs",
                )
            )

    return messages


def lint_all(repo_root: Path) -> list[LintMessage]:
    """Lint all templates and invocations.

    Returns a list of lint messages (errors and warnings).
    """
    messages: list[LintMessage] = []

    # Lint templates
    for name, _, is_local in list_items(repo_root, "templates"):
        try:
            content = load_text(repo_root, "templates", name)
            prefix = (
                f".familiar/templates/{name}.md"
                if is_local
                else f"(builtin) templates/{name}.md"
            )
            messages.extend(lint_template(content, prefix))
        except Exception as e:
            messages.append(
                LintMessage(
                    level="error",
                    file=f"templates/{name}.md",
                    line=None,
                    message=f"failed to load: {e}",
                )
            )

    # Lint invocations
    for name, _, is_local in list_items(repo_root, "invocations"):
        try:
            content = load_text(repo_root, "invocations", name)
            prefix = (
                f".familiar/invocations/{name}.md"
                if is_local
                else f"(builtin) invocations/{name}.md"
            )
            messages.extend(lint_invocation(content, prefix))
        except Exception as e:
            messages.append(
                LintMessage(
                    level="error",
                    file=f"invocations/{name}.md",
                    line=None,
                    message=f"failed to load: {e}",
                )
            )

    return messages
