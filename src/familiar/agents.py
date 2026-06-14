"""agent implementations for familiar."""

from __future__ import annotations

import subprocess
import warnings
from abc import ABC, abstractmethod
from pathlib import Path

from ._plugins import load_plugins


class Agent(ABC):
    """base class for AI coding agents."""

    name: str
    output_file: str
    skill_dir: str | None = None
    skill_file: str = "SKILL.md"
    subagent_dir: str | None = None
    subagent_file: str = "AGENT.md"

    @abstractmethod
    def run(
        self, repo_root: Path, prompt: str, headless: bool, auto: bool = False
    ) -> int:
        """run the agent with the given prompt."""

    def supports_skills(self) -> bool:
        """whether this agent supports reusable skill files."""
        return self.skill_dir is not None

    def skill_path(self, repo_root: Path, skill_name: str) -> Path:
        """build the skill path for a given skill name."""
        if self.skill_dir is None:
            raise ValueError(f"agent does not support skills: {self.name}")
        return repo_root / self.skill_dir / skill_name / self.skill_file

    def supports_subagents(self) -> bool:
        """whether this agent supports reusable subagent files."""
        return self.subagent_dir is not None

    def subagent_path(self, repo_root: Path, subagent_name: str) -> Path:
        """build the subagent path for a given subagent name."""
        if self.subagent_dir is None:
            raise ValueError(f"agent does not support subagents: {self.name}")
        return repo_root / self.subagent_dir / subagent_name / self.subagent_file


class CodexAgent(Agent):
    name = "codex"
    output_file = "AGENTS.md"
    skill_dir = ".codex/skills"
    subagent_dir = ".codex/subagents"

    def run(
        self, repo_root: Path, prompt: str, headless: bool, auto: bool = False
    ) -> int:
        if headless:
            cmd = ["codex"]
            if auto:
                cmd.append("--full-auto")
            cmd.extend(["exec", "--skip-git-repo-check", "-C", str(repo_root), "-"])
            proc = subprocess.run(cmd, input=prompt, text=True)
            return proc.returncode
        else:
            cmd = ["codex"]
            if auto:
                cmd.append("--full-auto")
            cmd.extend(["-C", str(repo_root), prompt])
            return subprocess.call(cmd)


class ClaudeAgent(Agent):
    name = "claude"
    output_file = "CLAUDE.md"
    skill_dir = ".claude/skills"
    subagent_dir = ".claude/subagents"

    def run(
        self, repo_root: Path, prompt: str, headless: bool, auto: bool = False
    ) -> int:
        cmd = ["claude"]
        if auto:
            cmd.append("--dangerously-skip-permissions")
        if headless:
            cmd.extend(["-p", prompt])
        else:
            cmd.append(prompt)
        return subprocess.call(cmd, cwd=repo_root)


def load_agents() -> dict[str, Agent]:
    """load all registered agent plugins via entry points.

    Returns:
        dictionary mapping agent names to Agent instances.
        plugins that fail to load are skipped with a warning.
    """
    plugins = load_plugins(
        "familiar.agents",
        lambda cls: isinstance(cls, type) and issubclass(cls, Agent),
        label="agent plugin",
        invalid_msg="not a valid Agent subclass",
    )
    agents: dict[str, Agent] = {}
    for cls in plugins:
        try:
            instance = cls()
            agents[instance.name] = instance
        except Exception as e:
            warnings.warn(
                f"failed to load agent plugin '{cls.__name__}': {e}",
                stacklevel=2,
            )
    return agents


_agents_cache: dict[str, Agent] | None = None


def get_agents() -> dict[str, Agent]:
    """get all available agents.

    returns a cached dictionary of agent name -> Agent instance.
    """
    global _agents_cache
    if _agents_cache is None:
        _agents_cache = load_agents()
    return _agents_cache


def get_agent(name: str) -> Agent:
    """get an agent by name.

    Raises:
        KeyError: if the agent name is not recognized.
    """
    agents = get_agents()
    if name not in agents:
        raise KeyError(f"unknown agent: {name}")
    return agents[name]
