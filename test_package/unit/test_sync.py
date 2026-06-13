from types import SimpleNamespace

import pytest

import mdfluence.__main__ as main_module
from mdfluence.document import Page
from mdfluence.sync import apply_title_prefix


# --- Ask 1.1: apply_title_prefix -------------------------------------------------


def test_apply_title_prefix_prefixes_title_and_parent_title():
    page = Page(title="My Page", body="", parent_title="Parent")

    apply_title_prefix(page, "X")

    assert page.title == "X - My Page"
    assert page.parent_title == "X - Parent"


@pytest.mark.parametrize("prefix", [None, ""])
def test_apply_title_prefix_noop_when_prefix_empty(prefix):
    page = Page(title="My Page", body="", parent_title="Parent")

    apply_title_prefix(page, prefix)

    assert page.title == "My Page"
    assert page.parent_title == "Parent"


def test_apply_title_prefix_leaves_none_parent_title_untouched():
    page = Page(title="My Page", body="", parent_title=None)

    apply_title_prefix(page, "X")

    assert page.title == "X - My Page"
    assert page.parent_title is None


# --- Ask 1.4: CLI --title override re-applies prefix -----------------------------


def _stdin_args(**overrides):
    base = dict(
        file_list=None,
        strip_top_header=False,
        remove_text_newlines=False,
        disable_emoji=True,
        disable_anchor_convert=True,
        render_diagrams=False,
        mmdc_path=None,
        plantuml_path=None,
        prefix=None,
        enable_line_numbers=False,
        title=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_collect_pages_title_override_reapplies_prefix(mocker):
    mocker.patch("sys.stdin")
    mocker.patch("sys.stdin.readlines", return_value=["# Document Header\n"])
    args = _stdin_args(prefix="X", title="Override Title")

    pages = main_module.collect_pages_to_upload(args)

    assert pages[0].title == "X - Override Title"
