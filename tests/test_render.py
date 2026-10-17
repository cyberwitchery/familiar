"""tests for familiar.render."""

from __future__ import annotations

import os
import re
from importlib import resources

import pytest

from familiar.render import (
    _MAX_INCLUDE_DEPTH,
    NotFoundError,
    UnreadableError,
    compose_system,
    list_items,
    list_snippets,
    load_snippet,
    load_text,
    render_invocation,
    resolve_includes,
    substitute,
)


def _locked(path):
    path.write_text("content")
    path.chmod(0o000)


def _invalid_utf8(path):
    path.write_bytes(b"\xff\xfe invalid utf-8")


def _directory(path):
    path.mkdir()


def _symlink_loop(path):
    path.symlink_to(path.name)


def _dangling_symlink(path):
    path.symlink_to(path.parent / "gone")


def _nothing(path):
    pass


class TestSubstitute:
    """tests for placeholder substitution."""

    @pytest.mark.parametrize(
        ("text", "args", "kv", "expected"),
        [
            ("hello $1 and $2", ["world", "friends"], {}, "hello world and friends"),
            ("args: $ARGUMENTS", ["one", "two", "three"], {}, "args: one two three"),
            (
                "name: {{name}}, value: {{value}}",
                [],
                {"name": "foo", "value": "bar"},
                "name: foo, value: bar",
            ),
            (
                "$1 says {{greeting}}",
                ["alice"],
                {"greeting": "hello"},
                "alice says hello",
            ),
            ("just {{used}}", [], {"used": "yes", "unused": "no"}, "just yes"),
            ("$ARGUMENTS", [], {}, ""),
            ("$2 before $1", ["first", "second"], {}, "second before first"),
        ],
        ids=[
            "positional",
            "arguments",
            "named",
            "mixed",
            "unused-kv-ignored",
            "empty-args",
            "positional-out-of-order",
        ],
    )
    def test_substitutes(self, text, args, kv, expected):
        assert substitute(text, args, kv) == expected

    @pytest.mark.parametrize(
        ("text", "args", "kv", "expected", "stderr"),
        [
            (
                "need $1 and $2 and $3",
                ["only_one"],
                {},
                "need only_one and  and ",
                "warning: missing arguments: $2, $3\n",
            ),
            (
                "spec: {{spec}}",
                [],
                {},
                "spec: {{spec}}",
                "warning: missing arguments: {{spec}}\n",
            ),
            ("spec: {{spec}}", [], {"spec": "caching"}, "spec: caching", ""),
            (
                "$1 and {{spec}} and $2",
                ["only_one"],
                {},
                "only_one and {{spec}} and ",
                "warning: missing arguments: {{spec}}, $2\n",
            ),
        ],
        ids=["missing-positional", "missing-named", "present-named", "missing-mixed"],
    )
    def test_missing_arguments_warn(self, capsys, text, args, kv, expected, stderr):
        assert substitute(text, args, kv) == expected
        assert capsys.readouterr().err == stderr


class TestLoadText:
    """tests for loading conjurings and invocations."""

    @pytest.mark.parametrize(
        ("kind", "name"), [("conjurings", "core"), ("invocations", "explain")]
    )
    def test_load_builtin(self, tmp_path, kind, name):
        packaged = resources.files(f"familiar.data.{kind}") / f"{name}.md"
        assert load_text(tmp_path, kind, name) == packaged.read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        ("name", "content"),
        [("core", "custom core content"), ("custom", "my custom template")],
        ids=["override", "new-item"],
    )
    def test_local_file(self, tmp_path, name, content):
        override_dir = tmp_path / ".familiar" / "conjurings"
        override_dir.mkdir(parents=True)
        (override_dir / f"{name}.md").write_text(content)
        assert load_text(tmp_path, "conjurings", name) == content

    @pytest.mark.parametrize("name", ["../../../etc/passwd", "abc\n"])
    def test_invalid_name_raises(self, tmp_path, name):
        with pytest.raises(NotFoundError, match="invalid conjuring name"):
            load_text(tmp_path, "conjurings", name)

    @pytest.mark.parametrize("kind", ["conjurings", "invocations"])
    def test_unknown_item_raises(self, tmp_path, kind):
        with pytest.raises(
            NotFoundError, match=f"unknown {kind[:-1]}: nonexistent"
        ) as e:
            load_text(tmp_path, kind, "nonexistent")
        assert type(e.value) is NotFoundError

    @pytest.mark.parametrize(
        ("make", "name", "detail"),
        [
            (_locked, "locked", "permission denied"),
            (_invalid_utf8, "binary", "not valid UTF-8"),
            (_directory, "nested", "is not a regular file"),
            (_nothing, "a" * 300, ""),
            (_symlink_loop, "python", ""),
            (_dangling_symlink, "python", ""),
        ],
        ids=[
            "permission-denied",
            "invalid-utf8",
            "directory",
            "overlong-name",
            "symlink-loop",
            "dangling-symlink",
        ],
    )
    def test_unreadable_override_raises(self, tmp_path, make, name, detail):
        override_dir = tmp_path / ".familiar" / "conjurings"
        override_dir.mkdir(parents=True)
        make(override_dir / f"{name}.md")
        with pytest.raises(
            UnreadableError, match=f"^cannot read conjuring '{name}': .*{detail}"
        ):
            load_text(tmp_path, "conjurings", name)


class TestComposeSystem:
    """tests for composing system prompts."""

    def test_compose_with_conjurings(self, tmp_path):
        conjurings = resources.files("familiar.data.conjurings")
        core = (conjurings / "core.md").read_text(encoding="utf-8")
        python = (conjurings / "python.md").read_text(encoding="utf-8")
        system = compose_system(tmp_path, ["python"])
        assert system == core.strip() + "\n\n" + python.strip()

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

    def test_compose_expands_include(self, tmp_path):
        """a conjuring with a valid snippet include is expanded, not left verbatim."""
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("CORE")
        (templates / "guide.md").write_text("see {{> snippet:test/rules.txt}}")
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "rules.txt").write_text("be precise")

        system = compose_system(tmp_path, ["guide"])
        assert system == "CORE\n\nsee be precise"
        assert "{{> snippet" not in system

    def test_compose_expands_include_in_core(self, tmp_path):
        """includes in the core conjuring are expanded too."""
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("core: {{> snippet:test/base.txt}}")
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "base.txt").write_text("BASE")

        system = compose_system(tmp_path, [])
        assert system == "core: BASE"

    def test_compose_expands_nested_include(self, tmp_path):
        """a snippet included by a conjuring may itself include other snippets."""
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "core.md").write_text("CORE")
        (templates / "guide.md").write_text("{{> snippet:test/outer.txt}}")
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "outer.txt").write_text("outer[{{> snippet:test/inner.txt}}]")
        (snippet_dir / "inner.txt").write_text("INNER")

        system = compose_system(tmp_path, ["guide"])
        assert system == "CORE\n\nouter[INNER]"


class TestRenderInvocation:
    """tests for rendering invocations."""

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
        core = resources.files("familiar.data.conjurings") / "core.md"
        expected = next(
            line.strip()
            for line in core.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        items = list_items(tmp_path, "conjurings")
        assert [item for item in items if item[0] == "core"] == [
            ("core", expected, False)
        ]

    @pytest.mark.parametrize(
        ("name", "content", "first_line"),
        [
            ("core", "# local core", "# local core"),
            ("custom", "# my custom", "# my custom"),
            ("custom", "\n  \n# my custom\n", "# my custom"),
            ("custom", "\n  \n", ""),
        ],
        ids=["override", "new-item", "leading-blank-lines", "blank-only"],
    )
    def test_list_local_item(self, tmp_path, name, content, first_line):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / f"{name}.md").write_text(content)

        items = list_items(tmp_path, "conjurings")
        assert [item for item in items if item[0] == name] == [(name, first_line, True)]

    def test_list_sorted(self, tmp_path):
        items = list_items(tmp_path, "conjurings")
        names = [name for name, _, _ in items]
        assert names == sorted(names)

    @pytest.mark.parametrize(
        ("make", "name"),
        [
            (_invalid_utf8, "bad"),
            (_locked, "locked"),
            (_invalid_utf8, "python"),
            (_dangling_symlink, "dangling"),
            (_directory, "nested"),
        ],
        ids=[
            "invalid-utf8",
            "permission-denied",
            "override-of-builtin",
            "dangling-symlink",
            "directory",
        ],
    )
    def test_list_marks_local_unreadable(self, tmp_path, make, name):
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "good.md").write_text("# good file")
        make(templates / f"{name}.md")

        items = list_items(tmp_path, "conjurings")
        assert ("good", "# good file", True) in items
        assert [item for item in items if item[0] == name] == [(name, None, True)]


class TestLoadSnippet:
    """tests for loading snippets."""

    def test_load_builtin_snippet(self, tmp_path):
        packaged = (
            resources.files("familiar.data.snippets") / "python" / "pyproject.toml"
        )
        result = load_snippet(tmp_path, "python/pyproject.toml")
        assert result == packaged.read_text(encoding="utf-8")

    def test_local_override(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "python"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "pyproject.toml").write_text("custom pyproject")
        result = load_snippet(tmp_path, "python/pyproject.toml")
        assert result == "custom pyproject"

    @pytest.mark.parametrize(
        "path",
        ["../../../etc/passwd", "nosubdir", "python/github ci.yml"],
        ids=["traversal", "single-segment", "invalid-character-after-valid-prefix"],
    )
    def test_invalid_path_rejected(self, tmp_path, path):
        with pytest.raises(NotFoundError, match="invalid snippet path"):
            load_snippet(tmp_path, path)

    def test_unknown_snippet_raises(self, tmp_path):
        with pytest.raises(NotFoundError, match="unknown snippet"):
            load_snippet(tmp_path, "nonexistent/file.txt")

    @pytest.mark.parametrize(
        ("make", "path", "detail"),
        [
            (_locked, "test/locked.txt", "permission denied"),
            (_invalid_utf8, "test/binary.txt", "not valid UTF-8"),
            (_directory, "test/nested", "is not a regular file"),
            (_nothing, "test/" + "a" * 300, ""),
            (_symlink_loop, "python/pyproject.toml", ""),
            (_dangling_symlink, "python/pyproject.toml", ""),
        ],
        ids=[
            "permission-denied",
            "invalid-utf8",
            "directory",
            "overlong-name",
            "symlink-loop",
            "dangling-symlink",
        ],
    )
    def test_unreadable_override_raises(self, tmp_path, make, path, detail):
        override = tmp_path / ".familiar" / "snippets" / path
        override.parent.mkdir(parents=True)
        make(override)
        with pytest.raises(
            UnreadableError,
            match=f"^cannot read snippet '{re.escape(path)}': .*{detail}",
        ):
            load_snippet(tmp_path, path)


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

        with pytest.raises(
            NotFoundError,
            match="^snippet include cycle: test/a.txt -> test/b.txt -> test/a.txt$",
        ):
            resolve_includes(tmp_path, "{{> snippet:test/a.txt}}")

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

    def test_list_snippets_marks_invalid_utf8_unreadable(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "good.txt").write_text("good content")
        (snippet_dir / "bad.txt").write_bytes(b"\xff\xfe not utf-8")

        items = list_snippets(tmp_path)
        assert ("test/good.txt", "good content", True) in items
        assert ("test/bad.txt", None, True) in items

    def test_list_snippets_marks_permission_denied_unreadable(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        locked = snippet_dir / "locked.txt"
        locked.write_text("content")
        locked.chmod(0o000)
        try:
            assert ("test/locked.txt", None, True) in list_snippets(tmp_path)
        finally:
            locked.chmod(0o644)


needs_fifo = pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs os.mkfifo")
not_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores file modes"
)


def _make_dir(path, tmp_path):
    path.mkdir()


def _make_fifo(path, tmp_path):
    os.mkfifo(path)


def _link_to_dir(path, tmp_path):
    (tmp_path / "target").mkdir()
    path.symlink_to(tmp_path / "target")


def _link_to_fifo(path, tmp_path):
    os.mkfifo(tmp_path / "target")
    path.symlink_to(tmp_path / "target")


_NOT_A_FILE = [
    _make_dir,
    pytest.param(_make_fifo, marks=needs_fifo),
    _link_to_dir,
    pytest.param(_link_to_fifo, marks=needs_fifo),
]


def _make_deep_file(root, depth):
    """create ``x.md`` under ``depth`` nested 250-character directories."""
    root.mkdir(parents=True)
    fd = os.open(root, os.O_RDONLY)
    try:
        for _ in range(depth):
            os.mkdir("d" * 250, dir_fd=fd)
            child = os.open("d" * 250, os.O_RDONLY, dir_fd=fd)
            os.close(fd)
            fd = child
        os.close(os.open("x.md", os.O_WRONLY | os.O_CREAT, 0o644, dir_fd=fd))
    finally:
        os.close(fd)


class TestLocalOverrideProbe:
    """listing and loading agree on what sits where a local override belongs."""

    @pytest.mark.parametrize("make", _NOT_A_FILE)
    def test_non_file_conjuring_is_local_and_unreadable(
        self, tmp_path, without_blocking, make
    ):
        override = tmp_path / ".familiar" / "conjurings" / "python.md"
        override.parent.mkdir(parents=True)
        make(override, tmp_path)

        items = without_blocking(list_items, tmp_path, "conjurings")
        assert [item for item in items if item[0] == "python"] == [
            ("python", None, True)
        ]
        with pytest.raises(UnreadableError, match="is not a regular file"):
            without_blocking(load_text, tmp_path, "conjurings", "python")

    @pytest.mark.parametrize("make", _NOT_A_FILE)
    def test_non_file_snippet_is_local_and_unreadable(
        self, tmp_path, without_blocking, make
    ):
        override = tmp_path / ".familiar" / "snippets" / "python" / "pyproject.toml"
        override.parent.mkdir(parents=True)
        make(override, tmp_path)

        items = without_blocking(list_snippets, tmp_path)
        assert [item for item in items if item[0] == "python/pyproject.toml"] == [
            ("python/pyproject.toml", None, True)
        ]
        with pytest.raises(UnreadableError, match="is not a regular file"):
            without_blocking(load_snippet, tmp_path, "python/pyproject.toml")

    def test_symlink_to_file_is_an_override(self, tmp_path):
        conjurings = tmp_path / ".familiar" / "conjurings"
        conjurings.mkdir(parents=True)
        (tmp_path / "mine.md").write_text("# mine\n")
        (conjurings / "python.md").symlink_to(tmp_path / "mine.md")

        assert ("python", "# mine", True) in list_items(tmp_path, "conjurings")
        assert load_text(tmp_path, "conjurings", "python") == "# mine\n"

    def test_snippet_directories_are_descended_not_listed(self, tmp_path):
        nested = tmp_path / ".familiar" / "snippets" / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "c.md").write_text("deep")

        local = [path for path, _, is_local in list_snippets(tmp_path) if is_local]
        assert local == ["a/b/c.md"]

    @not_root
    def test_unsearchable_conjurings_dir_lists_entries_unreadable(self, tmp_path):
        conjurings = tmp_path / ".familiar" / "conjurings"
        conjurings.mkdir(parents=True)
        (conjurings / "python.md").write_text("# mine")
        (conjurings / "custom.md").write_text("# custom")
        conjurings.chmod(0o644)
        try:
            items = list_items(tmp_path, "conjurings")
            with pytest.raises(UnreadableError, match="Permission denied"):
                load_text(tmp_path, "conjurings", "custom")
        finally:
            conjurings.chmod(0o755)

        assert ("python", None, True) in items
        assert ("custom", None, True) in items

    @not_root
    def test_unsearchable_snippet_dir_lists_entries_unreadable(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets"
        (snippets / "ok").mkdir(parents=True)
        (snippets / "ok" / "y.md").write_text("fine")
        (snippets / "sub").mkdir()
        (snippets / "sub" / "x.md").write_text("hidden")
        (snippets / "sub").chmod(0o644)
        try:
            items = list_snippets(tmp_path)
            with pytest.raises(UnreadableError, match="Permission denied"):
                load_snippet(tmp_path, "sub/x.md")
        finally:
            (snippets / "sub").chmod(0o755)

        assert ("sub/x.md", None, True) in items
        assert ("ok/y.md", "fine", True) in items

    @not_root
    def test_unsearchable_familiar_dir_marks_builtins_unreadable(self, tmp_path):
        (tmp_path / ".familiar" / "conjurings").mkdir(parents=True)
        (tmp_path / ".familiar").chmod(0o644)
        try:
            items = list_items(tmp_path, "conjurings")
            with pytest.raises(UnreadableError, match="Permission denied"):
                load_text(tmp_path, "conjurings", "python")
        finally:
            (tmp_path / ".familiar").chmod(0o755)

        assert ("python", None, True) in items

    @pytest.mark.skipif(
        os.mkdir not in os.supports_dir_fd, reason="needs mkdir with dir_fd"
    )
    def test_path_too_long_does_not_abort_listing(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets"
        _make_deep_file(snippets / "deep", depth=20)
        (snippets / "ok").mkdir()
        (snippets / "ok" / "y.md").write_text("fine")

        assert ("ok/y.md", "fine", True) in list_snippets(tmp_path)
