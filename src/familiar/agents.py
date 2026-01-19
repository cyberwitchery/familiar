"""Agent implementations for familiar."""

from __future__ import annotations

import subprocess
import warnings
from abc import ABC, abstractmethod
from importlib.metadata import entry_points
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
        if headless:
            cmd = ["claude", "-p", prompt]
        else:
            cmd = ["claude", prompt]
        return subprocess.call(cmd, cwd=repo_root)


def load_agents() -> dict[str, Agent]:
    """Load all registered agent plugins via entry points.

    Returns:
        Dictionary mapping agent names to Agent instances.
        Plugins that fail to load are skipped with a warning.
    """
    agents: dict[str, Agent] = {}
    eps = entry_points(group="familiar.agents")

    for ep in eps:
        try:
            cls = ep.load()
            if not (isinstance(cls, type) and issubclass(cls, Agent)):
                warnings.warn(
                    f"agent plugin '{ep.name}': not a valid Agent subclass",
                    stacklevel=2,
                )
                continue
            instance = cls()
            agents[instance.name] = instance
        except Exception as e:
            warnings.warn(
                f"failed to load agent plugin '{ep.name}': {e}",
                stacklevel=2,
            )

    return agents


_agents_cache: dict[str, Agent] | None = None


def get_agents() -> dict[str, Agent]:
    """Get all available agents.

    Returns a cached dictionary of agent name -> Agent instance.
    """
    global _agents_cache
    if _agents_cache is None:
        _agents_cache = load_agents()
    return _agents_cache


def get_agent(name: str) -> Agent:
    """Get an agent by name.

    Raises:
        KeyError: if the agent name is not recognized.
    """
    agents = get_agents()
    if name not in agents:
        raise KeyError(f"unknown agent: {name}")
    return agents[name]
