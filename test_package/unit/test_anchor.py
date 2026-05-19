from mdfluence.anchor import (
    _extract_headings_from_markdown,
    _heading_to_markdown_anchor,
    _strip_for_anchor,
    build_anchor_map_from_markdown,
)


class TestStripForAnchor:
    def test_removes_spaces(self):
        assert _strip_for_anchor("The Concept") == "TheConcept"

    def test_removes_hyphens(self):
        assert (
            _strip_for_anchor("SSH Reverse Tunnel - Guide") == "SSHReverseTunnelGuide"
        )

    def test_keeps_parentheses(self):
        assert (
            _strip_for_anchor("Disable Service (if needed)")
            == "DisableService(ifneeded)"
        )

    def test_empty_string(self):
        assert _strip_for_anchor("") == ""


class TestHeadingToMarkdownAnchor:
    def test_basic_heading(self):
        assert _heading_to_markdown_anchor("The Concept") == "the-concept"

    def test_strips_special_chars(self):
        assert _heading_to_markdown_anchor("What's Next?") == "whats-next"

    def test_multiple_spaces(self):
        assert _heading_to_markdown_anchor("A   B   C") == "a-b-c"

    def test_preserves_hyphens(self):
        assert _heading_to_markdown_anchor("pre-existing") == "pre-existing"

    def test_empty_string(self):
        assert _heading_to_markdown_anchor("") == ""

    def test_with_parentheses(self):
        assert _heading_to_markdown_anchor("Setup (Optional)") == "setup-optional"


class TestExtractHeadingsFromMarkdown:
    def test_basic_headings(self):
        md = "# Introduction\n\nsome text\n\n## Details\n"
        assert _extract_headings_from_markdown(md) == ["Introduction", "Details"]

    def test_skips_code_blocks(self):
        md = "## Real\n\n```\n## Not a heading\n```\n\n## Also Real\n"
        assert _extract_headings_from_markdown(md) == ["Real", "Also Real"]

    def test_no_headings(self):
        assert _extract_headings_from_markdown("just a paragraph\n") == []

    def test_various_levels(self):
        md = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\n"
        assert _extract_headings_from_markdown(md) == [
            "H1",
            "H2",
            "H3",
            "H4",
            "H5",
            "H6",
        ]

    def test_trailing_hashes(self):
        md = "## Heading ##\n"
        assert _extract_headings_from_markdown(md) == ["Heading"]


class TestBuildAnchorMapFromMarkdown:
    def test_basic_mapping(self):
        md = "## The Concept\n"
        result = build_anchor_map_from_markdown(md, "My Guide")
        assert result == {"the-concept": "MyGuide-TheConcept"}

    def test_duplicate_headings(self):
        md = "## Setup\n## Setup\n## Setup\n"
        result = build_anchor_map_from_markdown(md, "Page")
        assert result == {
            "setup": "Page-Setup",
            "setup-1": "Page-Setup-1",
            "setup-2": "Page-Setup-2",
        }

    def test_url_encodes_special_chars(self):
        md = "## Disable Service (if needed)\n"
        result = build_anchor_map_from_markdown(md, "Guide")
        assert result == {
            "disable-service-if-needed": "Guide-DisableService%28ifneeded%29",
        }

    def test_id_prefix_for_non_alpha_start(self):
        md = "## 3rd Party Libraries\n"
        result = build_anchor_map_from_markdown(md, "")
        assert "3rd-party-libraries" in result
        assert result["3rd-party-libraries"].startswith("id-")

    def test_empty_body(self):
        assert build_anchor_map_from_markdown("", "Title") == {}

    def test_long_title_with_hyphens(self):
        md = "## The Concept\n"
        title = "SSH Reverse Tunnel Setup Guide - Embedded Hardware to AWS EC2"
        result = build_anchor_map_from_markdown(md, title)
        expected_anchor = (
            "SSHReverseTunnelSetupGuideEmbeddedHardwaretoAWSEC2-TheConcept"
        )
        assert result == {"the-concept": expected_anchor}

    def test_skips_headings_in_code_blocks(self):
        md = "## Real\n\n```\n## Fake\n```\n"
        result = build_anchor_map_from_markdown(md, "Page")
        assert "real" in result
        assert "fake" not in result


class TestAnchorIntegration:
    """Integration tests using parse_page with convert_anchors=True."""

    def test_end_to_end(self):
        from mdfluence.document import parse_page

        md = (
            "# My Guide\n\n"
            "See [the concept](#the-concept).\n\n"
            "## The Concept\n\n"
            "Details here.\n\n"
            "Back to [intro](#my-guide).\n"
        )
        page = parse_page(list(md), convert_anchors=True)
        assert 'href="#MyGuide-TheConcept"' in page.body
        assert 'href="#MyGuide-MyGuide"' in page.body

    def test_forward_reference(self):
        from mdfluence.document import parse_page

        md = "# Page\n\nLink to [section](#details) below.\n\n## Details\n\nContent.\n"
        page = parse_page(list(md), convert_anchors=True)
        assert 'href="#Page-Details"' in page.body

    def test_no_convert_anchors(self):
        from mdfluence.document import parse_page

        md = "# Page\n\nLink to [section](#details).\n\n## Details\n"
        page = parse_page(list(md), convert_anchors=False)
        assert 'href="#details"' in page.body

    def test_with_prefix_in_title(self):
        md = "## Setup\n"
        result = build_anchor_map_from_markdown(md, "PREFIX - My Page")
        assert result == {"setup": "PREFIXMyPage-Setup"}


class TestAnchorWithTitlePrefix:
    def test_parse_page_with_prefix_generates_correct_anchors(self):
        from mdfluence.document import parse_page

        md = "# My Page\n\nGo to [setup](#setup).\n\n## Setup\n\nContent.\n"
        page = parse_page(
            list(md),
            strip_header=True,
            convert_anchors=True,
            title_prefix="testprefix",
        )

        assert "testprefixMyPage-Setup" in page.body
        assert 'href="#testprefixMyPage-Setup"' in page.body
        # No unprefixed anchors
        assert 'href="#MyPage-Setup"' not in page.body

    def test_parse_page_without_prefix_unchanged(self):
        from mdfluence.document import parse_page

        md = "# My Page\n\nGo to [setup](#setup).\n\n## Setup\n\nContent.\n"
        page = parse_page(list(md), strip_header=True, convert_anchors=True)

        assert "MyPage-Setup" in page.body
        assert 'href="#MyPage-Setup"' in page.body

    def test_prefix_with_multiple_headings(self):
        from mdfluence.document import parse_page

        md = "# Doc\n\n## Intro\n\n## Details\n"
        page = parse_page(list(md), convert_anchors=True, title_prefix="pre")

        assert "preDoc-Intro" in page.body
        assert "preDoc-Details" in page.body
        assert 'Doc-Intro"' not in page.body.replace("preDoc-Intro", "")
