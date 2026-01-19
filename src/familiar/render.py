"""Render system and user prompts from templates and invocations."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from importlib import resources

_VALID_NAME = re.compile(r"^[a-z0-9_-]+$")


class NotFoundError(Exception):
    """Raised when a template or invocation is not found."""


def load_text(repo_root: Path, kind: str, name: str) -> str:
    """Load a template or invocation; local overrides in .familiar override package data."""
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


def list_items(repo_root: Path, kind: str) -> list[tuple[str, str, bool]]:
    """List available templates or invocations.

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
    core = load_text(repo_root, "templates", "core").strip()
    parts: list[str] = [core]
    for name in conjurings:
        parts.append(load_text(repo_root, "templates", name).strip())
    return "\n\n".join(parts)


def render_invocation(
    repo_root: Path, invocation: str, args: list[str], kv: dict[str, str]
) -> str:
    """Render an invocation with argument substitution."""
    inv = load_text(repo_root, "invocations", invocation).strip()
    return substitute(inv, args, kv)
