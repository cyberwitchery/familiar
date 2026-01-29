"""integration tests for familiar cli."""

from __future__ import annotations

import subprocess
import sys


class TestConjureIntegration:
    """integration tests for conjure command."""

    def test_conjure_creates_claude_md(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "conjure",
                "claude",
                "python",
                "--into",
                str(tmp_path),
            ],
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
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "conjure",
                "codex",
                "rust",
                "sec",
                "--into",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text()
        assert "rust" in content.lower()
        assert "sec" in content.lower()

    def test_conjure_unknown_profile_fails(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "conjure",
                "claude",
                "nonexistent",
                "--into",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "unknown conjuring" in result.stderr


class TestInvokeIntegration:
    """integration tests for invoke command (without actually running agents)."""

    def test_invoke_unknown_invocation_fails(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "invoke",
                "claude",
                "nonexistent",
                "--into",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "unknown invocation" in result.stderr

    def test_invoke_invalid_kv_fails(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "invoke",
                "claude",
                "explain",
                "--kv",
                "invalid",
                "--into",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "invalid argument" in result.stderr

    def test_error_includes_hint(self, tmp_path):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "invoke",
                "claude",
                "nonexistent",
                "--into",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "hint:" in result.stderr


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
        assert "examples:" in result.stdout

    def test_conjure_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "conjure", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "conjurings" in result.stdout

    def test_invoke_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "invoke", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "invocation" in result.stdout
        assert "--headless" in result.stdout

    def test_list_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "list", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "conjurings" in result.stdout
        assert "invocations" in result.stdout


class TestListIntegration:
    """integration tests for list command."""

    def test_list_all(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "list"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "conjurings:" in result.stdout
        assert "invocations:" in result.stdout
        assert "snippets:" in result.stdout
        assert "core" in result.stdout
        assert "explain" in result.stdout

    def test_list_conjurings(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "list", "conjurings"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "core" in result.stdout
        assert "python" in result.stdout
        assert "rust" in result.stdout

    def test_list_invocations(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "list", "invocations"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "explain" in result.stdout
        assert "refactor" in result.stdout

    def test_list_conjurings_verbose(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "list", "conjurings", "-v"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # verbose includes description after colon
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
        )
        assert result.returncode == 0
        assert "custom (local)" in result.stdout

    def test_list_snippets(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "list", "snippets"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "python/pyproject.toml" in result.stdout
        assert "rust/Cargo.toml" in result.stdout
        assert "node/github-ci.yml" in result.stdout


class TestSnippetIntegration:
    """integration tests for snippet includes."""

    def test_invocation_with_snippet_renders(self, tmp_path):
        """Invocations using snippet includes should render with inlined content."""
        from familiar.render import render_invocation

        result = render_invocation(tmp_path, "bootstrap-python", ["myapp", "cli"], {})
        # The snippet content should be inlined
        assert "[project]" in result
        assert "pyproject.toml" not in result or "snippet:" not in result

    def test_add_ci_snippets_render(self, tmp_path):
        """add-ci invocation should render with CI workflow content."""
        from familiar.render import render_invocation

        result = render_invocation(tmp_path, "add-ci", ["github", "python"], {})
        # Should contain inlined workflow, not the snippet directive
        assert "{{> snippet:" not in result
        assert "actions/checkout" in result

    def test_snippet_override_changes_output(self, tmp_path):
        """Local snippet override should change rendered invocation."""
        from familiar.render import render_invocation

        snippet_dir = tmp_path / ".familiar" / "snippets" / "python"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "pyproject.toml").write_text("[custom]\noverride = true\n")

        result = render_invocation(tmp_path, "bootstrap-python", ["myapp", "cli"], {})
        assert "override = true" in result


class TestLintIntegration:
    """integration tests for lint command."""

    def test_lint_builtins_pass(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "lint", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "all checks passed" in result.stdout

    def test_lint_with_invalid_template(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "bad.md").write_text("no heading here")

        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "lint", "--into", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0  # warnings don't cause failure
        assert "warning" in result.stderr
        assert "heading" in result.stderr

    def test_lint_errors_only(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "bad.md").write_text("no heading here")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "familiar.cli",
                "lint",
                "--errors-only",
                "--into",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "all checks passed" in result.stdout  # no errors, warnings filtered

    def test_lint_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "familiar.cli", "lint", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--errors-only" in result.stdout
