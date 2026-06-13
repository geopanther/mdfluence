# Plan: Expose `mdfluence.sync` library surface for gitfluence

Status: not started. Two asks from gitfluence's API-design request.
Root cause: mdfluence only exposes orchestration through `main()`. Helpers exist but
are trapped in `__main__`, coupled to argparse `args` Namespace and `Md2cfTUI`.

**Working principle: TDD. Write the unit tests for each new exposure FIRST (red),
then implement until green. Tests precede implementation in every commit below.**

---

## Current state (verified)

- Orchestration helpers live in `mdfluence/__main__.py`, coupled to `args` + `Md2cfTUI`:
  - `pre_process_page` (~L546), `validate_relative_links`, `build_document_path_to_page_map`,
    `update_pages_with_relative_links` (~L615).
- `title_prefix` in `mdfluence/document.py:get_pages_from_directory` (L116, param L133) only
  feeds the **anchor map** via `parse_page` (L380). It does NOT prefix `page.title` /
  `page.parent_title`. Those are prefixed later by f-strings in `pre_process_page`.
- Prefix format identical in both places: `f"{prefix} - {title}"` → safe to unify.
- `Md2cfTUI` (mdfluence/tui.py) methods used by loop: `start_item_task`,
  `set_item_progress_label`, `set_item_finished_text`, `set_item_finished_text_from_result`,
  `tick_item_progress`, `tick_global_progress`, `reset_item_task`, `__enter__`/`__exit__`.
- Tests live in `test_package/` (pytest, pytest-mock, pyfakefs, requests-mock).

---

## Ask 1 — Option B: collection fully realizes the prefix

Goal: after `get_pages_from_directory(..., title_prefix=ctx.prefix)`, pages are upsert-ready
(title + parent_title + anchors all prefixed). No post-processing in gitfluence.

### 1.1 (TEST FIRST) `apply_title_prefix(page, prefix)` — args-free helper (escape hatch A)

- Tests in `test_package/unit/test_sync.py`:
  - prefixes `title` and `parent_title` when prefix set.
  - no-op when prefix is None/empty.
  - leaves `parent_title=None` untouched.
- Impl in `mdfluence/sync.py`:

```python
def apply_title_prefix(page: Page, prefix: str | None) -> None:
    if not prefix:
        return
    if page.title is not None:
        page.title = f"{prefix} - {page.title}"
    if page.parent_title is not None:
        page.parent_title = f"{prefix} - {page.parent_title}"
```

### 1.2 (TEST FIRST) collection realizes prefix (Option B)

- Tests in `test_package/unit/test_document.py`: with `title_prefix="X"`, returned pages
  (both file pages and folder/section pages) have prefixed `title` + `parent_title`;
  anchors already prefixed (existing behavior) stay consistent.
- Impl: in `get_pages_from_directory`, apply prefix to each page at the END of collection
  (after `processed_page.parent_title = parent_page_title`, and for the folder `Page(...)`),
  because title is only final after frontmatter override / `file_path.stem` fallback.

### 1.3 remove duplicate prefixing in `pre_process_page`

- Delete the two `if args.prefix: f"{...}"` blocks. Prefix now applied once, in collection.

### 1.4 (TEST FIRST) CLI `--title` edge case

- Test: `--title` override after collection re-applies prefix (does not lose it).
- Impl: in `collect_pages_to_upload`, call `apply_title_prefix(page, options.prefix)` right
  after each `--title` override (stdin + single-file paths).

---

## Ask 2 — `mdfluence.sync` library module with hooks

### 2.1 (TEST FIRST) `PublishOptions` dataclass

- Test: construct with defaults; required `space`; round-trips values.
- Impl in `mdfluence/sync.py`. Fields = every `args.*` the helpers + loop read:
  `space, content_type="page", page_id, parent_title, parent_id, top_level=False,
prefix, message, minor_edit=False, only_changed=False, replace_all_labels=False,
dry_run=False, debug=False, enable_relative_links=False,
ignore_relative_link_errors=False, preface_markup="", postface_markup=""`.

### 2.2 (TEST FIRST) `Reporter` protocol + `NullReporter`

- Test: `NullReporter` satisfies protocol, all methods no-op, works as context manager,
  `publish()` runs with default `NullReporter` (no `rich` needed).
- Impl: `Reporter` Protocol with the 7 methods + `__enter__`/`__exit__`; `NullReporter`
  all-`pass`. `Md2cfTUI` already satisfies the shape (declare it implements `Reporter`).

### 2.3 (TEST FIRST) move the four helpers into `mdfluence/sync.py`

- Update existing unit tests that import helpers from `__main__` → `mdfluence.sync`.
- Refactors:
  - `args` → `options: PublishOptions`; `tui` → `reporter: Reporter`.
  - `validate_relative_links`: raise typed `RelativeLinkError` instead of
    `error_console.log` + `sys.exit(1)` (library must not exit). CLI catches → exits.
  - `pre_process_page`: drop prefix f-strings (Ask 1); extract top_level/homepage parent
    logic into `default_parent_resolver(page, space_info, options)` (overridable).

### 2.4 (TEST FIRST) public `publish()` with hooks

- Tests (requests-mock / mocks):
  - happy path upserts each page once.
  - `prepare_pages(pages, space_info)` called exactly once before loop.
  - `parent_resolver(page, space_info)` called per page; can set `page.parent_id`.
  - default parent resolver used when hook is None.
  - relative-link 2-pass still runs when enabled; `RelativeLinkError` propagates.
  - `dry_run` performs no upserts.
- Signature:

```python
def publish(confluence, pages, options, reporter=None,
            prepare_pages=None, parent_resolver=None) -> None: ...
```

- Body = today's `main()` loop minus argparse/auth/title-collision/attachment-existence
  checks (stay CLI-side / small reusable validators):
  1. `reporter = reporter or NullReporter()`
  2. `space_info = confluence.get_space(options.space, additional_expansions=["homepage"])`
  3. build path→page map + validate links if enabled
  4. `if prepare_pages: prepare_pages(pages, space_info)` (one-time tree setup)
  5. `with reporter:` loop: `pre_process_page` → `(parent_resolver or default_parent_resolver)`
     → `upsert_page` → attachments via `upsert_attachment` → record uploaded
  6. 2-pass `update_pages_with_relative_links`

### 2.5 thin out `__main__.main()`

- `main()`: parse args → CLI validations → preface/postface markup → `MinimalConfluence`
  → build `PublishOptions` from args → `collect_pages_to_upload(args)`
  → `publish(confluence, pages, options, reporter=Md2cfTUI(pages))`.
  Catch `RelativeLinkError`/`HTTPError` → `error_console` + `sys.exit(1)`.

### 2.6 (TEST FIRST) export public surface

- Test: `from mdfluence import publish, PublishOptions, Reporter, NullReporter,
apply_title_prefix, Page, MinimalConfluence, get_pages_from_directory`.
- Impl: re-export in `mdfluence/__init__.py`.

---

## Docs updates (required)

### CHANGELOG.md — under `## Unreleased`

- **Added:** `### Added` — "Public `mdfluence.sync` library API (`publish()` with
  `prepare_pages` + `parent_resolver` hooks, `PublishOptions`, `Reporter`/`NullReporter`,
  `apply_title_prefix`) for embedding mdfluence as a library."
- **Changed:** title prefix now applied during directory collection (title + parent_title +
  anchors) instead of only at upload time. CLI behavior unchanged.
- Note internal move of orchestration helpers out of `__main__` (no CLI behavior change).

### README.md — add a "Using mdfluence as a library" section

- After the API/Features intro (README mentions "tool and library" L5, "embedded
  micro-implementation" L10). Add short example:
  ```python
  from mdfluence import (MinimalConfluence, PublishOptions, publish,
                         get_pages_from_directory)
  conf = MinimalConfluence(host=..., token=...)
  pages = get_pages_from_directory(Path("docs"), title_prefix="MyPrefix")
  publish(conf, pages, PublishOptions(space="TEST"))
  ```
- Mention `prepare_pages` / `parent_resolver` hooks for custom parenting/hierarchy.

### CONTRIBUTING.md — Project structure section (L52)

- Add `mdfluence/sync.py  # public orchestration/publish API` to the structure list.
- Note that orchestration helpers moved from `__main__.py` to `sync.py`.

---

## Commit / PR breakdown (atomic, tests-first within each)

1. `feat(sync): add apply_title_prefix + realize prefix in collection` (Ask 1; tests first).
2. `refactor(sync): add PublishOptions dataclass + Reporter protocol/NullReporter` (2.1/2.2).
3. `refactor(sync): move orchestration helpers from __main__ to mdfluence.sync`
   (2.3; raise `RelativeLinkError` instead of `sys.exit`; update test imports).
4. `feat(sync): public publish() with prepare_pages + parent_resolver hooks` (2.4/2.5).
5. `feat: export stable library surface in __init__` (2.6).
6. `docs: document library API (README, CHANGELOG, CONTRIBUTING)`.

## Verification

- `pytest` green at each commit; no `sys.exit` reachable from `mdfluence.sync`.
- CLI behavior unchanged (existing functional test `test_full_rendering.py` still passes).
- Respect pre-commit hooks; do not skip; fix findings with separate conventional commits.
