"""tests for familiar.render."""

from __future__ import annotations

import pytest

from familiar.render import (
    substitute,
    load_text,
    compose_system,
    render_invocation,
    list_items,
    NotFoundError,
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
    """tests for loading templates and invocations."""

    def test_load_builtin_template(self, tmp_path):
        result = load_text(tmp_path, "templates", "core")
        assert "# core profile" in result.lower() or "workflow" in result.lower()

    def test_load_builtin_invocation(self, tmp_path):
        result = load_text(tmp_path, "invocations", "explain")
        assert "explain" in result.lower()

    def test_local_override(self, tmp_path):
        override_dir = tmp_path / ".familiar" / "templates"
        override_dir.mkdir(parents=True)
        (override_dir / "core.md").write_text("custom core content")
        result = load_text(tmp_path, "templates", "core")
        assert result == "custom core content"

    def test_local_custom_template(self, tmp_path):
        override_dir = tmp_path / ".familiar" / "templates"
        override_dir.mkdir(parents=True)
        (override_dir / "custom.md").write_text("my custom template")
        result = load_text(tmp_path, "templates", "custom")
        assert result == "my custom template"

    def test_invalid_name_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="invalid"):
            load_text(tmp_path, "templates", "../../../etc/passwd")

    def test_unknown_template_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown template"):
            load_text(tmp_path, "templates", "nonexistent")

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
        templates = tmp_path / ".familiar" / "templates"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("CORE")
        (templates / "first.md").write_text("FIRST")
        (templates / "second.md").write_text("SECOND")

        system = compose_system(tmp_path, ["first", "second"])
        # verify order: core, then conjurings in order
        assert system == "CORE\n\nFIRST\n\nSECOND"

    def test_compose_missing_profile_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown template"):
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
    """tests for listing templates and invocations."""

    def test_list_builtin_templates(self, tmp_path):
        items = list_items(tmp_path, "templates")
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
        items = list_items(tmp_path, "templates")
        core_items = [(n, f, loc) for n, f, loc in items if n == "core"]
        assert len(core_items) == 1
        _, first_line, _ = core_items[0]
        assert first_line  # not empty

    def test_list_local_override_marked(self, tmp_path):
        templates = tmp_path / ".familiar" / "templates"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("# local core")

        items = list_items(tmp_path, "templates")
        core_items = [(n, f, loc) for n, f, loc in items if n == "core"]
        assert len(core_items) == 1
        _, first_line, is_local = core_items[0]
        assert is_local is True
        assert first_line == "# local core"

    def test_list_local_custom_template(self, tmp_path):
        templates = tmp_path / ".familiar" / "templates"
        templates.mkdir(parents=True)
        (templates / "custom.md").write_text("# my custom")

        items = list_items(tmp_path, "templates")
        custom_items = [(n, f, loc) for n, f, loc in items if n == "custom"]
        assert len(custom_items) == 1
        _, first_line, is_local = custom_items[0]
        assert is_local is True
        assert first_line == "# my custom"

    def test_list_sorted(self, tmp_path):
        items = list_items(tmp_path, "templates")
        names = [name for name, _, _ in items]
        assert names == sorted(names)

    def test_list_empty_dir(self, tmp_path):
        # no local overrides, but still gets builtins
        items = list_items(tmp_path, "templates")
        assert len(items) > 0
