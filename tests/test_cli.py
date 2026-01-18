"""tests for familiar.cli."""
from __future__ import annotations

import pytest
from unittest.mock import patch
import argparse

from familiar.cli import (
    find_repo_root,
    ensure_fam_dir,
    config_path,
    load_config,
    save_config,
    write_instruction,
    parse_kv,
    run_agent,
    cmd_conjure,
    cmd_invoke,
    cmd_list,
)


class TestFindRepoRoot:
    """tests for finding git repo root."""

    def test_finds_git_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        subdir = tmp_path / "a" / "b" / "c"
        subdir.mkdir(parents=True)
        result = find_repo_root(subdir)
        assert result == tmp_path

    def test_returns_start_if_no_git(self, tmp_path):
        subdir = tmp_path / "a" / "b"
        subdir.mkdir(parents=True)
        result = find_repo_root(subdir)
        assert result == subdir.resolve()


class TestEnsureFamDir:
    """tests for ensuring .familiar directory exists."""

    def test_creates_directory(self, tmp_path):
        result = ensure_fam_dir(tmp_path)
        assert result == tmp_path / ".familiar"
        assert result.is_dir()

    def test_idempotent(self, tmp_path):
        ensure_fam_dir(tmp_path)
        result = ensure_fam_dir(tmp_path)
        assert result.is_dir()


class TestConfigPath:
    """tests for config path generation."""

    def test_returns_correct_path(self, tmp_path):
        result = config_path(tmp_path, "claude")
        assert result == tmp_path / ".familiar" / "claude.json"
        assert (tmp_path / ".familiar").is_dir()


class TestLoadSaveConfig:
    """tests for config persistence."""

    def test_load_missing_returns_empty(self, tmp_path):
        result = load_config(tmp_path, "claude")
        assert result == {}

    def test_save_and_load(self, tmp_path):
        cfg = {"conjurings": ["rust", "sec"]}
        save_config(tmp_path, "claude", cfg)
        result = load_config(tmp_path, "claude")
        assert result == cfg

    def test_save_overwrites(self, tmp_path):
        save_config(tmp_path, "codex", {"conjurings": ["old"]})
        save_config(tmp_path, "codex", {"conjurings": ["new"]})
        result = load_config(tmp_path, "codex")
        assert result == {"conjurings": ["new"]}


class TestWriteInstruction:
    """tests for writing instruction files."""

    def test_writes_claude_md(self, tmp_path):
        write_instruction(tmp_path, "claude", "system prompt")
        assert (tmp_path / "CLAUDE.md").read_text() == "system prompt\n"

    def test_writes_agents_md(self, tmp_path):
        write_instruction(tmp_path, "codex", "agent prompt")
        assert (tmp_path / "AGENTS.md").read_text() == "agent prompt\n"

    def test_strips_whitespace(self, tmp_path):
        write_instruction(tmp_path, "claude", "  content  \n\n")
        assert (tmp_path / "CLAUDE.md").read_text() == "content\n"


class TestParseKv:
    """tests for key-value parsing."""

    def test_parses_pairs(self):
        result = parse_kv(["key=value", "foo=bar"])
        assert result == {"key": "value", "foo": "bar"}

    def test_handles_equals_in_value(self):
        result = parse_kv(["key=a=b=c"])
        assert result == {"key": "a=b=c"}

    def test_strips_whitespace(self):
        result = parse_kv(["  key  =  value  "])
        assert result == {"key": "value"}

    def test_empty_list(self):
        result = parse_kv([])
        assert result == {}

    def test_missing_equals_raises(self):
        with pytest.raises(SystemExit, match="expected key=value"):
            parse_kv(["invalid"])


class TestRunAgent:
    """tests for agent execution."""

    def test_missing_binary_raises(self, tmp_path):
        with patch("familiar.agents.subprocess.call", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit, match="claude not found in PATH"):
                run_agent(tmp_path, "claude", "prompt", headless=True)

    def test_returns_exit_code(self, tmp_path):
        with patch("familiar.agents.subprocess.call", return_value=42):
            result = run_agent(tmp_path, "claude", "prompt", headless=True)
            assert result == 42


class TestCmdConjure:
    """tests for conjure command."""

    def test_writes_output_file(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            conjurings=["python"],
            into=str(tmp_path),
        )
        result = cmd_conjure(args)
        assert result == 0
        assert (tmp_path / "CLAUDE.md").exists()
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "python" in content.lower()

    def test_saves_config(self, tmp_path):
        args = argparse.Namespace(
            agent="codex",
            conjurings=["rust", "sec"],
            into=str(tmp_path),
        )
        cmd_conjure(args)
        cfg = load_config(tmp_path, "codex")
        assert cfg == {"conjurings": ["rust", "sec"]}

    def test_unknown_profile_raises(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            conjurings=["nonexistent"],
            into=str(tmp_path),
        )
        with pytest.raises(SystemExit, match="unknown template"):
            cmd_conjure(args)


class TestCmdInvoke:
    """tests for invoke command."""

    def test_uses_saved_conjurings(self, tmp_path):
        # save config first
        save_config(tmp_path, "claude", {"conjurings": ["python"]})

        with patch("familiar.cli.run_agent", return_value=0) as mock_run:
            args = argparse.Namespace(
                agent="claude",
                invocation="explain",
                into=str(tmp_path),
                headless=True,
                conjurings=None,
                kv=None,
                inv_args=["some code"],
            )
            result = cmd_invoke(args)
            assert result == 0
            # check that the prompt includes python profile
            call_args = mock_run.call_args
            prompt = call_args[0][2]
            assert "python" in prompt.lower()

    def test_override_conjurings(self, tmp_path):
        save_config(tmp_path, "claude", {"conjurings": ["python"]})

        with patch("familiar.cli.run_agent", return_value=0) as mock_run:
            args = argparse.Namespace(
                agent="claude",
                invocation="explain",
                into=str(tmp_path),
                headless=True,
                conjurings=["rust"],
                kv=None,
                inv_args=[],
            )
            cmd_invoke(args)
            prompt = mock_run.call_args[0][2]
            assert "rust" in prompt.lower()
            assert "python" not in prompt.lower() or "rust" in prompt.lower()

    def test_warns_no_conjurings(self, tmp_path, capsys):
        with patch("familiar.cli.run_agent", return_value=0):
            args = argparse.Namespace(
                agent="claude",
                invocation="explain",
                into=str(tmp_path),
                headless=True,
                conjurings=None,
                kv=None,
                inv_args=[],
            )
            cmd_invoke(args)
            captured = capsys.readouterr()
            assert "no conjurings specified" in captured.err

    def test_unknown_invocation_raises(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            invocation="nonexistent",
            into=str(tmp_path),
            headless=True,
            conjurings=[],
            kv=None,
            inv_args=[],
        )
        with pytest.raises(SystemExit, match="unknown invocation"):
            cmd_invoke(args)

    def test_kv_args_passed(self, tmp_path):
        # create custom invocation that uses kv
        inv_dir = tmp_path / ".familiar" / "invocations"
        inv_dir.mkdir(parents=True)
        (inv_dir / "custom.md").write_text("value is {{mykey}}")

        with patch("familiar.cli.run_agent", return_value=0) as mock_run:
            args = argparse.Namespace(
                agent="claude",
                invocation="custom",
                into=str(tmp_path),
                headless=True,
                conjurings=[],
                kv=["mykey=myvalue"],
                inv_args=[],
            )
            cmd_invoke(args)
            prompt = mock_run.call_args[0][2]
            assert "value is myvalue" in prompt


class TestCmdList:
    """tests for list command."""

    def test_list_conjurings(self, tmp_path, capsys):
        args = argparse.Namespace(
            kind="conjurings",
            into=str(tmp_path),
            verbose=False,
        )
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "core" in captured.out
        assert "python" in captured.out

    def test_list_invocations(self, tmp_path, capsys):
        args = argparse.Namespace(
            kind="invocations",
            into=str(tmp_path),
            verbose=False,
        )
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "explain" in captured.out
        assert "refactor" in captured.out

    def test_list_verbose(self, tmp_path, capsys):
        args = argparse.Namespace(
            kind="conjurings",
            into=str(tmp_path),
            verbose=True,
        )
        cmd_list(args)
        captured = capsys.readouterr()
        # verbose mode includes first line after colon
        assert ":" in captured.out

    def test_list_local_marked(self, tmp_path, capsys):
        templates = tmp_path / ".familiar" / "templates"
        templates.mkdir(parents=True)
        (templates / "custom.md").write_text("# my custom profile")

        args = argparse.Namespace(
            kind="conjurings",
            into=str(tmp_path),
            verbose=False,
        )
        cmd_list(args)
        captured = capsys.readouterr()
        assert "custom (local)" in captured.out

    def test_list_override_marked_local(self, tmp_path, capsys):
        templates = tmp_path / ".familiar" / "templates"
        templates.mkdir(parents=True)
        (templates / "python.md").write_text("# custom python")

        args = argparse.Namespace(
            kind="conjurings",
            into=str(tmp_path),
            verbose=False,
        )
        cmd_list(args)
        captured = capsys.readouterr()
        assert "python (local)" in captured.out
