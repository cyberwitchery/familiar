"""Agent implementations for familiar."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class Agent(ABC):
    """Base class for AI coding agents."""

    name: str
    output_file: str

    @abstractmethod
    def run(self, repo_root: Path, prompt: str, headless: bool) -> int:
        """Run the agent with the given prompt."""


class CodexAgent(Agent):
    name = "codex"
    output_file = "AGENTS.md"

    def run(self, repo_root: Path, prompt: str, headless: bool) -> int:
        if headless:
            cmd = ["codex", "exec", "-C", str(repo_root), "-"]
            proc = subprocess.run(cmd, input=prompt, text=True)
            return proc.returncode
        else:
            cmd = ["codex", "-C", str(repo_root), prompt]
            return subprocess.call(cmd)


class ClaudeAgent(Agent):
    name = "claude"
    output_file = "CLAUDE.md"

    def run(self, repo_root: Path, prompt: str, headless: bool) -> int:
        # claude cli doesn't support a working directory flag like codex's -C;
        # it uses cwd automatically, so repo_root is unused here
        if headless:
            cmd = ["claude", "-p", prompt]
        else:
            cmd = ["claude", prompt]
        return subprocess.call(cmd)


AGENTS: dict[str, Agent] = {
    "codex": CodexAgent(),
    "claude": ClaudeAgent(),
}


def get_agent(name: str) -> Agent:
    """Get an agent by name.

    Raises:
        KeyError: if the agent name is not recognized.
    """
    if name not in AGENTS:
        raise KeyError(f"unknown agent: {name}")
    return AGENTS[name]
