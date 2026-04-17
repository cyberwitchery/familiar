"""Shared plugin loading utilities."""

from __future__ import annotations

import warnings
from importlib.metadata import entry_points
from typing import Any, Callable


def load_plugins(
    group: str,
    validate: Callable[[Any], bool],
    *,
    label: str,
    invalid_msg: str = "validation failed",
) -> list[Any]:
    """Load plugins from entry points with validation.

    Args:
        group: Entry point group name.
        validate: Predicate that returns True for valid loaded objects.
        label: Human-readable label for warning messages (e.g. "linter plugin").
        invalid_msg: Message when validation fails.

    Returns:
        List of loaded and validated plugin objects.
    """
    results: list[Any] = []
    for ep in entry_points(group=group):
        try:
            obj = ep.load()
            if not validate(obj):
                warnings.warn(
                    f"{label} '{ep.name}': {invalid_msg}",
                    stacklevel=2,
                )
                continue
            results.append(obj)
        except Exception as e:
            warnings.warn(
                f"failed to load {label} '{ep.name}': {e}",
                stacklevel=2,
            )
    return results
