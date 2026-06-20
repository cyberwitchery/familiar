"""tests for familiar.cli."""

from __future__ import annotations

import pytest
import subprocess
from unittest.mock import patch
import argparse

from familiar.cli import (
    _remove_worktree,
    _resolve_agent,
    _write_file,
    find_repo_root,
    create_worktree,
    write_instruction,
    write_skill,
    write_subagent,
    parse_kv,
    run_agent,
    main,
    cmd_conjure,
    cmd_invoke,
    cmd_list,
    cmd_lint,
    CliError,
)


class TestVersion:
    """tests for --version flag."""

    def test_version_prints_and_exits(self, capsys):
        with pytest.raises(SystemExit, match="0"):
            with patch("sys.argv", ["familiar", "--version"]):
                main()
        captured = capsys.readouterr()
        assert "familiar" in captured.out
        # version string should look like a semver
        assert any(c.isdigit() for c in captured.out)


class TestCreateWorktree:
    """tests for git worktree creation."""

    def test_create_worktree_success(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            # mock_run needs to be called twice: once for rev-parse, once for worktree add
            mock_run.return_value = argparse.Namespace(returncode=0)

            # We need to mock os.rmdir because the tmpdir won't actually exist
            with patch("os.rmdir"):
                result = create_worktree(tmp_path)
                assert "familiar-" in str(result)
                assert mock_run.call_count == 2

    def test_create_worktree_not_git_raises(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(CliError, match="not a git repository"):
                create_worktree(tmp_path)

    def test_create_worktree_fail_raises(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            # First call (rev-parse) succeeds
            # Second call (worktree add) fails
            mock_run.side_effect = [
                argparse.Namespace(returncode=0),
                subprocess.CalledProcessError(1, "git", stderr=b"already exists"),
            ]
            with patch("os.rmdir"):
                with pytest.raises(CliError, match="failed to create git worktree"):
                    create_worktree(tmp_path)


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


class TestResolveAgent:
    """tests for _resolve_agent helper."""

    def test_returns_known_agent(self):
        agent = _resolve_agent("claude")
        assert agent.name == "claude"

    def test_unknown_agent_raises(self):
        with pytest.raises(CliError, match="unknown agent"):
            _resolve_agent("nonexistent")

    def test_unknown_agent_includes_hint(self):
        with pytest.raises(CliError) as exc_info:
            _resolve_agent("nonexistent")
        assert exc_info.value.hint is not None
        assert "valid agents" in exc_info.value.hint


class TestWriteFile:
    """tests for _write_file helper."""

    def test_writes_content(self, tmp_path):
        dest = tmp_path / "out.txt"
        _write_file(dest, "hello\n")
        assert dest.read_text() == "hello\n"

    def test_creates_parent_dirs(self, tmp_path):
        dest = tmp_path / "a" / "b" / "out.txt"
        _write_file(dest, "nested\n")
        assert dest.read_text() == "nested\n"

    def test_oserror_without_label(self, tmp_path):
        dest = tmp_path / "out.txt"
        with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
            with pytest.raises(CliError, match="cannot write .*/out.txt"):
                _write_file(dest, "content")

    def test_oserror_with_label(self, tmp_path):
        dest = tmp_path / "out.txt"
        with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
            with pytest.raises(CliError, match="cannot write skill .*/out.txt"):
                _write_file(dest, "content", label="skill")


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


class TestRemoveWorktree:
    """tests for git worktree removal."""

    def test_warns_on_nonzero_return_code(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = argparse.Namespace(
                returncode=1, stderr=b"worktree not found"
            )
            with pytest.warns(UserWarning, match="failed to remove worktree"):
                _remove_worktree(tmp_path, tmp_path / "wt")

    def test_no_warning_on_success(self, tmp_path, recwarn):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = argparse.Namespace(returncode=0, stderr=b"")
            _remove_worktree(tmp_path, tmp_path / "wt")
            assert len(recwarn) == 0

    def test_silent_on_missing_git(self, tmp_path, recwarn):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            _remove_worktree(tmp_path, tmp_path / "wt")
            assert len(recwarn) == 0


class TestWriteFailures:
    """tests for write error handling."""

    def test_write_instruction_permission_denied(self, tmp_path):
        with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
            with pytest.raises(CliError, match="cannot write"):
                write_instruction(tmp_path, "claude", "content")

    def test_write_skill_permission_denied(self, tmp_path):
        with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
            with pytest.raises(CliError, match="cannot write skill"):
                write_skill(tmp_path, "claude", "explain", "my-skill", "prompt")

    def test_write_subagent_permission_denied(self, tmp_path):
        with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
            with pytest.raises(CliError, match="cannot write subagent"):
                write_subagent(tmp_path, "claude", ["python"], "my-subagent", "system")


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
            save_subagent=False,
            subagent_name=None,
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
            save_subagent=False,
            subagent_name=None,
        )
        with pytest.raises(CliError, match="unknown conjuring"):
            cmd_conjure(args)

    def test_writes_subagent_for_claude(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            conjurings=["python", "sec"],
            into=str(tmp_path),
            save_subagent=True,
            subagent_name=None,
        )
        result = cmd_conjure(args)
        assert result == 0
        subagent = tmp_path / ".claude" / "subagents" / "python_sec" / "AGENT.md"
        assert subagent.exists()
        content = subagent.read_text()
        assert "conjurings: python, sec" in content
        assert "agent: claude" in content

    def test_writes_subagent_for_codex_with_custom_name(self, tmp_path):
        args = argparse.Namespace(
            agent="codex",
            conjurings=["rust", "infra"],
            into=str(tmp_path),
            save_subagent=True,
            subagent_name="ship_ops",
        )
        result = cmd_conjure(args)
        assert result == 0
        subagent = tmp_path / ".codex" / "subagents" / "ship_ops" / "AGENT.md"
        assert subagent.exists()
        content = subagent.read_text()
        assert "conjurings: rust, infra" in content
        assert "agent: codex" in content

    def test_invalid_subagent_name_raises(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            conjurings=["python"],
            into=str(tmp_path),
            save_subagent=True,
            subagent_name="Not Valid",
        )
        with pytest.raises(CliError, match="invalid subagent name"):
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
                auto=False,
                dry_run=False,
                kv=None,
                inv_args=["some code"],
                worktree=False,
                save_skill=False,
                skill_name=None,
            )
            result = cmd_invoke(args)
            assert result == 0
            call_args = mock_run.call_args
            prompt = call_args[0][2]
            assert "explain" in prompt.lower()

    def test_unknown_invocation_raises(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            invocation="nonexistent",
            into=str(tmp_path),
            headless=True,
            auto=False,
            dry_run=False,
            kv=None,
            inv_args=[],
            worktree=False,
            save_skill=False,
            skill_name=None,
        )
        with pytest.raises(CliError, match="unknown invocation"):
            cmd_invoke(args)

    def test_kv_args_passed(self, tmp_path):
        inv_dir = tmp_path / ".familiar" / "invocations"
        inv_dir.mkdir(parents=True)
        (inv_dir / "custom.md").write_text("value is {{mykey}}")

        with patch("familiar.cli.run_agent", return_value=0) as mock_run:
            args = argparse.Namespace(
                agent="claude",
                invocation="custom",
                into=str(tmp_path),
                headless=True,
                auto=False,
                dry_run=False,
                kv=["mykey=myvalue"],
                inv_args=[],
                worktree=False,
                save_skill=False,
                skill_name=None,
            )
            cmd_invoke(args)
            prompt = mock_run.call_args[0][2]
            assert "value is myvalue" in prompt

    def test_dry_run_prints_prompt(self, tmp_path, capsys):
        args = argparse.Namespace(
            agent="claude",
            invocation="explain",
            into=str(tmp_path),
            headless=False,
            auto=False,
            dry_run=True,
            kv=None,
            inv_args=["some code"],
            worktree=False,
            save_skill=False,
            skill_name=None,
        )
        result = cmd_invoke(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "explain" in captured.out.lower()

    def test_dry_run_does_not_run_agent(self, tmp_path):
        with patch("familiar.cli.run_agent") as mock_run:
            args = argparse.Namespace(
                agent="claude",
                invocation="explain",
                into=str(tmp_path),
                headless=False,
                auto=False,
                dry_run=True,
                kv=None,
                inv_args=[],
                worktree=False,
                save_skill=False,
                skill_name=None,
            )
            cmd_invoke(args)
            mock_run.assert_not_called()

    def test_invoke_with_worktree(self, tmp_path):
        with patch(
            "familiar.cli.create_worktree", return_value=tmp_path / "wt"
        ) as mock_wt:
            with patch("familiar.cli.run_agent", return_value=0) as mock_run:
                with patch("shutil.copy2") as mock_copy:
                    (tmp_path / "CLAUDE.md").write_text("instr")

                    args = argparse.Namespace(
                        agent="claude",
                        invocation="explain",
                        into=str(tmp_path),
                        headless=True,
                        auto=False,
                        dry_run=False,
                        kv=None,
                        inv_args=[],
                        worktree=True,
                        save_skill=False,
                        skill_name=None,
                    )
                    result = cmd_invoke(args)
                    assert result == 0
                    mock_wt.assert_called_once()
                    assert mock_run.call_args[0][0] == tmp_path / "wt"
                    mock_copy.assert_called_once()

    def test_invoke_worktree_cleaned_up_on_error(self, tmp_path):
        with patch("familiar.cli.create_worktree", return_value=tmp_path / "wt"):
            with patch("familiar.cli.run_agent", side_effect=RuntimeError("boom")):
                with patch("familiar.cli._remove_worktree") as mock_remove:
                    args = argparse.Namespace(
                        agent="claude",
                        invocation="explain",
                        into=str(tmp_path),
                        headless=True,
                        auto=False,
                        dry_run=False,
                        kv=None,
                        inv_args=[],
                        worktree=True,
                        save_skill=False,
                        skill_name=None,
                    )
                    with pytest.raises(RuntimeError, match="boom"):
                        cmd_invoke(args)
                    mock_remove.assert_called_once()

    def test_invoke_save_skill_claude(self, tmp_path):
        with patch("familiar.cli.run_agent") as mock_run:
            args = argparse.Namespace(
                agent="claude",
                invocation="explain",
                into=str(tmp_path),
                headless=True,
                auto=False,
                dry_run=False,
                kv=None,
                inv_args=["some code"],
                worktree=False,
                save_skill=True,
                skill_name=None,
            )
            result = cmd_invoke(args)
            assert result == 0
            skill = tmp_path / ".claude" / "skills" / "explain" / "SKILL.md"
            assert skill.exists()
            content = skill.read_text()
            assert "invocation: explain" in content
            assert "agent: claude" in content
            mock_run.assert_not_called()

    def test_invoke_save_skill_codex_custom_name(self, tmp_path):
        with patch("familiar.cli.run_agent") as mock_run:
            args = argparse.Namespace(
                agent="codex",
                invocation="refactor",
                into=str(tmp_path),
                headless=True,
                auto=False,
                dry_run=False,
                kv=None,
                inv_args=["src/foo.py"],
                worktree=False,
                save_skill=True,
                skill_name="cleanup_refactor",
            )
            result = cmd_invoke(args)
            assert result == 0
            skill = tmp_path / ".codex" / "skills" / "cleanup_refactor" / "SKILL.md"
            assert skill.exists()
            content = skill.read_text()
            assert "invocation: refactor" in content
            assert "agent: codex" in content
            mock_run.assert_not_called()

    def test_invoke_save_skill_invalid_name(self, tmp_path):
        args = argparse.Namespace(
            agent="claude",
            invocation="explain",
            into=str(tmp_path),
            headless=True,
            auto=False,
            dry_run=False,
            kv=None,
            inv_args=["some code"],
            worktree=False,
            save_skill=True,
            skill_name="Not Valid",
        )
        with pytest.raises(CliError, match="invalid skill name"):
            cmd_invoke(args)


class TestCmdList:
    """tests for list command."""

    def test_list_all(self, tmp_path, capsys):
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
        assert "snippets:" in captured.out
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
        assert ":" in captured.out

    def test_list_local_marked(self, tmp_path, capsys):
        templates = tmp_path / ".familiar" / "conjurings"
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
        templates = tmp_path / ".familiar" / "conjurings"
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

    def test_list_snippets(self, tmp_path, capsys):
        args = argparse.Namespace(
            kind="snippets",
            into=str(tmp_path),
            verbose=False,
        )
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "python/pyproject.toml" in captured.out
        assert "rust/Cargo.toml" in captured.out


class TestCmdLint:
    """tests for lint command."""

    def test_lint_builtins_pass(self, tmp_path, capsys):
        args = argparse.Namespace(
            into=str(tmp_path),
            errors_only=False,
        )
        result = cmd_lint(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "all checks passed" in captured.out

    def test_lint_with_warning(self, tmp_path, capsys):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "bad.md").write_text("no heading here")

        args = argparse.Namespace(
            into=str(tmp_path),
            errors_only=False,
        )
        result = cmd_lint(args)
        assert result == 0  # warnings don't cause failure
        captured = capsys.readouterr()
        assert "warning" in captured.err
        assert "heading" in captured.err

    def test_lint_with_error(self, tmp_path, capsys):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "empty.md").write_text("")

        args = argparse.Namespace(
            into=str(tmp_path),
            errors_only=False,
        )
        result = cmd_lint(args)
        assert result == 1  # errors cause failure
        captured = capsys.readouterr()
        assert "error" in captured.err

    def test_lint_errors_only(self, tmp_path, capsys):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "bad.md").write_text("no heading here")

        args = argparse.Namespace(
            into=str(tmp_path),
            errors_only=True,
        )
        result = cmd_lint(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "all checks passed" in captured.out
