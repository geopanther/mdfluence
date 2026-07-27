"""Public orchestration/publish API for embedding mdfluence as a library."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)

import rich.text

from mdfluence.console_output import error_console
from mdfluence.document import apply_title_prefix
from mdfluence.upsert import upsert_attachment, upsert_page

if TYPE_CHECKING:
    from mdfluence.api import MinimalConfluence
    from mdfluence.document import Page


__all__ = [
    "NullReporter",
    "PublishOptions",
    "RelativeLinkError",
    "Reporter",
    "apply_title_prefix",
    "build_document_path_to_page_map",
    "default_parent_resolver",
    "pre_process_page",
    "publish",
    "update_pages_with_relative_links",
    "validate_relative_links",
]


class RelativeLinkError(Exception):
    """Raised when a page has an unresolvable relative link.

    The library raises this instead of exiting so that callers (including the
    CLI) can decide how to handle the error.
    """


@dataclass
class PublishOptions:
    """Options controlling a :func:`publish` run.

    Mirrors the CLI argument surface so orchestration helpers no longer depend
    on an argparse ``Namespace``.
    """

    space: str
    content_type: str = "page"
    page_id: Optional[str] = None
    parent_title: Optional[str] = None
    parent_id: Optional[str] = None
    top_level: bool = False
    prefix: Optional[str] = None
    message: Optional[str] = None
    minor_edit: bool = False
    only_changed: bool = False
    replace_all_labels: bool = False
    dry_run: bool = False
    debug: bool = False
    enable_relative_links: bool = False
    ignore_relative_link_errors: bool = False
    preface_markup: str = ""
    postface_markup: str = ""


@runtime_checkable
class Reporter(Protocol):
    """Progress-reporting surface used by :func:`publish`.

    ``Md2cfTUI`` implements this shape. Library callers that do not want any
    output can use :class:`NullReporter`.
    """

    def start_item_task(self, item_name) -> None: ...

    def set_item_progress_label(self, item_name, label: str) -> None: ...

    def set_item_finished_text(
        self, item_name, finished_text: "rich.text.Text"
    ) -> None: ...

    def set_item_finished_text_from_result(self, item_name, upsert_result) -> None: ...

    def tick_item_progress(self, item_name) -> None: ...

    def tick_global_progress(self) -> None: ...

    def reset_item_task(self, item_name, total: int) -> None: ...

    def __enter__(self) -> "Reporter": ...

    def __exit__(self, *args, **kwargs) -> None: ...


class NullReporter:
    """A :class:`Reporter` that does nothing. Default for :func:`publish`."""

    def start_item_task(self, item_name) -> None:
        pass

    def set_item_progress_label(self, item_name, label: str) -> None:
        pass

    def set_item_finished_text(
        self, item_name, finished_text: "rich.text.Text"
    ) -> None:
        pass

    def set_item_finished_text_from_result(self, item_name, upsert_result) -> None:
        pass

    def tick_item_progress(self, item_name) -> None:
        pass

    def tick_global_progress(self) -> None:
        pass

    def reset_item_task(self, item_name, total: int) -> None:
        pass

    def __enter__(self) -> "NullReporter":
        return self

    def __exit__(self, *args, **kwargs) -> None:
        pass


def pre_process_page(
    page: "Page",
    options: PublishOptions,
    postface_markup: str,
    preface_markup: str,
    space_info: Any = None,
) -> None:
    """Populate page metadata from ``options`` and wrap the body markup.

    Parent resolution (parent id / top-level homepage) is delegated to a
    parent resolver so it can be overridden by library callers.
    """
    page.original_title = page.title
    page.space = options.space
    page.page_id = options.page_id
    page.content_type = options.content_type

    if page.parent_title is None:  # This only happens for top level pages
        # If the option is not supplied this leaves the parent_title as None,
        # which is fine.
        page.parent_title = options.parent_title

    if preface_markup:
        page.body = preface_markup + page.body

    if postface_markup:
        page.body = page.body + postface_markup


def default_parent_resolver(
    page: "Page", space_info: Any, options: PublishOptions
) -> None:
    """Resolve a page's ``parent_id`` using the options and space homepage."""
    if page.parent_title is None:
        page.parent_id = (
            page.parent_id or options.parent_id
        )  # This can still end up being None -- a top level page.

    # If we want to *move* a page back to the top space, we need to make it
    # a child of the space's home page.
    if options.top_level and page.parent_title is None and page.parent_id is None:
        page.parent_id = space_info.homepage.id


def validate_relative_links(
    pages_to_upload: List["Page"], path_to_page: Dict[Path, Any]
) -> None:
    """Raise :class:`RelativeLinkError` if any relative link target is missing."""
    invalid_links = False
    for page in pages_to_upload:
        if page.file_path is None:
            continue
        for link_data in page.relative_links:
            link_absolute_path = (
                page.file_path.parent / Path(link_data.path)
            ).resolve()
            if link_absolute_path not in path_to_page:
                error_console.log(
                    f"Page {page.file_path} has a relative link to {link_data.path}"
                    ", which is not in the list of pages to be uploaded.\n"
                )
                invalid_links = True
    if invalid_links:
        raise RelativeLinkError(
            "Some of the pages to be uploaded have invalid relative links."
        )


def build_document_path_to_page_map(
    pages_to_upload: List["Page"],
) -> Dict[Path, Any]:
    """Index uploadable pages by their resolved file path."""
    path_to_page: Dict[Path, Any] = dict()
    for page in pages_to_upload:
        # A page might not have a file_path (e.g. if it represents a directory).
        if page.file_path is None:
            continue
        # Will be filled in later with the page returned by upsert.
        path_to_page[page.file_path.resolve()] = None
    return path_to_page


def update_pages_with_relative_links(
    options: PublishOptions,
    confluence: "MinimalConfluence",
    pages_to_upload: List["Page"],
    path_to_page: Dict[Path, Any],
    reporter: Reporter,
) -> None:
    """Second pass: rewrite relative links to Confluence URLs and re-upsert."""
    something_went_wrong = False
    error: Exception = Exception()
    for page in pages_to_upload:
        if page.file_path is None:
            # Skip pages without a file_path
            # (e.g. section pages representing directories).
            continue

        page_modified = False
        for link_data in page.relative_links:
            try:
                link_absolute_path = (
                    page.file_path.parent / Path(link_data.path)
                ).resolve()
                page_on_confluence = path_to_page[link_absolute_path]
            except KeyError:
                if options.ignore_relative_link_errors:
                    page.body = page.body.replace(
                        link_data.replacement,
                        link_data.escaped_original
                        + (("#" + link_data.fragment) if link_data.fragment else ""),
                    )
                    continue
                else:
                    error_console.log(
                        f"Page {page.file_path} has a relative link to {link_data.path}"
                        ", which was not uploaded correctly.\n"
                    )
                    break

            # In a dry run we don't actually have page URLs since we never
            # upload anything.
            if not options.dry_run:
                page.body = page.body.replace(
                    link_data.replacement,
                    confluence.get_url(page_on_confluence)
                    + (("#" + link_data.fragment) if link_data.fragment else ""),
                )
            page_modified = True

        if page_modified:
            reporter.reset_item_task(page.original_title, total=1)
            reporter.set_item_progress_label(
                page.original_title, "Updating relative links"
            )
            reporter.start_item_task(page.original_title)
            if not options.dry_run:
                try:
                    upsert_page(
                        confluence=confluence,
                        message=options.message,
                        page=page,
                        only_changed=options.only_changed,
                        replace_all_labels=options.replace_all_labels,
                        minor_edit=True,
                    )
                except Exception as e:
                    error = e
                    something_went_wrong = True

                if not something_went_wrong:
                    reporter.set_item_finished_text(
                        page.original_title,
                        rich.text.Text.from_markup(
                            "[green]:heavy_check_mark-emoji: Updated "
                            "(updated relative links)"
                        ),
                    )
                else:
                    reporter.set_item_progress_label(
                        page.original_title,
                        "[red]:x: Error while updating relative links",
                    )
            else:
                reporter.set_item_finished_text(
                    page.original_title,
                    rich.text.Text.from_markup(
                        "[yellow]Not updating relative links (dry run)"
                    ),
                )

            reporter.set_item_progress_label(page.original_title, "")
            reporter.tick_item_progress(page.original_title)

        if something_went_wrong:
            raise error


def publish(
    confluence: "MinimalConfluence",
    pages: List["Page"],
    options: PublishOptions,
    reporter: Optional[Reporter] = None,
    prepare_pages: Optional[Callable[[List["Page"], Any], None]] = None,
    parent_resolver: Optional[Callable[["Page", Any], None]] = None,
) -> None:
    """Publish ``pages`` to Confluence.

    :param confluence: an authenticated :class:`MinimalConfluence` client.
    :param pages: the pages to upload (e.g. from ``get_pages_from_directory``).
    :param options: a :class:`PublishOptions` describing the run.
    :param reporter: progress reporter; defaults to :class:`NullReporter`.
    :param prepare_pages: optional one-time hook ``(pages, space_info)`` called
        before the upload loop, e.g. to build a page tree.
    :param parent_resolver: optional per-page hook ``(page, space_info)`` that
        can set ``page.parent_id``. Defaults to :func:`default_parent_resolver`.
    """
    reporter = reporter or NullReporter()

    space_info = confluence.get_space(options.space, additional_expansions=["homepage"])

    path_to_page: Dict[Path, Any] = dict()
    if options.enable_relative_links:
        path_to_page = build_document_path_to_page_map(pages)
        if not options.ignore_relative_link_errors:
            validate_relative_links(pages, path_to_page)

    if prepare_pages is not None:
        prepare_pages(pages, space_info)

    with reporter:
        for page in pages:
            pre_process_page(
                page,
                options,
                options.postface_markup,
                options.preface_markup,
                space_info,
            )
            if parent_resolver is not None:
                parent_resolver(page, space_info)
            else:
                default_parent_resolver(page, space_info, options)

            reporter.start_item_task(page.original_title)
            reporter.set_item_progress_label(page.original_title, "Upserting")
            final_page = None
            upsert_page_result = None
            if not options.dry_run:
                upsert_page_result = upsert_page(
                    confluence=confluence,
                    message=options.message,
                    page=page,
                    only_changed=options.only_changed,
                    replace_all_labels=options.replace_all_labels,
                    minor_edit=options.minor_edit,
                )
                final_page = upsert_page_result.response

            if page.attachments:
                reporter.set_item_progress_label(
                    page.original_title, "Processing attachments"
                )
                for attachment in page.attachments:
                    attachment_identifier = f"{page.original_title} {attachment}"
                    reporter.start_item_task(attachment_identifier)
                    if not options.dry_run:
                        upsert_attachment_result = upsert_attachment(
                            confluence=confluence,
                            attachment=attachment,
                            existing_page=final_page,
                            message=options.message,
                            only_changed=options.only_changed,
                            page=page,
                        )
                        reporter.set_item_finished_text_from_result(
                            attachment_identifier, upsert_attachment_result
                        )
                    else:
                        reporter.set_item_finished_text(
                            attachment_identifier,
                            rich.text.Text.from_markup("[yellow]Skipped (dry run)"),
                        )
                    reporter.set_item_progress_label(attachment_identifier, "")
                    reporter.tick_item_progress(attachment_identifier)
                    reporter.tick_item_progress(page.original_title)
                    reporter.tick_global_progress()

            if page.file_path is not None and options.enable_relative_links:
                path_to_page[page.file_path.resolve()] = final_page

            reporter.set_item_progress_label(page.original_title, "")
            if not options.dry_run:
                reporter.set_item_finished_text_from_result(
                    page.original_title, upsert_page_result
                )
            else:
                reporter.set_item_finished_text(
                    page.original_title,
                    rich.text.Text.from_markup("[yellow]Skipped (dry run)"),
                )

            reporter.tick_item_progress(page.original_title)
            reporter.tick_global_progress()

    if options.enable_relative_links:
        update_pages_with_relative_links(
            options, confluence, pages, path_to_page, reporter
        )
