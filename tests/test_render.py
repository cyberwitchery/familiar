"""tests for familiar.render."""

from __future__ import annotations

import pytest

from familiar.render import (
    _MAX_INCLUDE_DEPTH,
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

    def test_missing_named_warns(self, capsys):
        text = "spec: {{spec}}"
        result = substitute(text, [], {})
        assert result == "spec: {{spec}}"
        captured = capsys.readouterr()
        assert "warning: missing arguments: {{spec}}" in captured.err

    def test_present_named_no_warning(self, capsys):
        text = "spec: {{spec}}"
        result = substitute(text, [], {"spec": "caching"})
        assert result == "spec: caching"
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_missing_mixed_reports_both(self, capsys):
        text = "$1 and {{spec}} and $2"
        result = substitute(text, ["only_one"], {})
        assert result == "only_one and {{spec}} and "
        captured = capsys.readouterr()
        assert "warning: missing arguments: {{spec}}, $2" in captured.err


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

    def test_permission_denied_raises(self, tmp_path):
        override_dir = tmp_path / ".familiar" / "conjurings"
        override_dir.mkdir(parents=True)
        f = override_dir / "locked.md"
        f.write_text("content")
        f.chmod(0o000)
        try:
            with pytest.raises(NotFoundError, match="permission denied"):
                load_text(tmp_path, "conjurings", "locked")
        finally:
            f.chmod(0o644)

    def test_invalid_utf8_raises(self, tmp_path):
        override_dir = tmp_path / ".familiar" / "conjurings"
        override_dir.mkdir(parents=True)
        (override_dir / "binary.md").write_bytes(b"\xff\xfe invalid utf-8")
        with pytest.raises(NotFoundError, match="not valid UTF-8"):
            load_text(tmp_path, "conjurings", "binary")


class TestComposeSystem:
    """tests for composing system prompts."""

    def test_compose_with_conjurings(self, tmp_path):
        system = compose_system(tmp_path, ["python"])
        assert "core" in system.lower() or "workflow" in system.lower()
        assert "python" in system.lower()

    def test_compose_order(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("CORE")
        (templates / "first.md").write_text("FIRST")
        (templates / "second.md").write_text("SECOND")

        system = compose_system(tmp_path, ["first", "second"])
        assert system == "CORE\n\nFIRST\n\nSECOND"

    def test_compose_core_only(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("CORE")

        system = compose_system(tmp_path, [])
        assert system == "CORE"

    def test_compose_multiple_conjurings(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("CORE")
        (templates / "a.md").write_text("A")
        (templates / "b.md").write_text("B")
        (templates / "c.md").write_text("C")

        system = compose_system(tmp_path, ["a", "b", "c"])
        assert system == "CORE\n\nA\n\nB\n\nC"

    def test_compose_strips_whitespace(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("  CORE  \n")
        (templates / "pad.md").write_text("\n  PAD  \n\n")

        system = compose_system(tmp_path, ["pad"])
        assert system == "CORE\n\nPAD"

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

    def test_render_with_snippet_and_args(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets" / "test"
        snippets.mkdir(parents=True)
        (snippets / "header.txt").write_text("== $1 ==")

        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "demo.md").write_text(
            "{{> snippet:test/header.txt}}\nbody: {{mode}}"
        )

        result = render_invocation(tmp_path, "demo", ["title"], {"mode": "fast"})
        assert result == "== title ==\nbody: fast"

    def test_render_no_args(self, tmp_path):
        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "plain.md").write_text("no placeholders here")

        result = render_invocation(tmp_path, "plain", [], {})
        assert result == "no placeholders here"

    def test_render_arguments_placeholder(self, tmp_path):
        invocations = tmp_path / ".familiar" / "invocations"
        invocations.mkdir(parents=True)
        (invocations / "all.md").write_text("run $ARGUMENTS")

        result = render_invocation(tmp_path, "all", ["a", "b", "c"], {})
        assert result == "run a b c"

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

    def test_list_skips_invalid_utf8_local(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "good.md").write_text("# good file")
        (templates / "bad.md").write_bytes(b"\xff\xfe not utf-8")

        items = list_items(tmp_path, "conjurings")
        names = [name for name, _, _ in items]
        assert "good" in names
        assert "bad" not in names

    def test_list_skips_permission_denied_local(self, tmp_path):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "good.md").write_text("# good file")
        locked = templates / "locked.md"
        locked.write_text("content")
        locked.chmod(0o000)
        try:
            items = list_items(tmp_path, "conjurings")
            names = [name for name, _, _ in items]
            assert "good" in names
            assert "locked" not in names
        finally:
            locked.chmod(0o644)


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

    def test_permission_denied_raises(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        f = snippet_dir / "locked.txt"
        f.write_text("content")
        f.chmod(0o000)
        try:
            with pytest.raises(NotFoundError, match="permission denied"):
                load_snippet(tmp_path, "test/locked.txt")
        finally:
            f.chmod(0o644)

    def test_invalid_utf8_raises(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "binary.txt").write_bytes(b"\xff\xfe invalid utf-8")
        with pytest.raises(NotFoundError, match="not valid UTF-8"):
            load_snippet(tmp_path, "test/binary.txt")


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

    def test_nonexistent_among_valid_raises(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "good.txt").write_text("ok")

        text = "{{> snippet:test/good.txt}} {{> snippet:test/missing.txt}}"
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

    def test_nested_include_resolves(self, tmp_path):
        """a snippet that includes another snippet is expanded fully."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "outer.txt").write_text("outer[{{> snippet:test/inner.txt}}]")
        (snippet_dir / "inner.txt").write_text("INNER")

        result = resolve_includes(tmp_path, "{{> snippet:test/outer.txt}}")
        assert result == "outer[INNER]"
        assert "{{> snippet" not in result

    def test_deeply_nested_include_resolves(self, tmp_path):
        """nested includes resolve through several levels."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "a.txt").write_text("a({{> snippet:test/b.txt}})")
        (snippet_dir / "b.txt").write_text("b({{> snippet:test/c.txt}})")
        (snippet_dir / "c.txt").write_text("c")

        result = resolve_includes(tmp_path, "{{> snippet:test/a.txt}}")
        assert result == "a(b(c))"

    def test_self_include_raises_cycle(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "loop.txt").write_text("{{> snippet:test/loop.txt}}")

        with pytest.raises(NotFoundError, match="snippet include cycle") as exc:
            resolve_includes(tmp_path, "{{> snippet:test/loop.txt}}")
        assert "test/loop.txt -> test/loop.txt" in str(exc.value)

    def test_mutual_include_raises_cycle(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "a.txt").write_text("{{> snippet:test/b.txt}}")
        (snippet_dir / "b.txt").write_text("{{> snippet:test/a.txt}}")

        with pytest.raises(NotFoundError, match="snippet include cycle") as exc:
            resolve_includes(tmp_path, "{{> snippet:test/a.txt}}")
        assert "test/a.txt" in str(exc.value)
        assert "test/b.txt" in str(exc.value)

    def test_include_depth_backstop(self, tmp_path):
        """an over-deep acyclic chain raises rather than recursing without bound."""
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        chain_len = _MAX_INCLUDE_DEPTH + 2
        for i in range(chain_len):
            if i < chain_len - 1:
                body = "{{> snippet:test/s" + str(i + 1) + ".txt}}"
            else:
                body = "end"
            (snippet_dir / f"s{i}.txt").write_text(body)

        with pytest.raises(NotFoundError, match="depth exceeded"):
            resolve_includes(tmp_path, "{{> snippet:test/s0.txt}}")


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

    def test_local_override_preserves_other_builtins(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "python"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "pyproject.toml").write_text("custom")

        items = list_snippets(tmp_path)
        lookup = {p: (f, loc) for p, f, loc in items}
        assert lookup["python/pyproject.toml"][1] is True
        assert "rust/Cargo.toml" in lookup
        assert lookup["rust/Cargo.toml"][1] is False

    def test_local_underscore_files_excluded(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "_hidden.txt").write_text("should not appear")
        (snippet_dir / "visible.txt").write_text("should appear")

        items = list_snippets(tmp_path)
        paths = [p for p, _, _ in items]
        assert "test/visible.txt" in paths
        assert "test/_hidden.txt" not in paths

    def test_list_snippets_skips_invalid_utf8(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "good.txt").write_text("good content")
        (snippet_dir / "bad.txt").write_bytes(b"\xff\xfe not utf-8")

        items = list_snippets(tmp_path)
        local_paths = [p for p, _, is_local in items if is_local]
        assert "test/good.txt" in local_paths
        assert "test/bad.txt" not in local_paths
