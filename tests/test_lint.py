"""tests for familiar.lint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from familiar.lint import (
    LintMessage,
    lint_all,
    lint_collection,
    lint_invocation,
    lint_snippet_collection,
    lint_snippet_placeholders,
    lint_snippet_references,
    lint_template,
    load_linters,
)
from familiar.render import _MAX_INCLUDE_DEPTH, NotFoundError


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

    def test_accepts_outputs_section(self):
        content = """task: do something

inputs
- $ARGUMENTS

outputs
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

    def test_placeholder_substring_in_other_word_warns(self):
        content = """task: process {{name}}

inputs
- filename (required): the file to process

output
- results
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{name}}" in m.message]
        assert len(placeholder_warnings) == 1
        assert placeholder_warnings[0].level == "warning"

    def test_placeholder_tag_in_inputs_section_no_warning(self):
        content = """task: implement {{spec}}

inputs
- {{spec}} (required): feature specification

output
- results
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{spec}}" in m.message]
        assert placeholder_warnings == []

    def test_fenced_example_does_not_end_inputs_section(self):
        content = """task: do something with {{target}}

## inputs

```sh
# run it like this
familiar invoke thing
```

- {{target}}: the file to operate on

## output

- results
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{target}}" in m.message]
        assert placeholder_warnings == []

    def test_tilde_fenced_example_does_not_end_inputs_section(self):
        content = """task: do something with {{target}}

## inputs

~~~
# run it like this
~~~

- {{target}}: the file to operate on

## output

- results
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{target}}" in m.message]
        assert placeholder_warnings == []

    def test_heading_after_fence_still_ends_inputs_section(self):
        content = """task: do something with {{target}}

## inputs

```sh
# run it like this
```

- other: something else

## notes

- {{target}} is described here, outside the inputs section

## output

- results
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{target}}" in m.message]
        assert len(placeholder_warnings) == 1
        assert placeholder_warnings[0].level == "warning"

    def test_unclosed_fence_runs_to_end_of_file(self):
        content = """task: do something with {{target}}

## inputs

```sh
# run it like this

## output

- {{target}}: the file to operate on
"""
        messages = lint_invocation(content, "test.md")
        placeholder_warnings = [m for m in messages if "{{target}}" in m.message]
        assert placeholder_warnings == []

    def test_positional_placeholder_not_matched_as_prefix(self):
        content = """task: process $1 and $10

## inputs

- ctx: $10 the tenth argument

## output

- results
"""
        messages = lint_invocation(content, "test.md")
        assert [m for m in messages if "'$10'" in m.message] == []
        first_warnings = [m for m in messages if "'$1'" in m.message]
        assert len(first_warnings) == 1
        assert first_warnings[0].level == "warning"

    def test_positional_placeholder_documented_with_trailing_punctuation(self):
        for doc in [
            "- ctx: $1",
            "- ctx: $1, the first argument",
            "- $1 (required): the first argument",
        ]:
            content = (
                f"task: process $1\n\n## inputs\n\n{doc}\n\n## output\n\n- results\n"
            )
            messages = lint_invocation(content, "test.md")
            warnings = [m for m in messages if "may not be documented" in m.message]
            assert warnings == [], f"failed for: {doc}"


class TestLintAll:
    """tests for linting all conjurings and invocations."""

    def test_lint_all_builtins(self, tmp_path):
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

        with patch("familiar._plugins.entry_points", return_value=[mock_ep]):
            with pytest.warns(UserWarning, match="not callable"):
                linters = load_linters("conjurings")
            assert len(linters) == 0

    def test_load_error_warns(self):
        """Plugin that fails to load should warn."""
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("module not found")

        with patch("familiar._plugins.entry_points", return_value=[mock_ep]):
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

        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "mytemplate.md").write_text("# test")

        with patch("familiar._plugins.entry_points") as mock_entry_points:
            # return the mock for conjurings, empty for invocations
            def ep_side_effect(group):
                if group == "familiar.linters.conjurings":
                    return [mock_ep]
                return []

            mock_entry_points.side_effect = ep_side_effect
            lint_all(tmp_path)

        local_calls = [c for c in calls if "mytemplate" in c[1]]
        assert len(local_calls) == 1

    def test_plugin_linter_error_handled(self, tmp_path):
        """Plugin linter that raises should produce error message."""

        def bad_linter(content: str, name: str) -> list[LintMessage]:
            raise RuntimeError("linter crashed")

        mock_ep = MagicMock()
        mock_ep.name = "bad"
        mock_ep.load.return_value = bad_linter

        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "test.md").write_text("# test")

        with patch("familiar._plugins.entry_points") as mock_entry_points:

            def ep_side_effect(group):
                if group == "familiar.linters.conjurings":
                    return [mock_ep]
                return []

            mock_entry_points.side_effect = ep_side_effect
            messages = lint_all(tmp_path)

        error_messages = [m for m in messages if "plugin linter failed" in m.message]
        assert len(error_messages) >= 1


class TestLintCollectionErrorHandling:
    """tests for error handling in lint_collection."""

    def test_load_error_produces_lint_error(self, tmp_path):
        """A NotFoundError from load_text should produce a lint error, not crash."""
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "broken.md").write_text("# heading")

        from familiar import lint as _lint_mod

        original = _lint_mod.load_text

        def patched(repo_root, kind, name):
            if name == "broken":
                raise NotFoundError("simulated read failure")
            return original(repo_root, kind, name)

        with patch.object(_lint_mod, "load_text", side_effect=patched):
            messages = lint_collection(tmp_path, "conjurings", lint_template, [])

        load_errors = [
            m
            for m in messages
            if "broken.md" in m.file and "failed to load" in m.message
        ]
        assert len(load_errors) == 1
        assert load_errors[0].level == "error"

    def test_unexpected_linter_error_propagates(self, tmp_path):
        """Errors not wrapped in NotFoundError should propagate, not be swallowed."""
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "test.md").write_text("# test")

        def exploding_linter(content: str, name: str) -> list[LintMessage]:
            raise RuntimeError("unexpected")

        with pytest.raises(RuntimeError, match="unexpected"):
            lint_collection(tmp_path, "conjurings", exploding_linter, [])


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

    def test_transitive_missing_reference(self, tmp_path):
        """a valid include whose child references a missing snippet is caught."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "outer.txt").write_text("{{> snippet:test/missing.txt}}")

        content = "prefix {{> snippet:test/outer.txt}} suffix"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert len(messages) == 1
        assert messages[0].level == "error"
        assert messages[0].line == 1
        assert "test/missing.txt" in messages[0].message

    def test_valid_transitive_include_no_error(self, tmp_path):
        """a chain of valid includes produces no false positives."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "outer.txt").write_text("outer[{{> snippet:test/inner.txt}}]")
        (snippet_dir / "inner.txt").write_text("INNER")

        content = "{{> snippet:test/outer.txt}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert messages == []

    def test_self_cycle_detected(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "loop.txt").write_text("{{> snippet:test/loop.txt}}")

        content = "{{> snippet:test/loop.txt}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert len(messages) == 1
        assert messages[0].level == "error"
        assert "snippet include cycle" in messages[0].message
        assert "test/loop.txt -> test/loop.txt" in messages[0].message

    def test_mutual_cycle_detected_and_anchored(self, tmp_path):
        """an a->b->a cycle is reported at the top-level directive's line."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "a.txt").write_text("{{> snippet:test/b.txt}}")
        (snippet_dir / "b.txt").write_text("{{> snippet:test/a.txt}}")

        content = "line one\n{{> snippet:test/a.txt}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert len(messages) == 1
        assert messages[0].level == "error"
        assert messages[0].line == 2
        assert "snippet include cycle" in messages[0].message
        assert "test/a.txt" in messages[0].message
        assert "test/b.txt" in messages[0].message

    def test_depth_exceeded_detected(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        chain_len = _MAX_INCLUDE_DEPTH + 2
        for i in range(chain_len):
            if i < chain_len - 1:
                body = "{{> snippet:test/s" + str(i + 1) + ".txt}}"
            else:
                body = "end"
            (snippet_dir / f"s{i}.txt").write_text(body)

        content = "{{> snippet:test/s0.txt}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert len(messages) == 1
        assert messages[0].level == "error"
        assert "depth exceeded" in messages[0].message

    def test_duplicate_include_no_false_cycle(self, tmp_path):
        """including the same valid snippet twice is not a cycle."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "shared.txt").write_text("shared")

        content = "{{> snippet:test/shared.txt}} {{> snippet:test/shared.txt}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert messages == []

    def test_diamond_include_no_false_cycle(self, tmp_path):
        """a snippet pulling the same leaf twice (diamond) is not a cycle."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "top.txt").write_text(
            "{{> snippet:test/leaf.txt}} {{> snippet:test/leaf.txt}}"
        )
        (snippet_dir / "leaf.txt").write_text("LEAF")

        content = "{{> snippet:test/top.txt}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert messages == []


class TestLintSnippetCollection:
    """tests for linting the snippet collection itself."""

    def test_builtins_clean(self, tmp_path):
        messages = lint_snippet_collection(tmp_path)
        assert messages == []

    def test_broken_include_in_local_snippet(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "broken.txt").write_text("{{> snippet:test/gone.txt}}")

        messages = lint_snippet_collection(tmp_path)
        broken = [m for m in messages if "test/broken.txt" in m.file]
        assert len(broken) == 1
        assert broken[0].level == "error"
        assert broken[0].file == ".familiar/snippets/test/broken.txt"
        assert "test/gone.txt" in broken[0].message

    def test_transitive_break_in_local_snippet(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "a.txt").write_text("{{> snippet:test/b.txt}}")
        (snippet_dir / "b.txt").write_text("{{> snippet:test/missing.txt}}")

        messages = lint_snippet_collection(tmp_path)
        a_errors = [m for m in messages if m.file == ".familiar/snippets/test/a.txt"]
        assert len(a_errors) == 1
        assert "test/missing.txt" in a_errors[0].message

    def test_cycle_in_local_snippet_collection(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "cyc"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "a.txt").write_text("{{> snippet:cyc/b.txt}}")
        (snippet_dir / "b.txt").write_text("{{> snippet:cyc/a.txt}}")

        messages = lint_snippet_collection(tmp_path)
        cyc = [m for m in messages if "snippet include cycle" in m.message]
        assert len(cyc) == 2
        files = {m.file for m in cyc}
        assert files == {
            ".familiar/snippets/cyc/a.txt",
            ".familiar/snippets/cyc/b.txt",
        }

    def test_lint_all_catches_broken_snippet_collection(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "broken.txt").write_text("{{> snippet:test/gone.txt}}")

        messages = lint_all(tmp_path)
        errs = [
            m
            for m in messages
            if "test/broken.txt" in m.file and "snippet not found" in m.message
        ]
        assert len(errs) == 1

    def test_load_failure_reports_error(self, tmp_path):
        """a snippet that lists but then fails to load produces a lint error."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "ok.txt").write_text("fine")

        from familiar import lint as _lint_mod

        original = _lint_mod.load_snippet

        def patched(repo_root, path):
            if path == "test/ok.txt":
                raise NotFoundError("simulated read failure")
            return original(repo_root, path)

        with patch.object(_lint_mod, "load_snippet", side_effect=patched):
            messages = lint_snippet_collection(tmp_path)

        load_errors = [
            m
            for m in messages
            if "test/ok.txt" in m.file and "failed to load" in m.message
        ]
        assert len(load_errors) == 1
        assert load_errors[0].level == "error"


class TestLintSnippetPlaceholders:
    """tests for placeholder checks on include-expanded invocation text."""

    def test_snippet_positional_undocumented_warns(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets" / "test"
        snippets.mkdir(parents=True)
        (snippets / "body.txt").write_text("run the tool with $1")

        content = (
            "task: demo\n\ninputs\n- $ARGUMENTS: stuff\n\n"
            "{{> snippet:test/body.txt}}\n\noutput\n- results\n"
        )
        messages = lint_snippet_placeholders(tmp_path, content, "demo.md")
        warns = [m for m in messages if "$1" in m.message]
        assert len(warns) == 1
        assert warns[0].level == "warning"
        assert warns[0].line is None

    def test_snippet_named_undocumented_warns(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets" / "test"
        snippets.mkdir(parents=True)
        (snippets / "body.txt").write_text("mode is {{key}}")

        content = (
            "task: demo\n\ninputs\n- $ARGUMENTS: stuff\n\n"
            "{{> snippet:test/body.txt}}\n\noutput\n- results\n"
        )
        messages = lint_snippet_placeholders(tmp_path, content, "demo.md")
        warns = [m for m in messages if "{{key}}" in m.message]
        assert len(warns) == 1
        assert warns[0].level == "warning"

    def test_snippet_named_documented_no_warn(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets" / "test"
        snippets.mkdir(parents=True)
        (snippets / "body.txt").write_text("mode is {{key}}")

        content = (
            "task: demo\n\ninputs\n- key (required): the mode\n\n"
            "{{> snippet:test/body.txt}}\n\noutput\n- results\n"
        )
        messages = lint_snippet_placeholders(tmp_path, content, "demo.md")
        assert messages == []

    def test_placeholder_in_raw_and_snippet_not_double_reported(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets" / "test"
        snippets.mkdir(parents=True)
        (snippets / "body.txt").write_text("also uses {{key}}")

        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "demo.md").write_text(
            "task: demo with {{key}}\n\ninputs\n- $ARGUMENTS: stuff\n\n"
            "{{> snippet:test/body.txt}}\n\noutput\n- results\n"
        )

        messages = lint_collection(tmp_path, "invocations", lint_invocation, [])
        warns = [m for m in messages if "{{key}}" in m.message and "demo.md" in m.file]
        assert len(warns) == 1

    def test_broken_include_reported_once(self, tmp_path):
        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "demo.md").write_text(
            "task: demo\n\ninputs\n- $ARGUMENTS: stuff\n\n"
            "{{> snippet:missing/gone.txt}}\n\noutput\n- results\n"
        )

        messages = lint_collection(tmp_path, "invocations", lint_invocation, [])
        errors = [
            m
            for m in messages
            if "snippet not found" in m.message and "demo.md" in m.file
        ]
        assert len(errors) == 1

    def test_conjuring_snippet_placeholder_not_checked(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets" / "test"
        snippets.mkdir(parents=True)
        (snippets / "body.txt").write_text("mode is {{key}}")

        conjurings = tmp_path / ".familiar" / "conjurings"
        conjurings.mkdir(parents=True)
        (conjurings / "demo.md").write_text("# demo\n\n{{> snippet:test/body.txt}}\n")

        messages = lint_collection(tmp_path, "conjurings", lint_template, [])
        warns = [m for m in messages if "may not be documented" in m.message]
        assert warns == []
