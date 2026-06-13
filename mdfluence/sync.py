"""Public orchestration/publish API for embedding mdfluence as a library."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mdfluence.document import Page


def apply_title_prefix(page: "Page", prefix: str | None) -> None:
    """Prefix a page's ``title`` and ``parent_title`` in place.

    No-op when ``prefix`` is ``None`` or empty. A ``parent_title`` of ``None``
    is left untouched (the page is a top-level page).
    """
    if not prefix:
        return
    if page.title is not None:
        page.title = f"{prefix} - {page.title}"
    if page.parent_title is not None:
        page.parent_title = f"{prefix} - {page.parent_title}"
