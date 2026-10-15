"""tests for familiar.agents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import familiar.agents as agents_module
from familiar.agents import (
    Agent,
    ClaudeAgent,
    CodexAgent,
    get_agent,
    get_agents,
    load_agents,
)
from familiar.cli import run_agent

PLUGINS_DOC = Path(__file__).resolve().parents[1] / "docs" / "plugins.md"
ROOT = str(Path("/repo"))


@pytest.fixture(autouse=True)
def reset_agents_cache():
    """Reset the agents cache before each test."""
    agents_module._agents_cache = None
    yield
    agents_module._agents_cache = None


class TestAgentRegistry:
    """tests for agent registry via entry points."""

    @pytest.mark.parametrize(
        ("name", "cls"), [("codex", CodexAgent), ("claude", ClaudeAgent)]
    )
    def test_registers_builtin_agent(self, name, cls):
        assert isinstance(load_agents()[name], cls)
        assert isinstance(get_agent(name), cls)

    def test_get_agents_returns_cached(self):
        agents1 = get_agents()
        agents2 = get_agents()
        assert agents1 is agents2

    def test_get_agent_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown agent"):
            get_agent("nonexistent")


class TestPluginLoadErrors:
    """tests for graceful handling of plugin load failures."""

    def test_invalid_class_warns(self):
        """Plugin that doesn't subclass Agent should warn."""
        mock_ep = MagicMock()
        mock_ep.name = "invalid"
        mock_ep.load.return_value = str  # not an Agent subclass

        with patch("familiar._plugins.entry_points", return_value=[mock_ep]):
            with pytest.warns(UserWarning, match="not a valid Agent subclass"):
                agents = load_agents()
            assert "invalid" not in agents

    def test_load_error_warns(self):
        """Plugin that fails to load should warn."""
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("module not found")

        with patch("familiar._plugins.entry_points", return_value=[mock_ep]):
            with pytest.warns(UserWarning, match="failed to load"):
                agents = load_agents()
            assert "broken" not in agents

    def test_instantiation_error_warns(self):
        """Plugin whose constructor fails should warn."""

        class BadAgent(Agent):
            name = "bad"
            output_file = "BAD.md"

            def __init__(self):
                raise RuntimeError("constructor failed")

            def run(self, repo_root, prompt, headless):
                pass

        mock_ep = MagicMock()
        mock_ep.name = "bad"
        mock_ep.load.return_value = BadAgent

        with patch("familiar._plugins.entry_points", return_value=[mock_ep]):
            with pytest.warns(UserWarning, match="failed to load"):
                agents = load_agents()
            assert "bad" not in agents


def _documented_agent_class() -> type[Agent]:
    blocks = re.findall(r"```python\n(.*?)```", PLUGINS_DOC.read_text(), re.DOTALL)
    source = next(block for block in blocks if "(Agent):" in block)
    namespace: dict[str, Any] = {"__name__": "my_plugin"}
    exec(source, namespace)  # noqa: S102
    agent_cls: type[Agent] = namespace["MyAgent"]
    return agent_cls


class TestDocumentedAgentPlugin:
    """tests for the agent plugin example in docs/plugins.md."""

    @pytest.mark.parametrize("auto", [False, True])
    def test_runs_through_run_agent(self, tmp_path, auto):
        agent_cls = _documented_agent_class()
        mock_ep = MagicMock()
        mock_ep.name = agent_cls.name
        mock_ep.load.return_value = agent_cls

        with (
            patch("familiar._plugins.entry_points", return_value=[mock_ep]),
            patch("subprocess.call", return_value=0) as mock_call,
        ):
            result = run_agent(
                tmp_path, agent_cls.name, "test prompt", headless=False, auto=auto
            )

        assert result == 0
        mock_call.assert_called_once()


class TestCodexAgent:
    """tests for codex agent."""

    def test_subagent_path_raises(self, tmp_path):
        agent = CodexAgent()
        with pytest.raises(ValueError, match="does not support subagents: codex"):
            agent.subagent_path(tmp_path, "python_sec")

    @pytest.mark.parametrize(
        ("headless", "auto", "argv"),
        [
            (True, False, ["codex", "exec", "--skip-git-repo-check", "-C", ROOT, "-"]),
            (False, False, ["codex", "-C", ROOT, "test prompt"]),
            (
                False,
                True,
                [
                    "codex",
                    "--ask-for-approval",
                    "on-request",
                    "--sandbox",
                    "workspace-write",
                    "-C",
                    ROOT,
                    "test prompt",
                ],
            ),
            (
                True,
                True,
                [
                    "codex",
                    "exec",
                    "--sandbox",
                    "workspace-write",
                    "--skip-git-repo-check",
                    "-C",
                    ROOT,
                    "-",
                ],
            ),
        ],
        ids=["headless", "interactive", "auto", "headless-auto"],
    )
    def test_run(self, headless, auto, argv):
        with (
            patch(
                "familiar.agents.subprocess.run", return_value=MagicMock(returncode=0)
            ) as mock_run,
            patch("familiar.agents.subprocess.call", return_value=0) as mock_call,
        ):
            result = CodexAgent().run(
                Path(ROOT), "test prompt", headless=headless, auto=auto
            )
        assert result == 0
        if headless:
            mock_run.assert_called_once_with(
                argv, input="test prompt", text=True, check=False
            )
            mock_call.assert_not_called()
        else:
            mock_call.assert_called_once_with(argv)
            mock_run.assert_not_called()


class TestClaudeAgent:
    """tests for claude agent."""

    @pytest.mark.parametrize(
        ("headless", "auto", "argv"),
        [
            (True, False, ["claude", "-p", "test prompt"]),
            (False, False, ["claude", "test prompt"]),
            (False, True, ["claude", "--dangerously-skip-permissions", "test prompt"]),
        ],
        ids=["headless", "interactive", "auto"],
    )
    def test_run(self, tmp_path, headless, auto, argv):
        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = ClaudeAgent().run(
                tmp_path, "test prompt", headless=headless, auto=auto
            )
        assert result == 0
        mock_call.assert_called_once_with(argv, cwd=tmp_path)
