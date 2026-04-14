from mdfluence.anchor import (
    _build_anchor_map,
    _extract_headings,
    _heading_to_markdown_anchor,
    _rewrite_anchors,
    _strip_for_anchor,
    rewrite_page_anchors,
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


class TestExtractHeadings:
    def test_basic_headings(self):
        body = "<h1>Introduction</h1><p>text</p><h2>Details</h2>"
        assert _extract_headings(body) == ["Introduction", "Details"]

    def test_strips_nested_tags(self):
        body = "<h2><strong>Bold Heading</strong></h2>"
        assert _extract_headings(body) == ["Bold Heading"]

    def test_ignores_empty_headings(self):
        body = "<h1></h1><h2>Real</h2>"
        assert _extract_headings(body) == ["Real"]

    def test_unescapes_html_entities(self):
        body = "<h2>A &amp; B</h2>"
        assert _extract_headings(body) == ["A & B"]

    def test_no_headings(self):
        assert _extract_headings("<p>just a paragraph</p>") == []

    def test_heading_with_attributes(self):
        body = '<h2 id="foo" class="bar">Heading</h2>'
        assert _extract_headings(body) == ["Heading"]


class TestBuildAnchorMap:
    def test_basic_mapping(self):
        body = "<h2>The Concept</h2>"
        result = _build_anchor_map(body, "My Guide")
        assert result == {"the-concept": "MyGuide-TheConcept"}

    def test_duplicate_headings(self):
        body = "<h2>Setup</h2><h2>Setup</h2><h2>Setup</h2>"
        result = _build_anchor_map(body, "Page")
        assert result == {
            "setup": "Page-Setup",
            "setup-1": "Page-Setup-1",
            "setup-2": "Page-Setup-2",
        }

    def test_url_encodes_special_chars(self):
        body = "<h2>Disable Service (if needed)</h2>"
        result = _build_anchor_map(body, "Guide")
        assert result == {
            "disable-service-if-needed": "Guide-DisableService%28ifneeded%29",
        }

    def test_id_prefix_for_non_alpha_start(self):
        body = "<h2>3rd Party Libraries</h2>"
        result = _build_anchor_map(body, "")
        # Title is empty so cf_anchor starts with "-" which is non-alpha
        assert "3rd-party-libraries" in result
        assert result["3rd-party-libraries"].startswith("id-")

    def test_skips_when_md_equals_cf(self):
        # Unlikely in practice but should not appear in map
        body = "<h2>a</h2>"
        result = _build_anchor_map(body, "")
        # md_anchor = "a", cf_anchor = "-a" (starts with -), so id prefix is added
        # They won't be equal in this case, but test the concept:
        # If they were equal, they'd be skipped
        for md, cf in result.items():
            assert md != cf

    def test_empty_body(self):
        assert _build_anchor_map("", "Title") == {}

    def test_long_title_with_hyphens(self):
        body = "<h2>The Concept</h2>"
        title = "SSH Reverse Tunnel Setup Guide" " - Embedded Hardware to AWS EC2"
        result = _build_anchor_map(body, title)
        expected_anchor = (
            "SSHReverseTunnelSetupGuideEmbeddedHardwaretoAWSEC2" "-TheConcept"
        )
        assert result == {"the-concept": expected_anchor}


class TestRewriteAnchors:
    def test_rewrites_href(self):
        body = '<a href="#the-concept">link</a>'
        anchor_map = {"the-concept": "MyGuide-TheConcept"}
        assert (
            _rewrite_anchors(body, anchor_map)
            == '<a href="#MyGuide-TheConcept">link</a>'
        )

    def test_rewrites_ac_anchor(self):
        body = (
            '<ac:link ac:anchor="the-concept">'
            "<ac:link-body>text</ac:link-body></ac:link>"
        )
        anchor_map = {"the-concept": "MyGuide-TheConcept"}
        result = _rewrite_anchors(body, anchor_map)
        assert 'ac:anchor="MyGuide-TheConcept"' in result

    def test_leaves_unknown_anchors(self):
        body = '<a href="#unknown-heading">link</a>'
        anchor_map = {"the-concept": "MyGuide-TheConcept"}
        assert _rewrite_anchors(body, anchor_map) == body

    def test_multiple_anchors(self):
        body = '<a href="#one">1</a><a href="#two">2</a>'
        anchor_map = {"one": "Page-One", "two": "Page-Two"}
        result = _rewrite_anchors(body, anchor_map)
        assert 'href="#Page-One"' in result
        assert 'href="#Page-Two"' in result


class TestRewritePageAnchors:
    def test_end_to_end(self):
        body = (
            "<h1>Introduction</h1>"
            '<p>See <a href="#the-concept">the concept</a>.</p>'
            "<h2>The Concept</h2>"
            "<p>Details here.</p>"
            '<p>Back to <a href="#introduction">intro</a>.</p>'
        )
        result = rewrite_page_anchors(body, "My Guide")
        assert 'href="#MyGuide-TheConcept"' in result
        assert 'href="#MyGuide-Introduction"' in result

    def test_no_headings_returns_unchanged(self):
        body = '<p>No headings <a href="#foo">here</a>.</p>'
        assert rewrite_page_anchors(body, "Title") == body

    def test_no_fragment_links_returns_unchanged(self):
        body = "<h2>Heading</h2><p>No links here.</p>"
        # There are headings but no fragment links to rewrite, body is unchanged
        result = rewrite_page_anchors(body, "Title")
        assert result == body

    def test_non_matching_fragment_left_untouched(self):
        body = "<h2>Real Heading</h2>" '<p><a href="#nonexistent">link</a></p>'
        result = rewrite_page_anchors(body, "Page")
        # The #nonexistent anchor doesn't match any heading, left as-is
        assert 'href="#nonexistent"' in result
        # But the heading-matching anchors would be rewritten if referenced
        assert (
            'href="#Page-RealHeading"' not in result
        )  # not referenced, so not in body

    def test_with_prefix_in_title(self):
        body = "<h2>Setup</h2>" '<a href="#setup">go</a>'
        result = rewrite_page_anchors(body, "PREFIX - My Page")
        assert 'href="#PREFIXMyPage-Setup"' in result

    def test_empty_body(self):
        assert rewrite_page_anchors("", "Title") == ""
