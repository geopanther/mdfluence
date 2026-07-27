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


# --- Ask 2.1: PublishOptions dataclass -------------------------------------------


def test_publish_options_requires_space():
    from mdfluence.sync import PublishOptions

    options = PublishOptions(space="TEST")

    assert options.space == "TEST"


def test_publish_options_has_expected_defaults():
    from mdfluence.sync import PublishOptions

    options = PublishOptions(space="TEST")

    assert options.content_type == "page"
    assert options.page_id is None
    assert options.parent_title is None
    assert options.parent_id is None
    assert options.top_level is False
    assert options.prefix is None
    assert options.message is None
    assert options.minor_edit is False
    assert options.only_changed is False
    assert options.replace_all_labels is False
    assert options.dry_run is False
    assert options.debug is False
    assert options.enable_relative_links is False
    assert options.ignore_relative_link_errors is False
    assert options.preface_markup == ""
    assert options.postface_markup == ""


def test_publish_options_round_trips_values():
    from mdfluence.sync import PublishOptions

    options = PublishOptions(
        space="TEST",
        content_type="blogpost",
        page_id="42",
        parent_title="Parent",
        parent_id="7",
        top_level=True,
        prefix="X",
        message="msg",
        minor_edit=True,
        only_changed=True,
        replace_all_labels=True,
        dry_run=True,
        debug=True,
        enable_relative_links=True,
        ignore_relative_link_errors=True,
        preface_markup="<pre>",
        postface_markup="<post>",
    )

    assert options.content_type == "blogpost"
    assert options.page_id == "42"
    assert options.parent_title == "Parent"
    assert options.parent_id == "7"
    assert options.top_level is True
    assert options.prefix == "X"
    assert options.message == "msg"
    assert options.minor_edit is True
    assert options.only_changed is True
    assert options.replace_all_labels is True
    assert options.dry_run is True
    assert options.debug is True
    assert options.enable_relative_links is True
    assert options.ignore_relative_link_errors is True
    assert options.preface_markup == "<pre>"
    assert options.postface_markup == "<post>"


# --- Ask 2.2: Reporter protocol + NullReporter ----------------------------------


def test_null_reporter_satisfies_reporter_protocol():
    from mdfluence.sync import NullReporter, Reporter

    assert isinstance(NullReporter(), Reporter)


def test_null_reporter_methods_are_noops():
    from mdfluence.sync import NullReporter

    reporter = NullReporter()

    assert reporter.start_item_task("item") is None
    assert reporter.set_item_progress_label("item", "label") is None
    assert reporter.set_item_finished_text("item", "text") is None
    assert reporter.set_item_finished_text_from_result("item", None) is None
    assert reporter.tick_item_progress("item") is None
    assert reporter.tick_global_progress() is None
    assert reporter.reset_item_task("item", total=1) is None


def test_null_reporter_works_as_context_manager():
    from mdfluence.sync import NullReporter

    with NullReporter() as reporter:
        assert reporter is not None


# --- Ask 2.3: orchestration helpers moved into mdfluence.sync --------------------


def _options(**overrides):
    from mdfluence.sync import PublishOptions

    base = dict(space="TEST")
    base.update(overrides)
    return PublishOptions(**base)


def _relative_link(path, fragment=""):
    from mdfluence.confluence_renderer import RelativeLink

    return RelativeLink(
        path=path,
        fragment=fragment,
        replacement=f"[[{path}]]",
        original=path,
        escaped_original=path,
    )


def test_pre_process_page_sets_metadata_from_options():
    from mdfluence.sync import pre_process_page

    page = Page(title="Title", body="Body")
    options = _options(page_id="7", content_type="blogpost")

    pre_process_page(page, options, "", "", space_info=None)

    assert page.original_title == "Title"
    assert page.space == "TEST"
    assert page.page_id == "7"
    assert page.content_type == "blogpost"


def test_pre_process_page_defaults_parent_title_from_options():
    from mdfluence.sync import pre_process_page

    page = Page(title="Title", body="Body", parent_title=None)
    options = _options(parent_title="Parent")

    pre_process_page(page, options, "", "", space_info=None)

    assert page.parent_title == "Parent"


def test_pre_process_page_applies_preface_and_postface():
    from mdfluence.sync import pre_process_page

    page = Page(title="Title", body="BODY")
    options = _options()

    pre_process_page(page, options, "POST", "PRE", space_info=None)

    assert page.body == "PREBODYPOST"


def test_pre_process_page_does_not_prefix_title():
    from mdfluence.sync import pre_process_page

    page = Page(title="Title", body="Body", parent_title="Parent")
    options = _options(prefix="X")

    pre_process_page(page, options, "", "", space_info=None)

    assert page.title == "Title"
    assert page.parent_title == "Parent"


def test_default_parent_resolver_uses_options_parent_id():
    from mdfluence.sync import default_parent_resolver

    page = Page(title="T", body="B", parent_title=None)
    options = _options(parent_id="99")

    default_parent_resolver(page, space_info=None, options=options)

    assert page.parent_id == "99"


def test_default_parent_resolver_keeps_existing_parent_id():
    from mdfluence.sync import default_parent_resolver

    page = Page(title="T", body="B", parent_title=None, parent_id="existing")
    options = _options(parent_id="99")

    default_parent_resolver(page, space_info=None, options=options)

    assert page.parent_id == "existing"


def test_default_parent_resolver_top_level_uses_homepage():
    from mdfluence.sync import default_parent_resolver

    page = Page(title="T", body="B", parent_title=None)
    options = _options(top_level=True)
    space_info = SimpleNamespace(homepage=SimpleNamespace(id="home-1"))

    default_parent_resolver(page, space_info=space_info, options=options)

    assert page.parent_id == "home-1"


def test_validate_relative_links_raises_on_missing_target(tmp_path):
    from mdfluence.sync import RelativeLinkError, validate_relative_links

    page = Page(
        title="A",
        body="B",
        file_path=tmp_path / "a.md",
        relative_links=[_relative_link("missing.md")],
    )

    with pytest.raises(RelativeLinkError):
        validate_relative_links([page], {})


def test_validate_relative_links_passes_when_target_present(tmp_path):
    from mdfluence.sync import validate_relative_links

    target = (tmp_path / "b.md").resolve()
    page = Page(
        title="A",
        body="B",
        file_path=tmp_path / "a.md",
        relative_links=[_relative_link("b.md")],
    )

    # Should not raise.
    validate_relative_links([page], {target: None})


def test_build_document_path_to_page_map_indexes_by_resolved_path(tmp_path):
    from mdfluence.sync import build_document_path_to_page_map

    file_page = Page(title="A", body="B", file_path=tmp_path / "a.md")
    dir_page = Page(title="Dir", body="")  # No file_path -> skipped.

    result = build_document_path_to_page_map([file_page, dir_page])

    assert result == {(tmp_path / "a.md").resolve(): None}


def test_update_pages_with_relative_links_rewrites_body_and_upserts(mocker, tmp_path):
    from mdfluence.sync import NullReporter, update_pages_with_relative_links

    confluence = mocker.Mock()
    confluence.get_url.return_value = "https://conf/x"
    upsert = mocker.patch("mdfluence.sync.upsert_page")

    target = (tmp_path / "b.md").resolve()
    link = _relative_link("b.md")
    page = Page(
        title="A",
        body=f"before {link.replacement} after",
        file_path=tmp_path / "a.md",
        relative_links=[link],
    )
    page.original_title = "A"
    options = _options(enable_relative_links=True)

    update_pages_with_relative_links(
        options,
        confluence,
        [page],
        {target: mocker.sentinel.conf_page},
        NullReporter(),
    )

    assert "https://conf/x" in page.body
    upsert.assert_called_once()


# --- Ask 2.4: public publish() with hooks ----------------------------------------


def _confluence_mock(mocker):
    confluence = mocker.Mock()
    confluence.get_space.return_value = SimpleNamespace(
        homepage=SimpleNamespace(id="home-1")
    )
    confluence.get_url.return_value = "https://conf/x"
    return confluence


def test_publish_upserts_each_page_once(mocker):
    from mdfluence.sync import publish

    confluence = _confluence_mock(mocker)
    upsert = mocker.patch("mdfluence.sync.upsert_page")
    pages = [Page(title="A", body="a"), Page(title="B", body="b")]

    publish(confluence, pages, _options())

    assert upsert.call_count == 2


def test_publish_calls_prepare_pages_once_before_loop(mocker):
    from mdfluence.sync import publish

    confluence = _confluence_mock(mocker)
    mocker.patch("mdfluence.sync.upsert_page")
    prepare_pages = mocker.Mock()
    pages = [Page(title="A", body="a"), Page(title="B", body="b")]

    publish(confluence, pages, _options(), prepare_pages=prepare_pages)

    prepare_pages.assert_called_once()
    called_pages, called_space = prepare_pages.call_args.args
    assert called_pages is pages
    assert called_space is confluence.get_space.return_value


def test_publish_parent_resolver_called_per_page_and_can_set_parent_id(mocker):
    from mdfluence.sync import publish

    confluence = _confluence_mock(mocker)
    mocker.patch("mdfluence.sync.upsert_page")
    pages = [Page(title="A", body="a"), Page(title="B", body="b")]

    def resolver(page, space_info):
        page.parent_id = "resolved"

    publish(confluence, pages, _options(), parent_resolver=resolver)

    assert all(p.parent_id == "resolved" for p in pages)


def test_publish_uses_default_parent_resolver_when_hook_none(mocker):
    from mdfluence.sync import publish

    confluence = _confluence_mock(mocker)
    mocker.patch("mdfluence.sync.upsert_page")
    default_resolver = mocker.patch("mdfluence.sync.default_parent_resolver")
    pages = [Page(title="A", body="a")]

    publish(confluence, pages, _options())

    default_resolver.assert_called_once()


def test_publish_dry_run_performs_no_upserts(mocker):
    from mdfluence.sync import publish

    confluence = _confluence_mock(mocker)
    upsert = mocker.patch("mdfluence.sync.upsert_page")
    pages = [Page(title="A", body="a")]

    publish(confluence, pages, _options(dry_run=True))

    upsert.assert_not_called()


def test_publish_propagates_relative_link_error(mocker, tmp_path):
    from mdfluence.sync import RelativeLinkError, publish

    confluence = _confluence_mock(mocker)
    mocker.patch("mdfluence.sync.upsert_page")
    page = Page(
        title="A",
        body="b",
        file_path=tmp_path / "a.md",
        relative_links=[_relative_link("missing.md")],
    )

    with pytest.raises(RelativeLinkError):
        publish(confluence, [page], _options(enable_relative_links=True))


# --- Ask 2.6: public library surface ---------------------------------------------


def test_public_surface_is_importable():
    from mdfluence import (
        MinimalConfluence,
        NullReporter,
        Page,
        PublishOptions,
        Reporter,
        apply_title_prefix,
        get_pages_from_directory,
        publish,
    )

    assert all(
        obj is not None
        for obj in (
            MinimalConfluence,
            NullReporter,
            Page,
            PublishOptions,
            Reporter,
            apply_title_prefix,
            get_pages_from_directory,
            publish,
        )
    )
