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


@pytest.fixture(autouse=True)
def reset_agents_cache():
    """Reset the agents cache before each test."""
    agents_module._agents_cache = None
    yield
    agents_module._agents_cache = None


class TestAgentRegistry:
    """tests for agent registry via entry points."""

    def test_load_agents_returns_dict(self):
        agents = load_agents()
        assert isinstance(agents, dict)

    def test_load_agents_includes_codex(self):
        agents = load_agents()
        assert "codex" in agents
        assert isinstance(agents["codex"], CodexAgent)

    def test_load_agents_includes_claude(self):
        agents = load_agents()
        assert "claude" in agents
        assert isinstance(agents["claude"], ClaudeAgent)

    def test_get_agents_returns_cached(self):
        agents1 = get_agents()
        agents2 = get_agents()
        assert agents1 is agents2

    def test_get_agent_returns_codex(self):
        agent = get_agent("codex")
        assert isinstance(agent, CodexAgent)

    def test_get_agent_returns_claude(self):
        agent = get_agent("claude")
        assert isinstance(agent, ClaudeAgent)

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

    def test_name(self):
        agent = CodexAgent()
        assert agent.name == "codex"

    def test_output_file(self):
        agent = CodexAgent()
        assert agent.output_file == "AGENTS.md"

    def test_supports_skills(self):
        agent = CodexAgent()
        assert agent.supports_skills() is True

    def test_skill_path(self, tmp_path):
        agent = CodexAgent()
        path = agent.skill_path(tmp_path, "refactor")
        assert path == tmp_path / ".codex" / "skills" / "refactor" / "SKILL.md"

    def test_supports_subagents(self):
        agent = CodexAgent()
        assert agent.supports_subagents() is True

    def test_subagent_path(self, tmp_path):
        agent = CodexAgent()
        path = agent.subagent_path(tmp_path, "python_sec")
        assert path == tmp_path / ".codex" / "subagents" / "python_sec" / "AGENT.md"

    def test_run_headless(self, tmp_path):
        agent = CodexAgent()
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(
            "familiar.agents.subprocess.run", return_value=mock_result
        ) as mock_run:
            result = agent.run(tmp_path, "test prompt", headless=True)
            assert result == 0
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "-C",
                str(tmp_path),
                "-",
            ]
            assert call_args[1]["input"] == "test prompt"
            assert call_args[1]["text"] is True

    def test_run_interactive(self, tmp_path):
        agent = CodexAgent()

        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = agent.run(tmp_path, "test prompt", headless=False)
            assert result == 0
            mock_call.assert_called_once_with(
                ["codex", "-C", str(tmp_path), "test prompt"]
            )

    def test_run_auto(self, tmp_path):
        agent = CodexAgent()

        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = agent.run(tmp_path, "test prompt", headless=False, auto=True)
            assert result == 0
            mock_call.assert_called_once_with(
                ["codex", "--full-auto", "-C", str(tmp_path), "test prompt"]
            )


class TestClaudeAgent:
    """tests for claude agent."""

    def test_name(self):
        agent = ClaudeAgent()
        assert agent.name == "claude"

    def test_output_file(self):
        agent = ClaudeAgent()
        assert agent.output_file == "CLAUDE.md"

    def test_supports_skills(self):
        agent = ClaudeAgent()
        assert agent.supports_skills() is True

    def test_skill_path(self, tmp_path):
        agent = ClaudeAgent()
        path = agent.skill_path(tmp_path, "review")
        assert path == tmp_path / ".claude" / "skills" / "review" / "SKILL.md"

    def test_supports_subagents(self):
        agent = ClaudeAgent()
        assert agent.supports_subagents() is True

    def test_subagent_path(self, tmp_path):
        agent = ClaudeAgent()
        path = agent.subagent_path(tmp_path, "python_sec")
        assert path == tmp_path / ".claude" / "subagents" / "python_sec" / "AGENT.md"

    def test_run_headless(self, tmp_path):
        agent = ClaudeAgent()

        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = agent.run(tmp_path, "test prompt", headless=True)
            assert result == 0
            mock_call.assert_called_once_with(
                ["claude", "-p", "test prompt"], cwd=tmp_path
            )

    def test_run_interactive(self, tmp_path):
        agent = ClaudeAgent()

        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = agent.run(tmp_path, "test prompt", headless=False)
            assert result == 0
            mock_call.assert_called_once_with(["claude", "test prompt"], cwd=tmp_path)

    def test_run_auto(self, tmp_path):
        agent = ClaudeAgent()

        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = agent.run(tmp_path, "test prompt", headless=False, auto=True)
            assert result == 0
            mock_call.assert_called_once_with(
                ["claude", "--dangerously-skip-permissions", "test prompt"],
                cwd=tmp_path,
            )

    def test_run_returns_exit_code(self, tmp_path):
        agent = ClaudeAgent()

        with patch("familiar.agents.subprocess.call", return_value=42):
            result = agent.run(tmp_path, "prompt", headless=True)
            assert result == 42
