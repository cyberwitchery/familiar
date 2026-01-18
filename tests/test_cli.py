"""tests for familiar.cli."""

from __future__ import annotations

import pytest
from unittest.mock import patch
import argparse

from familiar.cli import (
    find_repo_root,
    write_instruction,
    parse_kv,
    run_agent,
    cmd_conjure,
    cmd_invoke,
    cmd_list,
    CliError,
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
        with pytest.raises(CliError, match="invalid argument"):
            parse_kv(["invalid"])


class TestRunAgent:
    """tests for agent execution."""

    def test_missing_binary_raises(self, tmp_path):
        with patch("familiar.agents.subprocess.call", side_effect=FileNotFoundError):
            with pytest.raises(CliError, match="claude not found in PATH"):
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

    def test_unknown_profile_raises(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            conjurings=["nonexistent"],
            into=str(tmp_path),
        )
        with pytest.raises(CliError, match="unknown template"):
            cmd_conjure(args)


class TestCmdInvoke:
    """tests for invoke command."""

    def test_runs_agent_with_invocation(self, tmp_path):
        with patch("familiar.cli.run_agent", return_value=0) as mock_run:
            args = argparse.Namespace(
                agent="claude",
                invocation="explain",
                into=str(tmp_path),
                headless=True,
                kv=None,
                inv_args=["some code"],
            )
            result = cmd_invoke(args)
            assert result == 0
            # check that the prompt is the rendered invocation
            call_args = mock_run.call_args
            prompt = call_args[0][2]
            assert "explain" in prompt.lower()

    def test_unknown_invocation_raises(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            invocation="nonexistent",
            into=str(tmp_path),
            headless=True,
            kv=None,
            inv_args=[],
        )
        with pytest.raises(CliError, match="unknown invocation"):
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
                kv=["mykey=myvalue"],
                inv_args=[],
            )
            cmd_invoke(args)
            prompt = mock_run.call_args[0][2]
            assert "value is myvalue" in prompt


class TestCmdList:
    """tests for list command."""

    def test_list_both(self, tmp_path, capsys):
        args = argparse.Namespace(
            kind=None,
            into=str(tmp_path),
            verbose=False,
        )
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "conjurings:" in captured.out
        assert "invocations:" in captured.out
        assert "core" in captured.out
        assert "explain" in captured.out

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
