"""Rewrite markdown-style fragment anchors to Confluence-native anchor format.

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

import html
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


def _extract_headings(storage_body: str) -> list[str]:
    """Return plain-text heading strings from Confluence storage-format HTML."""
    headings: list[str] = []
    for m in re.finditer(r"<h[1-6][^>]*>(.*?)</h[1-6]>", storage_body, re.DOTALL):
        raw = re.sub(r"<[^>]+>", "", m.group(1))
        text = html.unescape(raw).strip()
        if text:
            headings.append(text)
    return headings


def _build_anchor_map(storage_body: str, page_title: str) -> dict[str, str]:
    """Build a mapping *markdown-anchor → confluence-anchor* for every heading.

    Handles duplicate headings with GFM-style suffixes:
    first "Setup" → ``#setup``, second → ``#setup-1``, etc.
    """
    title_part = _strip_for_anchor(page_title)
    anchor_map: dict[str, str] = {}
    seen_counts: dict[str, int] = {}

    for heading in _extract_headings(storage_body):
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

        if md_anchor != cf_anchor:
            anchor_map[md_anchor] = cf_anchor

    return anchor_map


def _rewrite_anchors(storage_body: str, anchor_map: dict[str, str]) -> str:
    """Replace markdown-style anchors with Confluence-style ones."""

    def _replace_href(m: re.Match[str]) -> str:
        anchor = m.group(1)
        if anchor in anchor_map:
            return f'href="#{anchor_map[anchor]}"'
        return m.group(0)

    def _replace_ac_anchor(m: re.Match[str]) -> str:
        anchor = m.group(1)
        if anchor in anchor_map:
            return f'ac:anchor="{anchor_map[anchor]}"'
        return m.group(0)

    storage_body = re.sub(r'href="#([^"]+)"', _replace_href, storage_body)
    storage_body = re.sub(r'ac:anchor="([^"]+)"', _replace_ac_anchor, storage_body)
    return storage_body


def rewrite_page_anchors(body: str, page_title: str) -> str:
    """Rewrite markdown-style fragment anchors in *body* to Confluence-native format.

    Returns *body* unchanged if no anchors need rewriting.
    """
    anchor_map = _build_anchor_map(body, page_title)
    if not anchor_map:
        return body
    return _rewrite_anchors(body, anchor_map)
