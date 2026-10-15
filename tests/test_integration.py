"""integration tests for familiar cli."""

from __future__ import annotations

import subprocess
import sys

import pytest

from familiar.render import compose_system, list_items, load_snippet, render_invocation


def _familiar(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "familiar.cli", *argv],
        capture_output=True,
        text=True,
        check=False,
    )


class TestConjureIntegration:
    """integration tests for conjure command."""

    @pytest.mark.parametrize(
        ("agent", "conjurings", "filename"),
        [("claude", ["python"], "CLAUDE.md"), ("codex", ["rust", "sec"], "AGENTS.md")],
    )
    def test_conjure_writes_instruction_file(
        self, tmp_path, agent, conjurings, filename
    ):
        result = _familiar("conjure", agent, *conjurings, "--into", str(tmp_path))
        assert result.returncode == 0
        assert result.stdout == f"wrote instructions for {agent}\n"

        content = (tmp_path / filename).read_text()
        assert content == compose_system(tmp_path, conjurings).strip() + "\n"


class TestErrorIntegration:
    """integration tests for usage errors."""

    @pytest.mark.parametrize(
        ("argv", "stderr"),
        [
            (
                ["conjure", "claude", "nonexistent"],
                (
                    "error: unknown conjuring: nonexistent\n"
                    "hint: run 'familiar list conjurings' to see available options\n"
                ),
            ),
            (
                ["invoke", "claude", "nonexistent"],
                (
                    "error: unknown invocation: nonexistent\n"
                    "hint: run 'familiar list invocations' to see available options\n"
                ),
            ),
            (
                ["invoke", "claude", "explain", "--kv", "invalid"],
                (
                    "error: invalid argument: invalid\n"
                    "hint: use key=value format, e.g. --kv name=myproject\n"
                ),
            ),
        ],
        ids=["unknown-conjuring", "unknown-invocation", "invalid-kv"],
    )
    def test_usage_error(self, tmp_path, argv, stderr):
        result = _familiar(*argv, "--into", str(tmp_path))
        assert result.returncode == 2
        assert result.stderr == stderr


class TestHelpIntegration:
    """integration tests for help output."""

    @pytest.mark.parametrize(
        ("argv", "tokens"),
        [
            (
                [],
                [
                    (
                        "usage: familiar [-h] [--version] [--debug] "
                        "{conjure,invoke,list,lint} ..."
                    ),
                    "conjure",
                    "invoke",
                    "list",
                    "lint",
                    "--version",
                    "--debug",
                    "examples:",
                ],
            ),
            (
                ["conjure"],
                ["conjurings", "--into", "--save-subagent", "--subagent-name"],
            ),
            (
                ["invoke"],
                [
                    "invocation",
                    "--into",
                    "--headless",
                    "--auto",
                    "--dry-run",
                    "--worktree",
                    "--save-skill",
                    "--skill-name",
                    "--kv",
                ],
            ),
            (
                ["list"],
                ["conjurings", "invocations", "snippets", "-v", "--verbose", "--into"],
            ),
            (["lint"], ["--errors-only", "--into"]),
        ],
        ids=["main", "conjure", "invoke", "list", "lint"],
    )
    def test_help(self, argv, tokens):
        result = _familiar(*argv, "--help")
        assert result.returncode == 0
        for token in tokens:
            assert token in result.stdout


class TestListIntegration:
    """integration tests for list command."""

    def test_list_all(self):
        result = _familiar("list")
        assert result.returncode == 0
        assert "conjurings:" in result.stdout
        assert "invocations:" in result.stdout
        assert "snippets:" in result.stdout
        assert "core" in result.stdout
        assert "explain" in result.stdout

    @pytest.mark.parametrize("kind", ["conjurings", "invocations"])
    def test_list_kind(self, tmp_path, kind):
        result = _familiar("list", kind, "--into", str(tmp_path))
        assert result.returncode == 0
        assert result.stdout == "".join(
            f"{name}\n" for name, _, _ in list_items(tmp_path, kind)
        )

    def test_list_conjurings_verbose(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "list", "conjurings", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert ":" in result.stdout

    def test_list_with_local_override(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "custom.md").write_text("# my custom profile")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "list",
                "conjurings",
                "--into",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "custom (local)" in result.stdout

    def test_list_snippets(self):
        result = _familiar("list", "snippets")
        assert result.returncode == 0
        assert "python/pyproject.toml" in result.stdout
        assert "rust/Cargo.toml" in result.stdout
        assert "node/github-ci.yml" in result.stdout


class TestSnippetIntegration:
    """integration tests for snippet includes."""

    def test_invocation_with_snippet_renders(self, tmp_path):
        """Invocations using snippet includes should render with inlined content."""
        result = render_invocation(tmp_path, "bootstrap-python", ["myapp", "cli"], {})
        assert "{{> snippet:" not in result
        assert load_snippet(tmp_path, "python/pyproject.toml") in result

    def test_add_ci_snippets_render(self, tmp_path):
        """add-ci invocation should render with CI workflow content."""
        result = render_invocation(tmp_path, "add-ci", ["github", "python"], {})
        assert "{{> snippet:" not in result
        for lang in ["python", "rust", "node"]:
            for ci in ["github-ci.yml", "gitlab-ci.yml"]:
                assert load_snippet(tmp_path, f"{lang}/{ci}") in result

    def test_snippet_override_changes_output(self, tmp_path):
        """Local snippet override should change rendered invocation."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "python"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "pyproject.toml").write_text("[custom]\noverride = true\n")

        result = render_invocation(tmp_path, "bootstrap-python", ["myapp", "cli"], {})
        assert "override = true" in result


class TestLintIntegration:
    """integration tests for lint command."""

    def test_lint_builtins_pass(self, tmp_path):
        result = _familiar("lint", "--into", str(tmp_path))
        assert result.returncode == 0
        assert "all checks passed" in result.stdout

    def test_lint_with_invalid_template(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "bad.md").write_text("no heading here")

        result = _familiar("lint", "--into", str(tmp_path))
        assert result.returncode == 0  # warnings don't cause failure
        assert result.stderr == (
            "warning: .familiar/conjurings/bad.md:1: template should start with "
            "a markdown heading (# ...)\n\n1 warning(s)\n"
        )

    def test_lint_errors_only(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "bad.md").write_text("no heading here")

        result = _familiar("lint", "--errors-only", "--into", str(tmp_path))
        assert result.returncode == 0
        assert "all checks passed" in result.stdout  # no errors, warnings filtered
