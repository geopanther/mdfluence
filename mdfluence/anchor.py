"""Anchor utilities for rewriting markdown-style fragment anchors to Confluence format.

Confluence generates heading anchors as ``PageTitleStripped-HeadingStripped``
where "stripped" means spaces and hyphens are removed but other characters
(like parentheses) are kept, with original casing preserved.

Example
-------
Page title : "SSH Reverse Tunnel Setup Guide - Embedded Hardware to AWS EC2"
Heading    : "The Concept"

Markdown anchor     : ``#the-concept``
Confluence anchor   : ``#SSHReverseTunnelSetupGuideEmbeddedHardwaretoAWSEC2-TheConcept``
"""

from __future__ import annotations

import re
from urllib.parse import quote as _url_quote


def _strip_for_anchor(text: str) -> str:
    """Remove spaces and hyphens/dashes.

    Confluence keeps other chars like parentheses.
    """
    return re.sub(r"[\s\-]", "", text)


def _heading_to_markdown_anchor(text: str) -> str:
    """Convert a heading string to a GitHub-Flavored-Markdown anchor slug."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug.strip("-")


def _extract_headings_from_markdown(markdown_text: str) -> list[str]:
    """Extract heading text from raw markdown lines.

    Returns plain heading text strings (without the ``#`` prefix).
    Skips headings inside fenced code blocks.
    """
    headings: list[str] = []
    in_code_block = False
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = re.match(r"^#{1,6}\s+(.+)$", stripped)
        if m:
            text = m.group(1).strip()
            # Remove trailing # characters (alternate heading syntax)
            text = re.sub(r"\s+#+\s*$", "", text)
            headings.append(text)
    return headings


def _detect_title_from_markdown(
    markdown_text: str, frontmatter_title: str | None = None
) -> str:
    """Determine page title from frontmatter or first H1."""
    if frontmatter_title:
        return frontmatter_title
    for line in markdown_text.splitlines():
        stripped = line.strip()
        m = re.match(r"^#\s+(.+)$", stripped)
        if m:
            text = m.group(1).strip()
            text = re.sub(r"\s+#+\s*$", "", text)
            return text
    return ""


def build_anchor_map_from_markdown(
    markdown_text: str,
    page_title: str,
) -> dict[str, str]:
    """Build a mapping *markdown-anchor -> confluence-anchor* from raw markdown.

    Pre-scans the markdown source so the map is available before rendering.
    Handles duplicate headings with GFM-style suffixes:
    first "Setup" -> ``#setup``, second -> ``#setup-1``, etc.
    """
    title_part = _strip_for_anchor(page_title)
    anchor_map: dict[str, str] = {}
    seen_counts: dict[str, int] = {}

    for heading in _extract_headings_from_markdown(markdown_text):
        md_base = _heading_to_markdown_anchor(heading)
        if not md_base:
            continue

        count = seen_counts.get(md_base, 0)
        md_anchor = md_base if count == 0 else f"{md_base}-{count}"
        seen_counts[md_base] = count + 1

        cf_base = f"{title_part}-{_strip_for_anchor(heading)}"
        cf_anchor = cf_base if count == 0 else f"{cf_base}-{count}"

        cf_anchor = _url_quote(cf_anchor, safe="-")

        if cf_anchor and not cf_anchor[0].isalpha():
            cf_anchor = f"id-{cf_anchor}"

        anchor_map[md_anchor] = cf_anchor

    return anchor_map
