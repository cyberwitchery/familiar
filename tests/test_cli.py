"""tests for familiar.cli."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from importlib.metadata import version
from unittest.mock import patch

import pytest

from familiar.cli import (
    CliError,
    _remove_worktree,
    _resolve_agent,
    _write_file,
    _yaml_string,
    cmd_conjure,
    cmd_invoke,
    cmd_lint,
    cmd_list,
    create_worktree,
    find_repo_root,
    main,
    parse_kv,
    run_agent,
    write_instruction,
    write_skill,
    write_subagent,
)
from familiar.render import compose_system, list_items, render_invocation


def _read_frontmatter(path):
    yaml = pytest.importorskip("yaml")
    head, sep, body = path.read_text(encoding="utf-8").partition("\n---\n")
    assert head.startswith("---\n")
    assert sep
    return yaml.safe_load(head[4:]), body


class TestVersion:
    """tests for --version flag."""

    def test_version_prints_and_exits(self, capsys):
        with (
            pytest.raises(SystemExit, match="0"),
            patch("sys.argv", ["familiar", "--version"]),
        ):
            main()
        captured = capsys.readouterr()
        assert captured.out == f"familiar {version('familiar-cli')}\n"


class TestCreateWorktree:
    """tests for git worktree creation."""

    def test_create_worktree_success(self, tmp_path):
        # We need to mock os.rmdir because the tmpdir won't actually exist
        with patch("subprocess.run") as mock_run, patch("os.rmdir"):
            # mock_run needs to be called twice: once for rev-parse, once for worktree add
            mock_run.return_value = argparse.Namespace(returncode=0)

            result = create_worktree(tmp_path)
            assert "familiar-" in str(result)
            assert mock_run.call_count == 2
            assert mock_run.call_args_list[1].args[0] == [
                "git",
                "-C",
                str(tmp_path),
                "worktree",
                "add",
                "--detach",
                str(result),
                "HEAD",
            ]

    def test_create_worktree_not_git_raises(self, tmp_path):
        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(CliError, match="not a git repository"),
        ):
            create_worktree(tmp_path)

    def test_create_worktree_fail_raises(self, tmp_path):
        with patch("subprocess.run") as mock_run, patch("os.rmdir"):
            # First call (rev-parse) succeeds
            # Second call (worktree add) fails
            mock_run.side_effect = [
                argparse.Namespace(returncode=0),
                subprocess.CalledProcessError(1, "git", stderr=b"already exists"),
            ]
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

    def test_unknown_agent_raises_with_hint(self):
        with pytest.raises(CliError, match="unknown agent: nonexistent") as exc_info:
            _resolve_agent("nonexistent")
        hint = exc_info.value.hint
        assert hint is not None
        assert hint.startswith("valid agents: ")
        assert "claude" in hint
        assert "codex" in hint


class TestWriteFile:
    """tests for _write_file helper."""

    def test_creates_parent_dirs(self, tmp_path):
        dest = tmp_path / "a" / "b" / "out.txt"
        _write_file(dest, "nested\n")
        assert dest.read_text() == "nested\n"


class TestWriteInstruction:
    """tests for writing instruction files."""

    @pytest.mark.parametrize(
        ("agent", "filename"), [("claude", "CLAUDE.md"), ("codex", "AGENTS.md")]
    )
    def test_writes_instruction_file(self, tmp_path, agent, filename):
        write_instruction(tmp_path, agent, "system prompt")
        assert (tmp_path / filename).read_text() == "system prompt\n"

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

    @pytest.mark.parametrize(
        ("write", "message"),
        [
            (
                lambda root: write_instruction(root, "claude", "content"),
                r"^cannot write /.*/CLAUDE\.md: denied$",
            ),
            (
                lambda root: write_skill(root, "claude", "explain", "my-skill", "p"),
                r"^cannot write skill /.*/SKILL\.md: denied$",
            ),
            (
                lambda root: write_subagent(
                    root, "claude", ["python"], "my-subagent", "system"
                ),
                r"^cannot write subagent /.*/my-subagent\.md: denied$",
            ),
        ],
        ids=["instruction", "skill", "subagent"],
    )
    def test_permission_denied(self, tmp_path, write, message):
        with (
            patch("pathlib.Path.write_text", side_effect=PermissionError("denied")),
            pytest.raises(CliError, match=message) as exc_info,
        ):
            write(tmp_path)
        assert exc_info.value.hint == "check file permissions and disk space"


class TestYamlString:
    """tests for the frontmatter scalar quoting."""

    @pytest.mark.parametrize(
        "text",
        [
            'fix "the" bug: in C:\\path # now',
            "tab\there\nnewline\r\nline\u2028separator",
            "del\x7f nul\x00 bom\ufeff c1\x9b",
            "café ✓ 😀 tag\U000e0001",
            "null",
            "- item",
            "",
        ],
    )
    def test_round_trips_as_one_line(self, text):
        yaml = pytest.importorskip("yaml")
        quoted = _yaml_string(text)
        assert "\n" not in quoted
        assert yaml.safe_load(f"key: {quoted}") == {"key": " ".join(text.split())}


class TestParseKv:
    """tests for key-value parsing."""

    @pytest.mark.parametrize(
        ("pairs", "expected"),
        [
            (["key=value", "foo=bar"], {"key": "value", "foo": "bar"}),
            (["key=a=b=c"], {"key": "a=b=c"}),
            (["  key  =  value  "], {"key": "value"}),
        ],
        ids=["pairs", "equals-in-value", "whitespace"],
    )
    def test_parses(self, pairs, expected):
        assert parse_kv(pairs) == expected

    def test_missing_equals_raises(self):
        with pytest.raises(CliError, match="invalid argument"):
            parse_kv(["invalid"])


class TestRunAgent:
    """tests for agent execution."""

    def test_missing_binary_raises(self, tmp_path):
        with (
            patch("familiar.agents.subprocess.call", side_effect=FileNotFoundError),
            pytest.raises(CliError, match="claude not found in PATH"),
        ):
            run_agent(tmp_path, "claude", "prompt", headless=True)

    def test_returns_exit_code(self, tmp_path):
        with patch("familiar.agents.subprocess.call", return_value=42):
            result = run_agent(tmp_path, "claude", "prompt", headless=True)
            assert result == 42


class TestCmdConjure:
    """tests for conjure command."""

    def test_writes_output_file(self, tmp_path, capsys):
        args = argparse.Namespace(
            agent="claude",
            conjurings=["python"],
            into=str(tmp_path),
            save_subagent=False,
            subagent_name=None,
        )
        result = cmd_conjure(args)
        assert result == 0
        content = (tmp_path / "CLAUDE.md").read_text()
        assert content == compose_system(tmp_path, ["python"]).strip() + "\n"
        assert capsys.readouterr().out == "wrote instructions for claude\n"

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
        subagent = tmp_path / ".claude" / "agents" / "python_sec.md"
        frontmatter, body = _read_frontmatter(subagent)
        assert frontmatter == {
            "name": "python_sec",
            "description": "use when work in this repository needs this "
            "behavior profile: python; security",
        }
        assert "conjurings: python, sec" in body
        assert "agent: claude" in body

    def test_subagent_frontmatter_survives_any_conjuring_heading(self, tmp_path):
        local = tmp_path / ".familiar" / "conjurings"
        local.mkdir(parents=True)
        (local / "weird.md").write_text(
            '\n## ops: "prod" \\ #1\tcafé\x7f\n\nbody\n', encoding="utf-8"
        )
        (local / "bare.md").write_text("#\n\nbody\n")
        args = argparse.Namespace(
            agent="claude",
            conjurings=["weird", "bare"],
            into=str(tmp_path),
            save_subagent=True,
            subagent_name="null",
        )
        cmd_conjure(args)
        frontmatter, _ = _read_frontmatter(tmp_path / ".claude" / "agents" / "null.md")
        assert frontmatter == {
            "name": "null",
            "description": "use when work in this repository needs this "
            'behavior profile: ops: "prod" \\ #1 café\x7f; bare',
        }

    def test_codex_reports_no_subagent_support(self, tmp_path):
        args = argparse.Namespace(
            agent="codex",
            conjurings=["rust", "infra"],
            into=str(tmp_path),
            save_subagent=True,
            subagent_name="ship_ops",
        )
        with pytest.raises(CliError, match="agent does not support subagents: codex"):
            cmd_conjure(args)
        assert not (tmp_path / ".codex").exists()

    @pytest.mark.parametrize("name", ["Not Valid", "abc\n"])
    def test_invalid_subagent_name_raises(self, tmp_path, name):
        args = argparse.Namespace(
            agent="claude",
            conjurings=["python"],
            into=str(tmp_path),
            save_subagent=True,
            subagent_name=name,
        )
        with pytest.raises(CliError, match="invalid subagent name"):
            cmd_conjure(args)
        assert not (tmp_path / ".claude").exists()


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
            mock_run.assert_called_once_with(
                tmp_path.resolve(),
                "claude",
                render_invocation(tmp_path, "explain", ["some code"], {}),
                headless=True,
                auto=False,
            )

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

    def test_dry_run_prints_prompt_without_running(self, tmp_path, capsys):
        with patch("familiar.cli.run_agent") as mock_run:
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
            mock_run.assert_not_called()
        assert result == 0
        expected = render_invocation(tmp_path, "explain", ["some code"], {})
        assert capsys.readouterr().out == expected + "\n"

    def test_invoke_with_worktree(self, tmp_path):
        with (
            patch(
                "familiar.cli.create_worktree", return_value=tmp_path / "wt"
            ) as mock_wt,
            patch("familiar.cli.run_agent", return_value=0) as mock_run,
            patch("shutil.copy2") as mock_copy,
        ):
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
            mock_copy.assert_called_once_with(
                tmp_path.resolve() / "CLAUDE.md", tmp_path / "wt" / "CLAUDE.md"
            )

    def test_invoke_worktree_cleaned_up_on_error(self, tmp_path):
        with (
            patch("familiar.cli.create_worktree", return_value=tmp_path / "wt"),
            patch("familiar.cli.run_agent", side_effect=RuntimeError("boom")),
            patch("familiar.cli._remove_worktree") as mock_remove,
        ):
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
            mock_remove.assert_called_once_with(tmp_path.resolve(), tmp_path / "wt")

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
            frontmatter, body = _read_frontmatter(skill)
            assert frontmatter == {
                "name": "explain",
                "description": "use when this task comes up in this repository: "
                "explain code or concepts.",
            }
            assert "invocation: explain" in body
            assert "agent: claude" in body
            mock_run.assert_not_called()

    def test_invoke_save_skill_describes_the_rendered_task(self, tmp_path):
        local = tmp_path / ".familiar" / "invocations"
        local.mkdir(parents=True)
        (local / "fix.md").write_text(
            'TASK: fix "$1": see C:\\tmp # now\n\n## inputs\n\n- $1: bug\n'
        )
        args = argparse.Namespace(
            agent="claude",
            invocation="fix",
            into=str(tmp_path),
            headless=True,
            auto=False,
            dry_run=False,
            kv=None,
            inv_args=["the bug"],
            worktree=False,
            save_skill=True,
            skill_name=None,
        )
        cmd_invoke(args)
        skill = tmp_path / ".claude" / "skills" / "fix" / "SKILL.md"
        frontmatter, _ = _read_frontmatter(skill)
        assert frontmatter["description"] == (
            'use when this task comes up in this repository: fix "the bug": '
            "see C:\\tmp # now"
        )

    def test_save_skill_for_empty_prompt_is_described_by_its_invocation(self, tmp_path):
        path = write_skill(tmp_path, "claude", "noop", "noop", "\n")
        frontmatter, _ = _read_frontmatter(path)
        assert frontmatter["description"] == (
            "use when this task comes up in this repository: noop"
        )

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
            frontmatter, body = _read_frontmatter(skill)
            assert frontmatter == {
                "name": "cleanup_refactor",
                "description": "use when this task comes up in this repository: "
                "refactor code without changing behavior.",
            }
            assert "invocation: refactor" in body
            assert "agent: codex" in body
            mock_run.assert_not_called()

    @pytest.mark.parametrize("name", ["Not Valid", "abc\n"])
    def test_invoke_save_skill_invalid_name(self, tmp_path, name):
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
            skill_name=name,
        )
        with pytest.raises(CliError, match="invalid skill name"):
            cmd_invoke(args)
        assert not (tmp_path / ".claude").exists()


class TestInvokeKvFlag:
    """tests for parsing --kv on the invoke command line."""

    def _dry_run(self, tmp_path, capsys, argv):
        argv = [*argv, "--into", str(tmp_path), "--dry-run"]
        with pytest.raises(SystemExit, match="0"), patch("sys.argv", argv):
            main()
        return capsys.readouterr()

    @pytest.mark.parametrize(
        ("kv_args", "expected"),
        [
            (["--kv", "a=1", "b=2"], "a=1 b=2"),
            (["--kv", "a=1", "--kv", "b=2"], "a=1 b=2"),
            (["--kv", "a=1", "b=2", "--kv", "a=3"], "a=3 b=2"),
            (["--kv"], "a={{a}} b={{b}}"),
            ([], "a={{a}} b={{b}}"),
        ],
        ids=["one-flag", "repeated-flag", "repeated-key-last-wins", "bare", "absent"],
    )
    def test_collects_pairs(self, tmp_path, capsys, kv_args, expected):
        inv_dir = tmp_path / ".familiar" / "invocations"
        inv_dir.mkdir(parents=True)
        (inv_dir / "custom.md").write_text("a={{a}} b={{b}}")
        argv = ["familiar", "invoke", "claude", "custom", *kv_args]
        assert self._dry_run(tmp_path, capsys, argv).out.strip() == expected

    def test_docs_example(self, tmp_path, capsys):
        argv = shlex.split(
            'familiar invoke codex implement-feature --kv spec="add caching" --kv ttl=300'
        )
        captured = self._dry_run(tmp_path, capsys, argv)
        assert "add caching" in captured.out
        assert "missing arguments" not in captured.err


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
        assert capsys.readouterr().out.splitlines() == [
            f"{name}: {first_line}"
            for name, first_line, _ in list_items(tmp_path, "conjurings")
        ]

    @pytest.mark.parametrize(
        ("filename", "content", "line"),
        [
            ("custom.md", "# my custom profile", "custom (local)"),
            ("python.md", "# custom python", "python (local)"),
        ],
        ids=["new-item", "override"],
    )
    def test_list_local_marked(self, tmp_path, capsys, filename, content, line):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / filename).write_text(content)

        args = argparse.Namespace(
            kind="conjurings",
            into=str(tmp_path),
            verbose=False,
        )
        cmd_list(args)
        assert line in capsys.readouterr().out.splitlines()

    @pytest.mark.parametrize("verbose", [False, True])
    def test_list_marks_unreadable_local(self, tmp_path, capsys, verbose):
        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "bad.md").write_bytes(b"task: caf\xe9\n")

        args = argparse.Namespace(
            kind="invocations",
            into=str(tmp_path),
            verbose=verbose,
        )
        assert cmd_list(args) == 0
        assert "bad (local, unreadable)" in capsys.readouterr().out.splitlines()

    def test_list_all_marks_unreadable_snippet(self, tmp_path, capsys):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "x"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "s.md").write_bytes(b"caf\xe9\n")

        args = argparse.Namespace(kind=None, into=str(tmp_path), verbose=False)
        cmd_list(args)
        assert "  x/s.md (local, unreadable)\n" in capsys.readouterr().out

    def test_list_escapes_undecodable_name(self, tmp_path, capsys):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "x"
        snippet_dir.mkdir(parents=True)
        try:
            (snippet_dir / os.fsdecode(b"a\xffb.md")).write_text("body\n")
        except OSError:
            pytest.skip("filesystem refuses names that are not valid UTF-8")

        args = argparse.Namespace(kind="snippets", into=str(tmp_path), verbose=False)
        assert cmd_list(args) == 0
        assert "x/a\\xffb.md (local)\n" in capsys.readouterr().out

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

    def test_lint_escapes_undecodable_name(self, tmp_path, capsys):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "x"
        snippet_dir.mkdir(parents=True)
        try:
            (snippet_dir / os.fsdecode(b"a\xffb.md")).write_text("body\n")
        except OSError:
            pytest.skip("filesystem refuses names that are not valid UTF-8")

        args = argparse.Namespace(into=str(tmp_path), errors_only=True)
        assert cmd_lint(args) == 1
        assert ".familiar/snippets/x/a\\xffb.md:" in capsys.readouterr().err

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
        assert capsys.readouterr().err == (
            "error: .familiar/conjurings/empty.md:1: template is empty\n"
            "\n1 error(s), 0 warning(s)\n"
        )

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
