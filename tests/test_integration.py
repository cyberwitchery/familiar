"""integration tests for familiar cli."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class TestConjureIntegration:
    """integration tests for conjure command."""

    def test_conjure_creates_claude_md(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "conjure", "claude", "python", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "wrote instructions for claude" in result.stdout

        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "python" in content.lower()

    def test_conjure_creates_agents_md(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "conjure", "codex", "rust", "sec", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text()
        assert "rust" in content.lower()
        assert "sec" in content.lower()

    def test_conjure_persists_config(self, tmp_path):
        subprocess.run(
            [sys.executable, "-m", "familiar.cli", "conjure", "claude", "python", "infra", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )

        config_file = tmp_path / ".familiar" / "claude.json"
        assert config_file.exists()
        import json
        config = json.loads(config_file.read_text())
        assert config["profiles"] == ["python", "infra"]

    def test_conjure_unknown_profile_fails(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "conjure", "claude", "nonexistent", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "unknown template" in result.stderr


class TestInvokeIntegration:
    """integration tests for invoke command (without actually running agents)."""

    def test_invoke_unknown_invocation_fails(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "invoke", "claude", "nonexistent", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "unknown invocation" in result.stderr

    def test_invoke_invalid_kv_fails(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "invoke", "claude", "explain", "--kv", "invalid", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "expected key=value" in result.stderr


class TestHelpIntegration:
    """integration tests for help output."""

    def test_main_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "conjure" in result.stdout
        assert "invoke" in result.stdout

    def test_conjure_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "conjure", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "profiles" in result.stdout

    def test_invoke_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "invoke", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "invocation" in result.stdout
        assert "--headless" in result.stdout
