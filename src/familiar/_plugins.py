"""shared plugin loading utilities."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any


def load_plugins(
    group: str,
    validate: Callable[[Any], bool],
    *,
    label: str,
    invalid_msg: str = "validation failed",
) -> list[Any]:
    """load plugins from entry points with validation.

    Args:
        group: entry point group name.
        validate: predicate that returns True for valid loaded objects.
        label: human-readable label for warning messages (e.g. "linter plugin").
        invalid_msg: message when validation fails.

    Returns:
        list of loaded and validated plugin objects.
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
        # a broken third-party entry point must not take down the cli
        except Exception as e:  # noqa: BLE001
            warnings.warn(
                f"failed to load {label} '{ep.name}': {e}",
                stacklevel=2,
            )
    return results
