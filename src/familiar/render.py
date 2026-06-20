"""render system and user prompts from conjurings and invocations."""

from __future__ import annotations

import re
import sys
from importlib import resources

try:
    from importlib.resources.abc import Traversable  # type: ignore[import-not-found]
except ImportError:
    from importlib.abc import Traversable
from pathlib import Path

_VALID_NAME = re.compile(r"^[a-z0-9_-]+$")
_VALID_SNIPPET_PATH = re.compile(r"^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)+$")
_SNIPPET_INCLUDE = re.compile(r"{{>\s*snippet:([^}]+?)\s*}}")


class NotFoundError(Exception):
    """raised when a conjuring, invocation, or snippet is not found."""


def _safe_read_text(path: Path, label: str) -> str:
    """read a UTF-8 text file, converting I/O errors to :class:`NotFoundError`."""
    try:
        return path.read_text(encoding="utf-8")
    except PermissionError:
        raise NotFoundError(f"cannot read {label}: permission denied on {path}")
    except UnicodeDecodeError:
        raise NotFoundError(f"cannot read {label}: {path} is not valid UTF-8")


def load_text(repo_root: Path, kind: str, name: str) -> str:
    """load a conjuring or invocation; local overrides in .familiar override package data."""
    if not _VALID_NAME.match(name):
        raise NotFoundError(f"invalid {kind.rstrip('s')} name: {name}")
    override = repo_root / ".familiar" / kind / f"{name}.md"
    if override.exists():
        return _safe_read_text(override, f"{kind.rstrip('s')} '{name}'")
    pkg = f"familiar.data.{kind}"
    try:
        return (resources.files(pkg) / f"{name}.md").read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        # TypeError: some python versions (e.g. 3.10) raise this if the
        # resource package exists but the specific file is missing.
        raise NotFoundError(f"unknown {kind.rstrip('s')}: {name}")


def load_snippet(repo_root: Path, path: str) -> str:
    """load a snippet by path; local overrides in .familiar/snippets/ win."""
    path = path.strip()
    if ".." in path.split("/"):
        raise NotFoundError(f"invalid snippet path: {path}")
    if not _VALID_SNIPPET_PATH.match(path):
        raise NotFoundError(f"invalid snippet path: {path}")

    override = repo_root / ".familiar" / "snippets" / path
    if override.exists():
        return _safe_read_text(override, f"snippet '{path}'")

    try:
        ref: Traversable = resources.files("familiar.data.snippets")
        for part in path.split("/"):
            ref = ref / part
        content: str = ref.read_text(encoding="utf-8")
        return content
    except (FileNotFoundError, TypeError):
        raise NotFoundError(f"unknown snippet: {path}")


def resolve_includes(repo_root: Path, text: str) -> str:
    """resolve {{> snippet:path}} includes by replacing them with snippet content."""

    def repl(m: re.Match[str]) -> str:
        return load_snippet(repo_root, m.group(1))

    return _SNIPPET_INCLUDE.sub(repl, text)


def substitute(text: str, args: list[str], kv: dict[str, str]) -> str:
    """substitute $1, $2, ... $ARGUMENTS and {{key}} placeholders in a single pass."""
    missing: list[str] = []

    def repl(m: re.Match[str]) -> str:
        pos_ident = m.group(1)
        named_ident = m.group(2)

        if pos_ident:
            if pos_ident == "ARGUMENTS":
                return " ".join(args).strip()
            idx = int(pos_ident) - 1
            if 0 <= idx < len(args):
                return args[idx]
            missing.append(f"${pos_ident}")
            return ""

        if named_ident:
            return kv.get(named_ident, m.group(0))

        return m.group(0)

    # combined regex for both types of placeholders:
    # group 1: \$(ARGUMENTS|\d+)
    # group 2: {{(\w+)}}
    pattern = re.compile(r"\$(ARGUMENTS|\d+)|{{(\w+)}}")
    text = pattern.sub(repl, text)

    if missing:
        print(f"warning: missing arguments: {', '.join(missing)}", file=sys.stderr)
    return text


def _walk_traversable(root: Traversable, prefix: str = "") -> list[tuple[str, str]]:
    """recursively walk a Traversable, returning (relative_path, first_line) pairs."""
    items: list[tuple[str, str]] = []
    try:
        for item in sorted(root.iterdir(), key=lambda x: x.name):
            rel = f"{prefix}/{item.name}" if prefix else item.name
            if item.is_dir():
                items.extend(_walk_traversable(item, rel))
            elif not item.name.startswith("_"):
                try:
                    content = item.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    continue
                first_line = content.split("\n", 1)[0].strip()
                items.append((rel, first_line))
    except (FileNotFoundError, TypeError):
        pass
    return items


def _list_resources(
    repo_root: Path,
    pkg: str,
    local_subdir: str,
    *,
    recursive: bool = False,
    suffix: str = "",
) -> list[tuple[str, str, bool]]:
    """list resources from package data and local overrides.

    items from local ``.familiar/{local_subdir}/`` override package builtins.

    Args:
        repo_root: repository root path.
        pkg: package name to scan for builtins.
        local_subdir: subdirectory name under ``.familiar/`` for local overrides.
        recursive: if True, scan recursively (for nested resources like snippets).
        suffix: file suffix filter (e.g. ``".md"``). empty string matches all files.

    Returns:
        sorted list of ``(key, first_line, is_local)`` tuples.
    """
    items: dict[str, tuple[str, bool]] = {}

    try:
        pkg_root = resources.files(pkg)
        if recursive:
            for rel, first_line in _walk_traversable(pkg_root):
                items[rel] = (first_line, False)
        else:
            for item in pkg_root.iterdir():
                if suffix and not item.name.endswith(suffix):
                    continue
                if item.name.startswith("_"):
                    continue
                key = item.name[: -len(suffix)] if suffix else item.name
                try:
                    content = item.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    continue
                first_line = content.split("\n", 1)[0].strip()
                items[key] = (first_line, False)
    except (FileNotFoundError, TypeError, ModuleNotFoundError):
        pass

    local_dir = repo_root / ".familiar" / local_subdir
    if local_dir.is_dir():
        files = (
            sorted(local_dir.rglob("*")) if recursive else local_dir.glob(f"*{suffix}")
        )
        for f in files:
            if not f.is_file() or f.name.startswith("_"):
                continue
            key = str(f.relative_to(local_dir)) if recursive else f.stem
            try:
                content = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            first_line = content.split("\n", 1)[0].strip()
            items[key] = (first_line, True)

    return [
        (key, first_line, is_local)
        for key, (first_line, is_local) in sorted(items.items())
    ]


def list_snippets(repo_root: Path) -> list[tuple[str, str, bool]]:
    """list available snippets.

    returns list of (path, first_line, is_local) tuples, sorted by path.
    """
    return _list_resources(
        repo_root, "familiar.data.snippets", "snippets", recursive=True
    )


def list_items(repo_root: Path, kind: str) -> list[tuple[str, str, bool]]:
    """list available conjurings or invocations.

    returns list of (name, first_line, is_local) tuples, sorted by name.
    """
    return _list_resources(repo_root, f"familiar.data.{kind}", kind, suffix=".md")


def compose_system(repo_root: Path, conjurings: list[str]) -> str:
    """compose system instructions from core + selected conjurings."""
    core = load_text(repo_root, "conjurings", "core").strip()
    parts: list[str] = [core]
    for name in conjurings:
        parts.append(load_text(repo_root, "conjurings", name).strip())
    return "\n\n".join(parts)


def render_invocation(
    repo_root: Path, invocation: str, args: list[str], kv: dict[str, str]
) -> str:
    """render an invocation with snippet inclusion and argument substitution."""
    inv = load_text(repo_root, "invocations", invocation).strip()
    inv = resolve_includes(repo_root, inv)
    return substitute(inv, args, kv)
