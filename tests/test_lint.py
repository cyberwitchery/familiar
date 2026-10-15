"""tests for familiar.lint."""

from __future__ import annotations

import os
import re
from unittest.mock import MagicMock, patch

import pytest

from familiar.lint import (
    LintMessage,
    _unfenced_lines,
    lint_all,
    lint_collection,
    lint_invocation,
    lint_snippet_collection,
    lint_snippet_placeholders,
    lint_snippet_references,
    lint_template,
    load_linters,
)
from familiar.render import _MAX_INCLUDE_DEPTH

INPUTS_MISSING = LintMessage(
    "warning", "test.md", None, "invocation should have an 'inputs' section"
)
OUTPUT_MISSING = LintMessage(
    "warning",
    "test.md",
    None,
    "invocation should have an 'output' or 'deliverables' section",
)
TARGET_UNDOCUMENTED = LintMessage(
    "warning",
    "test.md",
    None,
    "placeholder '{{target}}' may not be documented in inputs",
)


def _locked(path):
    path.write_text("content")
    path.chmod(0o000)


def _invalid_utf8(path):
    path.write_bytes(b"caf\xe9\n")


def _dangling_symlink(path):
    path.symlink_to(path.parent / "gone")


class TestLintTemplate:
    """tests for template linting."""

    def test_valid_template(self):
        content = "# my template\n\nsome content"
        messages = lint_template(content, "test.md")
        assert messages == []

    @pytest.mark.parametrize("content", ["", "\n", "  \n\t\n", "\r\n\r\n"])
    def test_whitespace_only_template_is_empty(self, content):
        messages = lint_template(content, "test.md")
        assert messages == [LintMessage("error", "test.md", 1, "template is empty")]

    @pytest.mark.parametrize(
        "content", ["\n# my template\n\nbody\n", "\r\n  \r\n# my template\r\n"]
    )
    def test_heading_after_leading_blank_lines(self, content):
        assert lint_template(content, "test.md") == []

    @pytest.mark.parametrize(
        ("content", "line"),
        [("\n  \nno heading here\n", 3), ("no heading here\njust text", 1)],
        ids=["after-leading-blank-lines", "first-line"],
    )
    def test_missing_heading(self, content, line):
        assert lint_template(content, "test.md") == [
            LintMessage(
                "warning",
                "test.md",
                line,
                "template should start with a markdown heading (# ...)",
            )
        ]


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

    @pytest.mark.parametrize("content", ["", "\n", "  \n\t\n", "\r\n\r\n"])
    def test_whitespace_only_invocation_is_empty(self, content):
        messages = lint_invocation(content, "test.md")
        assert messages == [LintMessage("error", "test.md", 1, "invocation is empty")]

    @pytest.mark.parametrize("newline", ["\n", "\r\n"])
    def test_task_line_after_leading_blank_lines(self, newline):
        content = newline.join(
            [
                "",
                "  ",
                "task: do something",
                "",
                "inputs",
                "- $ARGUMENTS",
                "",
                "output",
                "- results",
                "",
            ]
        )
        assert lint_invocation(content, "test.md") == []

    @pytest.mark.parametrize(
        ("content", "line"),
        [
            ("\n\nsome random text\n\ninputs\n- $1 name\n\noutput\n- results\n", 3),
            ("some random text\n\ninputs\n- $1 name\n\noutput\n- results\n", 1),
        ],
        ids=["after-leading-blank-lines", "first-line"],
    )
    def test_missing_task_line(self, content, line):
        assert lint_invocation(content, "test.md") == [
            LintMessage(
                "warning",
                "test.md",
                line,
                "invocation should start with 'task:' or similar verb",
            )
        ]

    def test_missing_inputs_section(self):
        content = """task: do something

output
- results
"""
        messages = lint_invocation(content, "test.md")
        assert messages == [INPUTS_MISSING]

    def test_missing_output_section(self):
        content = """task: do something

inputs
- $ARGUMENTS
"""
        messages = lint_invocation(content, "test.md")
        assert messages == [OUTPUT_MISSING]

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

    @pytest.mark.parametrize(
        ("inputs", "output"),
        [
            ("arguments:\n- $1 name", "output"),
            ("inputs\n- $ARGUMENTS", "deliverables"),
            ("inputs\n- $ARGUMENTS", "outputs"),
        ],
        ids=["arguments", "deliverables", "outputs"],
    )
    def test_accepts_section_label(self, inputs, output):
        content = f"task: do something\n\n{inputs}\n\n{output}\n- results\n"
        assert lint_invocation(content, "test.md") == []

    @pytest.mark.parametrize(
        ("task", "inputs", "expected"),
        [
            (
                "do something with {{myarg}}",
                "- $ARGUMENTS",
                ["placeholder '{{myarg}}' may not be documented in inputs"],
            ),
            ("do something with {{myarg}}", "- myarg (required): the argument", []),
            (
                "process {{name}}",
                "- filename (required): the file to process",
                ["placeholder '{{name}}' may not be documented in inputs"],
            ),
            ("implement {{spec}}", "- {{spec}} (required): feature specification", []),
        ],
        ids=[
            "undocumented",
            "documented",
            "substring-in-other-word",
            "tag-in-inputs-section",
        ],
    )
    def test_placeholder_documentation(self, task, inputs, expected):
        content = f"task: {task}\n\ninputs\n{inputs}\n\noutput\n- results\n"
        messages = lint_invocation(content, "test.md")
        assert messages == [
            LintMessage("warning", "test.md", None, message) for message in expected
        ]

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            pytest.param(
                """```sh
# run it like this
familiar invoke thing
```

- {{target}}: the file to operate on

## output

- results
""",
                [],
                id="fenced-example-does-not-end-inputs-section",
            ),
            pytest.param(
                """~~~
# run it like this
~~~

- {{target}}: the file to operate on

## output

- results
""",
                [],
                id="tilde-fenced-example-does-not-end-inputs-section",
            ),
            pytest.param(
                """```sh
# run it like this
```

- other: something else

## notes

- {{target}} is described here, outside the inputs section

## output

- results
""",
                [TARGET_UNDOCUMENTED],
                id="heading-after-fence-still-ends-inputs-section",
            ),
            pytest.param(
                """```sh
# run it like this

## output

- {{target}}: the file to operate on
""",
                [OUTPUT_MISSING],
                id="unclosed-fence-runs-to-end-of-file",
            ),
            pytest.param(
                """```familiar lint``` validates these files before you commit.

- ctx: the surrounding context

## output

- results mentioning {{target}}
""",
                [TARGET_UNDOCUMENTED],
                id="inline-code-line-does-not-open-a-fence",
            ),
            pytest.param(
                """~~~
```
# run it like this
~~~

- {{target}}: the file to operate on

## output

- results
""",
                [],
                id="backtick-fence-does-not-close-a-tilde-fence",
            ),
            pytest.param(
                """````
```
# run it like this
````

- {{target}}: the file to operate on

## output

- results
""",
                [],
                id="shorter-fence-does-not-close-a-longer-fence",
            ),
            pytest.param(
                """```
```python
# run it like this
```

- {{target}}: the file to operate on

## output

- results
""",
                [],
                id="fence-with-info-string-does-not-close-a-fence",
            ),
        ],
    )
    def test_fences_in_inputs_section(self, body, expected):
        content = "task: do something with {{target}}\n\n## inputs\n\n" + body
        assert lint_invocation(content, "test.md") == expected

    def test_fenced_inputs_heading_does_not_count_as_the_section(self):
        content = """task: show how to write an invocation

here is the shape of one:

```md
## inputs

- {{thing}}: a thing

## output

- results
```
"""
        messages = lint_invocation(content, "test.md")
        assert messages == [INPUTS_MISSING, OUTPUT_MISSING]

    def test_tilde_fenced_output_heading_does_not_count_as_the_section(self):
        content = """task: show how to write an invocation

## inputs

- ctx: the surrounding context

~~~md
## output

- results
~~~
"""
        messages = lint_invocation(content, "test.md")
        assert messages == [OUTPUT_MISSING]

    def test_fenced_inputs_heading_does_not_anchor_placeholder_search(self):
        content = """task: do something with {{target}}

an example of what to write:

```md
## inputs

- example: a placeholder

## output

- example results
```

## inputs

- {{target}}: the file to operate on

## output

- results
"""
        messages = lint_invocation(content, "test.md")
        assert messages == []

    @pytest.mark.parametrize("label", ["", "## "])
    def test_inputs_section_ends_where_the_next_section_starts(self, label):
        content = """task: build something {{flavor}}

LABELinputs
- $1 crate_name (required): the crate to build

LABELsteps
- build it as {{flavor}}
- pass $2 crate_name along

LABELoutput
- results
""".replace("LABEL", label)
        messages = lint_invocation(content, "test.md")
        assert [m.message for m in messages] == [
            "placeholder '{{flavor}}' may not be documented in inputs",
            "placeholder '$2' may not be documented in inputs",
        ]

    def test_hash_line_that_is_not_a_heading_does_not_end_inputs_section(self):
        content = """task: do something with {{target}}

## inputs

#tag

- {{target}}: the file to operate on

## output

- results
"""
        assert lint_invocation(content, "test.md") == []

    def test_label_like_line_does_not_end_a_heading_inputs_section(self):
        content = """task: do something with {{target}}

## inputs

required:

- {{target}}: the file to operate on

## output

- results
"""
        assert lint_invocation(content, "test.md") == []

    def test_loose_list_stays_in_a_bare_inputs_section(self):
        content = """task: do something with {{target}} in {{mode}}

inputs

- {{target}}: the file to operate on

  relative to the repository root

- {{mode}}: how to operate on it

steps

- run it

output

- results
"""
        assert lint_invocation(content, "test.md") == []

    def test_heading_indented_three_spaces_ends_inputs_section(self):
        content = """task: do something with {{target}}

## inputs

other: something else

   ## notes

- {{target}} is described here, outside the inputs section

## output

- results
"""
        messages = lint_invocation(content, "test.md")
        assert [m.message for m in messages] == [
            "placeholder '{{target}}' may not be documented in inputs"
        ]

    @pytest.mark.parametrize(
        "example", ["    # run it like this", "- for example:\n  # run it like this"]
    )
    def test_indented_hash_line_does_not_end_inputs_section(self, example):
        content = """task: do something with {{target}}

## inputs

EXAMPLE

- {{target}}: the file to operate on

## output

- results
""".replace("EXAMPLE", example)
        assert lint_invocation(content, "test.md") == []

    def test_fenced_comment_does_not_end_a_bare_inputs_section(self):
        content = """task: do something with {{target}}

inputs

```sh
# run it like this
familiar invoke thing
```

- {{target}}: the file to operate on

output

- results
"""
        assert lint_invocation(content, "test.md") == []

    @pytest.mark.parametrize(
        "body",
        [
            (
                "| input | meaning |\n|-------|---------|\n"
                "| $1 crate_name | the crate to build |\n"
                "| {{flavor}} | `debug` or `release` |"
            ),
            "{{flavor}} is the build flavor and $1 crate_name the crate to build",
        ],
    )
    def test_table_or_prose_stays_in_a_bare_inputs_section(self, body):
        content = """task: build something {{flavor}}

inputs

BODY

steps
- build $1 crate_name as {{flavor}}

output
- the build log
""".replace("BODY", body)
        assert lint_invocation(content, "test.md") == []

    @pytest.mark.parametrize("label", ["Steps:", "steps (in order)"])
    def test_label_with_colon_or_parenthetical_ends_a_bare_inputs_section(self, label):
        content = """task: build something {{flavor}}

inputs
- $1 crate_name: the crate to build

LABEL
- build $1 crate_name as {{flavor}}

output
- the build log
""".replace("LABEL", label)
        assert [m.message for m in lint_invocation(content, "test.md")] == [
            "placeholder '{{flavor}}' may not be documented in inputs"
        ]

    @pytest.mark.parametrize(
        "body",
        [
            "required:\n- {{target}}: the file to operate on\n- {{mode}}: how",
            (
                "- {{target}}: the file to operate on, relative to the repository\n"
                "root\n"
                "- {{mode}}: how to operate on it"
            ),
            (
                "\n<details>\nexample\n</details>\n\n"
                "- {{target}}: the file to operate on\n"
                "- {{mode}}: how to operate on it"
            ),
        ],
    )
    def test_continued_paragraph_and_html_stay_in_a_bare_inputs_section(self, body):
        content = """task: do something with {{target}} in {{mode}}

inputs
BODY

output

- results
""".replace("BODY", body)
        assert lint_invocation(content, "test.md") == []

    def test_positional_placeholder_not_matched_as_prefix(self):
        content = """task: process $1 and $10

## inputs

- ctx: $10 the tenth argument

## output

- results
"""
        messages = lint_invocation(content, "test.md")
        assert [m.message for m in messages] == [
            "placeholder '$1' may not be documented in inputs"
        ]

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


class TestContainerAwareFences:
    """tests for fences nested in list items and block quotes."""

    @staticmethod
    def _unfenced(text):
        return [line for _, line, _ in _unfenced_lines(text)]

    def test_bullet_nested_fence_with_indented_closer_does_not_swallow_the_file(self):
        content = """task: do something with {{target}}

- write the invocation like this:

   ```md
   ## inputs
    ```

## inputs

- {{target}}: the file to operate on
"""
        messages = lint_invocation(content, "test.md")
        assert [m for m in messages if "'inputs' section" in m.message] == []

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param(
                "- item\n\n  ```\n  ## inputs\n  ```\n\n## real\n",
                ["- item", "", "", "## real", ""],
                id="fence-in-a-list-item",
            ),
            pytest.param(
                "> quoted\n>\n> ```\n> ## inputs\n> ```\n\n## real\n",
                ["> quoted", ">", "", "## real", ""],
                id="fence-in-a-block-quote",
            ),
            pytest.param(
                "> - item\n>\n>   ```\n>   ## inputs\n>   ```\n>\n## real\n",
                ["> - item", ">", ">", "## real", ""],
                id="fence-in-a-list-item-inside-a-block-quote",
            ),
            pytest.param(
                "intro\n\n```\n## inputs\n\n## output\n",
                ["intro", ""],
                id="unclosed-fence-still-runs-to-the-end-of-the-file",
            ),
            pytest.param(
                "- item\n\n  ```\n  code\n## real\n",
                ["- item", "", "## real", ""],
                id="fence-ends-when-its-container-ends",
            ),
            pytest.param(
                "- item\n\n  ```\n  code\n\n  ## inputs\n  ```\n\n## real\n",
                ["- item", "", "", "## real", ""],
                id="blank-line-does-not-end-a-fence-in-a-list-item",
            ),
            pytest.param(
                "> ```\n> code\n\n## real\n",
                ["", "## real", ""],
                id="blank-line-ends-a-fence-in-a-block-quote",
            ),
            pytest.param(
                "- item\n\n      ```\n\n## real\n",
                ["- item", "", "      ```", "", "## real", ""],
                id="fence-marker-past-the-item-content-column-is-not-a-fence",
            ),
            pytest.param(
                "   ```\n   code\n    ```\n## swallowed\n",
                [],
                id="top-level-closer-indented-four-spaces-does-not-close",
            ),
            pytest.param(
                "-\ta\n\n\t```\n\t## inputs\n\t```\n\n## real\n",
                ["-\ta", "", "", "## real", ""],
                id="tab-indented-fence-under-a-bullet",
            ),
            pytest.param(
                "prose\n2) not a list\n      ```\n## real\n",
                [
                    "prose",
                    "2) not a list",
                    "      ```",
                    "## real",
                    "",
                ],
                id="ordered-marker-mid-paragraph-opens-no-container",
            ),
            pytest.param(
                "- item\n\n  ```\n  code\n```\n## swallowed\n",
                ["- item", ""],
                id="outdented-closer-ends-the-item-and-opens-a-new-fence",
            ),
        ],
    )
    def test_unfenced_lines(self, text, expected):
        assert self._unfenced(text) == expected


class TestHtmlBlocks:
    """tests for fence markers swallowed by a commonmark html block."""

    @staticmethod
    def _unfenced(text):
        return [line for _, line, _ in _unfenced_lines(text)]

    def test_details_wrapping_an_example_does_not_swallow_the_file(self):
        content = """task: do something with {{target}}

<details>
<summary>example</summary>
- ```md
  ## inputs
```
</details>

## inputs

- {{target}}: the file to operate on

## output

- the rewritten file
"""
        assert lint_invocation(content, "test.md") == []

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param(
                "<div>\n- ```\n## inputs\n```\n",
                ["<div>", "- ```", "## inputs", "```", ""],
                id="bullet-fence-under-an-open-tag-is-not-a-fence",
            ),
            pytest.param(
                "<div>\n\n```\n## inputs\n```\n\n## real\n",
                ["<div>", "", "", "## real", ""],
                id="blank-line-between-the-tag-and-the-fence-leaves-a-fence",
            ),
            pytest.param(
                "text\n<div>\n```\n## inputs\n```\n## real\n",
                [
                    "text",
                    "<div>",
                    "```",
                    "## inputs",
                    "```",
                    "## real",
                    "",
                ],
                id="open-tag-interrupts-a-paragraph",
            ),
            pytest.param(
                "- <div>\n  ```\n## real\n```\n",
                ["- <div>", "  ```", "## real"],
                id="html-block-ends-with-its-container",
            ),
            pytest.param(
                "- <details>\n  ```\n  ## inputs\n\n## real\n",
                [
                    "- <details>",
                    "  ```",
                    "  ## inputs",
                    "",
                    "## real",
                    "",
                ],
                id="html-block-in-a-list-item",
            ),
            pytest.param(
                "> <div>\n> ```\n> ## inputs\n\n## real\n",
                [
                    "> <div>",
                    "> ```",
                    "> ## inputs",
                    "",
                    "## real",
                    "",
                ],
                id="html-block-in-a-block-quote",
            ),
            pytest.param(
                "<script>\n```\n## inputs\n</script>\n```\n## real\n```\n## after\n",
                [
                    "<script>",
                    "```",
                    "## inputs",
                    "</script>",
                    "## after",
                    "",
                ],
                id="script-runs-to-its-closing-tag",
            ),
            pytest.param(
                "<PRE>\n```\n## inputs\n</PRE>\n```\n## real\n```\n## after\n",
                [
                    "<PRE>",
                    "```",
                    "## inputs",
                    "</PRE>",
                    "## after",
                    "",
                ],
                id="uppercase-script-runs-to-its-closing-tag",
            ),
            pytest.param(
                "<script>x</script>\n```\n## inputs\n```\n## real\n",
                ["<script>x</script>", "## real", ""],
                id="script-closed-on-its-own-line-leaves-a-fence",
            ),
            pytest.param(
                "<!--\n```\n-->\n```\n## real\n```\n## after\n",
                ["<!--", "```", "-->", "## after", ""],
                id="comment-runs-to-its-terminator",
            ),
            pytest.param(
                "<!-- c -->\n```\n## inputs\n```\n## real\n",
                ["<!-- c -->", "## real", ""],
                id="comment-closed-on-its-own-line-leaves-a-fence",
            ),
            pytest.param(
                "<?php\n```\n?>\n```\n## real\n```\n## after\n",
                ["<?php", "```", "?>", "## after", ""],
                id="processing-instruction-runs-to-its-terminator",
            ),
            pytest.param(
                "<!DOCTYPE\n```\n## inputs\nfoo>\n```\n## real\n```\n## after\n",
                [
                    "<!DOCTYPE",
                    "```",
                    "## inputs",
                    "foo>",
                    "## after",
                    "",
                ],
                id="declaration-runs-to-its-terminator",
            ),
            pytest.param(
                "<!DOCTYPE html>\n```\n## inputs\n```\n## real\n",
                ["<!DOCTYPE html>", "## real", ""],
                id="declaration-closed-on-its-own-line-leaves-a-fence",
            ),
            pytest.param(
                "<![CDATA[\n```\n]]>\n```\n## real\n```\n## after\n",
                ["<![CDATA[", "```", "]]>", "## after", ""],
                id="cdata-runs-to-its-terminator",
            ),
            pytest.param(
                "> <details>\n>\n> ```\n> ## inputs\n> ```\n\n## real\n",
                ["> <details>", ">", "", "## real", ""],
                id="empty-quote-line-ends-a-block-in-a-quote",
            ),
            pytest.param(
                "<pre>\n\n```\n## inputs\n```\n</pre>\n## real\n",
                [
                    "<pre>",
                    "",
                    "```",
                    "## inputs",
                    "```",
                    "</pre>",
                    "## real",
                    "",
                ],
                id="blank-line-does-not-end-a-terminated-block",
            ),
            pytest.param(
                "- <pre>\n\n  ```\n  ## inputs\n  ```\n\n## real\n",
                ["- <pre>", "", "", "## real", ""],
                id="blank-line-ends-a-terminated-block-in-a-list-item",
            ),
            pytest.param(
                "text\n<DIV>\n```\n## inputs\n```\n## real\n",
                [
                    "text",
                    "<DIV>",
                    "```",
                    "## inputs",
                    "```",
                    "## real",
                    "",
                ],
                id="uppercase-tag-interrupts-a-paragraph",
            ),
            pytest.param(
                "text\n   <div>\n```\n## inputs\n```\n## real\n",
                [
                    "text",
                    "   <div>",
                    "```",
                    "## inputs",
                    "```",
                    "## real",
                    "",
                ],
                id="indented-tag-interrupts-a-paragraph",
            ),
            pytest.param(
                "text\n</div>\n```\n## inputs\n```\n## real\n",
                [
                    "text",
                    "</div>",
                    "```",
                    "## inputs",
                    "```",
                    "## real",
                    "",
                ],
                id="closing-tag-interrupts-a-paragraph",
            ),
            pytest.param(
                "text\n<divider>\n```\n## inputs\n```\n## real\n",
                ["text", "<divider>", "## real", ""],
                id="tag-extending-a-block-name-does-not-interrupt-a-paragraph",
            ),
            pytest.param(
                "<span>i</span> trailing\n```\n## inputs\n```\n\n## real\n",
                ["<span>i</span> trailing", "", "## real", ""],
                id="tag-with-trailing-text-does-not-open-a-block",
            ),
            pytest.param(
                "<pre>x</pre>\n<span>\n```\n## inputs\n```\n\n## real\n",
                [
                    "<pre>x</pre>",
                    "<span>",
                    "```",
                    "## inputs",
                    "```",
                    "",
                    "## real",
                    "",
                ],
                id="tag-alone-after-a-closed-block-opens-a-block",
            ),
            pytest.param(
                "<x-tag>\n```\n## inputs\n```\n\n## real\n",
                [
                    "<x-tag>",
                    "```",
                    "## inputs",
                    "```",
                    "",
                    "## real",
                    "",
                ],
                id="unknown-tag-alone-on-a-line-opens-a-block",
            ),
            pytest.param(
                "text\n<x-tag>\n```\n## inputs\n```\n## real\n",
                ["text", "<x-tag>", "## real", ""],
                id="unknown-tag-does-not-interrupt-a-paragraph",
            ),
        ],
    )
    def test_unfenced_lines(self, text, expected):
        assert self._unfenced(text) == expected


class TestLintMessage:
    """tests for LintMessage formatting."""

    def test_str_with_line(self):
        msg = LintMessage(level="error", file="test.md", line=5, message="bad")
        assert str(msg) == "error: test.md:5: bad"

    def test_str_without_line(self):
        msg = LintMessage(level="warning", file="test.md", line=None, message="warning")
        assert str(msg) == "warning: test.md: warning"

    def test_str_escapes_undecodable_file_name(self):
        name = os.fsdecode(b"x/a\xffb.md")
        msg = LintMessage(level="error", file=name, line=None, message=name)
        assert str(msg) == "error: x/a\\xffb.md: x/a\\xffb.md"


class TestLinterPlugins:
    """tests for linter plugin loading."""

    def test_invalid_linter_warns(self):
        """Plugin that isn't callable should warn."""
        mock_ep = MagicMock()
        mock_ep.name = "invalid"
        mock_ep.load.return_value = "not a function"

        with patch("familiar._plugins.entry_points", return_value=[mock_ep]):
            with pytest.warns(UserWarning, match="not callable"):
                linters = load_linters("conjurings")
            assert len(linters) == 0

    def test_plugin_linter_called(self, tmp_path):
        """Plugin linter should be called for each file and its messages kept."""
        calls = []

        def mock_linter(content: str, name: str) -> list[LintMessage]:
            calls.append((content, name))
            return [LintMessage("warning", name, 1, "plugin says")]

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
            messages = lint_all(tmp_path)

        name = ".familiar/conjurings/mytemplate.md"
        assert ("# test", name) in calls
        assert LintMessage("warning", name, 1, "plugin says") in messages

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

        assert (
            LintMessage(
                "error",
                ".familiar/conjurings/test.md",
                None,
                "plugin linter failed: linter crashed",
            )
            in messages
        )


class TestLintCollectionErrorHandling:
    """tests for error handling in lint_collection."""

    def test_unexpected_linter_error_propagates(self, tmp_path):
        """Errors not wrapped in NotFoundError should propagate, not be swallowed."""
        templates = tmp_path / ".familiar" / "conjurings"
        templates.mkdir(parents=True)
        (templates / "test.md").write_text("# test")

        def exploding_linter(content: str, name: str) -> list[LintMessage]:
            raise RuntimeError("unexpected")

        with pytest.raises(RuntimeError, match="unexpected"):
            lint_collection(tmp_path, "conjurings", exploding_linter, [])


class TestLintUnreadableLocalFiles:
    """tests for local files that exist but cannot be read."""

    def _errors_for(self, messages, file):
        return [m for m in messages if m.level == "error" and m.file == file]

    @pytest.mark.parametrize(
        ("kind", "make", "name", "detail"),
        [
            ("invocations", _invalid_utf8, "bad", "not valid UTF-8"),
            ("conjurings", _invalid_utf8, "bad", "not valid UTF-8"),
            ("invocations", _locked, "locked", "permission denied"),
            ("conjurings", _dangling_symlink, "dangling", ""),
        ],
        ids=[
            "invalid-utf8-invocation",
            "invalid-utf8-conjuring",
            "permission-denied-invocation",
            "dangling-symlink-conjuring",
        ],
    )
    def test_unreadable_local_file_reported(self, tmp_path, kind, make, name, detail):
        local = tmp_path / ".familiar" / kind
        local.mkdir(parents=True)
        make(local / f"{name}.md")

        errors = self._errors_for(lint_all(tmp_path), f".familiar/{kind}/{name}.md")
        assert len(errors) == 1
        assert re.match(
            f"failed to load: cannot read {kind[:-1]} '{name}': .*{detail}",
            errors[0].message,
        )

    def test_invalid_utf8_snippet_reported(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "x"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "s.md").write_bytes(b"caf\xe9\n")

        errors = self._errors_for(
            lint_snippet_collection(tmp_path), ".familiar/snippets/x/s.md"
        )
        assert len(errors) == 1
        assert "cannot read snippet 'x/s.md'" in errors[0].message
        assert "not valid UTF-8" in errors[0].message

    def test_include_of_invalid_utf8_snippet_reports_reason(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "x"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "s.md").write_bytes(b"caf\xe9\n")

        content = "task: use it\n{{> snippet:x/s.md}}"
        messages = lint_snippet_references(tmp_path, content, "inc.md")
        assert len(messages) == 1
        assert messages[0].line == 2
        assert "cannot read snippet 'x/s.md'" in messages[0].message
        assert "not valid UTF-8" in messages[0].message

    def test_directory_over_builtin_conjuring_reported_as_local(self, tmp_path):
        (tmp_path / ".familiar" / "conjurings" / "python.md").mkdir(parents=True)

        messages = lint_all(tmp_path)
        errors = self._errors_for(messages, ".familiar/conjurings/python.md")
        assert len(errors) == 1
        assert "is not a regular file" in errors[0].message
        assert self._errors_for(messages, "(builtin) conjurings/python.md") == []

    def test_directory_over_builtin_snippet_reported_as_local(self, tmp_path):
        snippets = tmp_path / ".familiar" / "snippets"
        (snippets / "python" / "pyproject.toml").mkdir(parents=True)

        messages = lint_snippet_collection(tmp_path)
        errors = self._errors_for(messages, ".familiar/snippets/python/pyproject.toml")
        assert len(errors) == 1
        assert "is not a regular file" in errors[0].message
        assert (
            self._errors_for(messages, "(builtin) snippets/python/pyproject.toml") == []
        )

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs os.mkfifo")
    def test_fifo_over_builtin_conjuring_reported_without_blocking(
        self, tmp_path, without_blocking
    ):
        conjurings = tmp_path / ".familiar" / "conjurings"
        conjurings.mkdir(parents=True)
        os.mkfifo(conjurings / "python.md")

        errors = self._errors_for(
            without_blocking(lint_all, tmp_path), ".familiar/conjurings/python.md"
        )
        assert len(errors) == 1
        assert "is not a regular file" in errors[0].message

    @pytest.mark.skipif(
        hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores file modes"
    )
    def test_unsearchable_snippet_dir_reported(self, tmp_path):
        sub = tmp_path / ".familiar" / "snippets" / "sub"
        sub.mkdir(parents=True)
        (sub / "x.md").write_text("hidden")
        sub.chmod(0o644)
        try:
            messages = lint_all(tmp_path)
        finally:
            sub.chmod(0o755)

        errors = self._errors_for(messages, ".familiar/snippets/sub/x.md")
        assert len(errors) == 1
        assert "Permission denied" in errors[0].message

    def test_include_of_permission_denied_snippet_reports_reason(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "x"
        snippet_dir.mkdir(parents=True)
        locked = snippet_dir / "s.md"
        locked.write_text("content")
        locked.chmod(0o000)
        try:
            messages = lint_snippet_references(
                tmp_path, "{{> snippet:x/s.md}}", "inc.md"
            )
        finally:
            locked.chmod(0o644)

        assert len(messages) == 1
        assert "permission denied" in messages[0].message


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

    def test_missing_snippet_reference_split_across_lines(self, tmp_path):
        content = "{{> snippet:\n  missing/a.txt}}\n{{>\nsnippet:missing/b.txt\n}}"
        messages = lint_snippet_references(tmp_path, content, "test.md")
        assert [(m.line, m.message) for m in messages] == [
            (1, "snippet not found: missing/a.txt"),
            (3, "snippet not found: missing/b.txt"),
        ]

    def test_valid_snippet_reference_split_across_lines(self, tmp_path):
        snippet_dir = tmp_path / ".familiar" / "snippets" / "test"
        snippet_dir.mkdir(parents=True)
        (snippet_dir / "file.txt").write_text("content")

        content = "intro\n{{>\n  snippet:test/file.txt\n}}\nend"
        assert lint_snippet_references(tmp_path, content, "test.md") == []

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
        assert (
            messages[0].message
            == "snippet include cycle: test/a.txt -> test/b.txt -> test/a.txt"
        )

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


class TestLintSnippetPlaceholders:
    """tests for placeholder checks on include-expanded invocation text."""

    @pytest.mark.parametrize(
        ("body", "placeholder"),
        [("run the tool with $1", "$1"), ("mode is {{key}}", "{{key}}")],
        ids=["positional", "named"],
    )
    def test_snippet_placeholder_undocumented_warns(self, tmp_path, body, placeholder):
        snippets = tmp_path / ".familiar" / "snippets" / "test"
        snippets.mkdir(parents=True)
        (snippets / "body.txt").write_text(body)

        content = (
            "task: demo\n\ninputs\n- $ARGUMENTS: stuff\n\n"
            "{{> snippet:test/body.txt}}\n\noutput\n- results\n"
        )
        messages = lint_snippet_placeholders(tmp_path, content, "demo.md")
        assert messages == [
            LintMessage(
                "warning",
                "demo.md",
                None,
                f"placeholder '{placeholder}' may not be documented in inputs",
            )
        ]

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
