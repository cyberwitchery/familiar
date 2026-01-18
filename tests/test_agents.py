"""tests for familiar.agents."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from familiar.agents import (
    CodexAgent,
    ClaudeAgent,
    AGENTS,
    get_agent,
)


class TestAgentRegistry:
    """tests for agent registry."""

    def test_agents_dict_has_codex(self):
        assert "codex" in AGENTS
        assert isinstance(AGENTS["codex"], CodexAgent)

    def test_agents_dict_has_claude(self):
        assert "claude" in AGENTS
        assert isinstance(AGENTS["claude"], ClaudeAgent)

    def test_get_agent_returns_codex(self):
        agent = get_agent("codex")
        assert isinstance(agent, CodexAgent)

    def test_get_agent_returns_claude(self):
        agent = get_agent("claude")
        assert isinstance(agent, ClaudeAgent)

    def test_get_agent_unknown_raises(self):
        with pytest.raises(SystemExit, match="unknown agent"):
            get_agent("nonexistent")


class TestCodexAgent:
    """tests for codex agent."""

    def test_name(self):
        agent = CodexAgent()
        assert agent.name == "codex"

    def test_output_file(self):
        agent = CodexAgent()
        assert agent.output_file == "AGENTS.md"

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
            assert call_args[0][0] == ["codex", "exec", "-C", str(tmp_path), "-"]
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


class TestClaudeAgent:
    """tests for claude agent."""

    def test_name(self):
        agent = ClaudeAgent()
        assert agent.name == "claude"

    def test_output_file(self):
        agent = ClaudeAgent()
        assert agent.output_file == "CLAUDE.md"

    def test_run_headless(self, tmp_path):
        agent = ClaudeAgent()

        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = agent.run(tmp_path, "test prompt", headless=True)
            assert result == 0
            mock_call.assert_called_once_with(["claude", "-p", "test prompt"])

    def test_run_interactive(self, tmp_path):
        agent = ClaudeAgent()

        with patch("familiar.agents.subprocess.call", return_value=0) as mock_call:
            result = agent.run(tmp_path, "test prompt", headless=False)
            assert result == 0
            mock_call.assert_called_once_with(["claude", "test prompt"])

    def test_run_returns_exit_code(self, tmp_path):
        agent = ClaudeAgent()

        with patch("familiar.agents.subprocess.call", return_value=42):
            result = agent.run(tmp_path, "prompt", headless=True)
            assert result == 42
