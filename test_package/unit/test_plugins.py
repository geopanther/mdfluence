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
        (
            "> [!NOTE]\n> This is a note.\n",
            'ac:name="info"',
            "alert_note",
        ),
        (
            "> [!TIP]\n> This is a tip.\n",
            'ac:name="tip"',
            "alert_tip",
        ),
        (
            "> [!WARNING]\n> This is a warning.\n",
            'ac:name="warning"',
            "alert_warning",
        ),
        (
            "> [!CAUTION]\n> This is a caution.\n",
            'ac:name="warning"',
            "alert_caution",
        ),
        (
            "> [!IMPORTANT]\n> This is important.\n",
            'ac:name="note"',
            "alert_important",
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
        "alert_note",
        "alert_tip",
        "alert_warning",
        "alert_caution",
        "alert_important",
    ],
)
def test_plugin_enabled(markdown_input, expected_substring, plugin_name):
    page = parse_page(list(markdown_input))
    assert expected_substring in page.body, (
        f"Plugin '{plugin_name}' not active. Output: {page.body}"
    )


class TestEmojiPlugin:
    def test_emoji_enabled(self):
        page = parse_page(list(":smile: hello\n"), enable_emoji=True)
        assert "\U0001f604" in page.body

    def test_emoji_disabled(self):
        page = parse_page(list(":smile: hello\n"), enable_emoji=False)
        assert ":smile:" in page.body

    def test_unknown_shortcode_passthrough(self):
        page = parse_page(list(":nonexistent_emoji_xyz: text\n"), enable_emoji=True)
        assert ":nonexistent_emoji_xyz:" in page.body

    def test_multiple_emojis(self):
        page = parse_page(list(":warning: caution :thumbsup:\n"), enable_emoji=True)
        assert "\u26a0" in page.body  # warning
        assert "\U0001f44d" in page.body  # thumbsup

    def test_emoji_not_in_code(self):
        page = parse_page(list("`code :smile: here`\n"), enable_emoji=True)
        assert ":smile:" in page.body
