import pytest

from mdfluence.document import parse_page


@pytest.mark.parametrize(
    "markdown_input,expected_substring,plugin_name",
    [
        (
            "*[HTML]: Hyper Text Markup Language\nHTML is good\n",
            "<abbr",
            "abbr",
        ),
        (
            "Term\n:   Definition\n",
            "<dd>",
            "def_list",
        ),
        (
            "Text[^1]\n\n[^1]: footnote content\n",
            "footnote",
            "footnotes",
        ),
        (
            "^^inserted^^\n",
            "<ins>",
            "insert",
        ),
        (
            "==highlighted==\n",
            "<mark>",
            "mark",
        ),
        (
            "$$\nx^2\n$$\n",
            "mathblock",
            "math_block",
        ),
        (
            "Inline $x^2$ end\n",
            "mathinline",
            "math_inline",
        ),
        (
            ">! hidden spoiler\n",
            "spoiler",
            "spoiler",
        ),
        (
            "~~deleted~~\n",
            "<del>deleted</del>",
            "strikethrough",
        ),
        (
            "H~2~O\n",
            "<sub>",
            "subscript",
        ),
        (
            "x^2^\n",
            "<sup>",
            "superscript",
        ),
        (
            "| a | b |\n|---|---|\n| c | d |\n",
            "<table>",
            "table",
        ),
        (
            "- [ ] todo\n- [x] done\n",
            "ac:task-list",
            "task_lists",
        ),
        (
            "Visit https://example.com now\n",
            '<a href="https://example.com">',
            "url",
        ),
    ],
    ids=[
        "abbr",
        "def_list",
        "footnotes",
        "insert",
        "mark",
        "math_block",
        "math_inline",
        "spoiler",
        "strikethrough",
        "subscript",
        "superscript",
        "table",
        "task_lists",
        "url",
    ],
)
def test_plugin_enabled(markdown_input, expected_substring, plugin_name):
    page = parse_page(list(markdown_input))
    assert expected_substring in page.body, (
        f"Plugin '{plugin_name}' not active. Output: {page.body}"
    )
