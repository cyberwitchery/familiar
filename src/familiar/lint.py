"""linting for familiar conjurings and invocations."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ._plugins import load_plugins
from .render import (
    _SNIPPET_INCLUDE,
    NotFoundError,
    _expand_includes,
    list_items,
    list_snippets,
    load_snippet,
    load_text,
    resolve_includes,
)


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
    r"^(##\s+)?(outputs?|deliverables?):?\s*$", re.IGNORECASE | re.MULTILINE
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


def _check_placeholder_docs(
    positional: set[str], named: set[str], doc_content: str, name: str
) -> list[LintMessage]:
    """warn about placeholders not documented in ``doc_content``'s inputs section."""
    messages: list[LintMessage] = []

    # loose check: prefer the inputs section if it exists, else the whole file
    inputs_match = _INPUTS_SECTION.search(doc_content)
    if inputs_match:
        start = inputs_match.end()
        # look ahead for the next markdown heading or end of file
        next_heading = re.search(r"^#", doc_content[start:], re.MULTILINE)
        search_area = (
            doc_content[start : start + next_heading.start()]
            if next_heading
            else doc_content[start:]
        ).lower()
    else:
        search_area = doc_content.lower()

    for placeholder in named:
        tag = f"{{{{{placeholder.lower()}}}}}"
        stripped = search_area.replace(tag, "")
        # accept the placeholder as documented if its bare name appears as a
        # standalone word (after stripping {{…}} syntax) OR if the {{…}} tag
        # itself appears in the inputs section (the common "- {{name}}: …"
        # documentation pattern).
        bare_match = re.search(r"\b" + re.escape(placeholder.lower()) + r"\b", stripped)
        if not bare_match and tag not in search_area:
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
    messages.extend(_check_placeholder_docs(positional, named, content, name))

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
    """check that snippet includes resolve, following them transitively.

    each top-level ``{{> snippet:path}}`` directive is validated along with
    every snippet it pulls in, mirroring how the renderer expands includes at
    conjure/invoke time. a broken reference, an include cycle, or an over-deep
    chain is reported against the line of the top-level directive.
    """
    messages: list[LintMessage] = []
    for i, line in enumerate(content.split("\n"), 1):
        for m in _SNIPPET_INCLUDE.finditer(line):
            snippet_path = m.group(1).strip()
            try:
                body = load_snippet(repo_root, snippet_path)
            except NotFoundError:
                messages.append(
                    LintMessage(
                        level="error",
                        file=name,
                        line=i,
                        message=f"snippet not found: {snippet_path}",
                    )
                )
                continue
            try:
                _expand_includes(repo_root, body, [snippet_path])
            except NotFoundError as e:
                messages.append(
                    LintMessage(
                        level="error",
                        file=name,
                        line=i,
                        message=str(e),
                    )
                )
    return messages


def lint_snippet_collection(repo_root: Path) -> list[LintMessage]:
    """lint every snippet body for broken, cyclic, or over-deep includes.

    a snippet may include other snippets; a bad snippet->snippet include stays
    invisible until something transitively pulls it in. each snippet is checked
    against its own path.
    """
    messages: list[LintMessage] = []
    for path, _, is_local in list_snippets(repo_root):
        prefix = (
            f".familiar/snippets/{path}" if is_local else f"(builtin) snippets/{path}"
        )
        try:
            content = load_snippet(repo_root, path)
        except NotFoundError as e:
            messages.append(
                LintMessage(
                    level="error",
                    file=prefix,
                    line=None,
                    message=f"failed to load: {e}",
                )
            )
            continue
        messages.extend(lint_snippet_references(repo_root, content, prefix))
    return messages


def lint_snippet_placeholders(
    repo_root: Path, content: str, name: str
) -> list[LintMessage]:
    """check placeholders that included snippets contribute to an invocation.

    the renderer expands includes before substituting, so a ``$1``/``{{key}}``
    inside an included snippet is live at invoke time but invisible to the
    raw-text check in :func:`lint_invocation`. only the snippet-contributed
    delta is checked here; broken or cyclic includes are left to
    :func:`lint_snippet_references`.
    """
    try:
        expanded = resolve_includes(repo_root, content)
    except NotFoundError:
        return []

    positional = set(_POSITIONAL_PLACEHOLDER.findall(expanded)) - set(
        _POSITIONAL_PLACEHOLDER.findall(content)
    )
    named = set(_NAMED_PLACEHOLDER.findall(expanded)) - set(
        _NAMED_PLACEHOLDER.findall(content)
    )
    return _check_placeholder_docs(positional, named, content, name)


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
            if kind == "invocations":
                messages.extend(lint_snippet_placeholders(repo_root, content, prefix))
            for linter in plugin_linters:
                try:
                    messages.extend(linter(content, prefix))
                # a broken plugin linter is reported, not fatal to the run
                except Exception as e:  # noqa: BLE001
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
    messages.extend(lint_snippet_collection(repo_root))

    return messages
