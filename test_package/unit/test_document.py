from pathlib import Path

import mdfluence.document as doc
from test_package.utils import FakePage

ROOT_GITIGNORE = """.git
"""


def test_page_get_content_hash():
    p = doc.Page(title="test title", body="test content")

    assert p.get_content_hash() == "1eebdf4fdc9fc7bf283031b93f9aef3338de9052"


def test_get_pages_from_directory(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_dir("/root-folder/empty-dir")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"))
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(title="child", file_path=None, parent_title="parent"),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_use_pages(fs):
    fs.create_file("/root-folder/.gitignore", contents=ROOT_GITIGNORE)
    fs.create_dir("/root-folder/.git")
    fs.create_dir("/root-folder/.git/refs")
    fs.create_file("/root-folder/.git/refs/test.md")
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_dir("/root-folder/empty-dir")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), use_pages_file=True, enable_relative_links=True
    )
    print(result)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(title="child", file_path=None, parent_title="parent"),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(title="parent", file_path=None, parent_title=None),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_collapse_single_pages_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), collapse_single_pages=True
    )
    assert result == [
        FakePage(
            title="parent",
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent",
        ),
    ]


def test_get_pages_from_directory_skip_empty(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), skip_empty=True)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_skip_empty_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), skip_empty=True)
    assert result == [
        FakePage(
            title="child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty(fs):
    fs.create_file("/root-folder/root-folder-file.md")
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="root-folder-file",
            file_path=Path("/root-folder/root-folder-file.md", parent_title=None),
        ),
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_collapse_empty_no_non_empty_parent(fs):
    fs.create_file("/root-folder/parent/child/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), collapse_empty=True)
    assert result == [
        FakePage(
            title="parent/child",
            file_path=None,
            parent_title=None,
        ),
        FakePage(
            title="child-file",
            file_path=Path("/root-folder/parent/child/child-file.md"),
            parent_title="parent/child",
        ),
    ]


def test_get_pages_from_directory_beautify_folders(fs):
    fs.create_file("/root-folder/ugly-folder/another_yucky_folder/child-file.md")

    result = doc.get_pages_from_directory(Path("/root-folder"), beautify_folders=True)
    assert result == [
        FakePage(
            title="Ugly folder",
        ),
        FakePage(
            title="Another yucky folder",
        ),
        FakePage(
            title="child-file",
            file_path=Path(
                "/root-folder/ugly-folder/another_yucky_folder/child-file.md"
            ),
            parent_title="Another yucky folder",
        ),
    ]


def test_get_pages_from_directory_with_pages_file_multi_level(fs):
    fs.create_file("/root-folder/sub-folder-a/some-page.md")
    fs.create_file("/root-folder/sub-folder-b/some-page.md")
    fs.create_file("/root-folder/sub-folder-a/.pages", contents='title: "Folder A"')
    fs.create_file("/root-folder/sub-folder-b/.pages", contents='title: "Folder B"')

    result = doc.get_pages_from_directory(Path("/root-folder"), use_pages_file=True)
    assert result == [
        FakePage(
            title="Folder A",
        ),
        FakePage(
            title="some-page",
            file_path=Path("/root-folder/sub-folder-a/some-page.md"),
            parent_title="Folder A",
        ),
        FakePage(
            title="Folder B",
        ),
        FakePage(
            title="some-page",
            file_path=Path("/root-folder/sub-folder-b/some-page.md"),
            parent_title="Folder B",
        ),
    ]


def test_get_pages_from_directory_with_pages_file_single_level(fs):
    fs.create_file("/root-folder/some-page.md")
    fs.create_file("/root-folder/.pages", contents='title: "Root folder"')

    result = doc.get_pages_from_directory(Path("/root-folder"), use_pages_file=True)
    assert result == [
        FakePage(
            title="Root folder",
        ),
        FakePage(
            title="some-page",
            file_path=Path("/root-folder/some-page.md"),
            parent_title="Root folder",
        ),
    ]


def test_get_document_frontmatter():
    source_markdown = """---
title: This is a title
labels:
  - label1
  - label2
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {
        "title": "This is a title",
        "labels": ["label1", "label2"],
        "frontmatter_end_line": 6,
    }


def test_get_document_frontmatter_only_first():
    source_markdown = """---
title: This is a title
---
# This is normal markdown content

---

With other triple dashes!

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {
        "title": "This is a title",
        "frontmatter_end_line": 3,
    }


def test_get_document_frontmatter_no_closing():
    source_markdown = """---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_document_frontmatter_extra_whitespace():
    source_markdown = """

---
title: This is a title
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_document_frontmatter_empty():
    source_markdown = """---
---
# This is normal markdown content

Yep.
"""

    assert doc.get_document_frontmatter(source_markdown.splitlines(keepends=True)) == {}


def test_get_pages_from_directory_skip_subtrees_wo_markdown(fs):
    """Subtrees without any markdown files are skipped entirely."""
    fs.create_file("/root-folder/docs/readme.md")
    fs.create_file("/root-folder/images/logo.png")
    fs.create_dir("/root-folder/images/icons")
    fs.create_file("/root-folder/images/icons/favicon.ico")
    fs.create_file("/root-folder/data/config.yaml")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), skip_subtrees_wo_markdown=True
    )
    assert result == [
        FakePage(title="docs", file_path=None, parent_title=None),
        FakePage(
            title="readme",
            file_path=Path("/root-folder/docs/readme.md"),
            parent_title="docs",
        ),
    ]


def test_get_pages_from_directory_skip_subtrees_wo_markdown_nested(fs):
    """A subtree with markdown deeply nested is kept, but sibling subtrees without
    markdown are pruned."""
    fs.create_file("/root-folder/a/b/c/deep.md")
    fs.create_file("/root-folder/a/b/other/data.txt")
    fs.create_file("/root-folder/empty-tree/sub/file.txt")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), skip_subtrees_wo_markdown=True
    )
    assert result == [
        FakePage(title="a", file_path=None, parent_title=None),
        FakePage(title="b", file_path=None, parent_title="a"),
        FakePage(title="c", file_path=None, parent_title="b"),
        FakePage(
            title="deep",
            file_path=Path("/root-folder/a/b/c/deep.md"),
            parent_title="c",
        ),
    ]


def test_get_pages_from_directory_skip_subtrees_wo_markdown_root_has_md(fs):
    """Root-level markdown files are still included; only subtrees without markdown
    are pruned."""
    fs.create_file("/root-folder/index.md")
    fs.create_file("/root-folder/no-md/data.csv")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), skip_subtrees_wo_markdown=True
    )
    assert result == [
        FakePage(
            title="index",
            file_path=Path("/root-folder/index.md"),
            parent_title=None,
        ),
    ]


def test_get_pages_from_directory_skip_subtrees_wo_markdown_all_empty(fs):
    """When no subtree contains markdown, nothing is returned."""
    fs.create_file("/root-folder/images/logo.png")
    fs.create_file("/root-folder/data/config.yaml")

    result = doc.get_pages_from_directory(
        Path("/root-folder"), skip_subtrees_wo_markdown=True
    )
    assert result == []


def test_get_pages_from_directory_skip_subtrees_wo_markdown_disabled(fs):
    """Without the flag, subtrees without markdown are still traversed and produce
    folder pages when they have subdirectories."""
    fs.create_file("/root-folder/docs/readme.md")
    fs.create_file("/root-folder/images/icons/favicon.ico")

    result_with = doc.get_pages_from_directory(
        Path("/root-folder"), skip_subtrees_wo_markdown=True
    )
    result_without = doc.get_pages_from_directory(
        Path("/root-folder"), skip_subtrees_wo_markdown=False
    )
    # With the flag, images/ subtree is excluded
    assert FakePage(title="images") not in result_with
    # Without the flag, images/ subtree is included as a folder page
    # (it has a subdirectory, so it gets a page entry)
    assert FakePage(title="images") in result_without
