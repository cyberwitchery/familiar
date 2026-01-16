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
        # TypeError: some python versions raise this for missing resources
        raise NotFoundError(f"unknown {kind.rstrip('s')}: {name}")


def substitute(text: str, args: list[str], kv: dict[str, str]) -> str:
    """Substitute $1, $2, ... $ARGUMENTS and {{key}} placeholders.

    Note: positional args are substituted before kv args, so user-supplied
    args containing {{foo}} could get expanded. This is low risk in practice.
    """
    missing: list[str] = []

    def repl(m: re.Match[str]) -> str:
        ident = m.group(1)
        if ident == "ARGUMENTS":
            return " ".join(args).strip()
        if ident.isdigit():
            idx = int(ident) - 1
            if 0 <= idx < len(args):
                return args[idx]
            missing.append(f"${ident}")
            return ""
        return m.group(0)

    text = re.sub(r"\$(ARGUMENTS|\d+)", repl, text)
    if missing:
        print(f"warning: missing arguments: {', '.join(missing)}", file=sys.stderr)
    for k, v in kv.items():
        text = text.replace(f"{{{{{k}}}}}", v)
    return text


def compose(repo_root: Path, profiles: list[str], invocation: str, args: list[str], kv: dict[str, str]) -> tuple[str, str, str]:
    """Compose system and user sections from selected profiles and invocation."""
    core = load_text(repo_root, "templates", "core").strip()
    parts: list[str] = [core]
    for p in profiles:
        parts.append(load_text(repo_root, "templates", p).strip())
    system = "\n\n".join(parts)
    inv = load_text(repo_root, "invocations", invocation).strip()
    user = substitute(inv, args, kv)
    full = f"{system}\n\n---\n\n{user}\n"
    return system, user, full
