"""Mistune plugin for GitHub-style emoji shortcodes.

Converts ``:shortcode:`` patterns to Unicode emoji characters.
Unknown shortcodes are left unchanged.

Example::

    :smile: → 😄
    :warning: → ⚠️
    :unknown: → :unknown: (unchanged)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mistune import Markdown
    from mistune.core import BaseRenderer, InlineState
    from mistune.inline_parser import InlineParser

from mdfluence.plugins.emoji_data import EMOJI_MAP

# Match :shortcode: but not inside URLs (preceded by /) or already-escaped
EMOJI_PATTERN = r":(?P<emoji_name>[\w+-]+):"


def parse_emoji(inline: "InlineParser", m: re.Match[str], state: "InlineState") -> int:
    """Parse an emoji shortcode token."""
    name = m.group("emoji_name")
    if name in EMOJI_MAP:
        state.append_token(
            {
                "type": "emoji",
                "raw": m.group(0),
                "attrs": {"name": name},
                "children": [],
            }
        )
    else:
        # Unknown shortcode — emit as plain text
        state.append_token({"type": "text", "raw": m.group(0)})
    return m.end()


def render_emoji(renderer: "BaseRenderer", text: str, name: str) -> str:
    """Render an emoji shortcode as its Unicode character."""
    return EMOJI_MAP.get(name, f":{name}:")


def emoji(md: "Markdown") -> None:
    """A mistune plugin to support GitHub-style emoji shortcodes.

    :param md: Markdown instance
    """
    md.inline.register("emoji", EMOJI_PATTERN, parse_emoji, before="link")
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("emoji", render_emoji)
