"""tests for familiar.lint."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from familiar.lint import (
    LintMessage,
    lint_all,
    lint_invocation,
    lint_snippet_references,
    lint_template,
    load_linters,
)


class TestLintTemplate:
    """tests for template linting."""

    def test_valid_template(self):
        content = "# my template\n\nsome content"
        messages = lint_template(content, "test.md")
        assert messages == []

    def test_empty_template(self):
        messages = lint_template("", "test.md")
        assert len(messages) == 1
        assert messages[0].level == "error"
        assert "empty" in messages[0].message

    def test_missing_heading(self):
        content = "no heading here\njust text"
        messages = lint_template(content, "test.md")
        assert len(messages) == 1
        assert messages[0].level == "warning"
        assert "heading" in messages[0].message


class TestLintInvocation:
    """tests for invocation linting."""

    def test_valid_invocation(self):
        content = """task: do something

inputs
- $ARGUMENTS (required): what to do

steps
- step 1
- step 2

output
- show results
"""
        messages = lint_invocation(content, "test.md")
        assert messages == []

    def test_empty_invocation(self):
        messages = lint_invocation("", "test.md")
        assert len(messages) == 1
        assert messages[0].level == "error"
        assert "empty" in messages[0].message

    def test_missing_task_line(self):
        content = """some random text

inputs
- $1 name

output
- results
"""
        messages = lint_invocation(content, "test.md")
        task_warnings = [m for m in messages if "task:" in m.message]
        assert len(task_warnings) == 1
        assert task_warnings[0].level == "warning"

    def test_missing_inputs_section(self):
        content = """task: do something

output
- results
"""
        messages = lint_invocation(content, "test.md")
        input_warnings = [m for m in messages if "inputs" in m.message.lower()]
        assert len(input_warnings) == 1
        assert input_warnings[0].level == "warning"

    def test_missing_output_section(self):
        content = """task: do something

inputs
- $ARGUMENTS
"""
        messages = lint_invocation(content, "test.md")
        output_warnings = [m for m in messages if "output" in m.message.lower()]
        assert len(output_warnings) == 1
        assert output_warnings[0].level == "warning"

    def test_accepts_various_task_verbs(self):
        for verb in [
            "task:",
            "explain:",
            "review:",
            "refactor:",
            "bootstrap",
            "implement:",
            "add:",
            "fix:",
        ]:
            content = f"""{verb} something

inputs
- $ARGUMENTS

output
- results
"""
            messages = lint_invocation(content, f"test-{verb}.md")
            task_warnings = [m for m in messages if "task:" in m.message]
            assert task_warnings == [], f"Failed for verb: {verb}"

    def test_accepts_arguments_section(self):
        content = """task: do something

arguments:
- $1 name

output
- results
"""
        messages = lint_invocation(content, "test.md")
        input_warnings = [m for m in messages if "inputs" in m.message.lower()]
        assert input_warnings == []

    def test_accepts_deliverables_section(self):
        content = """task: do something

inputs
- $ARGUMENTS

deliverables
- results
"""
        messages = lint_invocation(content, "test.md")
        output_warnings = [m for m in messages if "output" in m.message.lower()]
        assert output_warnings == []

    def test_undocumented_placeholder_warning(self):
        content = """task: do something with {{myarg}}

inputs
- $ARGUMENTS

output
- results
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{myarg}}" in m.message]
        assert len(placeholder_warnings) == 1
        assert placeholder_warnings[0].level == "warning"

    def test_documented_placeholder_no_warning(self):
        content = """task: do something with {{myarg}}

inputs
- myarg (required): the argument

output
- results
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{myarg}}" in m.message]
        assert placeholder_warnings == []


class TestLintAll:
    """tests for linting all conjurings and invocations."""

    def test_lint_all_builtins(self, tmp_path):
        # should lint all built-ins without errors
        messages = lint_all(tmp_path)
        errors = [m for m in messages if m.level == "error"]
        assert errors == [], f"Unexpected errors: {errors}"

    def test_lint_all_with_local_override(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "bad.md").write_text("no heading")

        messages = lint_all(tmp_path)
        local_warnings = [m for m in messages if "bad.md" in m.file]
        assert len(local_warnings) == 1
        assert "heading" in local_warnings[0].message


class TestLintMessage:
    """tests for LintMessage formatting."""

    def test_str_with_line(self):
        msg = LintMessage(level="error", file="test.md", line=5, message="bad")
        assert str(msg) == "error: test.md:5: bad"

    def test_str_without_line(self):
        msg = LintMessage(level="warning", file="test.md", line=None, message="warning")
        assert str(msg) == "warning: test.md: warning"


class TestLinterPlugins:
    """tests for linter plugin loading."""

    def test_load_linters_returns_list(self):
        linters = load_linters("conjurings")
        assert isinstance(linters, list)

    def test_load_linters_invocations(self):
        linters = load_linters("invocations")
        assert isinstance(linters, list)

    def test_invalid_linter_warns(self):
        """Plugin that isn't callable should warn."""
        mock_ep = MagicMock()
        mock_ep.name = "invalid"
        mock_ep.load.return_value = "not a function"

        with patch("familiar.lint.entry_points", return_value=[mock_ep]):
            with pytest.warns(UserWarning, match="not callable"):
                linters = load_linters("conjurings")
            assert len(linters) == 0

    def test_load_error_warns(self):
        """Plugin that fails to load should warn."""
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("module not found")

        with patch("familiar.lint.entry_points", return_value=[mock_ep]):
            with pytest.warns(UserWarning, match="failed to load"):
                linters = load_linters("conjurings")
            assert len(linters) == 0

    def test_plugin_linter_called(self, tmp_path):
        """Plugin linter should be called for each file."""
        calls = []

        def mock_linter(content: str, name: str) -> list[LintMessage]:
            calls.append((content, name))
            return []

        mock_ep = MagicMock()
        mock_ep.name = "test"
        mock_ep.load.return_value = mock_linter

        # Create a local template to lint
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "mytemplate.md").write_text("# test")

        with patch("familiar.lint.entry_points") as mock_entry_points:
            # Return our mock for templates, empty for invocations
            def ep_side_effect(group):
                if group == "familiar.linters.conjurings":
                    return [mock_ep]
                return []

            mock_entry_points.side_effect = ep_side_effect
            lint_all(tmp_path)

        # Should have been called for the local template
        local_calls = [c for c in calls if "mytemplate" in c[1]]
        assert len(local_calls) == 1

    def test_plugin_linter_error_handled(self, tmp_path):
        """Plugin linter that raises should produce error message."""

        def bad_linter(content: str, name: str) -> list[LintMessage]:
            raise RuntimeError("linter crashed")

        mock_ep = MagicMock()
        mock_ep.name = "bad"
        mock_ep.load.return_value = bad_linter

        # Create a local template
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "test.md").write_text("# test")

        with patch("familiar.lint.entry_points") as mock_entry_points:

            def ep_side_effect(group):
                if group == "familiar.linters.conjurings":
                    return [mock_ep]
                return []

            mock_entry_points.side_effect = ep_side_effect
            messages = lint_all(tmp_path)

        error_messages = [m for m in messages if "plugin linter failed" in m.message]
        assert len(error_messages) >= 1


class TestLintSnippetReferences:
    """tests for snippet reference validation."""

    def test_valid_snippet_reference(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "file.txt").write_text("content")

        content = "some text {{> snippet:test/file.txt}} more text"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert messages == []

    def test_missing_snippet_reference(self, tmp_path):
        content = "text {{> snippet:nonexistent/file.txt}} more"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert len(messages) == 1
        assert messages[0].level == "error"
        assert "snippet not found" in messages[0].message
        assert messages[0].line == 1

    def test_multiple_references(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "a.txt").write_text("a")

        content = "{{> snippet:test/a.txt}}\n{{> snippet:missing/b.txt}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert len(messages) == 1
        assert messages[0].line == 2

    def test_no_references(self, tmp_path):
        content = "just plain text with {{named}} and $1"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert messages == []

    def test_lint_all_catches_missing_snippet(self, tmp_path):
        """lint_all should report errors for invocations with missing snippet refs."""
        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "bad.md").write_text(
            "task: do something\n\ninputs\n- $ARGUMENTS\n\n"
            "{{> snippet:nonexistent/file.txt}}\n\noutput\n- results\n"
        )

        messages = lint_all(tmp_path)
        snippet_errors = [
            m
            for m in messages
            if "snippet not found" in m.message and "bad.md" in m.file
        ]
        assert len(snippet_errors) == 1
