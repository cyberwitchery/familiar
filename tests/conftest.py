"""shared fixtures for familiar tests."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def without_blocking() -> Callable[..., Any]:
    """call a function, failing the test instead of hanging when it blocks."""

    def call(fn: Callable[..., Any], *args: Any) -> Any:
        outcome: dict[str, Any] = {}

        def run() -> None:
            try:
                outcome["value"] = fn(*args)
            except Exception as e:  # noqa: BLE001
                outcome["error"] = e

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout=10)
        if worker.is_alive():
            pytest.fail(f"{fn.__name__} blocked")
        if "error" in outcome:
            raise outcome["error"]
        return outcome["value"]

    return call
