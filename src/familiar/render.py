"""Render system and user prompts from conjurings and invocations."""

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
    """Raised when a conjuring, invocation, or snippet is not found."""


def load_text(repo_root: Path, kind: str, name: str) -> str:
    """Load a conjuring or invocation; local overrides in .familiar override package data."""
    if not _VALID_NAME.match(name):
        raise NotFoundError(f"invalid {kind.rstrip('s')} name: {name}")
    override = repo_root / ".familiar" / kind / f"{name}.md"
    if override.exists():
        return override.read_text(encoding="utf-8")
    pkg = f"familiar.data.{kind}"
    try:
        return (resources.files(pkg) / f"{name}.md").read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        # TypeError: some python versions (e.g. 3.10) raise this if the
        # resource package exists but the specific file is missing.
        raise NotFoundError(f"unknown {kind.rstrip('s')}: {name}")


def load_snippet(repo_root: Path, path: str) -> str:
    """Load a snippet by path; local overrides in .familiar/snippets/ win."""
    path = path.strip()
    if ".." in path.split("/"):
        raise NotFoundError(f"invalid snippet path: {path}")
    if not _VALID_SNIPPET_PATH.match(path):
        raise NotFoundError(f"invalid snippet path: {path}")

    override = repo_root / ".familiar" / "snippets" / path
    if override.exists():
        return override.read_text(encoding="utf-8")

    try:
        ref: Traversable = resources.files("familiar.data.snippets")
        for part in path.split("/"):
            ref = ref / part
        content: str = ref.read_text(encoding="utf-8")
        return content
    except (FileNotFoundError, TypeError):
        raise NotFoundError(f"unknown snippet: {path}")


def resolve_includes(repo_root: Path, text: str) -> str:
    """Resolve {{> snippet:path}} includes by replacing them with snippet content."""

    def repl(m: re.Match[str]) -> str:
        return load_snippet(repo_root, m.group(1))

    return _SNIPPET_INCLUDE.sub(repl, text)


def substitute(text: str, args: list[str], kv: dict[str, str]) -> str:
    """Substitute $1, $2, ... $ARGUMENTS and {{key}} placeholders in a single pass."""
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

    # Combined regex for both types of placeholders:
    # Group 1: \$(ARGUMENTS|\d+)
    # Group 2: {{(\w+)}}
    pattern = re.compile(r"\$(ARGUMENTS|\d+)|{{(\w+)}}")
    text = pattern.sub(repl, text)

    if missing:
        print(f"warning: missing arguments: {', '.join(missing)}", file=sys.stderr)
    return text


def _walk_traversable(root: Traversable, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively walk a Traversable, returning (relative_path, first_line) pairs."""
    items: list[tuple[str, str]] = []
    try:
        for item in sorted(root.iterdir(), key=lambda x: x.name):
            rel = f"{prefix}/{item.name}" if prefix else item.name
            if item.is_dir():
                items.extend(_walk_traversable(item, rel))
            elif not item.name.startswith("_"):
                content = item.read_text(encoding="utf-8")
                first_line = content.split("\n", 1)[0].strip()
                items.append((rel, first_line))
    except (FileNotFoundError, TypeError):
        pass
    return items


def list_snippets(repo_root: Path) -> list[tuple[str, str, bool]]:
    """List available snippets.

    Returns list of (path, first_line, is_local) tuples, sorted by path.
    """
    items: dict[str, tuple[str, bool]] = {}

    # built-ins
    try:
        pkg_root = resources.files("familiar.data.snippets")
        for rel, first_line in _walk_traversable(pkg_root):
            items[rel] = (first_line, False)
    except (FileNotFoundError, TypeError, ModuleNotFoundError):
        pass

    # local overrides
    local_dir = repo_root / ".familiar" / "snippets"
    if local_dir.is_dir():
        for f in sorted(local_dir.rglob("*")):
            if f.is_file() and not f.name.startswith("_"):
                rel = str(f.relative_to(local_dir))
                content = f.read_text(encoding="utf-8")
                first_line = content.split("\n", 1)[0].strip()
                items[rel] = (first_line, True)

    return [
        (path, first_line, is_local)
        for path, (first_line, is_local) in sorted(items.items())
    ]


def list_items(repo_root: Path, kind: str) -> list[tuple[str, str, bool]]:
    """List available conjurings or invocations.

    Returns list of (name, first_line, is_local) tuples, sorted by name.
    """
    items: dict[str, tuple[str, bool]] = {}

    # built-ins
    pkg = f"familiar.data.{kind}"
    try:
        pkg_files = resources.files(pkg)
        for item in pkg_files.iterdir():
            if item.name.endswith(".md") and not item.name.startswith("_"):
                name = item.name[:-3]
                content = item.read_text(encoding="utf-8")
                first_line = content.split("\n", 1)[0].strip()
                items[name] = (first_line, False)
    except (FileNotFoundError, TypeError):
        pass

    # local overrides
    local_dir = repo_root / ".familiar" / kind
    if local_dir.is_dir():
        for f in local_dir.glob("*.md"):
            if not f.name.startswith("_"):
                name = f.stem
                content = f.read_text(encoding="utf-8")
                first_line = content.split("\n", 1)[0].strip()
                items[name] = (first_line, True)

    return [
        (name, first_line, is_local)
        for name, (first_line, is_local) in sorted(items.items())
    ]


def compose_system(repo_root: Path, conjurings: list[str]) -> str:
    """Compose system instructions from core + selected conjurings."""
    core = load_text(repo_root, "conjurings", "core").strip()
    parts: list[str] = [core]
    for name in conjurings:
        parts.append(load_text(repo_root, "conjurings", name).strip())
    return "\n\n".join(parts)


def render_invocation(
    repo_root: Path, invocation: str, args: list[str], kv: dict[str, str]
) -> str:
    """Render an invocation with snippet inclusion and argument substitution."""
    inv = load_text(repo_root, "invocations", invocation).strip()
    inv = resolve_includes(repo_root, inv)
    return substitute(inv, args, kv)
