"""Mistune plugin for GitHub-style alerts/admonitions.

Supports the following alert types::

    > [!NOTE]
    > [!TIP]
    > [!WARNING]
    > [!CAUTION]
    > [!IMPORTANT]

Maps to Confluence structured macros: info, tip, warning, note.

This plugin must be registered AFTER the spoiler plugin since both
override the ``block_quote`` parse rule.  When registered last it
handles alerts, spoilers, and plain blockquotes in a single parser.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Match

if TYPE_CHECKING:
    from mistune import Markdown
    from mistune.block_parser import BlockParser
    from mistune.core import BaseRenderer, BlockState

# Pattern to detect alert marker as first line of blockquote content
_ALERT_PATTERN = re.compile(
    r"^\[!(NOTE|TIP|WARNING|CAUTION|IMPORTANT)\]\s*\n?", re.IGNORECASE
)

# Spoiler detection patterns (duplicated from mistune.plugins.spoiler
# so we can handle both in one parser)
_BLOCK_SPOILER_MATCH = re.compile(r"^( {0,3}![^\n]*\n)+$")
_BLOCK_SPOILER_START = re.compile(r"^ {0,3}! ?", re.M)

# Map GitHub alert types to Confluence macro names
ALERT_TYPE_MAP = {
    "NOTE": "info",
    "TIP": "tip",
    "WARNING": "warning",
    "CAUTION": "warning",
    "IMPORTANT": "note",
}


def parse_block_alert(block: "BlockParser", m: Match[str], state: "BlockState") -> int:
    """Parse a blockquote, detecting GitHub-style alert or spoiler syntax."""
    text, end_pos = block.extract_block_quote(m, state)
    if not text.endswith("\n"):
        text += "\n"

    depth = state.depth()
    alert_match = _ALERT_PATTERN.match(text) if not depth else None

    if alert_match:
        alert_type = alert_match.group(1).upper()
        text = text[alert_match.end() :]
        tok_type = "block_alert"

        child = state.child_state(text)
        if state.depth() >= block.max_nested_level - 1:
            rules = list(block.block_quote_rules)
            rules.remove("block_quote")
        else:
            rules = block.block_quote_rules

        block.parse(child, rules)
        token = {
            "type": tok_type,
            "children": child.tokens,
            "attrs": {"alert_type": alert_type},
        }
    elif not depth and _BLOCK_SPOILER_MATCH.match(text):
        text = _BLOCK_SPOILER_START.sub("", text)
        tok_type = "block_spoiler"

        child = state.child_state(text)
        if state.depth() >= block.max_nested_level - 1:
            rules = list(block.block_quote_rules)
            rules.remove("block_quote")
        else:
            rules = block.block_quote_rules

        block.parse(child, rules)
        token = {"type": tok_type, "children": child.tokens}
    else:
        tok_type = "block_quote"
        child = state.child_state(text)
        if state.depth() >= block.max_nested_level - 1:
            rules = list(block.block_quote_rules)
            rules.remove("block_quote")
        else:
            rules = block.block_quote_rules

        block.parse(child, rules)
        token = {"type": tok_type, "children": child.tokens}

    if end_pos:
        state.prepend_token(token)
        return end_pos
    state.append_token(token)
    return state.cursor


def render_block_alert(renderer: "BaseRenderer", text: str, alert_type: str) -> str:
    """Default HTML render for alerts (used when not rendering to Confluence)."""
    css_class = alert_type.lower()
    return f'<div class="alert alert-{css_class}">\n{text}</div>\n'


def alerts(md: "Markdown") -> None:
    """A mistune plugin to support GitHub-style alerts/admonitions.

    Must be registered AFTER the spoiler plugin.

    :param md: Markdown instance
    """
    md.block.register("block_quote", None, parse_block_alert)
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("block_alert", render_block_alert)
