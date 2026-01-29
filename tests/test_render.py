"""tests for familiar.render."""

from __future__ import annotations

import pytest

from familiar.render import (
    NotFoundError,
    compose_system,
    list_items,
    list_snippets,
    load_snippet,
    load_text,
    render_invocation,
    resolve_includes,
    substitute,
)


class TestSubstitute:
    """tests for placeholder substitution."""

    def test_positional_args(self):
        text = "hello $1 and $2"
        result = substitute(text, ["world", "friends"], {})
        assert result == "hello world and friends"

    def test_arguments_placeholder(self):
        text = "args: $ARGUMENTS"
        result = substitute(text, ["one", "two", "three"], {})
        assert result == "args: one two three"

    def test_named_args(self):
        text = "name: {{name}}, value: {{value}}"
        result = substitute(text, [], {"name": "foo", "value": "bar"})
        assert result == "name: foo, value: bar"

    def test_mixed_args(self):
        text = "$1 says {{greeting}}"
        result = substitute(text, ["alice"], {"greeting": "hello"})
        assert result == "alice says hello"

    def test_missing_positional_warns(self, capsys):
        text = "need $1 and $2 and $3"
        result = substitute(text, ["only_one"], {})
        assert result == "need only_one and  and "
        captured = capsys.readouterr()
        assert "warning: missing arguments: $2, $3" in captured.err

    def test_unused_kv_ignored(self):
        text = "just {{used}}"
        result = substitute(text, [], {"used": "yes", "unused": "no"})
        assert result == "just yes"

    def test_empty_args(self):
        text = "$ARGUMENTS"
        result = substitute(text, [], {})
        assert result == ""

    def test_positional_out_of_order(self):
        text = "$2 before $1"
        result = substitute(text, ["first", "second"], {})
        assert result == "second before first"


class TestLoadText:
    """tests for loading conjurings and invocations."""

    def test_load_builtin_template(self, tmp_path):
        result = load_text(tmp_path, "conjurings", "core")
        assert "# core profile" in result.lower() or "workflow" in result.lower()

    def test_load_builtin_invocation(self, tmp_path):
        result = load_text(tmp_path, "invocations", "explain")
        assert "explain" in result.lower()

    def test_local_override(self, tmp_path):
        override_dir = tmp_path / ".familiar" / "conjurings"
        override_dir.mkdir(parents=True)
        (override_dir / "core.md").write_text("custom core content")
        result = load_text(tmp_path, "conjurings", "core")
        assert result == "custom core content"

    def test_local_custom_template(self, tmp_path):
        override_dir = tmp_path / ".familiar" / "conjurings"
        override_dir.mkdir(parents=True)
        (override_dir / "custom.md").write_text("my custom template")
        result = load_text(tmp_path, "conjurings", "custom")
        assert result == "my custom template"

    def test_invalid_name_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="invalid"):
            load_text(tmp_path, "conjurings", "../../../etc/passwd")

    def test_unknown_template_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown conjuring"):
            load_text(tmp_path, "conjurings", "nonexistent")

    def test_unknown_invocation_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown invocation"):
            load_text(tmp_path, "invocations", "nonexistent")


class TestComposeSystem:
    """tests for composing system prompts."""

    def test_compose_with_conjurings(self, tmp_path):
        system = compose_system(tmp_path, ["python"])
        assert "core" in system.lower() or "workflow" in system.lower()
        assert "python" in system.lower()

    def test_compose_order(self, tmp_path):
        # create local overrides to control content
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("CORE")
        (templates / "first.md").write_text("FIRST")
        (templates / "second.md").write_text("SECOND")

        system = compose_system(tmp_path, ["first", "second"])
        # verify order: core, then conjurings in order
        assert system == "CORE\n\nFIRST\n\nSECOND"

    def test_compose_missing_profile_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown conjuring"):
            compose_system(tmp_path, ["nonexistent"])


class TestRenderInvocation:
    """tests for rendering invocations."""

    def test_render_with_args(self, tmp_path):
        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "greet.md").write_text("hello $1, {{style}}")

        result = render_invocation(tmp_path, "greet", ["world"], {"style": "friendly"})
        assert result == "hello world, friendly"

    def test_render_missing_invocation_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown invocation"):
            render_invocation(tmp_path, "nonexistent", [], {})


class TestListItems:
    """tests for listing conjurings and invocations."""

    def test_list_builtin_templates(self, tmp_path):
        items = list_items(tmp_path, "conjurings")
        names = [name for name, _, _ in items]
        assert "core" in names
        assert "python" in names
        assert "rust" in names

    def test_list_builtin_invocations(self, tmp_path):
        items = list_items(tmp_path, "invocations")
        names = [name for name, _, _ in items]
        assert "explain" in names
        assert "refactor" in names

    def test_list_excludes_underscore_files(self, tmp_path):
        items = list_items(tmp_path, "invocations")
        names = [name for name, _, _ in items]
        assert "__noop__" not in names

    def test_list_includes_first_line(self, tmp_path):
        items = list_items(tmp_path, "conjurings")
        core_items = [(n, f, loc) for n, f, loc in items if n == "core"]
        assert len(core_items) == 1
        _, first_line, _ = core_items[0]
        assert first_line  # not empty

    def test_list_local_override_marked(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("# local core")

        items = list_items(tmp_path, "conjurings")
        core_items = [(n, f, loc) for n, f, loc in items if n == "core"]
        assert len(core_items) == 1
        _, first_line, is_local = core_items[0]
        assert is_local is True
        assert first_line == "# local core"

    def test_list_local_custom_template(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "custom.md").write_text("# my custom")

        items = list_items(tmp_path, "conjurings")
        custom_items = [(n, f, loc) for n, f, loc in items if n == "custom"]
        assert len(custom_items) == 1
        _, first_line, is_local = custom_items[0]
        assert is_local is True
        assert first_line == "# my custom"

    def test_list_sorted(self, tmp_path):
        items = list_items(tmp_path, "conjurings")
        names = [name for name, _, _ in items]
        assert names == sorted(names)

    def test_list_empty_dir(self, tmp_path):
        # no local overrides, but still gets builtins
        items = list_items(tmp_path, "conjurings")
        assert len(items) > 0


class TestLoadSnippet:
    """tests for loading snippets."""

    def test_load_builtin_snippet(self, tmp_path):
        result = load_snippet(tmp_path, "python/pyproject.toml")
        assert "[project]" in result

    def test_local_override(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "python"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "pyproject.toml").write_text("custom pyproject")
        result = load_snippet(tmp_path, "python/pyproject.toml")
        assert result == "custom pyproject"

    def test_path_traversal_rejected(self, tmp_path):
        with pytest.raises(NotFoundError, match="invalid snippet path"):
            load_snippet(tmp_path, "../../../etc/passwd")

    def test_single_segment_rejected(self, tmp_path):
        with pytest.raises(NotFoundError, match="invalid snippet path"):
            load_snippet(tmp_path, "nosubdir")

    def test_unknown_snippet_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown snippet"):
            load_snippet(tmp_path, "nonexistent/file.txt")


class TestResolveIncludes:
    """tests for snippet include resolution."""

    def test_single_include(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "greeting.txt").write_text("hello world")

        text = "before {{> snippet:test/greeting.txt}} after"
        result = resolve_includes(tmp_path, text)
        assert result == "before hello world after"

    def test_multiple_includes(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "a.txt").write_text("AAA")
        (snippet_dir / "b.txt").write_text("BBB")

        text = "{{> snippet:test/a.txt}} and {{> snippet:test/b.txt}}"
        result = resolve_includes(tmp_path, text)
        assert result == "AAA and BBB"

    def test_missing_snippet_raises(self, tmp_path):
        text = "{{> snippet:nonexistent/file.txt}}"
        with pytest.raises(NotFoundError, match="unknown snippet"):
            resolve_includes(tmp_path, text)

    def test_include_before_substitute(self, tmp_path):
        """Include resolution happens before placeholder substitution."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "template.txt").write_text("name = $1")

        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "test.md").write_text("{{> snippet:test/template.txt}}")

        result = render_invocation(tmp_path, "test", ["myapp"], {})
        assert result == "name = myapp"

    def test_no_includes_unchanged(self, tmp_path):
        text = "no includes here, just {{named}} and $1"
        result = resolve_includes(tmp_path, text)
        assert result == text

    def test_whitespace_in_directive(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "file.txt").write_text("content")

        text = "{{>  snippet:test/file.txt  }}"
        result = resolve_includes(tmp_path, text)
        assert result == "content"


class TestListSnippets:
    """tests for listing snippets."""

    def test_list_builtin_snippets(self, tmp_path):
        items = list_snippets(tmp_path)
        paths = [path for path, _, _ in items]
        assert "python/pyproject.toml" in paths
        assert "rust/Cargo.toml" in paths

    def test_list_local_override_marked(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "python"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "pyproject.toml").write_text("custom")

        items = list_snippets(tmp_path)
        pyproject_items = [
            (p, f, loc) for p, f, loc in items if p == "python/pyproject.toml"
        ]
        assert len(pyproject_items) == 1
        _, _, is_local = pyproject_items[0]
        assert is_local is True

    def test_list_sorted(self, tmp_path):
        items = list_snippets(tmp_path)
        paths = [path for path, _, _ in items]
        assert paths == sorted(paths)

    def test_list_local_custom_snippet(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "custom"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "file.txt").write_text("first line here")

        items = list_snippets(tmp_path)
        custom_items = [(p, f, loc) for p, f, loc in items if p == "custom/file.txt"]
        assert len(custom_items) == 1
        _, first_line, is_local = custom_items[0]
        assert is_local is True
        assert first_line == "first line here"
