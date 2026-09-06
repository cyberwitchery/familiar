"""linting for familiar conjurings and invocations."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
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
    r"^(##\s+)?(inputs?|arguments?)(\s*\([^)]+\))?:?\s*$", re.IGNORECASE
)
_OUTPUT_SECTION = re.compile(r"^(##\s+)?(outputs?|deliverables?):?\s*$", re.IGNORECASE)
_FENCE = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
_LIST_ITEM = re.compile(r"^( {0,3})([-+*]|\d{1,9})([.)]?)( +|$)")
_ATX_HEADING = re.compile(r"^ {0,3}#{1,6}(?: |$)")

_QUOTE = "quote"
_ITEM = "item"

_HTML_BLOCK_NAMES = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|"
    "colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|"
    "form|frame|frameset|h1|h2|h3|h4|h5|h6|head|header|hr|html|iframe|legend|li|"
    "link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|"
    "section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul"
)
_HTML_ATTRIBUTE = (
    r"(?:\s+[a-zA-Z_:][a-zA-Z0-9:._-]*"
    r"(?:\s*=\s*(?:[^\"'=<>`\x00-\x20]+|'[^']*'|\"[^\"]*\"))?)"
)
_HTML_TAG = (
    rf"<[A-Za-z][A-Za-z0-9-]*{_HTML_ATTRIBUTE}*\s*/?>|</[A-Za-z][A-Za-z0-9-]*\s*>"
)

# commonmark's seven html block types in order; a ``None`` end condition means
# the block runs to the next blank line
_HTML_BLOCKS: tuple[tuple[re.Pattern[str], re.Pattern[str] | None], ...] = (
    (
        re.compile(r"^ {0,3}<(?:script|pre|style|textarea)(?=\s|>|$)", re.IGNORECASE),
        re.compile(r"</(?:script|pre|style|textarea)>", re.IGNORECASE),
    ),
    (re.compile(r"^ {0,3}<!--"), re.compile(r"-->")),
    (re.compile(r"^ {0,3}<\?"), re.compile(r"\?>")),
    (re.compile(r"^ {0,3}<![A-Za-z]"), re.compile(r">")),
    (re.compile(r"^ {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
    (
        re.compile(rf"^ {{0,3}}</?(?:{_HTML_BLOCK_NAMES})(?=\s|/?>|$)", re.IGNORECASE),
        None,
    ),
    (re.compile(rf"^ {{0,3}}(?:{_HTML_TAG})[ \t]*$"), None),
)
# type 7, any complete tag alone on a line, may not interrupt a paragraph
_HTML_LOOSE_TAG = 6


def _match_container(line: str, col: int, container: tuple[str, int]) -> int | None:
    """column just past ``container``'s prefix on ``line``, or ``None`` if absent."""
    kind, width = container
    stop = col + (3 if kind == _QUOTE else width)
    end = col
    while end < len(line) and line[end] == " " and end < stop:
        end += 1
    if kind == _ITEM:
        return end if end - col == width else None
    if end >= len(line) or line[end] != ">":
        return None
    end += 1
    return end + 1 if end < len(line) and line[end] == " " else end


def _opens_item(line: str, col: int, interrupting: bool) -> int | None:
    """content width of the list item starting at ``col``, or ``None`` if none does."""
    item = _LIST_ITEM.match(line[col:])
    if item is None or (item.group(2).isdigit() and not item.group(3)):
        return None
    content = line[col + item.end() :]
    if interrupting and (
        not content.strip() or item.group(2) not in ("-", "+", "*", "1")
    ):
        return None
    pad = len(item.group(4))
    marker = len(item.group(1)) + len(item.group(2)) + len(item.group(3))
    return marker + (pad if 1 <= pad <= 4 and content else 1)


def _open_containers(
    line: str, col: int, stack: list[tuple[str, int]], interrupting: bool
) -> int:
    """push every container ``line`` opens at ``col``, returning the content column."""
    while True:
        quoted = _match_container(line, col, (_QUOTE, 0))
        if quoted is not None:
            stack.append((_QUOTE, 0))
            col = quoted
        else:
            width = _opens_item(line, col, interrupting)
            if width is None:
                return col
            stack.append((_ITEM, width))
            col += width
        interrupting = False


def _closes(rest: str, fence: str) -> bool:
    match = _FENCE.match(rest)
    return (
        match is not None
        and match.group("marker")[0] == fence[0]
        and len(match.group("marker")) >= len(fence)
        and not match.group("info").strip()
    )


def _opens(rest: str) -> str | None:
    match = _FENCE.match(rest)
    if match is None:
        return None
    marker = match.group("marker")
    if marker[0] == "`" and "`" in match.group("info"):
        return None
    return marker


def _opens_html(rest: str, paragraph: bool) -> int | None:
    """index into ``_HTML_BLOCKS`` of the html block ``rest`` opens, else ``None``."""
    for kind, (start, _) in enumerate(_HTML_BLOCKS):
        if start.match(rest):
            return None if kind == _HTML_LOOSE_TAG and paragraph else kind
    return None


def _unfenced_lines(text: str) -> Iterator[tuple[int, str]]:
    """yield ``(offset, line)`` for every line of ``text`` outside a fenced code block.

    fence indentation is measured from the content column of the block quotes and
    list items open around it. an unclosed fence runs to the end of its container,
    or to the end of ``text`` at the top level. html blocks are tracked the same
    way and swallow any fence marker inside them.
    """
    stack: list[tuple[str, int]] = []
    fence: str | None = None
    html: int | None = None
    paragraph = False
    offset = 0
    for line in text.split("\n"):
        expanded = line.expandtabs(4)
        blank = not expanded.strip()

        col = 0
        depth = 0
        for container in stack:
            if blank:
                if container[0] == _QUOTE:
                    break
            else:
                nxt = _match_container(expanded, col, container)
                if nxt is None:
                    break
                col = nxt
            depth += 1

        if fence is not None:
            if depth == len(stack):
                if _closes(expanded[col:], fence):
                    fence = None
                offset += len(line) + 1
                continue
            fence = None

        if html is not None:
            end = _HTML_BLOCKS[html][1]
            inner_blank = not expanded[col:].strip()
            if depth < len(stack) or (
                inner_blank and (end is None or (blank and stack))
            ):
                html = None
            else:
                if end is not None and end.search(expanded[col:]):
                    html = None
                yield offset, line
                offset += len(line) + 1
                continue

        del stack[depth:]
        rest = ""
        opened: int | None = None
        if not blank:
            rest = expanded[_open_containers(expanded, col, stack, paragraph) :]
            fence = _opens(rest)
            if fence is not None:
                paragraph = False
                offset += len(line) + 1
                continue
            opened = _opens_html(rest, paragraph)
            if opened is not None:
                end = _HTML_BLOCKS[opened][1]
                html = None if end is not None and end.search(rest) else opened
        paragraph = (
            opened is None
            and bool(rest.strip())
            and not _ATX_HEADING.match(rest)
            and (paragraph or not rest.startswith("    "))
        )

        yield offset, line
        offset += len(line) + 1


def _next_heading_offset(text: str) -> int | None:
    """offset of the first line starting with ``#`` outside a fenced code block."""
    for offset, line in _unfenced_lines(text):
        if line.startswith("#"):
            return offset
    return None


def _section_end_offset(pattern: re.Pattern[str], text: str) -> int | None:
    """offset just past the first line matching ``pattern`` outside a fenced block."""
    for offset, line in _unfenced_lines(text):
        match = pattern.match(line)
        if match:
            return offset + match.end()
    return None


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
    start = _section_end_offset(_INPUTS_SECTION, doc_content)
    if start is not None:
        next_heading = _next_heading_offset(doc_content[start:])
        search_area = (
            doc_content[start : start + next_heading]
            if next_heading is not None
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
        ref = rf"\${p}(?!\d)"
        pattern = rf"(\w+[:\s]+{ref}|{ref}\s+[`\w]|{ref}\s*\()"
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

    if _section_end_offset(_INPUTS_SECTION, content) is None:
        messages.append(
            LintMessage(
                level="warning",
                file=name,
                line=None,
                message="invocation should have an 'inputs' section",
            )
        )

    if _section_end_offset(_OUTPUT_SECTION, content) is None:
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
